"""
Health Monitor - System health monitoring and alerting
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import Config

logger = logging.getLogger(__name__)

@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: str  # 'healthy', 'warning', 'critical'
    message: str
    timestamp: datetime
    value: Any = None

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_connected: bool
    uptime_seconds: float
    timestamp: datetime

class HealthMonitor:
    """System health monitoring and alerting"""
    
    def __init__(self, trading_engine):
        self.trading_engine = trading_engine
        self.running = False
        self.task = None
        self.last_health_check = None
        self.health_history: List[HealthCheck] = []
        self.system_metrics: List[SystemMetrics] = []
        self.alert_cooldown = {}  # Prevent spam alerts
        
        # Health thresholds
        self.thresholds = {
            'cpu_warning': 80.0,
            'cpu_critical': 95.0,
            'memory_warning': 85.0,
            'memory_critical': 95.0,
            'disk_warning': 90.0,
            'disk_critical': 95.0,
            'latency_warning': 100.0,  # ms
            'latency_critical': 500.0,  # ms
        }
    
    async def start_monitoring(self):
        """Start health monitoring"""
        self.running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitoring started")
    
    async def stop(self):
        """Stop health monitoring"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitoring stopped")
    
    async def _monitor_loop(self):
        """Main health monitoring loop"""
        while self.running:
            try:
                # Perform health checks
                health_checks = await self._perform_health_checks()
                
                # Update health history
                self.health_history.extend(health_checks)
                self.last_health_check = datetime.now()
                
                # Keep only last 1000 health checks
                if len(self.health_history) > 1000:
                    self.health_history = self.health_history[-1000:]
                
                # Check for alerts
                await self._check_alerts(health_checks)
                
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Wait for next check
                await asyncio.sleep(Config.HEALTH_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _perform_health_checks(self) -> List[HealthCheck]:
        """Perform all health checks"""
        checks = []
        
        # System resource checks
        checks.extend(await self._check_system_resources())
        
        # Trading engine checks
        checks.extend(await self._check_trading_engine())
        
        # Network connectivity checks
        checks.extend(await self._check_network_connectivity())
        
        # Kite API checks
        checks.extend(await self._check_kite_api())
        
        # Redis checks
        checks.extend(await self._check_redis())
        
        # Latency checks
        checks.extend(await self._check_latency())
        
        return checks
    
    async def _check_system_resources(self) -> List[HealthCheck]:
        """Check system resource usage"""
        checks = []
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent >= self.thresholds['cpu_critical']:
                status = 'critical'
                message = f"CPU usage critical: {cpu_percent:.1f}%"
            elif cpu_percent >= self.thresholds['cpu_warning']:
                status = 'warning'
                message = f"CPU usage high: {cpu_percent:.1f}%"
            else:
                status = 'healthy'
                message = f"CPU usage normal: {cpu_percent:.1f}%"
            
            checks.append(HealthCheck(
                name='cpu_usage',
                status=status,
                message=message,
                timestamp=datetime.now(),
                value=cpu_percent
            ))
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            if memory_percent >= self.thresholds['memory_critical']:
                status = 'critical'
                message = f"Memory usage critical: {memory_percent:.1f}%"
            elif memory_percent >= self.thresholds['memory_warning']:
                status = 'warning'
                message = f"Memory usage high: {memory_percent:.1f}%"
            else:
                status = 'healthy'
                message = f"Memory usage normal: {memory_percent:.1f}%"
            
            checks.append(HealthCheck(
                name='memory_usage',
                status=status,
                message=message,
                timestamp=datetime.now(),
                value=memory_percent
            ))
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent >= self.thresholds['disk_critical']:
                status = 'critical'
                message = f"Disk usage critical: {disk_percent:.1f}%"
            elif disk_percent >= self.thresholds['disk_warning']:
                status = 'warning'
                message = f"Disk usage high: {disk_percent:.1f}%"
            else:
                status = 'healthy'
                message = f"Disk usage normal: {disk_percent:.1f}%"
            
            checks.append(HealthCheck(
                name='disk_usage',
                status=status,
                message=message,
                timestamp=datetime.now(),
                value=disk_percent
            ))
            
        except Exception as e:
            checks.append(HealthCheck(
                name='system_resources',
                status='critical',
                message=f"Failed to check system resources: {e}",
                timestamp=datetime.now()
            ))
        
        return checks
    
    async def _check_trading_engine(self) -> List[HealthCheck]:
        """Check trading engine health"""
        checks = []
        
        try:
            if not self.trading_engine:
                checks.append(HealthCheck(
                    name='trading_engine',
                    status='critical',
                    message='Trading engine not initialized',
                    timestamp=datetime.now()
                ))
                return checks
            
            # Check if trading engine is running
            if not self.trading_engine.running:
                checks.append(HealthCheck(
                    name='trading_engine',
                    status='critical',
                    message='Trading engine not running',
                    timestamp=datetime.now()
                ))
            else:
                checks.append(HealthCheck(
                    name='trading_engine',
                    status='healthy',
                    message='Trading engine running normally',
                    timestamp=datetime.now()
                ))
            
            # Check if we have recent tick data
            if not self.trading_engine.latest_tick:
                checks.append(HealthCheck(
                    name='tick_data',
                    status='warning',
                    message='No recent tick data received',
                    timestamp=datetime.now()
                ))
            else:
                checks.append(HealthCheck(
                    name='tick_data',
                    status='healthy',
                    message='Tick data flowing normally',
                    timestamp=datetime.now()
                ))
            
        except Exception as e:
            checks.append(HealthCheck(
                name='trading_engine',
                status='critical',
                message=f'Trading engine check failed: {e}',
                timestamp=datetime.now()
            ))
        
        return checks
    
    async def _check_network_connectivity(self) -> List[HealthCheck]:
        """Check network connectivity"""
        checks = []
        
        try:
            # Check internet connectivity
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            
            checks.append(HealthCheck(
                name='network_connectivity',
                status='healthy',
                message='Network connectivity normal',
                timestamp=datetime.now()
            ))
            
        except Exception as e:
            checks.append(HealthCheck(
                name='network_connectivity',
                status='critical',
                message=f'Network connectivity failed: {e}',
                timestamp=datetime.now()
            ))
        
        return checks
    
    async def _check_kite_api(self) -> List[HealthCheck]:
        """Check Kite API connectivity"""
        checks = []
        
        try:
            if not self.trading_engine or not self.trading_engine.kite:
                checks.append(HealthCheck(
                    name='kite_api',
                    status='critical',
                    message='Kite API not authenticated',
                    timestamp=datetime.now()
                ))
                return checks
            
            # Try to get profile (lightweight API call)
            profile = self.trading_engine.kite.profile()
            
            checks.append(HealthCheck(
                name='kite_api',
                status='healthy',
                message=f'Kite API connected as {profile.get("user_name", "unknown")}',
                timestamp=datetime.now()
            ))
            
        except Exception as e:
            checks.append(HealthCheck(
                name='kite_api',
                status='critical',
                message=f'Kite API connection failed: {e}',
                timestamp=datetime.now()
            ))
        
        return checks
    
    async def _check_redis(self) -> List[HealthCheck]:
        """Check Redis connectivity"""
        checks = []
        
        try:
            if not self.trading_engine or not self.trading_engine.redis_client:
                checks.append(HealthCheck(
                    name='redis',
                    status='critical',
                    message='Redis client not initialized',
                    timestamp=datetime.now()
                ))
                return checks
            
            # Ping Redis
            self.trading_engine.redis_client.ping()
            
            checks.append(HealthCheck(
                name='redis',
                status='healthy',
                message='Redis connection normal',
                timestamp=datetime.now()
            ))
            
        except Exception as e:
            checks.append(HealthCheck(
                name='redis',
                status='critical',
                message=f'Redis connection failed: {e}',
                timestamp=datetime.now()
            ))
        
        return checks
    
    async def _check_latency(self) -> List[HealthCheck]:
        """Check system latency"""
        checks = []
        
        try:
            if not self.trading_engine or not self.trading_engine.latency_monitor:
                checks.append(HealthCheck(
                    name='latency',
                    status='warning',
                    message='Latency monitor not available',
                    timestamp=datetime.now()
                ))
                return checks
            
            # Get latency summary
            latency_summary = self.trading_engine.latency_monitor.get_latency_summary()
            
            if 'stage_statistics' in latency_summary:
                # Check average latency
                avg_latencies = []
                for stage, stats in latency_summary['stage_statistics'].items():
                    avg_latencies.append(stats['avg_ms'])
                
                if avg_latencies:
                    max_latency = max(avg_latencies)
                    if max_latency >= self.thresholds['latency_critical']:
                        status = 'critical'
                        message = f'Latency critical: {max_latency:.1f}ms'
                    elif max_latency >= self.thresholds['latency_warning']:
                        status = 'warning'
                        message = f'Latency high: {max_latency:.1f}ms'
                    else:
                        status = 'healthy'
                        message = f'Latency normal: {max_latency:.1f}ms'
                    
                    checks.append(HealthCheck(
                        name='latency',
                        status=status,
                        message=message,
                        timestamp=datetime.now(),
                        value=max_latency
                    ))
            
        except Exception as e:
            checks.append(HealthCheck(
                name='latency',
                status='warning',
                message=f'Latency check failed: {e}',
                timestamp=datetime.now()
            ))
        
        return checks
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            metrics = SystemMetrics(
                cpu_percent=psutil.cpu_percent(),
                memory_percent=psutil.virtual_memory().percent,
                disk_percent=(psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                network_connected=True,  # Simplified
                uptime_seconds=time.time() - psutil.boot_time(),
                timestamp=datetime.now()
            )
            
            self.system_metrics.append(metrics)
            
            # Keep only last 1000 metrics
            if len(self.system_metrics) > 1000:
                self.system_metrics = self.system_metrics[-1000:]
                
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    async def _check_alerts(self, health_checks: List[HealthCheck]):
        """Check for alerts and send notifications"""
        critical_checks = [check for check in health_checks if check.status == 'critical']
        warning_checks = [check for check in health_checks if check.status == 'warning']
        
        # Send critical alerts immediately
        if critical_checks:
            await self._send_alert('critical', critical_checks)
        
        # Send warning alerts (with cooldown)
        if warning_checks:
            await self._send_alert('warning', warning_checks)
    
    async def _send_alert(self, alert_type: str, checks: List[HealthCheck]):
        """Send email alert"""
        try:
            # Check cooldown
            alert_key = f"{alert_type}_{checks[0].name}"
            now = datetime.now()
            
            if alert_key in self.alert_cooldown:
                last_alert = self.alert_cooldown[alert_key]
                if now - last_alert < timedelta(minutes=15):  # 15 minute cooldown
                    return
            
            # Send email
            await self._send_email_alert(alert_type, checks)
            
            # Update cooldown
            self.alert_cooldown[alert_key] = now
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    async def _send_email_alert(self, alert_type: str, checks: List[HealthCheck]):
        """Send email alert"""
        try:
            if not Config.EMAIL_USERNAME or not Config.EMAIL_PASSWORD:
                logger.warning("Email credentials not configured")
                return
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = Config.EMAIL_USERNAME
            msg['To'] = Config.ALERT_EMAIL
            msg['Subject'] = f"Trading System Alert - {alert_type.upper()}"
            
            # Create body
            body = f"Trading System Health Alert\n\n"
            body += f"Alert Type: {alert_type.upper()}\n"
            body += f"Timestamp: {datetime.now().isoformat()}\n\n"
            
            for check in checks:
                body += f"- {check.name}: {check.message}\n"
            
            body += f"\nSystem Status: {self.get_overall_health()}\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
            server.starttls()
            server.login(Config.EMAIL_USERNAME, Config.EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Alert email sent: {alert_type}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        if not self.last_health_check:
            return {'overall_health': False, 'message': 'No health checks performed'}
        
        # Calculate overall health
        recent_checks = [check for check in self.health_history 
                        if (datetime.now() - check.timestamp).total_seconds() < 300]  # Last 5 minutes
        
        if not recent_checks:
            return {'overall_health': False, 'message': 'No recent health checks'}
        
        critical_count = len([check for check in recent_checks if check.status == 'critical'])
        warning_count = len([check for check in recent_checks if check.status == 'warning'])
        
        overall_health = critical_count == 0
        
        return {
            'overall_health': overall_health,
            'critical_issues': critical_count,
            'warning_issues': warning_count,
            'last_check': self.last_health_check.isoformat(),
            'recent_checks': [
                {
                    'name': check.name,
                    'status': check.status,
                    'message': check.message,
                    'timestamp': check.timestamp.isoformat()
                }
                for check in recent_checks[-10:]  # Last 10 checks
            ]
        }
    
    def get_overall_health(self) -> str:
        """Get overall health status as string"""
        status = self.get_system_status()
        if status['overall_health']:
            return 'healthy'
        elif status['critical_issues'] > 0:
            return 'critical'
        else:
            return 'warning'
    
    def get_system_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent system metrics"""
        recent_metrics = self.system_metrics[-limit:] if len(self.system_metrics) >= limit else self.system_metrics
        
        return [
            {
                'timestamp': metric.timestamp.isoformat(),
                'cpu_percent': metric.cpu_percent,
                'memory_percent': metric.memory_percent,
                'disk_percent': metric.disk_percent,
                'network_connected': metric.network_connected,
                'uptime_seconds': metric.uptime_seconds
            }
            for metric in recent_metrics
        ]
