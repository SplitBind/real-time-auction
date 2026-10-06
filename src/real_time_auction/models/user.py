from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from real_time_auction.database import Base

class User(Base):
    __tablename__= "users"

    id=Column(Integer, primary_key=True, index=True)
    email=Column(String(255),unique=True, index=True, nullable=False)
    hashed_password=Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at=Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc)
            )

    # Relationship
    bids = relationship(
            "Bid",
            back_populates="user", 
            cascade="all, delete-orphan",
            )
