# schemas/wallet.py
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

class WalletResponse(BaseModel):
    subaddress: str
    expected_amount_xmr: Decimal
    received_amount_xmr: Decimal
    is_paid: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AdminWalletMonitorResponse(WalletResponse):
    id: int
    bid_id: int
    user_id: int
    address_index: int

    class Config:
        from_attributes = True