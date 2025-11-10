"""
Trading Engine - Core trading logic and strategy execution
"""

import asyncio
import logging
import time
from datetime import datetime, time as dt_time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import redis
from kiteconnect import KiteConnect

from config import Config
from .latency_monitor import LatencyMonitor
from .order_book import OrderBook
from .strategy_adapter import StrategyAdapter, BankNiftyStrategy

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

@dataclass
class Order:
    order_id: str
    symbol: str
    quantity: int
    price: float
    order_type: str
    product: str
    status: OrderStatus
    timestamp: datetime
    filled_quantity: int = 0
    average_price: float = 0.0
    transaction_charges: float = 0.0

@dataclass
class Trade:
    trade_id: str
    order_id: str
    symbol: str
    quantity: int
    price: float
    timestamp: datetime
    pnl: float = 0.0
    transaction_charges: float = 0.0

class TradingEngine:
    """Main trading engine that orchestrates all trading activities"""
    
    def __init__(self):
        self.kite = None
        self.redis_client = None
        self.latency_monitor = LatencyMonitor()
        self.order_book = OrderBook()
        
        # Strategy management
        self.strategies: Dict[str, StrategyAdapter] = {}
        self.active_strategy = None
        
        # Trading state
        self.is_trading_active = False
        self.current_positions: Dict[str, float] = {}
        self.orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []
        
        # Market data
        self.latest_tick = None
        self.tick_queue = asyncio.Queue()
        
        # Background tasks
        self.tasks = []
        self.running = False
        
        self._setup_redis()
        self._setup_strategies()
    
    def _setup_redis(self):
        """Initialize Redis connection - Optional for demo mode"""
        try:
            # Skip Redis if not configured (for demo/test mode)
            if not Config.REDIS_HOST or Config.REDIS_HOST == 'localhost':
                logger.warning("Redis not configured - running in demo mode without Redis cache")
                self.redis_client = None
                return
            
            self.redis_client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                password=Config.REDIS_PASSWORD if Config.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis not available - running without Redis cache: {e}")
            self.redis_client = None  # Continue without Redis for demo mode
    
    def _setup_strategies(self):
        """Initialize trading strategies"""
        # Bank Nifty Strategy
        bank_nifty_strategy = BankNiftyStrategy()
        self.strategies["bank_nifty"] = bank_nifty_strategy
        self.active_strategy = bank_nifty_strategy
        logger.info("Strategies initialized")
    
    async def authenticate_kite(self, request_token: str) -> bool:
        """Authenticate with Kite using request token"""
        try:
            if not Config.KITE_API_KEY:
                logger.error("Kite API key not configured")
                return False
            
            self.kite = KiteConnect(api_key=Config.KITE_API_KEY)
            
            # Generate access token
            data = self.kite.generate_session(request_token, api_secret=Config.KITE_API_KEY)
            access_token = data["access_token"]
            
            # Update config and Redis (if available)
            Config.KITE_ACCESS_TOKEN = access_token
            if self.redis_client:
                self.redis_client.set("kite_access_token", access_token, ex=86400)  # 24 hours
            
            # Reinitialize with access token
            self.kite.set_access_token(access_token)
            
            # Verify connection
            profile = self.kite.profile()
            logger.info(f"Kite authentication successful for user: {profile['user_name']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Kite authentication failed: {e}")
            return False
    
    async def start_trading_loop(self):
        """Start the main trading loop"""
        self.running = True
        logger.info("Starting trading loop")
        
        # Start background tasks
        self.tasks = [
            asyncio.create_task(self._tick_consumer()),
            asyncio.create_task(self._strategy_executor()),
            asyncio.create_task(self._order_monitor()),
            asyncio.create_task(self._market_data_processor())
        ]
        
        try:
            await asyncio.gather(*self.tasks)
        except Exception as e:
            logger.error(f"Trading loop error: {e}")
        finally:
            self.running = False
    
    async def stop(self):
        """Stop the trading engine"""
        logger.info("Stopping trading engine")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("Trading engine stopped")
    
    async def _tick_consumer(self):
        """Consume tick data from queue and process"""
        while self.running:
            try:
                # Get tick from queue with timeout
                tick = await asyncio.wait_for(self.tick_queue.get(), timeout=1.0)
                
                # Record latency - tick received
                self.latency_monitor.record_tick_received(tick)
                
                # Update latest tick
                self.latest_tick = tick
                
                # Store in Redis
                await self._store_tick_in_redis(tick)
                
                # Update order book
                self.order_book.update(tick)
                
                # Process strategy
                if self.active_strategy:
                    await self.active_strategy.process_tick(tick, self)
                
                self.tick_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Tick consumer error: {e}")
    
    async def _strategy_executor(self):
        """Execute trading strategy logic"""
        while self.running:
            try:
                if self.active_strategy and self.latest_tick:
                    # Check if it's time to trade
                    current_time = datetime.now().time()
                    
                    # Market open check
                    if self._is_market_open():
                        await self.active_strategy.execute(self.latest_tick, self)
                    
                    # Market close check
                    if self._is_market_close():
                        await self.active_strategy.close_positions(self)
                
                await asyncio.sleep(0.1)  # 100ms check interval
                
            except Exception as e:
                logger.error(f"Strategy executor error: {e}")
                await asyncio.sleep(1)
    
    async def _order_monitor(self):
        """Monitor order status and update positions"""
        while self.running:
            try:
                if self.kite and self.orders:
                    # Check order status
                    for order_id, order in list(self.orders.items()):
                        if order.status in [OrderStatus.PENDING, OrderStatus.OPEN]:
                            await self._update_order_status(order_id)
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Order monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _market_data_processor(self):
        """Process market data and update positions"""
        while self.running:
            try:
                if self.latest_tick:
                    # Update current positions based on latest price
                    await self._update_positions()
                
                await asyncio.sleep(0.5)  # Update every 500ms
                
            except Exception as e:
                logger.error(f"Market data processor error: {e}")
                await asyncio.sleep(1)
    
    async def _store_tick_in_redis(self, tick: Dict[str, Any]):
        """Store tick data in Redis cache - Optional"""
        if not self.redis_client:
            return  # Skip if Redis not available
        
        try:
            # Store latest tick
            self.redis_client.set("latest_tick", str(tick), ex=60)
            
            # Store in time series
            timestamp = int(time.time())
            self.redis_client.zadd("tick_data", {str(tick): timestamp})
            
            # Keep only last 1000 ticks
            self.redis_client.zremrangebyrank("tick_data", 0, -1001)
            
        except Exception as e:
            logger.debug(f"Redis storage skipped: {e}")  # Don't error, just skip
    
    async def _update_order_status(self, order_id: str):
        """Update order status from Kite"""
        try:
            order_history = self.kite.order_history(order_id)
            if order_history:
                latest_status = order_history[-1]
                
                order = self.orders[order_id]
                order.status = OrderStatus(latest_status['status'])
                order.filled_quantity = latest_status['filled_quantity']
                order.average_price = latest_status['average_price']
                
                # If order is complete, create trade record
                if order.status == OrderStatus.COMPLETE and order.filled_quantity > 0:
                    await self._create_trade_record(order)
                
        except Exception as e:
            logger.error(f"Failed to update order status: {e}")
    
    async def _create_trade_record(self, order: Order):
        """Create trade record from completed order"""
        trade = Trade(
            trade_id=f"trade_{int(time.time())}",
            order_id=order.order_id,
            symbol=order.symbol,
            quantity=order.filled_quantity,
            price=order.average_price,
            timestamp=datetime.now(),
            transaction_charges=order.transaction_charges
        )
        
        self.trades.append(trade)
        
        # Update positions
        if order.symbol not in self.current_positions:
            self.current_positions[order.symbol] = 0
        
        # Add to position (positive for buy, negative for sell)
        quantity = order.filled_quantity if order.order_type == 'BUY' else -order.filled_quantity
        self.current_positions[order.symbol] += quantity
        
        logger.info(f"Trade executed: {trade}")
    
    async def _update_positions(self):
        """Update current positions based on latest market price"""
        if not self.latest_tick or not self.current_positions:
            return
        
        # Calculate unrealized PnL
        for symbol, quantity in self.current_positions.items():
            if quantity != 0 and symbol in self.latest_tick:
                current_price = self.latest_tick.get('last_price', 0)
                # This would need to be calculated based on average entry price
                # For now, just log the current position
                logger.debug(f"Position: {symbol} = {quantity} @ {current_price}")
    
    def _is_market_open(self) -> bool:
        """Check if market is currently open"""
        current_time = datetime.now().time()
        market_open = dt_time(9, 15)
        market_close = dt_time(15, 30)
        return market_open <= current_time <= market_close
    
    def _is_market_close(self) -> bool:
        """Check if it's market close time"""
        current_time = datetime.now().time()
        market_close = dt_time(15, 15)
        return current_time >= market_close
    
    async def place_order(self, symbol: str, quantity: int, order_type: str, 
                         product: str, price: float = None, user_type: str = 'real') -> Optional[str]:
        """Place order through Kite"""
        try:
            # Block order placement for test users
            if user_type == 'test':
                logger.warning(f"TEST MODE: Order placement blocked for test user. Would place: {order_type} {quantity} {symbol}")
                # Create simulated order for test users
                import uuid
                order_id = f"TEST_{uuid.uuid4().hex[:8]}"
                order = Order(
                    order_id=order_id,
                    symbol=symbol,
                    quantity=quantity,
                    price=price or 0,
                    order_type=order_type,
                    product=product,
                    status=OrderStatus.PENDING,
                    timestamp=datetime.now()
                )
                self.orders[order_id] = order
                logger.info(f"TEST MODE: Simulated order created: {order_id}")
                return order_id
            
            if not self.kite:
                logger.error("Kite not authenticated")
                return None
            
            # Record latency - order creation start
            self.latency_monitor.record_order_creation_start()
            
            # Prepare order parameters
            order_params = {
                'variety': 'regular',
                'exchange': Config.EXCHANGE,
                'tradingsymbol': symbol,
                'transaction_type': order_type,
                'quantity': quantity,
                'product': product,
                'order_type': 'MARKET' if price is None else 'LIMIT'
            }
            
            if price is not None:
                order_params['price'] = price
            
            # Place order
            order_id = self.kite.place_order(**order_params)
            
            # Record latency - order sent
            self.latency_monitor.record_order_sent(order_id)
            
            # Create order record
            order = Order(
                order_id=order_id,
                symbol=symbol,
                quantity=quantity,
                price=price or 0,
                order_type=order_type,
                product=product,
                status=OrderStatus.PENDING,
                timestamp=datetime.now()
            )
            
            self.orders[order_id] = order
            
            logger.info(f"Order placed: {order}")
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        try:
            if not self.kite:
                return False
            
            self.kite.cancel_order(variety='regular', order_id=order_id)
            
            if order_id in self.orders:
                self.orders[order_id].status = OrderStatus.CANCELLED
            
            logger.info(f"Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False
    
    def get_positions(self) -> Dict[str, float]:
        """Get current positions"""
        return self.current_positions.copy()
    
    def get_orders(self) -> Dict[str, Order]:
        """Get all orders"""
        return self.orders.copy()
    
    def get_trades(self) -> List[Trade]:
        """Get all trades"""
        return self.trades.copy()
    
    def get_pnl_summary(self) -> Dict[str, Any]:
        """Get PnL summary"""
        total_pnl = 0.0
        total_charges = 0.0
        
        for trade in self.trades:
            total_pnl += trade.pnl
            total_charges += trade.transaction_charges
        
        return {
            'total_pnl': total_pnl,
            'total_charges': total_charges,
            'net_pnl': total_pnl - total_charges,
            'trade_count': len(self.trades),
            'current_positions': self.current_positions
        }
    
    async def add_tick(self, tick: Dict[str, Any]):
        """Add tick data to processing queue"""
        await self.tick_queue.put(tick)
