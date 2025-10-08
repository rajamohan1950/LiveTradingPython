#!/usr/bin/env python3
"""
Test script for Live Trading System
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.trading_engine import TradingEngine
from src.core.latency_monitor import LatencyMonitor
from src.core.health_monitor import HealthMonitor
from src.core.strategy_adapter import BankNiftyStrategy
from src.core.order_book import OrderBook

async def test_trading_engine():
    """Test trading engine basic functionality"""
    print("Testing Trading Engine...")
    
    # Mock Redis client
    class MockRedis:
        def ping(self):
            return True
        def set(self, key, value, ex=None):
            pass
        def get(self, key):
            return None
    
    # Create trading engine with mocked dependencies
    engine = TradingEngine()
    engine.redis_client = MockRedis()
    
    # Test basic functionality
    print("✓ Trading engine created")
    
    # Test strategy setup
    assert 'bank_nifty' in engine.strategies
    print("✓ Bank Nifty strategy loaded")
    
    # Test tick processing
    mock_tick = {
        'instrument_token': 260105,
        'last_price': 45000.0,
        'volume': 1000,
        'timestamp': 1234567890
    }
    
    await engine.add_tick(mock_tick)
    print("✓ Tick processing works")
    
    # Test PnL summary
    pnl = engine.get_pnl_summary()
    assert 'total_pnl' in pnl
    print("✓ PnL summary works")
    
    print("✓ Trading Engine tests passed\n")

async def test_latency_monitor():
    """Test latency monitor"""
    print("Testing Latency Monitor...")
    
    monitor = LatencyMonitor()
    
    # Test metric recording
    monitor.record_tick_received({'instrument_token': 260105})
    monitor.record_redis_stored({'instrument_token': 260105})
    monitor.record_disk_written({'instrument_token': 260105})
    
    # Test summary
    summary = monitor.get_latency_summary()
    assert 'total_metrics' in summary
    print("✓ Latency monitoring works")
    
    print("✓ Latency Monitor tests passed\n")

async def test_health_monitor():
    """Test health monitor"""
    print("Testing Health Monitor...")
    
    # Mock trading engine
    class MockTradingEngine:
        def __init__(self):
            self.running = True
            self.latest_tick = {'last_price': 45000.0}
            self.redis_client = MockRedis()
            self.latency_monitor = LatencyMonitor()
        
        def get_positions(self):
            return {}
        
        def get_orders(self):
            return {}
        
        def get_trades(self):
            return []
    
    class MockRedis:
        def ping(self):
            return True
    
    engine = MockTradingEngine()
    monitor = HealthMonitor(engine)
    
    # Test health checks
    checks = await monitor._check_system_resources()
    assert len(checks) > 0
    print("✓ Health checks work")
    
    # Test system status
    status = monitor.get_system_status()
    assert 'overall_health' in status
    print("✓ System status works")
    
    print("✓ Health Monitor tests passed\n")

async def test_strategy():
    """Test Bank Nifty strategy"""
    print("Testing Bank Nifty Strategy...")
    
    strategy = BankNiftyStrategy()
    
    # Test configuration
    assert strategy.config.symbol == 'NIFTY BANK'
    assert strategy.config.quantity == 1
    print("✓ Strategy configuration correct")
    
    # Test PnL summary
    summary = strategy.get_pnl_summary()
    assert 'strategy_name' in summary
    print("✓ Strategy PnL summary works")
    
    print("✓ Bank Nifty Strategy tests passed\n")

async def test_order_book():
    """Test order book"""
    print("Testing Order Book...")
    
    order_book = OrderBook()
    
    # Test tick update
    mock_tick = {
        'instrument_token': 260105,
        'last_price': 45000.0,
        'volume': 1000,
        'bids': [
            {'price': 44999.0, 'quantity': 100},
            {'price': 44998.0, 'quantity': 200}
        ],
        'asks': [
            {'price': 45001.0, 'quantity': 150},
            {'price': 45002.0, 'quantity': 250}
        ]
    }
    
    order_book.update(mock_tick)
    
    # Test order book retrieval
    ob = order_book.get_order_book(260105)
    assert ob is not None
    print("✓ Order book update works")
    
    # Test spread calculation
    spread = order_book.get_spread(260105)
    assert spread > 0
    print("✓ Spread calculation works")
    
    print("✓ Order Book tests passed\n")

async def main():
    """Run all tests"""
    print("Live Trading System - Component Tests")
    print("=" * 50)
    
    try:
        await test_trading_engine()
        await test_latency_monitor()
        await test_health_monitor()
        await test_strategy()
        await test_order_book()
        
        print("=" * 50)
        print("✓ All component tests passed!")
        print("System is ready for deployment.")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
