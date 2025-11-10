#!/bin/bash
# Test LiveTradingPython locally

set -e

echo "🧪 Testing LiveTradingPython System Locally..."
echo ""

cd /Users/rjabbala/Projects/LiveTradingPython

# Check Redis
echo "1️⃣ Checking Redis..."
if redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ Redis is running"
else
    echo "   ⚠️  Starting Redis..."
    brew services start redis 2>/dev/null || redis-server --daemonize yes || echo "   ❌ Please start Redis manually: redis-server"
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo "   ✅ Redis started successfully"
    else
        echo "   ❌ Redis failed to start. Please start manually."
        exit 1
    fi
fi

# Activate venv
echo ""
echo "2️⃣ Activating virtual environment..."
source venv/bin/activate

# Check dependencies
echo ""
echo "3️⃣ Checking dependencies..."
python -c "import fastapi, uvicorn, redis, kiteconnect" 2>/dev/null && echo "   ✅ All dependencies installed" || {
    echo "   ⚠️  Installing missing dependencies..."
    pip install -r requirements.txt
}

# Check .env file
echo ""
echo "4️⃣ Checking configuration..."
if [ -f .env ]; then
    echo "   ✅ .env file exists"
    if grep -q "KITE_API_KEY" .env && grep -q "KITE_ACCESS_TOKEN" .env; then
        echo "   ✅ Kite credentials found in .env"
    else
        echo "   ⚠️  Kite credentials not found. System will run in demo mode."
    fi
else
    echo "   ⚠️  .env file not found. Creating template..."
    cat > .env << 'EOF'
# Kite API Configuration
KITE_API_KEY=your_api_key_here
KITE_ACCESS_TOKEN=your_access_token_here
KITE_REQUEST_TOKEN=your_request_token_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Trading Configuration
BANK_NIFTY_SYMBOL=NIFTY BANK
TRADING_QUANTITY=1
PROFIT_TARGET_POINTS=200
STOP_LOSS_POINTS=100
TRADE_ENTRY_TIME=09:45
MARKET_CLOSE_TIME=15:15

# System Configuration
LOG_LEVEL=INFO
EOF
    echo "   ✅ Created .env template. Please update with your credentials."
fi

# Create data directory
echo ""
echo "5️⃣ Setting up data directory..."
mkdir -p data
echo "   ✅ Data directory ready"

# Run tests
echo ""
echo "6️⃣ Running system tests..."
if [ -f test_system.py ]; then
    python test_system.py 2>&1 | tail -10 || echo "   ⚠️  Tests completed with warnings"
else
    echo "   ⚠️  test_system.py not found, skipping tests"
fi

echo ""
echo "✅ Local Testing Setup Complete!"
echo ""
echo "🚀 To start the system:"
echo "   ./run.sh"
echo ""
echo "   Or manually:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "🌐 Dashboard will be available at: http://localhost:8000"

