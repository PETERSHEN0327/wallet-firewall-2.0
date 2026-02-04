import streamlit as st
import pandas as pd
from utils.api import get_json, healthcheck
from utils.fmt import pretty_ts

st.set_page_config(page_title="Intercepts", layout="wide")
st.title("Intercepts")

# ---------- Health ----------
ok, msg = healthcheck()
if not ok:
    st.error(f"Backend unavailable: {msg}")
    st.stop()

# ---------- Controls ----------
colA, colB, colC = st.columns([2, 2, 3])
with colA:
    limit = st.number_input("Limit", min_value=10, max_value=2000, value=200, step=10)

# Virtual Wallet alerts use: INFO / WARN / CRITICAL (based on your screenshots)
with colB:
    level_filter = st.selectbox("Risk level filter", ["ALL", "INFO", "WARN", "CRITICAL"])

with colC:
    keyword = st.text_input("Search keyword (tx_id / message)", value="").strip()

# ---------- Load alerts from Virtual Wallet (8002) ----------
# NOTE: if your backend implements /api/alerts/{tx_id} and also /api/alerts?limit=,
# this list endpoint is correct for the Intercepts page.
ok, data, err = get_json("/api/alerts", params={"limit": int(limit)})
if not ok:
    st.error(err)
    st.stop()

items = data.get("alerts", []) if isinstance(data, dict) else []
df = pd.DataFrame(items)

if df.empty:
    st.info("No records yet.")
    st.stop()

# ---------- Normalize columns ----------
# Ensure expected columns exist to avoid KeyError in dataframe display
for col in ["created_at", "level", "message", "tx_id", "risk_score", "id"]:
    if col not in df.columns:
        df[col] = None

# ---------- Filters ----------
if level_filter != "ALL":
    df = df[df["level"].fillna("").astype(str).str.upper() == level_filter]

if keyword:
    k = keyword.lower()

    def hit(row: pd.Series) -> bool:
        tx_id = str(row.get("tx_id", "")).lower()
        msg_ = str(row.get("message", "")).lower()
        lvl = str(row.get("level", "")).lower()
        return (k in tx_id) or (k in msg_) or (k in lvl)

    df = df[df.apply(hit, axis=1)]

if df.empty:
    st.warning("No matched records after filtering.")
    st.stop()

# ---------- Beautify / display ----------
df_show = df.copy()

# created_at is ISO string in Virtual Wallet
df_show["created_at"] = df_show["created_at"].apply(lambda x: pretty_ts(x) if x else x)

# Make sure types are friendly
df_show["tx_id"] = df_show["tx_id"].astype(str)
df_show["level"] = df_show["level"].astype(str)
df_show["risk_score"] = pd.to_numeric(df_show["risk_score"], errors="coerce").fillna(0).astype(int)

# Reorder columns for UI
preferred_cols = ["message", "created_at", "tx_id", "level", "id", "risk_score"]
cols = [c for c in preferred_cols if c in df_show.columns] + [c for c in df_show.columns if c not in preferred_cols]
df_show = df_show[cols]

st.caption("Tip: copy tx_id to Transaction Detail page.")
st.dataframe(df_show, use_container_width=True)
