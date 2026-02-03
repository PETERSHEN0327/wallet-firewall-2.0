import requests
from typing import List

AML_BASE = "http://127.0.0.1:8000"

def aml_predict(features: List[float]) -> dict:
    payload = {"features": features}
    r = requests.post(f"{AML_BASE}/risk/predict", json=payload, timeout=5)
    r.raise_for_status()
    return r.json()
