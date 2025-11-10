#!/usr/bin/env python3
"""
Live Trading System - Main Entry Point
High-frequency trading system with Kite integration
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
import uvicorn

from src.core.trading_engine import TradingEngine
from src.core.health_monitor import HealthMonitor
from src.api.routes import router, set_global_references
from src.core.latency_monitor import LatencyMonitor
from src.core.kite_websocket import KiteWebSocketClient
from config import Config

# Setup logging
os.makedirs(Config.DATA_DIR, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.SYSTEM_LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Global instances
trading_engine = None
health_monitor = None
latency_monitor = None
kite_websocket = None

# Simple session storage for authentication
# Format: {session_id: {'user_type': 'test'|'real', 'username': str, 'authenticated_at': datetime}}
authenticated_sessions = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global trading_engine, health_monitor, latency_monitor, kite_websocket
    
    # Startup
    logger.info("Starting Live Trading System...")
    
    # Initialize core services
    latency_monitor = LatencyMonitor()
    trading_engine = TradingEngine()
    health_monitor = HealthMonitor(trading_engine)
    
    # Initialize Kite WebSocket client
    if Config.KITE_ACCESS_TOKEN:
        kite_websocket = KiteWebSocketClient(Config.KITE_ACCESS_TOKEN, Config.KITE_API_KEY)
        # Set up callbacks
        kite_websocket.set_tick_callback(trading_engine.add_tick)
        kite_websocket.set_error_callback(lambda msg: logger.error(f"Kite WebSocket error: {msg}"))
    
    # Set global references for API routes
    set_global_references(trading_engine, health_monitor, latency_monitor)
    
    # Start background tasks
    asyncio.create_task(health_monitor.start_monitoring())
    asyncio.create_task(trading_engine.start_trading_loop())
    asyncio.create_task(latency_monitor.start_monitoring())
    
    # Start Kite WebSocket if available
    if kite_websocket:
        asyncio.create_task(kite_websocket.run())
    
    logger.info("Live Trading System started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Live Trading System...")
    
    if trading_engine:
        await trading_engine.stop()
    if health_monitor:
        await health_monitor.stop()
    if latency_monitor:
        await latency_monitor.stop()
    if kite_websocket:
        await kite_websocket.stop()
    
    logger.info("Live Trading System shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="Live Trading System",
    description="High-frequency trading system with Kite integration",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files and templates
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include API routes
app.include_router(router, prefix="/api")

@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint - REQUIRES authentication"""
    # Require authentication for health endpoint too
    if not check_authentication(request):
        raise HTTPException(status_code=401, detail="Not authenticated. Please login first.")
    
    if health_monitor:
        status = health_monitor.get_system_status()
        return {"status": "healthy" if status["overall_health"] else "unhealthy", "details": status}
    return {"status": "unknown"}

def check_authentication(request: Request) -> bool:
    """Check if user is authenticated - ONLY checks session, not Config"""
    # Check session cookie - this is the ONLY way to authenticate
    session_id = request.cookies.get("session_id")
    if session_id and session_id in authenticated_sessions:
        session_data = authenticated_sessions[session_id]
        # Check if session is still valid (24 hours)
        from datetime import datetime, timedelta
        if 'authenticated_at' in session_data:
            auth_time = session_data['authenticated_at']
            if isinstance(auth_time, str):
                from dateutil.parser import parse
                auth_time = parse(auth_time)
            if datetime.now() - auth_time < timedelta(hours=24):
                return True
            else:
                # Session expired, remove it
                authenticated_sessions.pop(session_id, None)
        return True
    return False

def get_user_type(request: Request) -> str:
    """Get user type: 'test' or 'real'"""
    session_id = request.cookies.get("session_id")
    if session_id and session_id in authenticated_sessions:
        return authenticated_sessions[session_id].get('user_type', 'real')
    return 'real'

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root - ALWAYS redirect to login (starting point)"""
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page - STARTING POINT, no auth required"""
    # If already authenticated, redirect to dashboard
    if check_authentication(request):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page - REQUIRES authentication, blocks if not authenticated"""
    # CRITICAL: Check authentication - if not authenticated, redirect to login
    if not check_authentication(request):
        return RedirectResponse(url="/login")
    
    # Set user type on trading engine for order placement checks
    user_type = get_user_type(request)
    if trading_engine:
        trading_engine.user_type = user_type
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "trading_engine": trading_engine,
        "health_monitor": health_monitor,
        "latency_monitor": latency_monitor,
        "user_type": user_type
    })

@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    """Orders page - REQUIRES authentication"""
    if not check_authentication(request):
        return RedirectResponse(url="/login")
    
    user_type = get_user_type(request)
    return templates.TemplateResponse("orders.html", {
        "request": request,
        "user_type": user_type
    })

@app.get("/trades", response_class=HTMLResponse)
async def trades_page(request: Request):
    """Trades page - REQUIRES authentication"""
    if not check_authentication(request):
        return RedirectResponse(url="/login")
    
    user_type = get_user_type(request)
    return templates.TemplateResponse("trades.html", {
        "request": request,
        "user_type": user_type
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Analytics page - REQUIRES authentication"""
    if not check_authentication(request):
        return RedirectResponse(url="/login")
    
    user_type = get_user_type(request)
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "user_type": user_type
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page - REQUIRES authentication"""
    if not check_authentication(request):
        return RedirectResponse(url="/login")
    
    user_type = get_user_type(request)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user_type": user_type
    })

@app.get("/logout")
async def logout(request: Request):
    """Logout and redirect to login"""
    # Remove session
    session_id = request.cookies.get("session_id")
    if session_id:
        authenticated_sessions.pop(session_id, None)
    
    # Clear config
    Config.KITE_ACCESS_TOKEN = ''
    Config.KITE_API_KEY = ''
    import os
    os.environ.pop('KITE_ACCESS_TOKEN', None)
    os.environ.pop('KITE_API_KEY', None)
    
    response = RedirectResponse(url="/login")
    response.delete_cookie("session_id")
    return response


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=Config.LOG_LEVEL.lower()
    )
