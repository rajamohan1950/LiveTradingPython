"""
API Routes - REST API endpoints for the trading system
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio

from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class AuthRequest(BaseModel):
    request_token: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user_name: Optional[str] = None

class SystemStatusResponse(BaseModel):
    overall_health: bool
    critical_issues: int
    warning_issues: int
    last_check: str
    recent_checks: List[Dict[str, Any]]

class PnLResponse(BaseModel):
    total_pnl: float
    total_charges: float
    net_pnl: float
    trade_count: int
    current_positions: Dict[str, float]

class OrderBookResponse(BaseModel):
    symbol: str
    timestamp: float
    last_price: float
    spread: float
    volume: int
    bids: List[Dict[str, Any]]
    asks: List[Dict[str, Any]]

# Global reference to trading engine (will be set by main.py)
trading_engine = None
health_monitor = None
latency_monitor = None

def get_trading_engine():
    """Dependency to get trading engine instance"""
    global trading_engine
    if not trading_engine:
        raise HTTPException(status_code=503, detail="Trading engine not available")
    return trading_engine

def get_health_monitor():
    """Dependency to get health monitor instance"""
    global health_monitor
    if not health_monitor:
        raise HTTPException(status_code=503, detail="Health monitor not available")
    return health_monitor

def get_latency_monitor():
    """Dependency to get latency monitor instance"""
    global latency_monitor
    if not latency_monitor:
        raise HTTPException(status_code=503, detail="Latency monitor not available")
    return latency_monitor

@router.post("/auth/kite", response_model=AuthResponse)
async def authenticate_kite(request: AuthRequest, engine=Depends(get_trading_engine)):
    """Authenticate with Kite using request token"""
    try:
        success = await engine.authenticate_kite(request.request_token)
        
        if success:
            # Get user profile
            profile = engine.kite.profile()
            return AuthResponse(
                success=True,
                message="Authentication successful",
                user_name=profile.get('user_name', 'Unknown')
            )
        else:
            return AuthResponse(
                success=False,
                message="Authentication failed"
            )
    
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/system", response_model=SystemStatusResponse)
async def get_system_status(monitor=Depends(get_health_monitor)):
    """Get system health status"""
    try:
        status = await monitor.get_system_status()
        return SystemStatusResponse(**status)
    
    except Exception as e:
        logger.error(f"System status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/trading")
async def get_trading_status(engine=Depends(get_trading_engine)):
    """Get trading engine status"""
    try:
        return {
            "is_running": engine.running,
            "is_trading_active": engine.is_trading_active,
            "latest_tick": engine.latest_tick,
            "active_strategy": engine.active_strategy.__class__.__name__ if engine.active_strategy else None,
            "current_positions": engine.get_positions(),
            "order_count": len(engine.get_orders()),
            "trade_count": len(engine.get_trades())
        }
    
    except Exception as e:
        logger.error(f"Trading status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pnl", response_model=PnLResponse)
async def get_pnl_summary(engine=Depends(get_trading_engine)):
    """Get PnL summary"""
    try:
        pnl_data = engine.get_pnl_summary()
        return PnLResponse(**pnl_data)
    
    except Exception as e:
        logger.error(f"PnL summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pnl/strategy/{strategy_name}")
async def get_strategy_pnl(strategy_name: str, engine=Depends(get_trading_engine)):
    """Get PnL for specific strategy"""
    try:
        if strategy_name not in engine.strategies:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        strategy = engine.strategies[strategy_name]
        return strategy.get_pnl_summary()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Strategy PnL error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders")
async def get_orders(engine=Depends(get_trading_engine)):
    """Get all orders"""
    try:
        orders = engine.get_orders()
        return {
            "orders": [
                {
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "quantity": order.quantity,
                    "price": order.price,
                    "order_type": order.order_type,
                    "status": order.status.value,
                    "timestamp": order.timestamp.isoformat(),
                    "filled_quantity": order.filled_quantity,
                    "average_price": order.average_price
                }
                for order in orders.values()
            ]
        }
    
    except Exception as e:
        logger.error(f"Get orders error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades")
async def get_trades(engine=Depends(get_trading_engine)):
    """Get all trades"""
    try:
        trades = engine.get_trades()
        return {
            "trades": [
                {
                    "trade_id": trade.trade_id,
                    "order_id": trade.order_id,
                    "symbol": trade.symbol,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "timestamp": trade.timestamp.isoformat(),
                    "pnl": trade.pnl,
                    "transaction_charges": trade.transaction_charges
                }
                for trade in trades
            ]
        }
    
    except Exception as e:
        logger.error(f"Get trades error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orderbook/{symbol}")
async def get_order_book(symbol: str, engine=Depends(get_trading_engine)):
    """Get order book for symbol"""
    try:
        order_book = engine.order_book.get_order_book(symbol)
        if not order_book:
            raise HTTPException(status_code=404, detail="Order book not found for symbol")
        
        return {
            "symbol": order_book.symbol,
            "timestamp": order_book.timestamp,
            "last_price": order_book.last_price,
            "spread": order_book.spread,
            "volume": order_book.volume,
            "bids": [
                {
                    "price": level.price,
                    "quantity": level.quantity,
                    "orders": level.orders
                }
                for level in order_book.bids
            ],
            "asks": [
                {
                    "price": level.price,
                    "quantity": level.quantity,
                    "orders": level.orders
                }
                for level in order_book.asks
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get order book error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orderbook/summary")
async def get_order_book_summary(engine=Depends(get_trading_engine)):
    """Get order book summary for all symbols"""
    try:
        summary = engine.order_book.get_order_book_summary()
        return {"order_books": summary}
    
    except Exception as e:
        logger.error(f"Get order book summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latency/summary")
async def get_latency_summary(monitor=Depends(get_latency_monitor)):
    """Get latency monitoring summary"""
    try:
        summary = monitor.get_latency_summary()
        return summary
    
    except Exception as e:
        logger.error(f"Latency summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latency/recent")
async def get_recent_latency(limit: int = 50, monitor=Depends(get_latency_monitor)):
    """Get recent latency metrics"""
    try:
        metrics = monitor.get_recent_metrics(limit)
        return {"metrics": metrics}
    
    except Exception as e:
        logger.error(f"Recent latency error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/system")
async def get_system_metrics(limit: int = 100, monitor=Depends(get_health_monitor)):
    """Get system performance metrics"""
    try:
        metrics = monitor.get_system_metrics(limit)
        return {"metrics": metrics}
    
    except Exception as e:
        logger.error(f"System metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategy/{strategy_name}/toggle")
async def toggle_strategy(strategy_name: str, engine=Depends(get_trading_engine)):
    """Toggle strategy on/off"""
    try:
        if strategy_name not in engine.strategies:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        strategy = engine.strategies[strategy_name]
        strategy.is_active = not strategy.is_active
        
        return {
            "strategy": strategy_name,
            "is_active": strategy.is_active,
            "message": f"Strategy {'activated' if strategy.is_active else 'deactivated'}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Toggle strategy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategy/{strategy_name}/paper-trading")
async def toggle_paper_trading(strategy_name: str, engine=Depends(get_trading_engine)):
    """Toggle paper trading mode for strategy"""
    try:
        if strategy_name not in engine.strategies:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        strategy = engine.strategies[strategy_name]
        if hasattr(strategy, 'config'):
            strategy.config.is_paper_trading = not strategy.config.is_paper_trading
            
            return {
                "strategy": strategy_name,
                "paper_trading": strategy.config.is_paper_trading,
                "message": f"Paper trading {'enabled' if strategy.config.is_paper_trading else 'disabled'}"
            }
        else:
            raise HTTPException(status_code=400, detail="Strategy does not support paper trading")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Toggle paper trading error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_config():
    """Get system configuration"""
    try:
        return {
            "trading": {
                "bank_nifty_symbol": Config.BANK_NIFTY_SYMBOL,
                "trading_quantity": Config.TRADING_QUANTITY,
                "profit_target_points": Config.PROFIT_TARGET_POINTS,
                "stop_loss_points": Config.STOP_LOSS_POINTS,
                "entry_time": Config.TRADE_ENTRY_TIME,
                "exit_time": Config.MARKET_CLOSE_TIME
            },
            "system": {
                "exchange": Config.EXCHANGE,
                "data_dir": Config.DATA_DIR,
                "cache_update_interval": Config.CACHE_UPDATE_INTERVAL,
                "health_check_interval": Config.HEALTH_CHECK_INTERVAL
            }
        }
    
    except Exception as e:
        logger.error(f"Get config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@router.websocket("/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time updates"""
    try:
        await websocket.accept()
        
        while True:
            # Send system status
            if health_monitor:
                status = await health_monitor.get_system_status()
                await websocket.send_json({
                    "type": "system_status",
                    "data": status
                })
            
            # Send trading status
            if trading_engine:
                await websocket.send_json({
                    "type": "trading_status",
                    "data": {
                        "is_running": trading_engine.running,
                        "latest_tick": trading_engine.latest_tick,
                        "positions": trading_engine.get_positions()
                    }
                })
            
            # Send latency metrics
            if latency_monitor:
                summary = latency_monitor.get_latency_summary()
                await websocket.send_json({
                    "type": "latency_summary",
                    "data": summary
                })
            
            await asyncio.sleep(1)  # Update every second
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

# Set global references (called by main.py)
def set_global_references(engine, health, latency):
    """Set global references to core services"""
    global trading_engine, health_monitor, latency_monitor
    trading_engine = engine
    health_monitor = health
    latency_monitor = latency
