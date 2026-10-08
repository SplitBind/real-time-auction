# app/schemas/bid.py
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from real_time_auction.schemas.user import UserResponse


# Request: Placing a Bid (from custom mobile text input)
class BidCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Bid amount must be greater than 0")

    @field_validator("amount")
    def validate_max_bid(cls, value: Decimal) -> Decimal:
        # Prevents numeric overflow before querying DB
        if value >= Decimal("10000000000006"):
            raise ValueError("Bid amount exceeds the maximum allowable limit.")
        return value
# Response: Individual Bid Details
class BidResponse(BaseModel):
    id: int
    item_id: int
    user_id: int
    amount: Decimal
    created_at: datetime
    user: UserResponse  # Includes bidder details (email/id) for live feeds

    model_config = ConfigDict(from_attributes=True)
