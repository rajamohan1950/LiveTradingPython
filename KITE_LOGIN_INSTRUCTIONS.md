# Kite Login Instructions

## 🚀 How to Login to Kite

### Step 1: Get Your Kite API Key
1. Go to [Kite Developer Console](https://kite.trade/connect/login?api_key=your_api_key)
2. Login to your Kite account
3. Go to "My Apps" section
4. Create a new app or use existing one
5. Copy your **API Key**

### Step 2: Login to the Trading System
1. Open the dashboard: http://localhost:8000
2. Go to **"Admin Settings"** tab
3. Enter your **Kite API Key** in the first field
4. Click **"Generate Login URL"** button
5. Copy the generated URL and open it in a new tab
6. Login to your Kite account
7. After login, you'll be redirected to a URL that contains `request_token=XXXXX`
8. Copy the request token from the URL
9. Paste the request token in the **"Request Token"** field
10. Click **"Authenticate"** button

### Step 3: Verify Authentication
- The system will show "Authentication successful!"
- The page will refresh automatically
- Check the system health - it should show "healthy" status
- You're now ready to trade!

## 🔧 Troubleshooting

### If Authentication Fails:
1. Make sure your API key is correct
2. Ensure the request token is copied completely
3. Check if your Kite account is active
4. Try generating a new login URL

### If System Shows "Unhealthy":
- This is normal before authentication
- After successful authentication, status should change to "healthy"

## 📱 Quick Reference

**Dashboard URL**: http://localhost:8000
**Admin Settings**: Click "Admin Settings" tab
**API Key**: Get from Kite Developer Console
**Request Token**: Get from login redirect URL

## ⚠️ Important Notes

- Keep your API key and access token secure
- The system uses paper trading by default (safe mode)
- Always test with paper trading before live trading
- Monitor the system health regularly

## 🆘 Need Help?

If you encounter any issues:
1. Check the system logs in the terminal
2. Verify Redis is running: `redis-server`
3. Restart the system: `./run.sh`
4. Check the health endpoint: http://localhost:8000/health
