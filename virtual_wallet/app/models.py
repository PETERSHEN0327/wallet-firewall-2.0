from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Wallet(SQLModel, table=True):
    wallet_id: str = Field(primary_key=True, index=True)
    balance: float = 0.0
    tag: str = "NORMAL"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tx_id: str = Field(index=True)
    from_wallet: str = Field(index=True)
    to_wallet: str = Field(index=True)
    amount: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    risk_score: float = 0.0
    risk_label: str = "LOW"
    reason: str = ""


class Alert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    tx_id: str = Field(index=True)
    level: str = "INFO"
    message: str
    risk_score: float = 0.0
