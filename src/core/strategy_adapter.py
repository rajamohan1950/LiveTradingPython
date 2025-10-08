"""
Strategy Adapter Pattern - Base class for all trading strategies
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, time as dt_time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from config import Config

logger = logging.getLogger(__name__)

@dataclass
class StrategyConfig:
    """Configuration for trading strategy"""
    symbol: str
    quantity: int
    profit_target_points: int
    stop_loss_points: int
    entry_time: str
    exit_time: str
    is_paper_trading: bool = True

class StrategyAdapter(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.is_active = False
        self.entry_price = None
        self.entry_time = None
        self.profit_order_id = None
        self.stop_loss_order_id = None
        self.exit_order_id = None
        self.position_quantity = 0
        self.is_position_open = False
        
    @abstractmethod
    async def process_tick(self, tick: Dict[str, Any], trading_engine) -> None:
        """Process incoming tick data"""
        pass
    
    @abstractmethod
    async def execute(self, tick: Dict[str, Any], trading_engine) -> None:
        """Execute strategy logic"""
        pass
    
    @abstractmethod
    async def close_positions(self, trading_engine) -> None:
        """Close all positions at market close"""
        pass
    
    def get_pnl_summary(self) -> Dict[str, Any]:
        """Get PnL summary for this strategy"""
        return {
            'strategy_name': self.__class__.__name__,
            'is_active': self.is_active,
            'is_position_open': self.is_position_open,
            'position_quantity': self.position_quantity,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'profit_target_points': self.config.profit_target_points,
            'stop_loss_points': self.config.stop_loss_points
        }

class BankNiftyStrategy(StrategyAdapter):
    """Bank Nifty trading strategy implementation"""
    
    def __init__(self):
        config = StrategyConfig(
            symbol=Config.BANK_NIFTY_SYMBOL,
            quantity=Config.TRADING_QUANTITY,
            profit_target_points=Config.PROFIT_TARGET_POINTS,
            stop_loss_points=Config.STOP_LOSS_POINTS,
            entry_time=Config.TRADE_ENTRY_TIME,
            exit_time=Config.MARKET_CLOSE_TIME,
            is_paper_trading=True  # Start with paper trading
        )
        super().__init__(config)
        
        # Strategy state
        self.entry_completed = False
        self.profit_order_placed = False
        self.stop_loss_order_placed = False
        self.exit_order_placed = False
        
        logger.info(f"Bank Nifty Strategy initialized: {config}")
    
    async def process_tick(self, tick: Dict[str, Any], trading_engine) -> None:
        """Process incoming tick data for Bank Nifty"""
        try:
            # Check if this is our target symbol
            if not self._is_target_symbol(tick):
                return
            
            current_price = tick.get('last_price', 0)
            current_time = datetime.now().time()
            
            # Log tick processing
            logger.debug(f"Processing Bank Nifty tick: {current_price} at {current_time}")
            
            # Check for entry signal
            if not self.entry_completed and self._is_entry_time():
                await self._execute_entry(tick, trading_engine)
            
            # Check for profit target hit
            elif self.entry_completed and self.profit_order_id and not self.profit_order_placed:
                await self._check_profit_target(tick, trading_engine)
            
            # Check for stop loss hit
            elif self.entry_completed and self.stop_loss_order_id and not self.stop_loss_order_placed:
                await self._check_stop_loss(tick, trading_engine)
            
            # Check for market close exit
            elif self.entry_completed and self._is_exit_time() and not self.exit_order_placed:
                await self._execute_exit(tick, trading_engine)
                
        except Exception as e:
            logger.error(f"Error processing Bank Nifty tick: {e}")
    
    async def execute(self, tick: Dict[str, Any], trading_engine) -> None:
        """Execute Bank Nifty strategy logic"""
        # This method is called by the trading engine
        # The actual logic is in process_tick
        pass
    
    async def close_positions(self, trading_engine) -> None:
        """Close all positions at market close"""
        try:
            if self.is_position_open and not self.exit_order_placed:
                logger.info("Market close - executing exit order")
                await self._execute_exit(tick=None, trading_engine=trading_engine)
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
    
    def _is_target_symbol(self, tick: Dict[str, Any]) -> bool:
        """Check if tick is for our target symbol"""
        # This would need to be implemented based on how Kite sends symbol data
        # For now, assume we're filtering at a higher level
        return True
    
    def _is_entry_time(self) -> bool:
        """Check if it's time to enter the trade"""
        current_time = datetime.now().time()
        entry_time = dt_time(9, 45)  # 9:45 AM
        return current_time >= entry_time and not self.entry_completed
    
    def _is_exit_time(self) -> bool:
        """Check if it's time to exit the trade"""
        current_time = datetime.now().time()
        exit_time = dt_time(15, 15)  # 3:15 PM
        return current_time >= exit_time
    
    async def _execute_entry(self, tick: Dict[str, Any], trading_engine) -> None:
        """Execute entry order at 9:45 AM"""
        try:
            current_price = tick.get('last_price', 0)
            
            if self.config.is_paper_trading:
                # Paper trading - just log the action
                logger.info(f"PAPER TRADE: Would buy {self.config.quantity} {self.config.symbol} at {current_price}")
                self.entry_price = current_price
                self.entry_time = datetime.now()
                self.position_quantity = self.config.quantity
                self.is_position_open = True
                self.entry_completed = True
                
                # Send email notification
                await self._send_entry_notification(current_price)
                
            else:
                # Live trading
                order_id = await trading_engine.place_order(
                    symbol=self.config.symbol,
                    quantity=self.config.quantity,
                    order_type='BUY',
                    product='MIS'  # Intraday
                )
                
                if order_id:
                    self.entry_price = current_price
                    self.entry_time = datetime.now()
                    self.position_quantity = self.config.quantity
                    self.is_position_open = True
                    self.entry_completed = True
                    
                    # Place profit target order
                    await self._place_profit_target_order(trading_engine)
                    
                    # Place stop loss order
                    await self._place_stop_loss_order(trading_engine)
                    
                    # Send email notification
                    await self._send_entry_notification(current_price)
            
        except Exception as e:
            logger.error(f"Error executing entry: {e}")
    
    async def _place_profit_target_order(self, trading_engine) -> None:
        """Place profit target sell order"""
        try:
            if not self.entry_price:
                return
            
            target_price = self.entry_price + self.config.profit_target_points
            
            if self.config.is_paper_trading:
                logger.info(f"PAPER TRADE: Would place sell order at {target_price}")
                self.profit_order_placed = True
            else:
                order_id = await trading_engine.place_order(
                    symbol=self.config.symbol,
                    quantity=self.config.quantity,
                    order_type='SELL',
                    product='MIS',
                    price=target_price
                )
                
                if order_id:
                    self.profit_order_id = order_id
                    logger.info(f"Profit target order placed: {order_id} at {target_price}")
        
        except Exception as e:
            logger.error(f"Error placing profit target order: {e}")
    
    async def _place_stop_loss_order(self, trading_engine) -> None:
        """Place stop loss sell order"""
        try:
            if not self.entry_price:
                return
            
            stop_loss_price = self.entry_price - self.config.stop_loss_points
            
            if self.config.is_paper_trading:
                logger.info(f"PAPER TRADE: Would place stop loss order at {stop_loss_price}")
                self.stop_loss_order_placed = True
            else:
                order_id = await trading_engine.place_order(
                    symbol=self.config.symbol,
                    quantity=self.config.quantity,
                    order_type='SELL',
                    product='MIS',
                    price=stop_loss_price
                )
                
                if order_id:
                    self.stop_loss_order_id = order_id
                    logger.info(f"Stop loss order placed: {order_id} at {stop_loss_price}")
        
        except Exception as e:
            logger.error(f"Error placing stop loss order: {e}")
    
    async def _check_profit_target(self, tick: Dict[str, Any], trading_engine) -> None:
        """Check if profit target is hit"""
        current_price = tick.get('last_price', 0)
        target_price = self.entry_price + self.config.profit_target_points
        
        if current_price >= target_price:
            logger.info(f"Profit target hit: {current_price} >= {target_price}")
            self.profit_order_placed = True
            await self._send_profit_target_notification(current_price)
    
    async def _check_stop_loss(self, tick: Dict[str, Any], trading_engine) -> None:
        """Check if stop loss is hit"""
        current_price = tick.get('last_price', 0)
        stop_loss_price = self.entry_price - self.config.stop_loss_points
        
        if current_price <= stop_loss_price:
            logger.info(f"Stop loss hit: {current_price} <= {stop_loss_price}")
            self.stop_loss_order_placed = True
            await self._send_stop_loss_notification(current_price)
    
    async def _execute_exit(self, tick: Dict[str, Any], trading_engine) -> None:
        """Execute market exit order at 3:15 PM"""
        try:
            current_price = tick.get('last_price', 0) if tick else 0
            
            if self.config.is_paper_trading:
                logger.info(f"PAPER TRADE: Would sell {self.config.quantity} {self.config.symbol} at market price")
                self.exit_order_placed = True
                self.is_position_open = False
                
                # Calculate PnL
                pnl = self._calculate_pnl(current_price)
                await self._send_exit_notification(current_price, pnl)
                
            else:
                # Cancel existing orders first
                if self.profit_order_id:
                    await trading_engine.cancel_order(self.profit_order_id)
                if self.stop_loss_order_id:
                    await trading_engine.cancel_order(self.stop_loss_order_id)
                
                # Place market exit order
                order_id = await trading_engine.place_order(
                    symbol=self.config.symbol,
                    quantity=self.config.quantity,
                    order_type='SELL',
                    product='MIS'
                )
                
                if order_id:
                    self.exit_order_id = order_id
                    self.exit_order_placed = True
                    logger.info(f"Exit order placed: {order_id}")
        
        except Exception as e:
            logger.error(f"Error executing exit: {e}")
    
    def _calculate_pnl(self, exit_price: float) -> float:
        """Calculate PnL for the trade"""
        if not self.entry_price or not self.position_quantity:
            return 0.0
        
        # PnL = (Exit Price - Entry Price) * Quantity
        pnl = (exit_price - self.entry_price) * self.position_quantity
        
        # Subtract transaction charges (approximate)
        transaction_charges = 50.0  # Rs 50 per transaction
        net_pnl = pnl - transaction_charges
        
        return net_pnl
    
    async def _send_entry_notification(self, price: float) -> None:
        """Send email notification for entry"""
        # This would integrate with email service
        logger.info(f"ENTRY NOTIFICATION: Bought {self.config.symbol} at {price}")
    
    async def _send_profit_target_notification(self, price: float) -> None:
        """Send email notification for profit target hit"""
        logger.info(f"PROFIT TARGET NOTIFICATION: {self.config.symbol} hit profit target at {price}")
    
    async def _send_stop_loss_notification(self, price: float) -> None:
        """Send email notification for stop loss hit"""
        logger.info(f"STOP LOSS NOTIFICATION: {self.config.symbol} hit stop loss at {price}")
    
    async def _send_exit_notification(self, price: float, pnl: float) -> None:
        """Send email notification for exit"""
        logger.info(f"EXIT NOTIFICATION: Sold {self.config.symbol} at {price}, PnL: {pnl}")
