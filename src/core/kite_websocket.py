"""
Kite WebSocket Client - Handle live tick data from Kite
"""

import asyncio
import logging
import json
import websockets
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from config import Config

logger = logging.getLogger(__name__)

class KiteWebSocketClient:
    """WebSocket client for Kite live data"""
    
    def __init__(self, access_token: str, api_key: str):
        self.access_token = access_token
        self.api_key = api_key
        self.websocket = None
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5  # seconds
        
        # Callbacks
        self.tick_callback: Optional[Callable] = None
        self.order_update_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
        # Subscription data
        self.subscribed_tokens = set()
        self.subscription_mode = "ltp"  # ltp, quote, full
        
    def set_tick_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback for tick data"""
        self.tick_callback = callback
    
    def set_order_update_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback for order updates"""
        self.order_update_callback = callback
    
    def set_error_callback(self, callback: Callable[[str], None]):
        """Set callback for errors"""
        self.error_callback = callback
    
    async def connect(self) -> bool:
        """Connect to Kite WebSocket"""
        try:
            # WebSocket URL for Kite
            ws_url = f"wss://ws.kite.trade/?api_key={self.api_key}&access_token={self.access_token}"
            
            logger.info(f"Connecting to Kite WebSocket: {ws_url}")
            
            self.websocket = await websockets.connect(ws_url)
            self.running = True
            self.reconnect_attempts = 0
            
            logger.info("Connected to Kite WebSocket")
            
            # Subscribe to Bank Nifty futures after connection
            await self.subscribe_bank_nifty()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Kite WebSocket: {e}")
            if self.error_callback:
                self.error_callback(f"WebSocket connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        logger.info("Disconnected from Kite WebSocket")
    
    async def start_listening(self):
        """Start listening for messages"""
        if not self.websocket:
            logger.error("WebSocket not connected")
            return
        
        try:
            async for message in self.websocket:
                if not self.running:
                    break
                
                await self._handle_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            if self.running:
                await self._handle_reconnection()
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {e}")
            if self.error_callback:
                self.error_callback(f"WebSocket error: {e}")
            if self.running:
                await self._handle_reconnection()
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            # Handle different message types
            if 'type' in data:
                if data['type'] == 'order':
                    await self._handle_order_update(data)
                elif data['type'] == 'tick':
                    await self._handle_tick_data(data)
                elif data['type'] == 'error':
                    await self._handle_error(data)
                else:
                    logger.debug(f"Unknown message type: {data['type']}")
            else:
                # Assume it's tick data if no type specified
                await self._handle_tick_data(data)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def _handle_tick_data(self, data: Dict[str, Any]):
        """Handle tick data"""
        try:
            # Process tick data
            tick = {
                'instrument_token': data.get('instrument_token'),
                'last_price': data.get('last_price'),
                'volume': data.get('volume'),
                'average_price': data.get('average_price'),
                'ohlc': data.get('ohlc', {}),
                'change': data.get('change'),
                'last_quantity': data.get('last_quantity'),
                'buy_quantity': data.get('buy_quantity'),
                'sell_quantity': data.get('sell_quantity'),
                'ohlc': data.get('ohlc', {}),
                'depth': data.get('depth', {}),
                'timestamp': data.get('timestamp', datetime.now().timestamp()),
                'exchange_timestamp': data.get('exchange_timestamp')
            }
            
            # Call tick callback
            if self.tick_callback:
                await self.tick_callback(tick)
                
        except Exception as e:
            logger.error(f"Error handling tick data: {e}")
    
    async def _handle_order_update(self, data: Dict[str, Any]):
        """Handle order update"""
        try:
            order_update = {
                'order_id': data.get('order_id'),
                'status': data.get('status'),
                'filled_quantity': data.get('filled_quantity'),
                'pending_quantity': data.get('pending_quantity'),
                'average_price': data.get('average_price'),
                'message': data.get('message'),
                'timestamp': data.get('timestamp', datetime.now().timestamp())
            }
            
            # Call order update callback
            if self.order_update_callback:
                await self.order_update_callback(order_update)
                
        except Exception as e:
            logger.error(f"Error handling order update: {e}")
    
    async def _handle_error(self, data: Dict[str, Any]):
        """Handle error message"""
        error_message = data.get('message', 'Unknown error')
        logger.error(f"Kite WebSocket error: {error_message}")
        
        if self.error_callback:
            self.error_callback(error_message)
    
    async def _handle_reconnection(self):
        """Handle WebSocket reconnection"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            if self.error_callback:
                self.error_callback("Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        
        await asyncio.sleep(self.reconnect_delay)
        
        if await self.connect():
            # Resubscribe to tokens
            if self.subscribed_tokens:
                await self.subscribe(self.subscribed_tokens)
            # Restart listening
            asyncio.create_task(self.start_listening())
    
    async def subscribe(self, tokens: set, mode: str = "ltp"):
        """Subscribe to tokens for live data"""
        if not self.websocket or not self.running:
            logger.error("WebSocket not connected")
            return False
        
        try:
            # Update subscription mode
            self.subscription_mode = mode
            
            # Add tokens to subscribed set
            self.subscribed_tokens.update(tokens)
            
            # Create subscription message
            subscription_data = {
                "a": "subscribe",  # action
                "v": list(tokens),  # values (tokens)
                "m": mode  # mode
            }
            
            # Send subscription message
            await self.websocket.send(json.dumps(subscription_data))
            
            logger.info(f"Subscribed to {len(tokens)} tokens in {mode} mode")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to tokens: {e}")
            return False
    
    async def unsubscribe(self, tokens: set):
        """Unsubscribe from tokens"""
        if not self.websocket or not self.running:
            logger.error("WebSocket not connected")
            return False
        
        try:
            # Remove tokens from subscribed set
            self.subscribed_tokens -= tokens
            
            # Create unsubscription message
            unsubscription_data = {
                "a": "unsubscribe",  # action
                "v": list(tokens)  # values (tokens)
            }
            
            # Send unsubscription message
            await self.websocket.send(json.dumps(unsubscription_data))
            
            logger.info(f"Unsubscribed from {len(tokens)} tokens")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from tokens: {e}")
            return False
    
    async def subscribe_bank_nifty(self):
        """Subscribe to Bank Nifty futures"""
        try:
            # Bank Nifty futures token (this would need to be looked up from instruments)
            # For now, using a placeholder token
            bank_nifty_token = 260105  # This needs to be the actual token
            
            tokens = {bank_nifty_token}
            return await self.subscribe(tokens, "full")  # Use full mode for L3 data
            
        except Exception as e:
            logger.error(f"Failed to subscribe to Bank Nifty: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.websocket is not None and self.running
    
    def get_subscribed_tokens(self) -> set:
        """Get currently subscribed tokens"""
        return self.subscribed_tokens.copy()
    
    async def run(self):
        """Main run loop"""
        while self.running:
            try:
                if not self.is_connected():
                    if not await self.connect():
                        await asyncio.sleep(self.reconnect_delay)
                        continue
                
                # Start listening for messages
                await self.start_listening()
                
            except Exception as e:
                logger.error(f"Error in WebSocket run loop: {e}")
                await asyncio.sleep(self.reconnect_delay)
    
    async def stop(self):
        """Stop the WebSocket client"""
        self.running = False
        await self.disconnect()
