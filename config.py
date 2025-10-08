import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Kite API Configuration
    KITE_API_KEY = os.getenv('KITE_API_KEY', '')
    KITE_ACCESS_TOKEN = os.getenv('KITE_ACCESS_TOKEN', '')
    KITE_REQUEST_TOKEN = os.getenv('KITE_REQUEST_TOKEN', '')
    
    # Redis Configuration
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
    
    # Email Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    ALERT_EMAIL = os.getenv('ALERT_EMAIL', 'rjabbala@gmail.com')
    
    # Trading Configuration
    BANK_NIFTY_SYMBOL = os.getenv('BANK_NIFTY_SYMBOL', 'NIFTY BANK')
    TRADING_QUANTITY = int(os.getenv('TRADING_QUANTITY', 1))
    PROFIT_TARGET_POINTS = int(os.getenv('PROFIT_TARGET_POINTS', 200))
    STOP_LOSS_POINTS = int(os.getenv('STOP_LOSS_POINTS', 100))
    MARKET_OPEN_TIME = os.getenv('MARKET_OPEN_TIME', '09:15')
    TRADE_ENTRY_TIME = os.getenv('TRADE_ENTRY_TIME', '09:45')
    MARKET_CLOSE_TIME = os.getenv('MARKET_CLOSE_TIME', '15:15')
    
    # System Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    DATA_DIR = os.getenv('DATA_DIR', './data')
    CACHE_UPDATE_INTERVAL = int(os.getenv('CACHE_UPDATE_INTERVAL', 600))
    HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', 30))
    
    # NSE Exchange Configuration
    EXCHANGE = 'NSE'
    INSTRUMENT_TYPE = 'FUT'
    
    # Latency Monitoring
    LATENCY_LOG_FILE = os.path.join(DATA_DIR, 'latency_metrics.log')
    TRADE_LOG_FILE = os.path.join(DATA_DIR, 'trade_history.log')
    SYSTEM_LOG_FILE = os.path.join(DATA_DIR, 'system.log')
