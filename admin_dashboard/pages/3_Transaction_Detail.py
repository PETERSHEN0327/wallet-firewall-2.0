import streamlit as st
from utils.api import get_json, healthcheck
from utils.fmt import pretty_ts

st.set_page_config(page_title="Transaction Detail", layout="wide")
st.title("Transaction Detail")

ok, msg = healthcheck()
if not ok:
    st.error(f"Backend unavailable: {msg}")
    st.stop()

tx_id = st.text_input("tx_id", value="").strip()

col1, col2 = st.columns([1, 2])
with col1:
    fetch = st.button("Fetch Detail", type="primary", use_container_width=True)


def _pretty_time_inplace(d: dict, key: str) -> dict:
    if isinstance(d, dict) and key in d and d[key]:
        try:
            d[key] = pretty_ts(d[key])
        except Exception:
            pass
    return d


def _safe_get_tx_by_id(tx_id: str) -> dict | None:
    """
    GET /api/transactions/{tx_id}
    Returns:
      - tx dict if exists (ALLOW case)
      - None if 404 (BLOCK / REQUIRE_CONFIRM typically won't be in transactions table)
    """
    ok1, data1, err1 = get_json(f"/api/transactions/{tx_id}")
    if not ok1:
        # 404 is normal for blocked/confirm-required flows where tx is not persisted
        return None

    if not isinstance(data1, dict):
        return None

    # Support both shapes:
    #  - {"transaction": {...}}   (recommended)
    #  - {"tx": {...}}            (older)
    #  - {...}                    (raw tx object)
    tx = data1.get("transaction") or data1.get("tx") or data1
    return tx if isinstance(tx, dict) else None


def _get_alerts_by_tx_id(tx_id: str) -> list[dict]:
    """
    GET /api/alerts/{tx_id}
    Returns:
      - list of alert dicts
    """
    ok2, data2, err2 = get_json(f"/api/alerts/{tx_id}")
    if not ok2:
        st.warning(f"Alerts load failed: {err2}")
        return []

    if not isinstance(data2, dict):
        return []

    alerts = data2.get("alerts", [])
    if not isinstance(alerts, list):
        return []

    # normalize created_at for display
    for a in alerts:
        if isinstance(a, dict):
            _pretty_time_inplace(a, "created_at")
    return alerts


def _infer_status(tx: dict | None, alerts: list[dict]) -> str:
    """
    Heuristic:
      - If tx exists => approved
      - Else if any CRITICAL => blocked
      - Else if any WARN => require_confirm
      - Else => not_found_or_no_records
    """
    if tx:
        return "approved"

    levels = {str(a.get("level", "")).upper() for a in alerts if isinstance(a, dict)}
    if "CRITICAL" in levels:
        return "blocked"
    if "WARN" in levels:
        return "require_confirm"
    return "not_found_or_no_records"


if fetch:
    if not tx_id:
        st.warning("Please input tx_id.")
        st.stop()

    # 1) Try tx detail (may be None for blocked/confirm-required)
    tx = _safe_get_tx_by_id(tx_id)
    if tx:
        _pretty_time_inplace(tx, "created_at")

    # 2) Alerts should exist for BLOCK/WARN flows
    alerts = _get_alerts_by_tx_id(tx_id)

    status = _infer_status(tx, alerts)

    st.subheader("Status")
    if status == "approved":
        st.success("APPROVED (transaction persisted)")
    elif status == "require_confirm":
        st.warning("REQUIRE_CONFIRM / WARN (transaction not persisted)")
    elif status == "blocked":
        st.error("BLOCKED / CRITICAL (transaction not persisted)")
    else:
        st.info("No transaction record and no alerts found for this tx_id.")

    st.subheader("Transaction (if persisted)")
    if tx:
        st.json(tx)
    else:
        st.caption(
            "Note: For BLOCK / REQUIRE_CONFIRM flows, the tx is typically not written into the transactions table."
        )

    st.subheader("Related Alerts")
    if alerts:
        st.json(alerts)
    else:
        st.info("No alerts for this tx_id.")

    st.subheader("Quick Summary")
    summary = {
        "tx_id": tx_id,
        "status": status,
        "alerts_count": len(alerts),
    }
    if tx:
        summary.update(
            {
                "from_wallet": tx.get("from_wallet"),
                "to_wallet": tx.get("to_wallet"),
                "amount": tx.get("amount"),
                "created_at": tx.get("created_at"),
                "risk_score": tx.get("risk_score"),
                "risk_label": tx.get("risk_label"),
                "reason": tx.get("reason"),
            }
        )
    else:
        # summarize best-effort from alerts
        # (alerts schema: tx_id, level, message, risk_score, created_at, id)
        top = alerts[0] if alerts else {}
        if isinstance(top, dict):
            summary.update(
                {
                    "top_alert_level": top.get("level"),
                    "top_alert_message": top.get("message"),
                    "top_alert_risk_score": top.get("risk_score"),
                    "top_alert_created_at": top.get("created_at"),
                }
            )
    st.write(summary)
