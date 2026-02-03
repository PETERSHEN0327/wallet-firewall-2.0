import random
import string
from datetime import datetime, timedelta
from typing import Dict, List


def _rand_wallet(prefix: str = "0x") -> str:
    return prefix + "".join(random.choices("abcdef" + string.digits, k=10))


def generate_wallets(n: int = 20) -> List[Dict]:
    wallets = []
    for _ in range(n):
        wallets.append(
            {
                "wallet_id": _rand_wallet(),
                "balance": round(random.uniform(1000, 20000), 2),
                "tag": "NORMAL",
            }
        )
    return wallets


def generate_transactions(wallet_ids: List[str], scenario: str, n: int = 200) -> List[Dict]:
    now = datetime.utcnow()
    rows: List[Dict] = []

    mixer_addr = "0xMIXER0001"
    high_risk_addr = "0xSCAM00001"
    mule_addr = "0xMULE000001"

    def add_row(frm: str, to: str, amount: float, t: datetime, label_hint: str) -> None:
        rows.append(
            {
                "tx_id": f"tx_{len(rows) + 1}",
                "from_wallet": frm,
                "to_wallet": to,
                "amount": amount,
                "timestamp": t,
                "label_hint": label_hint,
            }
        )

    if scenario == "normal":
        for _ in range(n):
            frm, to = random.sample(wallet_ids, 2)
            amt = round(random.uniform(5, 800), 2)
            t = now - timedelta(minutes=random.randint(0, 24 * 60))
            add_row(frm, to, amt, t, "BENIGN")

    elif scenario == "structuring":
        sender = random.choice(wallet_ids)
        receivers = random.sample(wallet_ids, min(10, len(wallet_ids)))
        base_t = now - timedelta(minutes=60)
        for _ in range(n):
            to = random.choice(receivers)
            amt = round(random.uniform(90, 199), 2)
            t = base_t + timedelta(minutes=random.randint(0, 60))
            add_row(sender, to, amt, t, "SUSPICIOUS_STRUCTURING")

    elif scenario == "burst":
        sender = random.choice(wallet_ids)
        receivers = random.sample(wallet_ids, min(8, len(wallet_ids)))
        base_t = now - timedelta(minutes=10)
        for _ in range(n):
            to = random.choice(receivers)
            amt = round(random.uniform(50, 1200), 2)
            t = base_t + timedelta(seconds=random.randint(0, 600))
            add_row(sender, to, amt, t, "SUSPICIOUS_BURST")

    elif scenario == "layering":
        chain = random.sample(wallet_ids, min(6, len(wallet_ids)))
        base_t = now - timedelta(hours=6)
        for i in range(n):
            a = random.choice(chain[:-1])
            b = chain[chain.index(a) + 1]
            amt = round(random.uniform(300, 3000), 2)
            t = base_t + timedelta(minutes=i % 240)
            add_row(a, b, amt, t, "SUSPICIOUS_LAYERING")

    elif scenario == "mixer":
        base_t = now - timedelta(hours=2)
        for _ in range(n):
            frm = random.choice(wallet_ids)
            amt = round(random.uniform(200, 5000), 2)
            t = base_t + timedelta(minutes=random.randint(0, 120))
            add_row(frm, mixer_addr, amt, t, "SUSPICIOUS_MIXER")

    elif scenario == "mule":
        sources = random.sample(wallet_ids, min(12, len(wallet_ids)))
        sinks = random.sample(wallet_ids, min(12, len(wallet_ids)))
        base_t = now - timedelta(hours=3)

        for _ in range(n // 2):
            frm = random.choice(sources)
            amt = round(random.uniform(100, 2500), 2)
            t = base_t + timedelta(minutes=random.randint(0, 90))
            add_row(frm, mule_addr, amt, t, "SUSPICIOUS_MULE_IN")

        for _ in range(n - n // 2):
            to = random.choice(sinks)
            amt = round(random.uniform(100, 2500), 2)
            t = base_t + timedelta(minutes=90 + random.randint(0, 90))
            add_row(mule_addr, to, amt, t, "SUSPICIOUS_MULE_OUT")

    elif scenario == "highrisk":
        base_t = now - timedelta(hours=2)
        for _ in range(n):
            frm = random.choice(wallet_ids)
            amt = round(random.uniform(1500, 7000), 2)
            t = base_t + timedelta(minutes=random.randint(0, 120))
            add_row(frm, high_risk_addr, amt, t, "SUSPICIOUS_HIGH_RISK")

    else:
        raise ValueError("Unknown scenario")

    return rows
