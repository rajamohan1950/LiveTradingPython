#!/usr/bin/env python3
"""
Startup script for Live Trading System
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import fastapi
        import redis
        import kiteconnect
        import pandas
        import numpy
        import psutil
        print("✓ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_redis():
    """Check if Redis is running"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✓ Redis is running")
        return True
    except Exception as e:
        print(f"✗ Redis is not running: {e}")
        print("Please start Redis: redis-server")
        return False

def check_config():
    """Check if configuration is set up"""
    config_file = Path('.env')
    if not config_file.exists():
        print("✗ Configuration file not found")
        print("Please copy .env.example to .env and configure it")
        return False
    
    print("✓ Configuration file found")
    return True

def create_directories():
    """Create necessary directories"""
    directories = ['data', 'logs', 'static', 'templates']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print("✓ Directories created")

def main():
    """Main startup function"""
    print("Live Trading System - Startup Check")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check Redis
    if not check_redis():
        sys.exit(1)
    
    # Check configuration
    if not check_config():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    print("\n✓ All checks passed!")
    print("Starting Live Trading System...")
    print("=" * 40)
    
    # Start the application
    try:
        subprocess.run([sys.executable, 'main.py'], check=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
