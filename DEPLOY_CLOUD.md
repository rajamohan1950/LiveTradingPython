# LiveTradingPython - Cloud Deployment Guide

## 🚀 Quick Local Test

```bash
cd /Users/rjabbala/Projects/LiveTradingPython
./test_local.sh
./run.sh
```

Access dashboard: http://localhost:8000

---

## ☁️ Cloud Deployment Options

### Option 1: Railway (Recommended - Easiest)

```bash
./deploy-cloud.sh railway
```

Railway will:
- Auto-detect Python
- Build and deploy automatically
- Provide PostgreSQL and Redis
- Give you a public URL instantly

**Manual Steps:**
1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Initialize: `railway init`
4. Deploy: `railway up`
5. Set environment variables from `.env` file

---

### Option 2: Render.com (Free Tier Available)

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Create render.yaml:**
   ```yaml
   services:
     - type: web
       name: live-trading-python
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: python main.py
       envVars:
         - key: REDIS_URL
           sync: false
         - key: KITE_API_KEY
           sync: false
         - key: KITE_ACCESS_TOKEN
           sync: false
   
   databases:
     - name: live-trading-redis
       plan: starter
   ```

3. **Deploy:**
   - Go to https://render.com
   - Click "New" → "Blueprint"
   - Connect GitHub repo
   - Render auto-detects and deploys

---

### Option 3: Heroku

```bash
./deploy-cloud.sh heroku
```

Or manually:
```bash
heroku create live-trading-python
heroku addons:create heroku-redis:mini
heroku config:set KITE_API_KEY=your_key
heroku config:set KITE_ACCESS_TOKEN=your_token
git push heroku main
```

---

### Option 4: AWS (EC2/ECS)

**Using EC2:**
1. Launch EC2 instance (Ubuntu 22.04)
2. Install dependencies:
   ```bash
   sudo apt update
   sudo apt install python3-pip redis-server -y
   pip3 install -r requirements.txt
   ```
3. Start Redis: `sudo systemctl start redis`
4. Run: `python3 main.py`

**Using ECS:**
1. Build Docker image: `docker build -t live-trading-python .`
2. Push to ECR
3. Create ECS service with the image

---

### Option 5: Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/live-trading-python
gcloud run deploy live-trading-python \
  --image gcr.io/PROJECT_ID/live-trading-python \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## 🔧 Required Environment Variables

Set these in your cloud platform:

```env
# Kite API (Required)
KITE_API_KEY=your_api_key
KITE_ACCESS_TOKEN=your_access_token
KITE_REQUEST_TOKEN=your_request_token

# Redis (Required)
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Trading Configuration
BANK_NIFTY_SYMBOL=NIFTY BANK
TRADING_QUANTITY=1
PROFIT_TARGET_POINTS=200
STOP_LOSS_POINTS=100
TRADE_ENTRY_TIME=09:45
MARKET_CLOSE_TIME=15:15

# System
LOG_LEVEL=INFO
```

---

## 📊 Infrastructure Requirements

### Minimum
- CPU: 1 core
- RAM: 512MB
- Storage: 1GB

### Recommended
- CPU: 2+ cores
- RAM: 2GB+
- Storage: 5GB
- Redis: Managed service (ElastiCache, Memorystore, etc.)

---

## 🔒 Security Notes

1. **Never commit `.env` file** - Use cloud secrets manager
2. **Use HTTPS** - Enable SSL/TLS in production
3. **Restrict access** - Use firewall rules
4. **Monitor logs** - Set up alerting
5. **Backup data** - Regular backups of trade history

---

## 🚀 Quick Deploy Commands

```bash
# Test locally first
./test_local.sh

# Deploy to Railway
./deploy-cloud.sh railway

# Deploy to Render
./deploy-cloud.sh render

# Deploy to Heroku
./deploy-cloud.sh heroku
```

---

## 📈 Monitoring

- Health endpoint: `/health`
- Dashboard: `/dashboard`
- API docs: `/docs` (FastAPI auto-generated)

---

## 💡 Recommendation

**For fastest deployment**: Use **Railway** - handles everything automatically.

**For free hosting**: Use **Render.com** - generous free tier.

**For production**: Use **AWS/GCP** - better control and reliability.

