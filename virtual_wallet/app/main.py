from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from .aml_adapter import AMLDecision, check_tx
from .db import DATA_DIR, get_session, init_db
from .generator import generate_transactions, generate_wallets
from .models import Alert, Transaction, Wallet

app = FastAPI(
    title="Wallet Firewall API",
    description="Virtual wallet transaction system with AML risk analysis and enforcement",
    version="0.2.0",
)


BASE_DIR = Path(__file__).resolve().parent
app.mount("/ui", StaticFiles(directory=str(BASE_DIR / "ui")), name="ui")


class WalletCreate(BaseModel):
    wallet_id: Optional[str] = None
    balance: float = Field(0, ge=0)
    tag: str = Field("NORMAL", min_length=3, max_length=16)


class TransferRequest(BaseModel):
    tx_id: Optional[str] = None
    from_wallet: str
    to_wallet: str
    amount: float = Field(..., gt=0)
    policy: str = Field("WARN", min_length=4, max_length=8)


class DatasetRequest(BaseModel):
    scenario: str = Field("normal", min_length=3, max_length=24)
    n: int = Field(200, ge=10, le=2000)
    persist: bool = True


class SeedRequest(BaseModel):
    count: int = Field(6, ge=2, le=50)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    with open(BASE_DIR / "ui" / "index.html", "r", encoding="utf-8") as handle:
        return HTMLResponse(handle.read())


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/stats")
def stats(session: Session = Depends(get_session)) -> Dict[str, int]:
    return {
        "wallets": len(session.exec(select(Wallet)).all()),
        "transactions": len(session.exec(select(Transaction)).all()),
        "alerts": len(session.exec(select(Alert)).all()),
    }


def _random_wallet_id() -> str:
    return f"0x{uuid4().hex[:10]}"


def _aml_to_dict(aml: AMLDecision) -> Dict[str, object]:
    """Normalize AMLDecision(dataclass) into a JSON-friendly dict for UI."""
    return {
        "request_id": aml.request_id,
        "risk_score": aml.risk_score,
        "risk_level": aml.risk_level,
        "decision": aml.decision,
        "reason_codes": aml.reason_codes,
        "model_votes": aml.model_votes,
    }


@app.post("/api/wallets")
def create_wallet(payload: WalletCreate, session: Session = Depends(get_session)) -> Dict[str, Wallet]:
    wallet_id = payload.wallet_id or _random_wallet_id()
    if session.get(Wallet, wallet_id):
        raise HTTPException(status_code=409, detail="wallet already exists")

    wallet = Wallet(wallet_id=wallet_id, balance=payload.balance, tag=payload.tag.upper())
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return {"wallet": wallet}


@app.post("/api/wallets/seed")
def seed_wallets(payload: SeedRequest, session: Session = Depends(get_session)) -> Dict[str, List[Wallet]]:
    created: List[Wallet] = []
    for wallet in generate_wallets(payload.count):
        if session.get(Wallet, wallet["wallet_id"]):
            continue
        item = Wallet(**wallet)
        session.add(item)
        created.append(item)
    session.commit()
    return {"wallets": created}


@app.get("/api/wallets")
def list_wallets(session: Session = Depends(get_session)) -> Dict[str, List[Wallet]]:
    wallets = session.exec(select(Wallet).order_by(Wallet.created_at.desc())).all()
    return {"wallets": wallets}


@app.post("/api/transfer")
def transfer(payload: TransferRequest, session: Session = Depends(get_session)) -> Dict[str, object]:
    sender = session.get(Wallet, payload.from_wallet)
    receiver = session.get(Wallet, payload.to_wallet)

    if not sender:
        raise HTTPException(status_code=404, detail="sender wallet not found")
    if sender.balance < payload.amount:
        raise HTTPException(status_code=400, detail="insufficient balance")

    now = datetime.utcnow()
    tx_id = payload.tx_id or f"tx_{int(datetime.utcnow().timestamp())}"

    # === AML check via Wallet Firewall backend (adapter) ===
    aml = check_tx(
        chain="wallet",
        to_address=payload.to_wallet,
        amount_usdt=payload.amount,
        from_address=payload.from_wallet,  # optional
    )

    aml_dict = _aml_to_dict(aml)
    decision = aml.decision
    risk_level = aml.risk_level
    risk_score = aml.risk_score
    reasons = aml.reason_codes

    # --- BLOCK ---
    if decision == "BLOCK":
        session.add(
            Alert(
                tx_id=tx_id,
                level="CRITICAL",
                message=f"BLOCKED by AML: {','.join(reasons)}" if reasons else "BLOCKED by AML",
                risk_score=risk_score,
            )
        )
        session.commit()
        return {"status": "blocked", "aml": aml_dict}

    # --- REQUIRE_CONFIRM ---
    if decision == "REQUIRE_CONFIRM":
        session.add(
            Alert(
                tx_id=tx_id,
                level="WARN",
                message=f"REQUIRE_CONFIRM: {','.join(reasons)}" if reasons else "REQUIRE_CONFIRM",
                risk_score=risk_score,
            )
        )
        session.commit()
        return {"status": "require_confirm", "aml": aml_dict, "confirm_token": tx_id}

    # --- ALLOW => execute transaction ---
    tx = Transaction(
        tx_id=tx_id,
        from_wallet=payload.from_wallet,
        to_wallet=payload.to_wallet,
        amount=payload.amount,
        risk_score=risk_score,
        risk_label=risk_level,
        reason=";".join(reasons) if reasons else "normal_pattern",
        created_at=now,
    )
    session.add(tx)

    sender.balance -= payload.amount
    if receiver:
        receiver.balance += payload.amount

    # optional: flag as alert even if allowed but risk level high/medium
    if risk_level in {"HIGH", "MEDIUM"}:
        level = "CRITICAL" if risk_level == "HIGH" else "WARN"
        msg = f"Suspicious transaction detected ({risk_level}): {tx.reason}"
        session.add(Alert(tx_id=tx.tx_id, level=level, message=msg, risk_score=risk_score))

    session.commit()
    session.refresh(tx)
    return {"status": "approved", "tx": tx, "aml": aml_dict}


