# Inside routers/auctions.py or routers/wallets.py
from fastapi import APIrouter, Depends, HTTPException
from sqlalchemy.orm import Session
from real_time_auction.database import get_db
from real_time_auction.models.user import User
from real_time_auction.models.wallet import TransactionWallet
from real_time_auction.core.deps import get_current_user
from real_time_auction.schemas.wallet import WalletResponse

router = APIRouter()


@router.get("/bids/{bid_id}/payment", response_model=WalletResponse)
def get_bid_payment_info(
        bid_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    wallet = db.query(TransactionWallet).filter(
        TransactionWallet.bid_id == bid_id,
        TransactionWallet.user_id == current_user.id
    ).first()

    if not wallet:
        raise HTTPException(status_code=404, detail="Payment wallet not assigned yet.")

    return wallet