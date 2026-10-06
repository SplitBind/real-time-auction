from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from real_time_auction.core.deps import get_current_admin_user_html
from real_time_auction.core.security import create_access_token, verify_password
from real_time_auction.database import get_db
from real_time_auction.models.user import User
from real_time_auction.models.item import AuctionItem
from real_time_auction.models.bid import Bid

router = APIRouter(prefix="/admin", tags=["Sanctum Admin Portal"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

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
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    starting_price: Decimal = Form(...),
    reserve_price: Decimal = Form(...),
    min_increment: Decimal = Form(...),
    start_time: datetime = Form(...),
    end_time: datetime = Form(...),
    image_url: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user_html),
):
    """Process auction lot creation with local imafe file upload."""
    saved_image_url: Optional[str] = None

    if image and image.filename:
        """Extract extension and generate a non-collinding UUID filename"""
        ext=Path(image.filename).suffix or ".jpg"
        unique_filename=f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / unique_filename

        contents = await image.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # Set DB path matching existing lot format
        saved_image_url = f"/static/uploads/{unique_filename}"
    
    """Process auction lot creation form submission."""
    new_item = AuctionItem(
        title=title,
        description=description,
        starting_price=starting_price,
        current_price=starting_price,
        reserve_price=reserve_price,
        min_increment=min_increment,
        start_time=start_time,
        end_time=end_time,
        image_url=saved_image_url,
        is_active=True,
    )

    db.add(new_item)
    await db.commit()

    # Redirect back to the admin dashboard on successful creation
    return RedirectResponse(
        url="/admin/dashboard", 
        status_code=status.HTTP_303_SEE_OTHER
    )

@router.get("/email", response_class=HTMLResponse)
async def render_email_page(
    request: Request,
    current_admin: User = Depends(get_current_admin_user_html),
):
    return templates.TemplateResponse(request=request, name="send_email.html")
