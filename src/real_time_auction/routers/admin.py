import uuid
import json
import aiofiles
from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter,HTTPException ,Depends, File,Form, Request, status, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from real_time_auction.core.deps import get_current_admin_user_html
from real_time_auction.core.security import create_access_token, verify_password
from real_time_auction.database import get_db
from real_time_auction.models.user import User
from real_time_auction.models.item import AuctionItem
from real_time_auction.models.bid import Bid
from real_time_auction.core.websockets import ws_manager

router = APIRouter(prefix="/admin", tags=["Sanctum Admin Portal"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- AUTHENTICATION ENDPOINTS ---
@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Render admin login page."""
    return templates.TemplateResponse(request=request, name="login.html")


@router.post("/login")
async def admin_login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Validate admin credentials and set secure HTTP-only access cookie."""
    stmt = select(User).where(User.email == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Reject non-existent users, bad passwords, or non-admins
    if not user or not verify_password(password, user.hashed_password) or not user.is_admin:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Invalid administrative credentials or unauthorized clearance."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Issue JWT and store in HTTP-only cookie
    access_token = create_access_token(subject=str(user.id))
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in HTTPS production
    )
    return response


@router.get("/logout")
async def admin_logout():
    """Clear session token cookie and return to login page."""
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="admin_access_token")
    return response


# --- PROTECTED ADMIN DASHBOARD ROUTES ---
@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user_html),
):
    """Sanctum Ledger & Control Portal"""
    
    # 1. Compute aggregate metrics
    total_active_res = await db.execute(
        select(func.count(AuctionItem.id)).where(AuctionItem.is_active == True)
    )
    total_active = total_active_res.scalar() or 0

    total_bids_res = await db.execute(select(func.count(Bid.id)))
    total_bids = total_bids_res.scalar() or 0

    total_items_res = await db.execute(select(func.count(AuctionItem.id)))
    total_items = total_items_res.scalar() or 0

    # 2. Query active lots
    active_stmt = (
        select(AuctionItem)
        .where(AuctionItem.is_active == True)
        .order_by(AuctionItem.end_time.asc())
    )
    active_items = (await db.execute(active_stmt)).scalars().all()

    # 3. Query recent bids
    bids_stmt = (
        select(Bid)
        .options(selectinload(Bid.user), selectinload(Bid.item))
        .order_by(Bid.created_at.desc())
        .limit(15)
    )
    recent_bids = (await db.execute(bids_stmt)).scalars().all()

    # 4. Query verification queue
    now = datetime.now(timezone.utc)
    verification_stmt = (
        select(AuctionItem)
        .options(selectinload(AuctionItem.bids))
        .where((AuctionItem.end_time <= now) | (AuctionItem.is_active == False))
        .order_by(AuctionItem.end_time.desc())
        .limit(10)
    )
    verification_queue = (await db.execute(verification_stmt)).scalars().all()

    # 5. Render dashboard template with defined variables
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "current_admin": current_admin,
            "total_active": total_active,
            "total_bids": total_bids,
            "total_items": total_items,
            "active_items": active_items,
            "recent_bids": recent_bids,
            "verification_queue": verification_queue,
            "now": now,
        },
    )



@router.get("/items/add", response_class=HTMLResponse)
async def render_add_item_page(
    request: Request,
    current_admin: User = Depends(get_current_admin_user_html),
):
    return templates.TemplateResponse(
            request=request, 
            name="add_item.html",
            context={"current_admin": current_admin}
            )

@router.post("/items/add")
async def handle_add_item(
    title: str = Form(...),
    description: str = Form(""),
    starting_price: float = Form(...),
    reserve_price: Optional[float] = Form(None),
    min_increment: float = Form(5.00),
    start_time: datetime = Form(...),
    end_time: datetime = Form(...),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    # 1. Initialize image URL variable
    saved_image_url = None

    # 2. Process image upload if provided
    if image and image.filename:
        file_ext = image.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        destination = UPLOAD_DIR / unique_filename

        async with aiofiles.open(destination, "wb") as buffer:
            content = await image.read()
            await buffer.write(content)

        saved_image_url = f"/static/uploads/{unique_filename}"

    # 3. Pass saved_image_url to the model
    new_item = AuctionItem(
        title=title,
        description=description,
        starting_price=starting_price,
        current_price=starting_price,
        reserve_price=reserve_price,
        min_increment=min_increment,
        start_time=start_time,
        end_time=end_time,
        image_url=saved_image_url,  # Matching variable name
    )

    db.add(new_item)
    await db.commit()

    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/items/{item_id}/close")
async def close_auction_lot(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Closes an active auction lot, evaluates winner/reserve, and broadcasts status."""
    now = datetime.now(timezone.utc)

    # 1. Fetch item with row lock to prevent race conditions
    stmt = select(AuctionItem).where(AuctionItem.id == item_id).with_for_update()
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auction item not found",
        )

    if not item.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This lot is already closed.",
        )

    # 2. Get highest bid
    bid_stmt = (
        select(Bid)
        .where(Bid.item_id == item_id)
        .order_by(Bid.amount.desc())
        .limit(1)
    )
    bid_result = await db.execute(bid_stmt)
    winning_bid = bid_result.scalar_one_or_none()

    # 3. Determine outcome
    reserve_met = True
    if item.reserve_price and item.current_price < item.reserve_price:
        reserve_met = False

    is_sold = bool(winning_bid and reserve_met)

    # 4. Update item status in database
    item.is_active = False
    item.end_time = now

    await db.commit()
    await db.refresh(item)

    # 5. Broadcast auction status to WebSocket listeners
    await ws_manager.broadcast_auction_closed(
        item_id=item.id,
        is_sold=is_sold,
        winning_bid_id=winning_bid.id if winning_bid else None,
        winning_user_id=winning_bid.user_id if winning_bid else None,
        final_price=float(item.current_price),
    )
    if not item.is_active:
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/email", response_class=HTMLResponse)
async def render_email_page(
    request: Request,
    current_admin: User = Depends(get_current_admin_user_html),
):
    return templates.TemplateResponse(request=request, name="send_email.html")

@router.get("/auctions", response_class=HTMLResponse)
async def list_admin_auctions(request: Request, db: AsyncSession = Depends(get_db)):
    # Fetch all items from DB in a single query
    stmt = select(AuctionItem).order_by(AuctionItem.created_at.desc())
    result = await db.execute(stmt)
    raw_auctions = result.scalars().all()

    # Serialize objects into a JS-friendly JSON structure
    auctions_json = json.dumps([
        {
            "id": item.id,
            "title": item.title,
            "description": item.description or "",
            "current_price": float(item.current_price),
            "is_active": item.is_active,
            "end_time": item.end_time.strftime('%Y-%m-%d %H:%M') if item.end_time else 'N/A',
            "created_at": item.created_at.isoformat() if item.created_at else ''
        }
        for item in raw_auctions
    ])

    return templates.TemplateResponse(
        request=request,
        name="admin_auctions_filter.html",
        context={
            "auctions_json": auctions_json,
            "total_count": len(raw_auctions),
        }
    )

