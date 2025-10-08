"""
Order Book - Construct and maintain order book from tick data
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)

@dataclass
class OrderBookLevel:
    """Single level in the order book"""
    price: float
    quantity: int
    orders: int = 1

@dataclass
class OrderBookSnapshot:
    """Complete order book snapshot"""
    timestamp: float
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    last_price: float
    volume: int
    spread: float = 0.0

class OrderBook:
    """Order book construction and management"""
    
    def __init__(self, max_levels: int = 21):
        self.max_levels = max_levels
        self.order_books: Dict[str, OrderBookSnapshot] = {}
        self.tick_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # L3 data structure
        self.l3_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
    def update(self, tick: Dict[str, Any]) -> None:
        """Update order book with new tick data"""
        try:
            symbol = tick.get('instrument_token', 'unknown')
            
            # Store tick in history
            self.tick_history[symbol].append(tick)
            
            # Extract L3 data if available
            if 'depth' in tick:
                self._update_l3_data(symbol, tick['depth'])
            
            # Update order book snapshot
            self._update_order_book_snapshot(symbol, tick)
            
        except Exception as e:
            logger.error(f"Error updating order book: {e}")
    
    def _update_l3_data(self, symbol: str, depth_data: Dict[str, Any]) -> None:
        """Update L3 order book data"""
        try:
            # Store L3 data
            self.l3_data[symbol] = {
                'bids': depth_data.get('buy', []),
                'asks': depth_data.get('sell', []),
                'timestamp': depth_data.get('timestamp', 0)
            }
            
        except Exception as e:
            logger.error(f"Error updating L3 data: {e}")
    
    def _update_order_book_snapshot(self, symbol: str, tick: Dict[str, Any]) -> None:
        """Update order book snapshot"""
        try:
            # Extract bid/ask data from tick
            bids = self._extract_bids(tick)
            asks = self._extract_asks(tick)
            
            # Calculate spread
            spread = 0.0
            if bids and asks:
                best_bid = max(bids, key=lambda x: x.price)
                best_ask = min(asks, key=lambda x: x.price)
                spread = best_ask.price - best_bid.price
            
            # Create snapshot
            snapshot = OrderBookSnapshot(
                timestamp=tick.get('timestamp', 0),
                symbol=symbol,
                bids=bids[:self.max_levels],
                asks=asks[:self.max_levels],
                last_price=tick.get('last_price', 0),
                volume=tick.get('volume', 0),
                spread=spread
            )
            
            self.order_books[symbol] = snapshot
            
        except Exception as e:
            logger.error(f"Error updating order book snapshot: {e}")
    
    def _extract_bids(self, tick: Dict[str, Any]) -> List[OrderBookLevel]:
        """Extract bid levels from tick data"""
        bids = []
        
        # Try different possible field names for bid data
        bid_fields = ['depth', 'buy', 'bids', 'bid']
        
        for field in bid_fields:
            if field in tick:
                bid_data = tick[field]
                if isinstance(bid_data, list):
                    for level in bid_data:
                        if isinstance(level, dict) and 'price' in level and 'quantity' in level:
                            bids.append(OrderBookLevel(
                                price=float(level['price']),
                                quantity=int(level['quantity']),
                                orders=level.get('orders', 1)
                            ))
                break
        
        # Sort by price descending (highest bid first)
        bids.sort(key=lambda x: x.price, reverse=True)
        return bids
    
    def _extract_asks(self, tick: Dict[str, Any]) -> List[OrderBookLevel]:
        """Extract ask levels from tick data"""
        asks = []
        
        # Try different possible field names for ask data
        ask_fields = ['depth', 'sell', 'asks', 'ask']
        
        for field in ask_fields:
            if field in tick:
                ask_data = tick[field]
                if isinstance(ask_data, list):
                    for level in ask_data:
                        if isinstance(level, dict) and 'price' in level and 'quantity' in level:
                            asks.append(OrderBookLevel(
                                price=float(level['price']),
                                quantity=int(level['quantity']),
                                orders=level.get('orders', 1)
                            ))
                break
        
        # Sort by price ascending (lowest ask first)
        asks.sort(key=lambda x: x.price)
        return asks
    
    def get_order_book(self, symbol: str) -> Optional[OrderBookSnapshot]:
        """Get current order book for symbol"""
        return self.order_books.get(symbol)
    
    def get_all_order_books(self) -> Dict[str, OrderBookSnapshot]:
        """Get all order books"""
        return self.order_books.copy()
    
    def get_spread(self, symbol: str) -> float:
        """Get current spread for symbol"""
        order_book = self.get_order_book(symbol)
        if order_book:
            return order_book.spread
        return 0.0
    
    def get_best_bid_ask(self, symbol: str) -> tuple:
        """Get best bid and ask prices"""
        order_book = self.get_order_book(symbol)
        if order_book and order_book.bids and order_book.asks:
            best_bid = order_book.bids[0].price
            best_ask = order_book.asks[0].price
            return best_bid, best_ask
        return 0.0, 0.0
    
    def get_market_depth(self, symbol: str, levels: int = 5) -> Dict[str, Any]:
        """Get market depth for symbol"""
        order_book = self.get_order_book(symbol)
        if not order_book:
            return {}
        
        return {
            'symbol': symbol,
            'timestamp': order_book.timestamp,
            'last_price': order_book.last_price,
            'spread': order_book.spread,
            'bids': [
                {
                    'price': level.price,
                    'quantity': level.quantity,
                    'orders': level.orders
                }
                for level in order_book.bids[:levels]
            ],
            'asks': [
                {
                    'price': level.price,
                    'quantity': level.quantity,
                    'orders': level.orders
                }
                for level in order_book.asks[:levels]
            ]
        }
    
    def get_l3_data(self, symbol: str) -> Dict[str, Any]:
        """Get L3 order book data"""
        return self.l3_data.get(symbol, {})
    
    def get_tick_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent tick history for symbol"""
        history = self.tick_history.get(symbol, deque())
        return list(history)[-limit:]
    
    def get_order_book_summary(self) -> Dict[str, Any]:
        """Get summary of all order books"""
        summary = {}
        
        for symbol, order_book in self.order_books.items():
            best_bid, best_ask = self.get_best_bid_ask(symbol)
            
            summary[symbol] = {
                'last_price': order_book.last_price,
                'best_bid': best_bid,
                'best_ask': best_ask,
                'spread': order_book.spread,
                'volume': order_book.volume,
                'bid_levels': len(order_book.bids),
                'ask_levels': len(order_book.asks),
                'timestamp': order_book.timestamp
            }
        
        return summary
    
    def export_to_json(self, symbol: str) -> str:
        """Export order book to JSON"""
        order_book = self.get_order_book(symbol)
        if not order_book:
            return "{}"
        
        data = {
            'symbol': order_book.symbol,
            'timestamp': order_book.timestamp,
            'last_price': order_book.last_price,
            'spread': order_book.spread,
            'volume': order_book.volume,
            'bids': [
                {
                    'price': level.price,
                    'quantity': level.quantity,
                    'orders': level.orders
                }
                for level in order_book.bids
            ],
            'asks': [
                {
                    'price': level.price,
                    'quantity': level.quantity,
                    'orders': level.orders
                }
                for level in order_book.asks
            ]
        }
        
        return json.dumps(data, indent=2)
