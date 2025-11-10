"""
API Routes - REST API endpoints for the trading system
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi import Request as FastAPIRequest
from pydantic import BaseModel
import asyncio

from config import Config

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class AuthRequest(BaseModel):
    api_key: str
    api_secret: str
    request_token: str

class TestAuthRequest(BaseModel):
    username: str
    password: str

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

@router.post("/auth/test")
async def authenticate_test(request: TestAuthRequest):
    """Test/Demo login - bypasses Kite API for demo purposes"""
    from config import Config
    import uuid
    import sys
    from datetime import datetime
    
    # Check test credentials
    if request.username == Config.TEST_USERNAME and request.password == Config.TEST_PASSWORD:
        # Create session
        session_id = str(uuid.uuid4())
        
        # Get authenticated_sessions from main module
        main_module = sys.modules.get('main')
        if main_module and hasattr(main_module, 'authenticated_sessions'):
            main_module.authenticated_sessions[session_id] = {
                'user_type': 'test',
                'username': request.username,
                'authenticated_at': datetime.now()
            }
        
        response = JSONResponse(content={
            "success": True,
            "message": "Test login successful",
            "username": request.username,
            "user_type": "test"
        })
        response.set_cookie(key="session_id", value=session_id, max_age=86400, httponly=True)
        return response
    else:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": "Invalid test credentials"
            }
        )

@router.post("/auth/kite", response_model=AuthResponse)
async def authenticate_kite(request: AuthRequest, engine=Depends(get_trading_engine)):
    """Authenticate with Kite using API key and request token"""
    try:
        # Update the engine's API key
        engine.kite = None  # Reset existing connection
        
        # Create new KiteConnect instance with the provided API key
        from kiteconnect import KiteConnect
        engine.kite = KiteConnect(api_key=request.api_key)
        
        # Generate access token using provided API secret
        data = engine.kite.generate_session(request.request_token, api_secret=request.api_secret)
        access_token = data["access_token"]
        
        # Update config and Redis
        from config import Config
        import os
        Config.KITE_API_KEY = request.api_key
        Config.KITE_ACCESS_TOKEN = access_token
        os.environ['KITE_API_KEY'] = request.api_key
        os.environ['KITE_ACCESS_TOKEN'] = access_token
        
        engine.redis_client.set("kite_api_key", request.api_key, ex=86400)
        engine.redis_client.set("kite_access_token", access_token, ex=86400)
        
        # Reinitialize with access token
        engine.kite.set_access_token(access_token)
        
        # Verify connection
        profile = engine.kite.profile()
        
        # Mark as authenticated - update main app's session storage
        import uuid
        import sys
        from datetime import datetime
        session_id = str(uuid.uuid4())
        
        # Get authenticated_sessions from main module
        main_module = sys.modules.get('main')
        if main_module and hasattr(main_module, 'authenticated_sessions'):
            main_module.authenticated_sessions[session_id] = {
                'user_type': 'real',
                'username': profile.get('user_name', 'Unknown'),
                'authenticated_at': datetime.now()
            }
        
        response = AuthResponse(
            success=True,
            message="Authentication successful",
            user_name=profile.get('user_name', 'Unknown')
        )
        
        # Return response with session cookie
        json_response = JSONResponse(content=response.dict())
        json_response.set_cookie(key="session_id", value=session_id, max_age=86400, httponly=True)
        return json_response
    
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return AuthResponse(
            success=False,
            message=f"Authentication failed: {str(e)}"
        )

def check_api_auth(request: FastAPIRequest = None):
    """Check if API is authenticated"""
    from main import check_authentication
    if request and not check_authentication(request):
        raise HTTPException(status_code=401, detail="Not authenticated. Please login first.")
    return True

def get_user_type_from_request(request: FastAPIRequest) -> str:
    """Get user type from request"""
    from main import get_user_type
    return get_user_type(request) if request else 'real'

def generate_simulated_orders(count: int = 15) -> List[Dict[str, Any]]:
    """Generate simulated order data for demo users"""
    import random
    import uuid
    from datetime import datetime, timedelta
    
    symbols = ['NIFTY BANK', 'NIFTY 50', 'SENSEX', 'RELIANCE', 'TCS', 'INFY']
    order_types = ['BUY', 'SELL']
    statuses = ['COMPLETE', 'PENDING', 'OPEN', 'REJECTED', 'CANCELLED']
    
    orders = []
    base_time = datetime.now()
    
    for i in range(count):
        order_time = base_time - timedelta(minutes=random.randint(1, 1440))
        symbol = random.choice(symbols)
        order_type = random.choice(order_types)
        status = random.choice(statuses)
        price = random.uniform(40000, 50000)
        quantity = random.choice([1, 2, 3, 5, 10])
        
        filled_qty = quantity if status == 'COMPLETE' else random.randint(0, quantity)
        avg_price = price if status == 'COMPLETE' else None
        
        orders.append({
            "order_id": f"TEST_{uuid.uuid4().hex[:8].upper()}",
            "symbol": symbol,
            "quantity": quantity,
            "price": round(price, 2),
            "order_type": order_type,
            "status": status,
            "timestamp": order_time.isoformat(),
            "filled_quantity": filled_qty,
            "average_price": round(avg_price, 2) if avg_price else None
        })
    
    return sorted(orders, key=lambda x: x['timestamp'], reverse=True)

def generate_simulated_trades(count: int = 18) -> List[Dict[str, Any]]:
    """Generate simulated trade data for demo users"""
    import random
    import uuid
    from datetime import datetime, timedelta
    
    symbols = ['NIFTY BANK', 'NIFTY 50', 'SENSEX', 'RELIANCE', 'TCS', 'INFY']
    
    trades = []
    base_time = datetime.now()
    
    for i in range(count):
        trade_time = base_time - timedelta(minutes=random.randint(1, 1440))
        symbol = random.choice(symbols)
        quantity = random.choice([1, 2, 3, 5, 10])
        price = random.uniform(40000, 50000)
        pnl = random.uniform(-5000, 15000)
        charges = random.uniform(50, 500)
        
        trades.append({
            "trade_id": f"TRADE_{uuid.uuid4().hex[:8].upper()}",
            "order_id": f"TEST_{uuid.uuid4().hex[:8].upper()}",
            "symbol": symbol,
            "quantity": quantity,
            "price": round(price, 2),
            "timestamp": trade_time.isoformat(),
            "pnl": round(pnl, 2),
            "transaction_charges": round(charges, 2)
        })
    
    return sorted(trades, key=lambda x: x['timestamp'], reverse=True)

def generate_simulated_pnl() -> Dict[str, Any]:
    """Generate simulated PnL data for demo users"""
    import random
    
    total_pnl = random.uniform(-50000, 200000)
    total_charges = random.uniform(5000, 25000)
    net_pnl = total_pnl - total_charges
    trade_count = random.randint(15, 25)
    
    positions = {
        'NIFTY BANK': random.choice([0, 1, 2, -1, -2]),
        'NIFTY 50': random.choice([0, 1, -1]),
        'RELIANCE': random.choice([0, 5, 10, -5])
    }
    positions = {k: v for k, v in positions.items() if v != 0}
    
    return {
        "total_pnl": round(total_pnl, 2),
        "total_charges": round(total_charges, 2),
        "net_pnl": round(net_pnl, 2),
        "trade_count": trade_count,
        "current_positions": positions
    }

@router.get("/status/system", response_model=SystemStatusResponse)
async def get_system_status(request: FastAPIRequest, monitor=Depends(get_health_monitor)):
    """Get system health status - requires authentication"""
    check_api_auth(request)
    user_type = get_user_type_from_request(request)
    
    try:
        # For test users, return simulated health data
        if user_type == 'test':
            from datetime import datetime
            return SystemStatusResponse(
                overall_health=True,
                critical_issues=0,
                warning_issues=1,
                last_check=datetime.now().isoformat(),
                recent_checks=[
                    {"name": "cpu_usage", "status": "healthy", "message": "CPU usage normal: 15.2%", "timestamp": datetime.now().isoformat()},
                    {"name": "memory_usage", "status": "healthy", "message": "Memory usage normal: 68.5%", "timestamp": datetime.now().isoformat()},
                    {"name": "disk_usage", "status": "healthy", "message": "Disk usage normal: 3.8%", "timestamp": datetime.now().isoformat()},
                    {"name": "trading_engine", "status": "healthy", "message": "Trading engine running normally", "timestamp": datetime.now().isoformat()},
                    {"name": "tick_data", "status": "warning", "message": "Simulated tick data (demo mode)", "timestamp": datetime.now().isoformat()},
                    {"name": "network_connectivity", "status": "healthy", "message": "Network connectivity normal", "timestamp": datetime.now().isoformat()},
                    {"name": "kite_api", "status": "healthy", "message": "Demo mode - API simulation", "timestamp": datetime.now().isoformat()},
                    {"name": "redis", "status": "healthy", "message": "Redis connection normal", "timestamp": datetime.now().isoformat()}
                ]
            )
        
        status = monitor.get_system_status()  # Remove await - it's not async
        return SystemStatusResponse(**status)
    
    except Exception as e:
        logger.error(f"System status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/trading")
async def get_trading_status(request: FastAPIRequest, engine=Depends(get_trading_engine)):
    """Get trading engine status - requires authentication"""
    check_api_auth(request)
    user_type = get_user_type_from_request(request)
    
    try:
        # For test users, return simulated data
        if user_type == 'test':
            return {
                "is_running": True,
                "is_trading_active": False,
                "latest_tick": {"last_price": 45000, "volume": 1000, "timestamp": datetime.now().isoformat()},
                "active_strategy": "BankNiftyStrategy",
                "current_positions": {},
                "order_count": len(engine.get_orders()),
                "trade_count": len(engine.get_trades()),
                "user_type": "test",
                "mode": "DEMO - Orders are simulated"
            }
        
        return {
            "is_running": engine.running,
            "is_trading_active": engine.is_trading_active,
            "latest_tick": engine.latest_tick,
            "active_strategy": engine.active_strategy.__class__.__name__ if engine.active_strategy else None,
            "current_positions": engine.get_positions(),
            "order_count": len(engine.get_orders()),
            "trade_count": len(engine.get_trades()),
            "user_type": "real"
        }
    
    except Exception as e:
        logger.error(f"Trading status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pnl", response_model=PnLResponse)
async def get_pnl_summary(request: FastAPIRequest, engine=Depends(get_trading_engine)):
    """Get PnL summary - requires authentication"""
    check_api_auth(request)
    user_type = get_user_type_from_request(request)
    
    try:
        # For test users, return simulated PnL data
        if user_type == 'test':
            pnl_data = generate_simulated_pnl()
            return PnLResponse(**pnl_data)
        
        pnl_data = engine.get_pnl_summary()
        return PnLResponse(**pnl_data)
    
    except Exception as e:
        logger.error(f"PnL summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pnl/strategy/{strategy_name}")
async def get_strategy_pnl(strategy_name: str, request: FastAPIRequest, engine=Depends(get_trading_engine)):
    """Get PnL for specific strategy - requires authentication"""
    check_api_auth(request)
    user_type = get_user_type_from_request(request)
    
    try:
        # For test users, return simulated strategy PnL
        if user_type == 'test':
            import random
            return {
                "total_pnl": round(random.uniform(-20000, 100000), 2),
                "total_charges": round(random.uniform(2000, 10000), 2),
                "net_pnl": round(random.uniform(-25000, 90000), 2),
                "trade_count": random.randint(10, 20),
                "win_rate": round(random.uniform(45, 75), 1)
            }
        
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
async def get_orders(request: FastAPIRequest, engine=Depends(get_trading_engine)):
    """Get all orders - requires authentication"""
    check_api_auth(request)
    user_type = get_user_type_from_request(request)
    
    try:
        # For test users, return simulated orders
        if user_type == 'test':
            return {
                "orders": generate_simulated_orders(15)
            }
        
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
async def get_trades(request: FastAPIRequest, engine=Depends(get_trading_engine)):
    """Get all trades - requires authentication"""
    check_api_auth(request)
    user_type = get_user_type_from_request(request)
    
    try:
        # For test users, return simulated trades
        if user_type == 'test':
            return {
                "trades": generate_simulated_trades(18)
            }
        
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
async def get_order_book(symbol: str, request: FastAPIRequest, engine=Depends(get_trading_engine)):
    """Get order book for symbol - requires authentication"""
    check_api_auth(request)
    user_type = get_user_type_from_request(request)
    
    try:
        # For test users, return simulated order book
        if user_type == 'test':
            import random
            base_price = 45000
            bids = []
            asks = []
            for i in range(5):
                bids.append({
                    "price": round(base_price - (i+1) * 5, 2),
                    "quantity": random.randint(100, 1000),
                    "orders": random.randint(5, 20)
                })
                asks.append({
                    "price": round(base_price + (i+1) * 5, 2),
                    "quantity": random.randint(100, 1000),
                    "orders": random.randint(5, 20)
                })
            return {
                "symbol": symbol,
                "timestamp": datetime.now().timestamp(),
                "last_price": base_price,
                "spread": 10.0,
                "volume": random.randint(50000, 200000),
                "bids": bids,
                "asks": asks
            }
        
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
async def get_order_book_summary(request: FastAPIRequest, engine=Depends(get_trading_engine)):
    """Get order book summary for all symbols - requires authentication"""
    check_api_auth(request)
    try:
        summary = engine.order_book.get_order_book_summary()
        return {"order_books": summary}
    
    except Exception as e:
        logger.error(f"Get order book summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latency/summary")
async def get_latency_summary(request: FastAPIRequest, monitor=Depends(get_latency_monitor)):
    """Get latency monitoring summary - requires authentication"""
    check_api_auth(request)
    user_type = get_user_type_from_request(request)
    
    try:
        # For test users, return simulated latency data
        if user_type == 'test':
            return {
                "avg_tick_latency_us": 125.5,
                "max_tick_latency_us": 450.2,
                "avg_order_latency_ms": 12.8,
                "max_order_latency_ms": 45.3,
                "total_ticks": 15420,
                "total_orders": 156
            }
        
        summary = monitor.get_latency_summary()
        return summary
    
    except Exception as e:
        logger.error(f"Latency summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latency/recent")
async def get_recent_latency(limit: int = 50, request: FastAPIRequest = None, monitor=Depends(get_latency_monitor)):
    """Get recent latency metrics - requires authentication"""
    if request:
        check_api_auth(request)
    try:
        metrics = monitor.get_recent_metrics(limit)
        return {"metrics": metrics}
    
    except Exception as e:
        logger.error(f"Recent latency error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/system")
async def get_system_metrics(limit: int = 100, request: FastAPIRequest = None, monitor=Depends(get_health_monitor)):
    """Get system performance metrics - requires authentication"""
    if request:
        check_api_auth(request)
        user_type = get_user_type_from_request(request)
    
    try:
        # For test users, return simulated metrics
        if request and user_type == 'test':
            import random
            from datetime import datetime, timedelta
            metrics = []
            base_time = datetime.now()
            for i in range(min(limit, 20)):
                metrics.append({
                    "timestamp": (base_time - timedelta(minutes=i*5)).isoformat(),
                    "cpu_percent": round(random.uniform(10, 25), 1),
                    "memory_percent": round(random.uniform(60, 75), 1),
                    "disk_percent": round(random.uniform(2, 5), 1)
                })
            return {"metrics": metrics}
        
        metrics = monitor.get_system_metrics(limit)
        return {"metrics": metrics}
    
    except Exception as e:
        logger.error(f"System metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategy/{strategy_name}/toggle")
async def toggle_strategy(strategy_name: str, request: FastAPIRequest, engine=Depends(get_trading_engine)):
    """Toggle strategy on/off - requires authentication"""
    check_api_auth(request)
    user_type = get_user_type_from_request(request)
    
    # Block strategy toggling for test users
    if user_type == 'test':
        raise HTTPException(status_code=403, detail="Test users cannot modify strategies")
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
async def toggle_paper_trading(strategy_name: str, request: FastAPIRequest, engine=Depends(get_trading_engine)):
    """Toggle paper trading mode for strategy - requires authentication"""
    check_api_auth(request)
    user_type = get_user_type_from_request(request)
    
    # Block paper trading toggle for test users
    if user_type == 'test':
        raise HTTPException(status_code=403, detail="Test users cannot modify paper trading settings")
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
async def get_config(request: FastAPIRequest = None):
    """Get system configuration - requires authentication"""
    if request:
        check_api_auth(request)
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

# WebSocket endpoint for real-time updates (disabled for now)
# @router.websocket("/ws")
# async def websocket_endpoint(websocket):
#     """WebSocket endpoint for real-time updates"""
#     try:
#         await websocket.accept()
#         
#         while True:
#             # Send system status
#             if health_monitor:
#                 status = health_monitor.get_system_status()
#                 await websocket.send_json({
#                     "type": "system_status",
#                     "data": status
#                 })
#             
#             # Send trading status
#             if trading_engine:
#                 await websocket.send_json({
#                     "type": "trading_status",
#                     "data": {
#                         "is_running": trading_engine.running,
#                         "latest_tick": trading_engine.latest_tick,
#                         "positions": trading_engine.get_positions()
#                     }
#                 })
#             
#             # Send latency metrics
#             if latency_monitor:
#                 summary = latency_monitor.get_latency_summary()
#                 await websocket.send_json({
#                     "type": "latency_summary",
#                     "data": summary
#                 })
#             
#             await asyncio.sleep(1)  # Update every second
#     
#     except Exception as e:
#         logger.error(f"WebSocket error: {e}")
#         await websocket.close()

# Set global references (called by main.py)
def set_global_references(engine, health, latency):
    """Set global references to core services"""
    global trading_engine, health_monitor, latency_monitor
    trading_engine = engine
    health_monitor = health
    latency_monitor = latency
