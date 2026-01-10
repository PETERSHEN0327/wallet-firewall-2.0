from fastapi import FastAPI, HTTPException
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np

from .models.schemas import TxRequest, RiskResult, TxReceipt, AMLInput, AMLPrediction
from .services.risk_engine import assess, make_request_id
from .utils.logger import (
    init_db, log_intercept, get_recent_intercepts, get_by_request_id,
    list_add, list_remove, list_get
)

# -----------------------------
# Load model (robust path)
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "xgboost_aml_model.pkl"

try:
    model = joblib.load(MODEL_PATH)
except Exception as e:
    # 让启动时就清晰报错，而不是等请求时 500
    raise RuntimeError(f"Failed to load model from {MODEL_PATH}: {e}")

# 自动读取模型期望维度（路线A核心）
EXPECTED_DIM = getattr(model, "n_features_in_", None)
if EXPECTED_DIM is None:
    # 某些模型对象没有 n_features_in_，可以用 booster 特征数兜底（XGBoost 通常有）
    try:
        EXPECTED_DIM = model.get_booster().num_features()
    except Exception:
        EXPECTED_DIM = None

print("MODEL PATH =", MODEL_PATH)
print("MODEL EXPECTED_DIM =", EXPECTED_DIM)

app = FastAPI(title="Wallet Firewall API")

@app.on_event("startup")
def _startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok"}

# -----------------------------
# Rule-based check
# -----------------------------
@app.post("/risk/check", response_model=RiskResult)
def risk_check(req: TxRequest):
    request_id = make_request_id(req.chain, req.to_address, req.amount_usdt)
    score, level, decision, reasons, votes = assess(req.chain, req.to_address, req.amount_usdt)

    row = {
        "request_id": request_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "chain": req.chain,
        "from_address": req.from_address,
        "to_address": req.to_address,
        "amount_usdt": req.amount_usdt,   # 先保留，不要随便改字段名
        "risk_score": score,
        "risk_level": level,
        "decision": decision,
        "reason_codes": ",".join(reasons),
        "forced": 0,
        "tx_hash": None
    }
    log_intercept(row)

    return RiskResult(
        risk_score=score,
        risk_level=level,
        decision=decision,
        reason_codes=reasons,
        model_votes=votes,
        request_id=request_id
    )

# -----------------------------
# ML-based AML prediction
# -----------------------------
@app.post("/risk/predict", response_model=AMLPrediction)
def predict_risk(tx: AMLInput):
    if EXPECTED_DIM is None:
        raise HTTPException(
            status_code=500,
            detail="Model expected feature dimension is unknown (EXPECTED_DIM=None)."
        )

    if len(tx.features) != EXPECTED_DIM:
        raise HTTPException(
            status_code=400,
            detail=f"features must be length {EXPECTED_DIM}"
        )

    X = np.array([tx.features], dtype=np.float32)

    try:
        label = int(model.predict(X)[0])
        proba = model.predict_proba(X)[0]
        score = float(proba[1]) if len(proba) > 1 else float(proba[0])
    except Exception as e:
        # 把 XGBoost shape mismatch 等错误清晰返回
        raise HTTPException(status_code=500, detail=f"Model inference failed: {e}")

    return AMLPrediction(
        prediction="illicit" if label == 1 else "licit",
        risk_score=round(score, 4)
    )

# -----------------------------
# Simulated blockchain tx
# -----------------------------
@app.post("/tx/send", response_model=TxReceipt)
def tx_send(request_id: str, forced: bool = False):
    row = get_by_request_id(request_id)
    if not row:
        raise HTTPException(404, "request_id not found")

    if row["decision"] == "BLOCK" and not forced:
        return TxReceipt(status="BLOCKED", request_id=request_id, tx_hash=None)

    tx_hash = f"tx_{request_id}"
    row["forced"] = 1 if forced else 0
    row["tx_hash"] = tx_hash
    log_intercept(row)

    status = "FORCED_LOGGED" if forced else "FORWARDED"
    return TxReceipt(status=status, request_id=request_id, tx_hash=tx_hash)

# -----------------------------
# Admin endpoints
# -----------------------------
@app.get("/admin/intercepts")
def admin_intercepts(limit: int = 200):
    return {"items": get_recent_intercepts(limit=limit)}

@app.get("/admin/intercepts/{request_id}")
def admin_intercept_detail(request_id: str):
    row = get_by_request_id(request_id)
    if not row:
        raise HTTPException(404, "not found")
    return row

@app.post("/admin/list/add")
def admin_list_add(kind: str, address: str):
    if kind not in ("BLACKLIST", "WHITELIST"):
        raise HTTPException(400, "kind must be BLACKLIST or WHITELIST")
    list_add(kind, address)
    return {"ok": True}

@app.post("/admin/list/remove")
def admin_list_remove(kind: str, address: str):
    if kind not in ("BLACKLIST", "WHITELIST"):
        raise HTTPException(400, "kind must be BLACKLIST or WHITELIST")
    list_remove(kind, address)
    return {"ok": True}

@app.get("/admin/list")
def admin_list(kind: str):
    if kind not in ("BLACKLIST", "WHITELIST"):
        raise HTTPException(400, "kind must be BLACKLIST or WHITELIST")
    return {"items": list_get(kind)}
