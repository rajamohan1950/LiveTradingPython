"""
Latency Monitor - Track and measure system latency at various stages
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

from config import Config

logger = logging.getLogger(__name__)

@dataclass
class LatencyMetric:
    timestamp: datetime
    stage: str
    latency_ms: float
    additional_data: Dict[str, Any] = None

class LatencyMonitor:
    """Monitor and track latency across the trading pipeline"""
    
    def __init__(self):
        self.metrics: List[LatencyMetric] = []
        self.stage_timestamps: Dict[str, float] = {}
        self.running = False
        self.task = None
        
        # Pipeline stages
        self.STAGES = {
            'tick_received': 'Tick received from Kite',
            'redis_stored': 'Data stored in Redis cache',
            'disk_written': 'Data written to disk file',
            'order_creation_start': 'Order creation initiated',
            'order_creation_end': 'Order creation completed',
            'order_sent': 'Order sent to Kite',
            'order_executed': 'Order fully executed',
            'order_partial': 'Order partially executed'
        }
    
    async def start_monitoring(self):
        """Start the latency monitoring system"""
        self.running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("Latency monitoring started")
    
    async def stop(self):
        """Stop the latency monitoring system"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Latency monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Log current metrics every 30 seconds
                await self._log_current_metrics()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Latency monitor error: {e}")
                await asyncio.sleep(5)
    
    def record_tick_received(self, tick: Dict[str, Any]):
        """Record when tick is received from Kite"""
        timestamp = time.time()
        self.stage_timestamps['tick_received'] = timestamp
        
        # Calculate latency from previous tick if available
        if 'tick_received' in self.stage_timestamps:
            prev_timestamp = self.stage_timestamps.get('prev_tick_received', timestamp)
            latency = (timestamp - prev_timestamp) * 1000  # Convert to ms
            
            self._add_metric('tick_received', latency, {
                'symbol': tick.get('instrument_token'),
                'price': tick.get('last_price'),
                'volume': tick.get('volume')
            })
        
        self.stage_timestamps['prev_tick_received'] = timestamp
    
    def record_redis_stored(self, tick: Dict[str, Any]):
        """Record when tick is stored in Redis"""
        timestamp = time.time()
        self.stage_timestamps['redis_stored'] = timestamp
        
        if 'tick_received' in self.stage_timestamps:
            latency = (timestamp - self.stage_timestamps['tick_received']) * 1000
            self._add_metric('redis_stored', latency, {
                'symbol': tick.get('instrument_token')
            })
    
    def record_disk_written(self, tick: Dict[str, Any]):
        """Record when tick is written to disk"""
        timestamp = time.time()
        self.stage_timestamps['disk_written'] = timestamp
        
        if 'redis_stored' in self.stage_timestamps:
            latency = (timestamp - self.stage_timestamps['redis_stored']) * 1000
            self._add_metric('disk_written', latency, {
                'symbol': tick.get('instrument_token')
            })
    
    def record_order_creation_start(self):
        """Record when order creation starts"""
        self.stage_timestamps['order_creation_start'] = time.time()
    
    def record_order_creation_end(self):
        """Record when order creation ends"""
        timestamp = time.time()
        self.stage_timestamps['order_creation_end'] = timestamp
        
        if 'order_creation_start' in self.stage_timestamps:
            latency = (timestamp - self.stage_timestamps['order_creation_start']) * 1000
            self._add_metric('order_creation_end', latency)
    
    def record_order_sent(self, order_id: str):
        """Record when order is sent to Kite"""
        timestamp = time.time()
        self.stage_timestamps['order_sent'] = timestamp
        
        if 'order_creation_end' in self.stage_timestamps:
            latency = (timestamp - self.stage_timestamps['order_creation_end']) * 1000
            self._add_metric('order_sent', latency, {'order_id': order_id})
    
    def record_order_executed(self, order_id: str, execution_type: str = 'full'):
        """Record when order is executed"""
        timestamp = time.time()
        self.stage_timestamps['order_executed'] = timestamp
        
        if 'order_sent' in self.stage_timestamps:
            latency = (timestamp - self.stage_timestamps['order_sent']) * 1000
            self._add_metric(f'order_{execution_type}', latency, {'order_id': order_id})
    
    def _add_metric(self, stage: str, latency_ms: float, additional_data: Dict[str, Any] = None):
        """Add a latency metric"""
        metric = LatencyMetric(
            timestamp=datetime.now(),
            stage=stage,
            latency_ms=latency_ms,
            additional_data=additional_data or {}
        )
        
        self.metrics.append(metric)
        
        # Keep only last 1000 metrics to prevent memory issues
        if len(self.metrics) > 1000:
            self.metrics = self.metrics[-1000:]
        
        # Log high latency events
        if latency_ms > 100:  # More than 100ms
            logger.warning(f"High latency detected: {stage} = {latency_ms:.2f}ms")
    
    async def _log_current_metrics(self):
        """Log current latency metrics to file"""
        try:
            if not self.metrics:
                return
            
            # Calculate average latencies for each stage
            stage_latencies = {}
            for metric in self.metrics[-100:]:  # Last 100 metrics
                if metric.stage not in stage_latencies:
                    stage_latencies[metric.stage] = []
                stage_latencies[metric.stage].append(metric.latency_ms)
            
            # Calculate averages
            avg_latencies = {}
            for stage, latencies in stage_latencies.items():
                avg_latencies[stage] = sum(latencies) / len(latencies)
            
            # Log to file
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'average_latencies': avg_latencies,
                'total_metrics': len(self.metrics)
            }
            
            with open(Config.LATENCY_LOG_FILE, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            logger.info(f"Latency metrics logged: {avg_latencies}")
            
        except Exception as e:
            logger.error(f"Failed to log latency metrics: {e}")
    
    def get_latency_summary(self) -> Dict[str, Any]:
        """Get current latency summary"""
        if not self.metrics:
            return {'message': 'No latency data available'}
        
        # Calculate statistics for each stage
        stage_stats = {}
        for stage in self.STAGES.keys():
            stage_metrics = [m for m in self.metrics if m.stage == stage]
            if stage_metrics:
                latencies = [m.latency_ms for m in stage_metrics]
                stage_stats[stage] = {
                    'count': len(latencies),
                    'avg_ms': sum(latencies) / len(latencies),
                    'min_ms': min(latencies),
                    'max_ms': max(latencies),
                    'latest_ms': latencies[-1] if latencies else 0
                }
        
        return {
            'total_metrics': len(self.metrics),
            'stage_statistics': stage_stats,
            'overall_health': self._calculate_overall_health()
        }
    
    def _calculate_overall_health(self) -> str:
        """Calculate overall system health based on latency"""
        if not self.metrics:
            return 'unknown'
        
        # Check recent metrics (last 50)
        recent_metrics = self.metrics[-50:] if len(self.metrics) >= 50 else self.metrics
        
        # Calculate average latency
        avg_latency = sum(m.latency_ms for m in recent_metrics) / len(recent_metrics)
        
        # Health thresholds
        if avg_latency < 50:
            return 'excellent'
        elif avg_latency < 100:
            return 'good'
        elif avg_latency < 200:
            return 'fair'
        else:
            return 'poor'
    
    def get_recent_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent latency metrics"""
        recent = self.metrics[-limit:] if len(self.metrics) >= limit else self.metrics
        
        return [
            {
                'timestamp': metric.timestamp.isoformat(),
                'stage': metric.stage,
                'latency_ms': metric.latency_ms,
                'additional_data': metric.additional_data
            }
            for metric in recent
        ]
