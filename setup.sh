#!/bin/bash

# Live Trading System Setup Script
echo "🚀 Setting up Live Trading System..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install fastapi uvicorn websockets redis kiteconnect pandas numpy psutil python-dotenv email-validator aiofiles python-multipart jinja2 python-jose passlib schedule pytest pytest-asyncio pytest-mock

# Create data and static directories
echo "📁 Creating directories..."
mkdir -p data
mkdir -p static

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️ Creating .env file..."
    cat > .env << EOF
# Kite API Configuration
KITE_API_KEY=your_api_key_here
KITE_ACCESS_TOKEN=your_access_token_here
KITE_REQUEST_TOKEN=your_request_token_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
ALERT_EMAIL=rjabbala@gmail.com

# Trading Configuration
BANK_NIFTY_SYMBOL=NIFTY BANK
TRADING_QUANTITY=1
PROFIT_TARGET_POINTS=200
STOP_LOSS_POINTS=100
MARKET_OPEN_TIME=09:15
TRADE_ENTRY_TIME=09:45
MARKET_CLOSE_TIME=15:15

# System Configuration
LOG_LEVEL=INFO
DATA_DIR=./data
CACHE_UPDATE_INTERVAL=600
HEALTH_CHECK_INTERVAL=30
EOF
    echo "✅ .env file created. Please edit it with your credentials."
fi

echo "✅ Setup complete!"
echo ""
echo "To run the system:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start Redis: redis-server (in another terminal)"
echo "3. Run the system: ./run.sh"
echo ""
echo "Or use: ./run.sh (it will activate venv automatically)"
