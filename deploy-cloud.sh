#!/bin/bash
# Deploy LiveTradingPython to Cloud

set -e

echo "☁️  LiveTradingPython Cloud Deployment"
echo ""

PLATFORM=${1:-railway}

case $PLATFORM in
    railway)
        echo "🚂 Deploying to Railway..."
        
        if ! command -v railway &> /dev/null; then
            echo "📦 Installing Railway CLI..."
            npm install -g @railway/cli
        fi
        
        railway login
        railway init
        
        echo "⚙️ Setting environment variables..."
        railway variables set REDIS_URL="redis://localhost:6379"
        railway variables set LOG_LEVEL="INFO"
        
        echo "📝 Please set Kite credentials:"
        echo "   railway variables set KITE_API_KEY=your_key"
        echo "   railway variables set KITE_ACCESS_TOKEN=your_token"
        
        railway up
        ;;
        
    render)
        echo "🎨 Deploying to Render.com..."
        echo ""
        echo "1. Push code to GitHub"
        echo "2. Go to https://render.com"
        echo "3. Create new Web Service"
        echo "4. Connect GitHub repository"
        echo "5. Use these settings:"
        echo "   - Build Command: pip install -r requirements.txt"
        echo "   - Start Command: python main.py"
        echo "   - Environment: Python 3"
        echo ""
        echo "6. Add environment variables from .env file"
        echo "7. Add Redis service (or use external Redis)"
        ;;
        
    heroku)
        echo "🟣 Deploying to Heroku..."
        
        if ! command -v heroku &> /dev/null; then
            echo "📦 Installing Heroku CLI..."
            echo "Visit: https://devcenter.heroku.com/articles/heroku-cli"
        fi
        
        heroku login
        heroku create live-trading-python
        
        echo "⚙️ Setting up Redis addon..."
        heroku addons:create heroku-redis:mini
        
        echo "📝 Setting environment variables..."
        heroku config:set LOG_LEVEL=INFO
        
        echo "📝 Please set Kite credentials:"
        echo "   heroku config:set KITE_API_KEY=your_key"
        echo "   heroku config:set KITE_ACCESS_TOKEN=your_token"
        
        git push heroku main
        ;;
        
    *)
        echo "❌ Unknown platform: $PLATFORM"
        echo "Available: railway, render, heroku"
        exit 1
        ;;
esac

echo ""
echo "✅ Deployment initiated!"
echo "🌐 Your trading system will be available at the provided URL"

