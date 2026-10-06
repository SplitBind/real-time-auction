# app/models/item.py
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime
from sqlalchemy.orm import relationship
from real_time_auction.database import Base


class AuctionItem(Base):
    __tablename__ = "auction_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(512), nullable=True)
    starting_price = Column(Numeric(15, 2), nullable=False)
    current_price = Column(Numeric(15, 2), nullable=False)
    reserve_price = Column(Numeric(15, 2), nullable=True, default=None)
    min_increment = Column(Numeric(15, 2), default=5.00, nullable=False)
    start_time = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    end_time = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    bids = relationship(
        "Bid",
        back_populates="item",
        order_by="desc(Bid.created_at)",
        cascade="all, delete-orphan"
    )
