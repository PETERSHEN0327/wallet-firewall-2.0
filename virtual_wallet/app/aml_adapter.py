from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import uuid4

from .aml_client import aml_predict

# === Decision rules (only change here) ===
WARN_THRESHOLD = 0.0  # >= WARN_THRESHOLD => REQUIRE_CONFIRM
# prediction == "illicit" => BLOCK
# otherwise => ALLOW


def make_request_id(chain: str, to_address: str, amount_usdt: float) -> str:
    # Keep a stable request id format for logging / UI display
    return f"{chain}-{to_address}-{uuid4().hex[:8]}"


@dataclass
class AMLDecision:
    request_id: str
    risk_score: float            # changed to float (model returns 0.x)
    risk_level: str
    decision: str
    reason_codes: List[str]
    model_votes: Dict


def _tx_to_features(chain: str, to_address: str, amount_usdt: float, from_address: Optional[str] = None) -> List[float]:
    """
    MVP feature bridge:
    - Always produce a 165-length vector (matches your Wallet Firewall model).
    - Put amount into feature[0] for demo.
    NOTE: Replace this function later with real feature engineering / alignment.
    """
    features = [0.0] * 165
    features[0] = float(amount_usdt or 0.0)
    return features


def _risk_level_from_score(score: float) -> str:
    # Simple mapping for UI; adjust if you want.
    if score >= 0.8:
        return "HIGH"
    if score >= 0.5:
        return "MEDIUM"
    return "LOW"


def check_tx(chain: str, to_address: str, amount_usdt: float, from_address: Optional[str] = None) -> AMLDecision:
    """
    Public entry used by Virtual Wallet before executing a transfer.
    It calls the AML backend (Wallet Firewall) via HTTP and returns a normalized decision object.
    """
    rid = make_request_id(chain, to_address, amount_usdt)

    # 1) build features
    features = _tx_to_features(chain, to_address, amount_usdt, from_address=from_address)

    # 2) call AML backend: POST /risk/predict
    result = aml_predict(features)

    prediction = (result.get("prediction") or "").lower()

    prediction = "illicit"  # DEMO: force block

    risk_score = float(result.get("risk_score", 0.0))

    # 3) decision rule (single source of truth)
    if prediction == "illicit":
        decision = "BLOCK"
        reason_codes = ["model_illicit"]
    elif risk_score >= WARN_THRESHOLD:
        decision = "REQUIRE_CONFIRM"
        reason_codes = ["score_threshold"]
    else:
        decision = "ALLOW"
        reason_codes = []

    risk_level = _risk_level_from_score(risk_score)

    # model_votes kept for compatibility (your backend may not return it)
    votes = result.get("model_votes") or {}

    return AMLDecision(
        request_id=rid,
        risk_score=risk_score,
        risk_level=risk_level,
        decision=decision,
        reason_codes=reason_codes,
        model_votes=votes,
    )
