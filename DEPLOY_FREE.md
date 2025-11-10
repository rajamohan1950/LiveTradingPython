# 🆓 Free Cloud Deployment Guide

## ✅ 100% Free Deployment Options

### Option 1: Render.com (FREE Tier)

**Important:** Use the updated `render.yaml` with `plan: free` for both web service and Redis.

**Steps:**
1. Go to https://render.com
2. Sign up (free account)
3. Click "New" → "Web Service" (NOT Blueprint - that requires paid plan)
4. Connect GitHub → Select `rajamohan1950/LiveTradingPython`
5. Settings:
   - **Name:** live-trading-python
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Plan:** FREE
6. Add Redis separately:
   - Click "New" → "Redis"
   - Name: live-trading-redis
   - Plan: FREE
7. Set environment variables in Web Service:
   - `REDIS_HOST`: (from Redis service - internal hostname)
   - `REDIS_PORT`: `6379`
   - `REDIS_PASSWORD`: (from Redis service)
   - `KITE_API_KEY`: (your key - optional for demo)
   - `KITE_ACCESS_TOKEN`: (your token - optional for demo)
   - `TEST_MODE_ENABLED`: `true`
   - `TEST_USERNAME`: `demo_user`
   - `TEST_PASSWORD`: `demo123`
8. Deploy!

**Note:** Free tier spins down after 15 minutes of inactivity, but wakes up on first request.

---

### Option 2: Railway (FREE Tier - $5 credit monthly)

1. Go to https://railway.app
2. Sign up (free account with $5 monthly credit)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select `rajamohan1950/LiveTradingPython`
5. Railway auto-detects Python
6. Add Redis:
   - Click "+ New" → "Database" → "Add Redis"
   - Use free tier
7. Set environment variables
8. Deploy!

**Note:** Railway gives $5 free credit monthly, which is usually enough for small apps.

---

### Option 3: Fly.io (FREE Tier)

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Sign up: `fly auth signup`
3. Launch: `fly launch` (from project directory)
4. Deploy: `fly deploy`

**Note:** Free tier includes 3 shared VMs.

---

### Option 4: PythonAnywhere (FREE Tier)

1. Go to https://www.pythonanywhere.com
2. Sign up (free account)
3. Upload code via Git or Files
4. Configure web app
5. Set environment variables
6. Deploy!

**Note:** Free tier has limitations but works for demos.

---

### Option 5: Replit (FREE Tier)

1. Go to https://replit.com
2. Sign up (free account)
3. Import from GitHub: `rajamohan1950/LiveTradingPython`
4. Configure environment variables
5. Run!

**Note:** Free tier has usage limits but good for demos.

---

## 🎯 Recommended: Render.com (Web Service, not Blueprint)

**Why:** 
- Truly free (no credit card needed)
- Easy setup
- Auto-deploys from GitHub
- Free Redis included

**Steps:**
1. Go to https://render.com
2. New → **Web Service** (NOT Blueprint)
3. Connect GitHub → Select repo
4. Configure manually (see above)
5. Add Redis separately (free tier)
6. Deploy!

---

## ⚠️ Important Notes

- **Render Blueprint** requires paid plan - use **Web Service** instead
- Free tiers may have limitations (sleep after inactivity, usage limits)
- For production, consider paid plans
- Demo/test mode works perfectly on free tiers

---

## 🔧 Environment Variables (All Free Tiers)

```
REDIS_HOST=<from-redis-service>
REDIS_PORT=6379
REDIS_PASSWORD=<from-redis-service>
KITE_API_KEY=<optional-for-demo>
KITE_ACCESS_TOKEN=<optional-for-demo>
TEST_MODE_ENABLED=true
TEST_USERNAME=demo_user
TEST_PASSWORD=demo123
LOG_LEVEL=INFO
```

---

## ✅ Quick Start (Render.com - FREE)

1. https://render.com → Sign up
2. New → **Web Service** (not Blueprint!)
3. Connect GitHub → Select repo
4. Build: `pip install -r requirements.txt`
5. Start: `python main.py`
6. Plan: **FREE**
7. Add Redis (separate, free tier)
8. Set env vars
9. Deploy!

🎉 Done! Your app will be live at: `https://live-trading-python.onrender.com`

