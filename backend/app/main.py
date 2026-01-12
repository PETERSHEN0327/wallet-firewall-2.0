from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException

from .models.schemas import AMLInput, AMLPrediction, RiskResult, TxReceipt, TxRequest
from .services.risk_engine import assess, make_request_id
from .utils.logger import (
    get_by_request_id,
    get_recent_intercepts,
    init_db,
    list_add,
    list_get,
    list_remove,
    log_intercept,
)

# ============================================================
# Configuration
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "xgboost_aml_model.pkl"


# ============================================================
# Model loading + expected feature dim (Route A: auto-detect)
# ============================================================

def _load_model(model_path: Path):
    try:
        return joblib.load(model_path)
    except Exception as e:
        # Fail fast at startup (avoid runtime 500 later)
        raise RuntimeError(f"Failed to load model from {model_path}: {e}") from e


def _infer_expected_dim(model) -> Optional[int]:
    # 1) sklearn-style estimator
    dim = getattr(model, "n_features_in_", None)
    if isinstance(dim, int) and dim > 0:
        return dim

    # 2) xgboost booster fallback
    try:
        booster = model.get_booster()
        dim2 = booster.num_features()
        if isinstance(dim2, int) and dim2 > 0:
            return dim2
    except Exception:
        pass

    return None


model = _load_model(MODEL_PATH)
EXPECTED_DIM: Optional[int] = _infer_expected_dim(model)

print("MODEL PATH =", MODEL_PATH)
print("MODEL EXPECTED_DIM =", EXPECTED_DIM)


# ============================================================
# FastAPI app
# ============================================================

app = FastAPI(title="Wallet Firewall API")


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/")
def root():
    return {
        "name": "Wallet Firewall API",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ============================================================
# Rule-based check
# ============================================================

@app.post("/risk/check", response_model=RiskResult)
def risk_check(req: TxRequest):
    # Keep field naming stable (amount_usdt) to avoid breaking other code paths.
    request_id = make_request_id(req.chain, req.to_address, req.amount_usdt)
    score, level, decision, reasons, votes = assess(req.chain, req.to_address, req.amount_usdt)

    row = {
        "request_id": request_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "chain": req.chain,
        "from_address": req.from_address,
        "to_address": req.to_address,
        "amount_usdt": req.amount_usdt,
        "risk_score": score,
        "risk_level": level,
        "decision": decision,
        "reason_codes": ",".join(reasons),
        "forced": 0,
        "tx_hash": None,
    }
    log_intercept(row)

    return RiskResult(
        risk_score=score,
        risk_level=level,
        decision=decision,
        reason_codes=reasons,
        model_votes=votes,
        request_id=request_id,
    )


# ============================================================
# ML-based AML prediction
# ============================================================

@app.post("/risk/predict", response_model=AMLPrediction)
def predict_risk(tx: AMLInput):
    if EXPECTED_DIM is None:
        raise HTTPException(
            status_code=500,
            detail="Model expected feature dimension is unknown (EXPECTED_DIM=None).",
        )

    if len(tx.features) != EXPECTED_DIM:
        raise HTTPException(
            status_code=400,
            detail=f"features must be length {EXPECTED_DIM}",
        )

    X = np.array([tx.features], dtype=np.float32)

    try:
        label = int(model.predict(X)[0])

        # Some models have predict_proba, some don't; handle both.
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)[0]
            score = float(proba[1]) if len(proba) > 1 else float(proba[0])
        else:
            # If no probability output, use 1.0/0.0 fallback
            score = 1.0 if label == 1 else 0.0

    except Exception as e:
        # Return clear error for shape mismatch / inference failures
        raise HTTPException(status_code=500, detail=f"Model inference failed: {e}")

    return AMLPrediction(
        prediction="illicit" if label == 1 else "licit",
        risk_score=round(score, 4),
    )


# ============================================================
# Simulated blockchain tx
# ============================================================

@app.post("/tx/send", response_model=TxReceipt)
def tx_send(request_id: str, forced: bool = False):
    row = get_by_request_id(request_id)
    if not row:
        raise HTTPException(status_code=404, detail="request_id not found")

    if row["decision"] == "BLOCK" and not forced:
        return TxReceipt(status="BLOCKED", request_id=request_id, tx_hash=None)

    tx_hash = f"tx_{request_id}"
    row["forced"] = 1 if forced else 0
    row["tx_hash"] = tx_hash
    log_intercept(row)

    status = "FORCED_LOGGED" if forced else "FORWARDED"
    return TxReceipt(status=status, request_id=request_id, tx_hash=tx_hash)


# ============================================================
# Admin endpoints
# ============================================================

@app.get("/admin/intercepts")
def admin_intercepts(limit: int = 200):
    return {"items": get_recent_intercepts(limit=limit)}


@app.get("/admin/intercepts/{request_id}")
def admin_intercept_detail(request_id: str):
    row = get_by_request_id(request_id)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    return row


@app.post("/admin/list/add")
def admin_list_add(kind: str, address: str):
    if kind not in ("BLACKLIST", "WHITELIST"):
        raise HTTPException(status_code=400, detail="kind must be BLACKLIST or WHITELIST")
    list_add(kind, address)
    return {"ok": True}


@app.post("/admin/list/remove")
def admin_list_remove(kind: str, address: str):
    if kind not in ("BLACKLIST", "WHITELIST"):
        raise HTTPException(status_code=400, detail="kind must be BLACKLIST or WHITELIST")
    list_remove(kind, address)
    return {"ok": True}


@app.get("/admin/list")
def admin_list(kind: str):
    if kind not in ("BLACKLIST", "WHITELIST"):
        raise HTTPException(status_code=400, detail="kind must be BLACKLIST or WHITELIST")
    return {"items": list_get(kind)}
