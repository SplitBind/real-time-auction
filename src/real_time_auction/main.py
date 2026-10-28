# app/main.py
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError

from real_time_auction.config import settings
from real_time_auction.database import Base, engine
from real_time_auction.routers import auth, admin, auctions
from real_time_auction.core.websockets import ws_manager


# Lifespan event to create database tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run synchronous metadata creation via run_sync
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

    # Optional cleanup on shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    debug=settings.DEBUG
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# CORS configuration (allows React Native & Web clients)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploaded images directory exists and mount static route
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- GLOBAL EXCEPTION HANDLER FOR DATABASE INTEGRITY ERRORS ---
@app.exception_handler(IntegrityError)
async def sqlalchemy_integrity_exception_handler(request: Request, exc: IntegrityError):
    """
    Catches database constraint violations globally (e.g., duplicate unique emails, 
    foreign key conflicts) and translates them into clean 400 responses.
    """
    error_message = str(exc.orig) if exc.orig else "Database integrity violation."
    
    if "unique constraint" in error_message.lower():
        detail = "A record with this unique value already exists."
    elif "foreign key constraint" in error_message.lower():
        detail = "Referenced related record does not exist."
    else:
        detail = "A database constraint violation occurred."

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "status": "error",
            "message": detail,
            "diagnostic": error_message if app.debug else None
        },
    )


# Include REST Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(auctions.router)


# --- WEBSOCKET ROUTE ---
@app.websocket("/ws/auctions/{item_id}")
async def websocket_auction_endpoint(websocket: WebSocket, item_id: int):
    """WebSocket endpoint for mobile clients to stream live bids for an item."""
    await ws_manager.connect(websocket, item_id)
    try:
        while True:
            # Keep connection alive; clients can send ping/pong frames
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, item_id)


@app.get("/")
async def render_admin_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"title": "Sanctum Admin"}
    )
