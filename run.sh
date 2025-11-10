#!/bin/bash

# Live Trading System Run Script
echo "🚀 Starting Live Trading System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if Redis is running
echo "🔍 Checking Redis connection..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Please start Redis first:"
    echo "   redis-server"
    echo ""
    echo "Or install Redis if not installed:"
    echo "   brew install redis  # on macOS"
    echo "   sudo apt-get install redis-server  # on Ubuntu"
    exit 1
fi

echo "✅ Redis is running"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please run ./setup.sh first."
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data

# Run component tests first
echo "🧪 Running component tests..."
python test_system.py

if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
    echo ""
    echo "🌐 Starting Live Trading System..."
    echo "📊 Dashboard will be available at: http://localhost:8000"
    echo "🛑 Press Ctrl+C to stop the system"
    echo ""
    
    # Start the main application
    python main.py
else
    echo "❌ Tests failed. Please check the errors above."
    exit 1
fi
