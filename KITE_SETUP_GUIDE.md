# 🔧 Kite App Setup Guide

## 📋 **Complete Setup Instructions**

### **Step 1: Create Kite App**

1. **Go to Kite Developer Console:**
   - Visit: https://kite.trade/connect/login
   - Login with your Kite credentials

2. **Create New App:**
   - Click "My Apps" → "Create New App"
   - **App Name**: `Live Trading System`
   - **Description**: `High-frequency trading system with real-time data`

3. **Set Redirect URL:**
   - **Redirect URL**: `http://localhost:8000/login`
   - This is where Kite will redirect after authentication

4. **Get Your Credentials:**
   - **API Key**: Copy this (starts with letters/numbers)
   - **API Secret**: Copy this (keep it secure!)

### **Step 2: Configure Your App**

#### **For Local Development:**
```
Redirect URL: http://localhost:8000/login
```

#### **For Production (when deployed):**
```
Redirect URL: https://yourdomain.com/login
```

### **Step 3: Login Process**

1. **Start the System:**
   ```bash
   ./run.sh
   # or
   source venv/bin/activate && python main.py
   ```

2. **Open Login Page:**
   - Go to: http://localhost:8000
   - You'll be redirected to the login page

3. **Enter Credentials:**
   - **API Key**: Your Kite API key
   - **API Secret**: Your Kite API secret
   - **Request Token**: Get this from Kite login

4. **Get Request Token:**
   - Click "Generate Login URL"
   - Copy the generated URL
   - Open it in a new tab
   - Login to Kite
   - Copy the `request_token` from the redirect URL

5. **Complete Authentication:**
   - Paste the request token
   - Click "Login to Trading System"

## 🔍 **Troubleshooting**

### **Common Issues:**

#### **1. "Invalid checksum" Error:**
- **Cause**: Wrong API secret
- **Fix**: Double-check your API secret from Kite Developer Console

#### **2. "API key should be minimum 6 characters" Error:**
- **Cause**: Invalid API key format
- **Fix**: Use the correct API key from Kite

#### **3. Redirect URL Mismatch:**
- **Cause**: Wrong redirect URL in Kite app
- **Fix**: Set redirect URL to `http://localhost:8000/login`

#### **4. "Authentication failed" Error:**
- **Cause**: Expired or invalid request token
- **Fix**: Generate a new login URL and get a fresh request token

### **Step-by-Step Debugging:**

1. **Check Kite App Settings:**
   - Verify redirect URL is exactly: `http://localhost:8000/login`
   - Ensure API key and secret are correct

2. **Check System Logs:**
   - Look for authentication errors in terminal
   - Check if system is running on port 8000

3. **Test API Endpoints:**
   ```bash
   # Test if system is running
   curl http://localhost:8000/health
   
   # Test login page
   curl http://localhost:8000/login
   ```

## 📱 **Quick Reference**

### **URLs:**
- **System**: http://localhost:8000
- **Login**: http://localhost:8000/login
- **Dashboard**: http://localhost:8000/dashboard (after login)

### **Kite Developer Console:**
- **URL**: https://kite.trade/connect/login
- **Redirect URL**: `http://localhost:8000/login`

### **Required Fields:**
- **API Key**: From Kite Developer Console
- **API Secret**: From Kite Developer Console  
- **Request Token**: From Kite login redirect

## ✅ **Success Indicators**

When everything is working correctly, you should see:
- ✅ Login page loads without errors
- ✅ "Generate Login URL" creates a valid Kite login URL
- ✅ Kite redirects back to your system with request token
- ✅ Authentication succeeds with "Welcome [username]!" message
- ✅ Dashboard loads with system status

## 🚨 **Important Notes**

1. **Keep API Secret Secure**: Never share your API secret
2. **Use HTTPS in Production**: Always use HTTPS for production deployments
3. **Test with Paper Trading**: Start with paper trading mode
4. **Monitor Logs**: Check system logs for any errors
5. **Backup Credentials**: Keep your API credentials safe

## 🆘 **Need Help?**

If you're still having issues:
1. Check the terminal logs for error messages
2. Verify all URLs are correct
3. Ensure Redis is running: `redis-server`
4. Try restarting the system: `./run.sh`

The system is designed to be robust and provide clear error messages to help you troubleshoot any issues! 🎯
