import json
from pathlib import Path

import joblib
import pandas as pd

# ---- 1) Locate project root and model ----
ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "backend" / "app" / "models" / "xgboost_aml_model.pkl"  # 按你现在项目实际模型名改
# 如果你的模型文件名是 xgboost_aml_model.pkl，就保持不变；
# 如果你实际是 xgboost_aml_model.pkl 或 xgboost_aml_model.pkl，请确保这里与文件名一致。

model = joblib.load(MODEL_PATH)
EXPECTED_DIM = getattr(model, "n_features_in_", None)

if EXPECTED_DIM is None:
    raise RuntimeError("Model does not expose n_features_in_. Cannot auto-align feature length.")

print("MODEL_PATH =", MODEL_PATH)
print("EXPECTED_DIM =", EXPECTED_DIM)

# ---- 2) Find Elliptic BTC features CSV ----
CANDIDATES = [
    ROOT / "data" / "elliptic_txs_features.csv",   # 你现在 data 目录里的真实文件名
    ROOT / "data" / "btc_features.csv",            # 兼容备用
    ROOT / "data" / "btc_features_normalized.csv", # 兼容备用
]

csv_path = next((p for p in CANDIDATES if p.exists()), None)
if csv_path is None:
    print("\nCannot find features CSV. Tried:")
    for p in CANDIDATES:
        print(" -", p)
    raise FileNotFoundError("Put your features CSV in one of the paths above, or edit CANDIDATES.")

print("FEATURES_CSV =", csv_path)

# ---- 3) Load CSV and extract features ----
df = pd.read_csv(csv_path)

# Elliptic features file usually includes 'txId' as first column + many numeric columns
DROP_COLS = {"txId", "tx_id", "time_step", "label", "class", "target", "is_illicit"}
X = df.drop(columns=[c for c in df.columns if c in DROP_COLS], errors="ignore")

# keep only numeric columns
X = X.select_dtypes(include=["number"])
if X.shape[1] == 0:
    raise ValueError("After dropping non-feature columns, no numeric feature columns remain.")

# take the first row as a real sample
row = X.iloc[0].astype(float).tolist()

# ---- 4) Align length to EXPECTED_DIM ----
if len(row) < EXPECTED_DIM:
    row = row + [0.0] * (EXPECTED_DIM - len(row))
elif len(row) > EXPECTED_DIM:
    row = row[:EXPECTED_DIM]

print("len(features) =", len(row))
print(json.dumps({"features": row}, ensure_ascii=False))
