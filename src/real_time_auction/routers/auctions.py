import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from real_time_auction.core.deps import get_current_user
from real_time_auction.core.websockets import ws_manager
from real_time_auction.database import get_db
from real_time_auction.models.bid import Bid
from real_time_auction.models.item import AuctionItem
from real_time_auction.models.user import User
from real_time_auction.schemas.bid import BidCreate, BidResponse
from real_time_auction.schemas.item import ItemDetailResponse, ItemListResponse

router = APIRouter(prefix="/api/v1/auctions", tags=["User Auctions & Bidding"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/add", response_class=HTMLResponse)
async def get_add_item_page(request: Request):
    """Renders the HTML form to list a new auction item."""
    return templates.TemplateResponse(request=request, name="add_item.html")


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_auction_item(
    title: str = Form(...),
    description: str = Form(...),
    starting_price: float = Form(...),
    reserve_price: Optional[float] = Form(None),
    start_time: str = Form(...),
    end_time: str = Form(...),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """Handles form submission, processes image saving, and creates DB record."""
    image_path = None

    # Handle image upload non-blockingly
    if image and image.filename:
        file_ext = image.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        destination = UPLOAD_DIR / unique_filename

        # Save file asynchronously
        async with aiofiles.open(destination, "wb") as buffer:
            content = await image.read()
            await buffer.write(content)

        image_path = f"/static/uploads/{unique_filename}"

    # Parse ISO Datetime strings safely
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid datetime format provided.",
        )

    # Create model instance
    new_item = AuctionItem(
        title=title,
        description=description,
        starting_price=starting_price,
        current_price=starting_price,
        reserve_price=reserve_price,
        start_time=start_dt,
        end_time=end_dt,
        image_url=image_path,
    )

    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    return {
        "status": "success",
        "message": "Auction item created successfully",
        "item_id": new_item.id,
    }


@router.get("", response_model=List[ItemListResponse])
async def get_active_auctions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch active auction feed for mobile app catalog/dashboard."""
    stmt = (
        select(AuctionItem)
        .where(AuctionItem.is_active == True)
        .order_by(AuctionItem.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return items


@router.get("/{item_id}", response_model=ItemDetailResponse)
async def get_auction_detail(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch single product details along with its full ordered bid history stack."""
    stmt = select(AuctionItem).where(AuctionItem.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auction item not found",
        )
    return item


@router.post(
    "/{item_id}/bid",
    response_model=BidResponse,
    status_code=status.HTTP_201_CREATED,
)
async def place_bid(
    item_id: int,
    bid_in: BidCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Place a bid on an auction item with row locking and real-time broadcast."""
    now = datetime.now(timezone.utc)

    # 1. Lock the auction item row asynchronously in PostgreSQL
    stmt = select(AuctionItem).where(AuctionItem.id == item_id).with_for_update()
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auction item not found",
        )

    # 2. Check active status and expiration
    # Ensure timezone awareness matching database timestamps
    end_time = item.end_time
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    if not item.is_active or end_time <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This auction has already ended.",
        )

    # 3. Validate minimum bid increment
    min_required_bid = item.current_price + item.min_increment
    if bid_in.amount < min_required_bid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bid amount must be at least ${min_required_bid:.2f}",
        )

    # 4. Create new bid record and update current price
    new_bid = Bid(
        user_id=current_user.id,
        item_id=item.id,
        amount=bid_in.amount,
    )
    item.current_price = bid_in.amount

    db.add(new_bid)
    await db.commit()
    await db.refresh(new_bid)
    await db.refresh(item)

    # 5. Broadcast update to all connected WebSocket clients viewing this item
    await ws_manager.broadcast_new_bid(
        item_id=item.id,
        bid_id=new_bid.id,
        amount=float(new_bid.amount),
        user_id=current_user.id,
        user_email=current_user.email,
        timestamp=new_bid.created_at.isoformat(),
    )

    return new_bid
