#!/bin/bash
# Push LiveTradingPython to GitHub

set -e

echo "🚀 Pushing LiveTradingPython to GitHub..."
echo ""

# Check if remote exists
if ! git remote get-url origin &> /dev/null; then
    echo "📝 Adding GitHub remote..."
    git remote add origin https://github.com/rajamohan1950/LiveTradingPython.git
fi

echo "📦 Pushing to GitHub..."
git push -u origin main

echo ""
echo "✅ Successfully pushed to GitHub!"
echo "🌐 Repository: https://github.com/rajamohan1950/LiveTradingPython"
echo ""
echo "☁️  Next: Deploy to cloud!"
echo "   - Render.com: https://render.com"
echo "   - Railway: https://railway.app"

