# Live Trading System

A high-frequency trading system with Kite integration, designed for automated Bank Nifty futures trading with real-time monitoring, latency tracking, and comprehensive risk management.

## Features

### Core Trading System
- **Kite Integration**: Full authentication and live data streaming
- **Real-time Tick Processing**: Ultra-low latency tick data processing with Redis caching
- **Order Management**: Automated order placement, monitoring, and execution
- **Strategy Framework**: Adapter pattern for multiple trading strategies
- **Paper Trading**: Safe testing environment before live deployment

### Bank Nifty Strategy
- **Automated Entry**: Market buy order at 9:45 AM
- **Profit Target**: Automatic sell order 200 points above entry
- **Stop Loss**: Automatic sell order 100 points below entry
- **Market Exit**: Forced exit at 3:15 PM to avoid overnight charges
- **Partial Fill Handling**: Intelligent quantity management for partial executions

### Monitoring & Analytics
- **Latency Monitoring**: Track pipeline latency at every stage
- **Health Checks**: System resource monitoring and alerting
- **Real-time Dashboard**: Web-based UI with live updates
- **PnL Tracking**: Comprehensive profit/loss tracking with transaction costs
- **Order Book**: Live L3 order book construction and display

### Risk Management
- **Email Alerts**: Critical system alerts and trade notifications
- **Health Monitoring**: CPU, memory, disk, and network monitoring
- **Connection Monitoring**: Automatic reconnection and failover
- **Paper Trading Mode**: Safe testing before live deployment

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Kite API     │    │  Trading Engine │    │   Web UI        │
│   WebSocket    │───▶│                 │───▶│   Dashboard     │
│   Live Data    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │  Redis Cache    │              │
         │              │  Tick Storage   │              │
         │              └─────────────────┘              │
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │  Health Monitor │              │
         │              │  Email Alerts   │              │
         │              └─────────────────┘              │
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │  Latency Monitor│              │
         │              │  Performance    │              │
         │              └─────────────────┘              │
```

## Installation

### Prerequisites
- Python 3.8+
- Redis Server
- Kite API credentials

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd LiveTradingPython
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Start Redis server**
```bash
redis-server
```

5. **Run the application**
```bash
python main.py
```

6. **Access the dashboard**
Open http://localhost:8000 in your browser

## Configuration

### Environment Variables

```env
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
```

### Trading Parameters

- **BANK_NIFTY_SYMBOL**: Symbol for Bank Nifty futures
- **TRADING_QUANTITY**: Number of lots to trade
- **PROFIT_TARGET_POINTS**: Points above entry for profit target
- **STOP_LOSS_POINTS**: Points below entry for stop loss
- **TRADE_ENTRY_TIME**: Time to enter the trade (24-hour format)
- **MARKET_CLOSE_TIME**: Time to exit the trade (24-hour format)

## Usage

### 1. Authentication

1. Open the dashboard at http://localhost:8000
2. Go to the "Admin Settings" tab
3. Enter your Kite request token
4. Click "Authenticate"

### 2. Paper Trading (Recommended for first 2 days)

1. Ensure "Paper Trading" is enabled in Admin Settings
2. Monitor the system behavior and PnL
3. Verify all alerts and notifications work correctly
4. Review logs and performance metrics

### 3. Live Trading

1. Disable "Paper Trading" in Admin Settings
2. Ensure all health checks are green
3. Monitor the system closely during market hours
4. Be ready to intervene if needed

### 4. Monitoring

- **System Health**: Real-time system resource monitoring
- **Trading Status**: Current positions, orders, and trades
- **Latency Metrics**: Pipeline performance tracking
- **PnL Summary**: Profit/loss tracking with transaction costs
- **Order Book**: Live market depth visualization

## API Endpoints

### Authentication
- `POST /api/auth/kite` - Authenticate with Kite

### System Status
- `GET /api/status/system` - System health status
- `GET /api/status/trading` - Trading engine status
- `GET /api/health` - Health check endpoint

### Trading Data
- `GET /api/pnl` - PnL summary
- `GET /api/orders` - All orders
- `GET /api/trades` - All trades
- `GET /api/orderbook/{symbol}` - Order book for symbol

### Monitoring
- `GET /api/latency/summary` - Latency metrics summary
- `GET /api/metrics/system` - System performance metrics

### Strategy Management
- `POST /api/strategy/{name}/toggle` - Toggle strategy on/off
- `POST /api/strategy/{name}/paper-trading` - Toggle paper trading

### WebSocket
- `WS /api/ws` - Real-time updates

## Strategy Details

### Bank Nifty Strategy

**Entry Logic:**
- Market opens at 9:15 AM
- System health check at 8:45 AM
- Market buy order placed at exactly 9:45 AM

**Exit Logic:**
- Profit target: Sell order 200 points above entry
- Stop loss: Sell order 100 points below entry
- Market exit: Force sell at 3:15 PM

**Risk Management:**
- Partial fill handling
- Transaction cost tracking
- Email notifications for all major events

## Monitoring & Alerts

### Health Checks
- CPU usage monitoring
- Memory usage monitoring
- Disk space monitoring
- Network connectivity
- Redis connection
- Kite API connection
- Latency monitoring

### Email Alerts
- System health issues
- Trading engine problems
- Order execution notifications
- Strategy status updates
- Market close notifications

### Dashboard Alerts
- Real-time system status
- Trading activity indicators
- Performance metrics
- Error notifications

## Testing

### Unit Tests
```bash
pytest tests/test_trading_engine.py -v
```

### Integration Tests
```bash
pytest tests/test_integration.py -v
```

### Load Testing
```bash
pytest tests/test_load.py -v
```

## Performance Optimization

### Latency Optimization
- Async/await throughout the pipeline
- Redis caching for tick data
- Queue-based processing
- Minimal blocking operations

### Memory Management
- Bounded data structures
- Automatic cleanup of old data
- Efficient data serialization

### Network Optimization
- WebSocket for real-time data
- Connection pooling
- Automatic reconnection

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check API key and access token
   - Verify request token is valid
   - Ensure Kite account is active

2. **No Tick Data**
   - Check WebSocket connection
   - Verify market is open
   - Check symbol subscription

3. **High Latency**
   - Monitor system resources
   - Check network connectivity
   - Review Redis performance

4. **Orders Not Placing**
   - Verify authentication
   - Check account balance
   - Review order parameters

### Logs

- System logs: `./data/system.log`
- Trade logs: `./data/trade_history.log`
- Latency logs: `./data/latency_metrics.log`

## Security Considerations

- Store credentials securely
- Use environment variables
- Enable HTTPS in production
- Regular security updates
- Monitor access logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. Trading involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Always test thoroughly in paper trading mode before using with real money.

## Support

For support and questions:
- Email: rjabbala@gmail.com
- Create an issue in the repository
- Check the troubleshooting section

## Roadmap

- [ ] Additional trading strategies
- [ ] Machine learning integration
- [ ] Advanced risk management
- [ ] Mobile app
- [ ] Cloud deployment
- [ ] Multi-exchange support
