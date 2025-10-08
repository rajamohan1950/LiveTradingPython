"""
Unit tests for Trading Engine
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.core.trading_engine import TradingEngine, Order, Trade, OrderStatus
from src.core.strategy_adapter import BankNiftyStrategy, StrategyConfig
from config import Config

class TestTradingEngine:
    """Test cases for TradingEngine"""
    
    @pytest.fixture
    def trading_engine(self):
        """Create a trading engine instance for testing"""
        with patch('src.core.trading_engine.redis.Redis'):
            engine = TradingEngine()
            engine.redis_client = Mock()
            engine.kite = Mock()
            return engine
    
    @pytest.fixture
    def mock_tick(self):
        """Create a mock tick data"""
        return {
            'instrument_token': 260105,
            'last_price': 45000.0,
            'volume': 1000,
            'timestamp': datetime.now().timestamp()
        }
    
    def test_trading_engine_initialization(self, trading_engine):
        """Test trading engine initialization"""
        assert trading_engine is not None
        assert trading_engine.running == False
        assert trading_engine.is_trading_active == False
        assert len(trading_engine.strategies) > 0
        assert 'bank_nifty' in trading_engine.strategies
    
    def test_strategy_setup(self, trading_engine):
        """Test strategy setup"""
        assert trading_engine.active_strategy is not None
        assert isinstance(trading_engine.active_strategy, BankNiftyStrategy)
    
    @pytest.mark.asyncio
    async def test_add_tick(self, trading_engine, mock_tick):
        """Test adding tick data"""
        await trading_engine.add_tick(mock_tick)
        
        # Check if tick was added to queue
        assert not trading_engine.tick_queue.empty()
    
    @pytest.mark.asyncio
    async def test_authenticate_kite_success(self, trading_engine):
        """Test successful Kite authentication"""
        # Mock successful authentication
        trading_engine.kite.generate_session.return_value = {
            'access_token': 'test_access_token'
        }
        trading_engine.kite.profile.return_value = {
            'user_name': 'test_user'
        }
        
        result = await trading_engine.authenticate_kite('test_request_token')
        
        assert result == True
        assert trading_engine.kite is not None
    
    @pytest.mark.asyncio
    async def test_authenticate_kite_failure(self, trading_engine):
        """Test failed Kite authentication"""
        # Mock failed authentication
        trading_engine.kite.generate_session.side_effect = Exception("Auth failed")
        
        result = await trading_engine.authenticate_kite('invalid_token')
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_place_order_success(self, trading_engine):
        """Test successful order placement"""
        trading_engine.kite.place_order.return_value = 'test_order_id'
        
        order_id = await trading_engine.place_order(
            symbol='BANKNIFTY',
            quantity=1,
            order_type='BUY',
            product='MIS'
        )
        
        assert order_id == 'test_order_id'
        assert 'test_order_id' in trading_engine.orders
    
    @pytest.mark.asyncio
    async def test_place_order_failure(self, trading_engine):
        """Test failed order placement"""
        trading_engine.kite = None  # Not authenticated
        
        order_id = await trading_engine.place_order(
            symbol='BANKNIFTY',
            quantity=1,
            order_type='BUY',
            product='MIS'
        )
        
        assert order_id is None
    
    @pytest.mark.asyncio
    async def test_cancel_order_success(self, trading_engine):
        """Test successful order cancellation"""
        trading_engine.kite.cancel_order.return_value = None
        
        # Add a test order
        order = Order(
            order_id='test_order_id',
            symbol='BANKNIFTY',
            quantity=1,
            price=45000.0,
            order_type='BUY',
            product='MIS',
            status=OrderStatus.PENDING,
            timestamp=datetime.now()
        )
        trading_engine.orders['test_order_id'] = order
        
        result = await trading_engine.cancel_order('test_order_id')
        
        assert result == True
        assert trading_engine.orders['test_order_id'].status == OrderStatus.CANCELLED
    
    def test_get_positions(self, trading_engine):
        """Test getting positions"""
        trading_engine.current_positions = {'BANKNIFTY': 1}
        
        positions = trading_engine.get_positions()
        
        assert positions == {'BANKNIFTY': 1}
    
    def test_get_orders(self, trading_engine):
        """Test getting orders"""
        order = Order(
            order_id='test_order_id',
            symbol='BANKNIFTY',
            quantity=1,
            price=45000.0,
            order_type='BUY',
            product='MIS',
            status=OrderStatus.PENDING,
            timestamp=datetime.now()
        )
        trading_engine.orders['test_order_id'] = order
        
        orders = trading_engine.get_orders()
        
        assert len(orders) == 1
        assert 'test_order_id' in orders
    
    def test_get_trades(self, trading_engine):
        """Test getting trades"""
        trade = Trade(
            trade_id='test_trade_id',
            order_id='test_order_id',
            symbol='BANKNIFTY',
            quantity=1,
            price=45000.0,
            timestamp=datetime.now()
        )
        trading_engine.trades.append(trade)
        
        trades = trading_engine.get_trades()
        
        assert len(trades) == 1
        assert trades[0].trade_id == 'test_trade_id'
    
    def test_get_pnl_summary(self, trading_engine):
        """Test getting PnL summary"""
        trade = Trade(
            trade_id='test_trade_id',
            order_id='test_order_id',
            symbol='BANKNIFTY',
            quantity=1,
            price=45000.0,
            timestamp=datetime.now(),
            pnl=100.0,
            transaction_charges=50.0
        )
        trading_engine.trades.append(trade)
        
        pnl_summary = trading_engine.get_pnl_summary()
        
        assert pnl_summary['total_pnl'] == 100.0
        assert pnl_summary['total_charges'] == 50.0
        assert pnl_summary['net_pnl'] == 50.0
        assert pnl_summary['trade_count'] == 1
    
    @pytest.mark.asyncio
    async def test_trading_loop_lifecycle(self, trading_engine):
        """Test trading loop start and stop"""
        # Start trading loop
        task = asyncio.create_task(trading_engine.start_trading_loop())
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Stop trading engine
        await trading_engine.stop()
        
        # Wait for task to complete
        await asyncio.wait_for(task, timeout=1.0)
        
        assert trading_engine.running == False

class TestBankNiftyStrategy:
    """Test cases for BankNiftyStrategy"""
    
    @pytest.fixture
    def strategy(self):
        """Create a BankNiftyStrategy instance for testing"""
        return BankNiftyStrategy()
    
    @pytest.fixture
    def mock_tick(self):
        """Create a mock tick data"""
        return {
            'instrument_token': 260105,
            'last_price': 45000.0,
            'volume': 1000,
            'timestamp': datetime.now().timestamp()
        }
    
    def test_strategy_initialization(self, strategy):
        """Test strategy initialization"""
        assert strategy.config.symbol == Config.BANK_NIFTY_SYMBOL
        assert strategy.config.quantity == Config.TRADING_QUANTITY
        assert strategy.config.profit_target_points == Config.PROFIT_TARGET_POINTS
        assert strategy.config.stop_loss_points == Config.STOP_LOSS_POINTS
        assert strategy.config.is_paper_trading == True
    
    def test_is_target_symbol(self, strategy, mock_tick):
        """Test target symbol identification"""
        # This is a simplified test - in real implementation,
        # this would check the actual symbol matching logic
        result = strategy._is_target_symbol(mock_tick)
        assert result == True
    
    def test_is_entry_time(self, strategy):
        """Test entry time checking"""
        # This would need to be tested with specific times
        # For now, just test that the method exists and returns a boolean
        result = strategy._is_entry_time()
        assert isinstance(result, bool)
    
    def test_is_exit_time(self, strategy):
        """Test exit time checking"""
        result = strategy._is_exit_time()
        assert isinstance(result, bool)
    
    def test_calculate_pnl(self, strategy):
        """Test PnL calculation"""
        strategy.entry_price = 45000.0
        strategy.position_quantity = 1
        
        pnl = strategy._calculate_pnl(46000.0)
        
        assert pnl == 950.0  # (46000 - 45000) * 1 - 50 (transaction charges)
    
    def test_get_pnl_summary(self, strategy):
        """Test getting PnL summary"""
        strategy.entry_price = 45000.0
        strategy.entry_time = datetime.now()
        strategy.position_quantity = 1
        strategy.is_position_open = True
        
        summary = strategy.get_pnl_summary()
        
        assert summary['strategy_name'] == 'BankNiftyStrategy'
        assert summary['entry_price'] == 45000.0
        assert summary['position_quantity'] == 1
        assert summary['is_position_open'] == True

class TestOrderAndTrade:
    """Test cases for Order and Trade classes"""
    
    def test_order_creation(self):
        """Test Order creation"""
        order = Order(
            order_id='test_order_id',
            symbol='BANKNIFTY',
            quantity=1,
            price=45000.0,
            order_type='BUY',
            product='MIS',
            status=OrderStatus.PENDING,
            timestamp=datetime.now()
        )
        
        assert order.order_id == 'test_order_id'
        assert order.symbol == 'BANKNIFTY'
        assert order.quantity == 1
        assert order.price == 45000.0
        assert order.order_type == 'BUY'
        assert order.product == 'MIS'
        assert order.status == OrderStatus.PENDING
        assert order.filled_quantity == 0
        assert order.average_price == 0.0
    
    def test_trade_creation(self):
        """Test Trade creation"""
        trade = Trade(
            trade_id='test_trade_id',
            order_id='test_order_id',
            symbol='BANKNIFTY',
            quantity=1,
            price=45000.0,
            timestamp=datetime.now()
        )
        
        assert trade.trade_id == 'test_trade_id'
        assert trade.order_id == 'test_order_id'
        assert trade.symbol == 'BANKNIFTY'
        assert trade.quantity == 1
        assert trade.price == 45000.0
        assert trade.pnl == 0.0
        assert trade.transaction_charges == 0.0

if __name__ == '__main__':
    pytest.main([__file__])
