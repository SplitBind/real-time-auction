# app/schemas/item.py
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from real_time_auction.schemas.bid import BidResponse


# Request: Admin Creating an Item
class ItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    image_url: Optional[str] = None
    starting_price: Decimal = Field(..., gt=0, decimal_places=2)
    min_increment: Decimal = Field(default=Decimal("5.00"), gt=0, decimal_places=2)
    end_time: datetime


# Response: Summary View for Mobile Feed Cards
class ItemListResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    starting_price: Decimal
    current_price: Decimal
    min_increment: Decimal
    end_time: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# Response: Full Detailed View (Product Details + Live Bid History Stack)
class ItemDetailResponse(ItemListResponse):
    start_time: datetime
    created_at: datetime
    bids: List[BidResponse] = []  # All placed bids sorted newest to oldest

    model_config = ConfigDict(from_attributes=True)
