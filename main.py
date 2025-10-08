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

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
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

# Initialize FastAPI app
app = FastAPI(
    title="Live Trading System",
    description="High-frequency trading system with Kite integration",
    version="1.0.0"
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include API routes
app.include_router(router, prefix="/api")

# Global instances
trading_engine = None
health_monitor = None
latency_monitor = None
kite_websocket = None

@app.on_event("startup")
async def startup_event():
    """Initialize all core services on startup"""
    global trading_engine, health_monitor, latency_monitor, kite_websocket
    
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

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global kite_websocket
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

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "trading_engine": trading_engine,
        "health_monitor": health_monitor,
        "latency_monitor": latency_monitor
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if health_monitor:
        status = await health_monitor.get_system_status()
        return {"status": "healthy" if status["overall_health"] else "unhealthy", "details": status}
    return {"status": "unknown"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=Config.LOG_LEVEL.lower()
    )
