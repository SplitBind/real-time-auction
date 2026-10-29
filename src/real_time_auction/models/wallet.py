from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from real_time_auction.database import Base

class TransactionWallet(Base):
    __tablename__ = "transaction_wallets"

    id = Column(Integer, primary_key=True, index=True)
    bid_id = Column(Integer, ForeignKey("bids.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subaddress = Column(String(255), unique=True, index=True, nullable=False)
    address_index = Column(Integer, nullable=False)
    expected_amount_xmr = Column(Numeric(18, 12), nullable=False)
    received_amount_xmr = Column(Numeric(18, 12), default=0.0)
    is_paid = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships (assuming Bid and User models exist)
    bid = relationship("Bid", backref="wallet")
    user = relationship("User", backref="wallets")