@app.get("/api/transactions")
def list_transactions(
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
) -> Dict[str, List[Transaction]]:
    txs = session.exec(select(Transaction).order_by(Transaction.created_at.desc()).limit(limit)).all()
    return {"transactions": txs}


# ✅ NEW: true transaction detail by tx_id
@app.get("/api/transactions/{tx_id}")
def get_transaction(tx_id: str, session: Session = Depends(get_session)) -> Dict[str, object]:
    tx = session.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction not found")
    return {"tx": tx}


@app.get("/api/alerts")
def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> Dict[str, List[Alert]]:
    alerts = session.exec(select(Alert).order_by(Alert.created_at.desc()).limit(limit)).all()
    return {"alerts": alerts}


@app.get("/api/transactions/{tx_id}")
def get_transaction(tx_id: str, session: Session = Depends(get_session)) -> Dict[str, object]:
    tx = session.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="tx not found")
    return {"tx": tx}


@app.get("/api/alerts/{tx_id}")
def get_alerts_by_tx(tx_id: str, session: Session = Depends(get_session)) -> Dict[str, List[Alert]]:
    alerts = session.exec(
        select(Alert).where(Alert.tx_id == tx_id).order_by(Alert.created_at.desc())
    ).all()
    return {"alerts": alerts}



# ✅ NEW: alerts filtered by tx_id (for Transaction Detail / Intercepts drill-down)
@app.get("/api/alerts/by-tx/{tx_id}")
def get_alerts_by_tx(tx_id: str, session: Session = Depends(get_session)) -> Dict[str, List[Alert]]:
    alerts = session.exec(
        select(Alert).where(Alert.tx_id == tx_id).order_by(Alert.created_at.desc())
    ).all()
    return {"alerts": alerts}


@app.post("/api/dataset/generate")
def generate_dataset(payload: DatasetRequest, session: Session = Depends(get_session)) -> JSONResponse:
    wallets = session.exec(select(Wallet)).all()
    wallet_ids = [wallet.wallet_id for wallet in wallets]
    if len(wallet_ids) < 2:
        raise HTTPException(status_code=400, detail="create at least 2 wallets first")

    rows = generate_transactions(wallet_ids, scenario=payload.scenario, n=payload.n)
    rows.sort(key=lambda item: item["timestamp"])

    out_path = DATA_DIR / f"synthetic_{payload.scenario}_{int(datetime.utcnow().timestamp())}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "tx_id",
                "from_wallet",
                "to_wallet",
                "amount",
                "timestamp",
                "label_hint",
                "risk_score",
                "risk_label",
                "reason",
            ]
        )

        for row in rows:
            sender = session.get(Wallet, row["from_wallet"])
            receiver = session.get(Wallet, row["to_wallet"])

            aml = check_tx(
                chain="wallet",
                to_address=row["to_wallet"],
                amount_usdt=row["amount"],
                from_address=row.get("from_wallet"),
            )

            # persist to DB if requested
            if payload.persist:
                tx = Transaction(
                    tx_id=row["tx_id"],
                    from_wallet=row["from_wallet"],
                    to_wallet=row["to_wallet"],
                    amount=row["amount"],
                    created_at=row["timestamp"],
                    risk_score=aml.risk_score,
                    risk_label=aml.risk_level,
                    reason=";".join(aml.reason_codes) if aml.reason_codes else "normal_pattern",
                )
                session.add(tx)

                if sender:
                    sender.balance -= row["amount"]
                if receiver:
                    receiver.balance += row["amount"]

                if aml.risk_level in {"HIGH", "MEDIUM"}:
                    level = "CRITICAL" if aml.risk_level == "HIGH" else "WARN"
                    msg = f"Dataset transaction flagged ({aml.risk_level}): {tx.reason}"
                    session.add(Alert(tx_id=row["tx_id"], level=level, message=msg, risk_score=aml.risk_score))

            writer.writerow(
                [
                    row["tx_id"],
                    row["from_wallet"],
                    row["to_wallet"],
                    row["amount"],
                    row["timestamp"].isoformat(),
                    row["label_hint"],
                    aml.risk_score,
                    aml.risk_level,
                    ";".join(aml.reason_codes) if aml.reason_codes else "normal_pattern",
                ]
            )

    if payload.persist:
        session.commit()

    return JSONResponse(
        {
            "ok": True,
            "file": out_path.name,
            "rows": len(rows),
            "scenario": payload.scenario,
            "persisted": payload.persist,
        }
    )


@app.get("/api/dataset/download/{filename}")
def download_dataset(filename: str) -> FileResponse:
    file_path = DATA_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(str(file_path), media_type="text/csv", filename=filename)


@app.post("/api/transfer/confirm")
def confirm_transfer(payload: dict, session: Session = Depends(get_session)) -> Dict[str, str]:
    tx_id = payload.get("confirm_token")
    if not tx_id:
        raise HTTPException(status_code=400, detail="confirm_token required")

    # still placeholder: you can implement pending transaction storage later
    return {"ok": True, "message": "Confirm endpoint placeholder (implement pending tx storage next)"}
