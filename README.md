# Crypto Market Analytics Platform - Quick Start Guide

## 🚀 Start in 5 Minutes

### Prerequisites
- Docker Desktop installed
- 4GB RAM minimum
- Port 3000 (Grafana), 8000 (API), 5432 (PostgreSQL) available

### Step 1: Configure Your API Keys (Optional)
Edit `.env` file and add your exchange API keys:
```bash
BINANCE_API_KEY=your_key_here
BINANCE_SECRET=your_secret_here
# Add other exchange keys as needed
```

**Note:** The system will work without API keys using public endpoints, but with rate limits.

### Step 2: Start Everything
```bash
# Start all services
docker-compose up -d

# Check if everything is running
docker-compose ps

# View logs if needed
docker-compose logs -f backend
```

### Step 3: Access Grafana Dashboard
1. Open browser: http://localhost:3000
2. Login: admin / admin
3. Dashboard will auto-load with market data

## 📊 What You Get

### Real-time Monitoring
- **Bid/Ask Prices** across all exchanges
- **Spread Analysis** in basis points
- **24H Volume** tracking
- **Market Maker Compliance** metrics
- **Long/Short Ratios**
- **Open Interest** trends
- **Funding Rates**
- **Whale Activity** tracking

### Data Collection Frequencies
- Market data: Every 30 seconds
- Order books: Every minute
- Binance Perps data: Every 5 minutes
- Whale data: Every 15 minutes
- MM metrics: Every 5 minutes

## 🔧 Customization

### Track Different Symbols
Edit `.env`:
```bash
TRACK_SYMBOL=BTCUSDT,ETHUSDT,SOLUSDT
```

### Adjust Collection Frequency
Edit `backend/main.py` scheduler intervals

### Add Custom Alerts
In Grafana:
1. Click any panel → Edit
2. Go to Alert tab
3. Create alert rule

## 📝 API Endpoints

Base URL: http://localhost:8000

- `GET /` - Health check
- `GET /api/market/{symbol}` - Market data
- `GET /api/orderbook/{symbol}` - Order book
- `GET /api/perps/{symbol}` - Binance Perps data
- `GET /api/whale/{symbol}` - Whale activity
- `GET /api/mm/compliance/{symbol}` - MM compliance
- `GET /api/long-short/{symbol}` - Long/Short ratios
- `POST /api/collect/force` - Force data collection

### Example API Call
```bash
curl http://localhost:8000/api/market/BTCUSDT?hours=24
```

## 🛠️ Troubleshooting

### No Data Showing
```bash
# Check if backend is collecting data
docker-compose logs backend | tail -50

# Force data collection
curl -X POST http://localhost:8000/api/collect/force

# Check database
docker-compose exec postgres psql -U admin -d market_analytics -c "SELECT COUNT(*) FROM market_data;"
```

### Connection Issues
```bash
# Restart services
docker-compose restart

# Full reset
docker-compose down
docker volume prune
docker-compose up -d
```

### Grafana Issues
```bash
# Reset Grafana admin password
docker-compose exec grafana grafana-cli admin reset-admin-password newpassword
```

## 📈 Production Deployment

### Using a VPS (DigitalOcean/Linode)
1. Get a 4GB RAM VPS ($24/month)
2. Install Docker:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```
3. Clone repo and run:
```bash
git clone <your-repo>
cd market-analytics
docker-compose up -d
```

### Security
1. Use strong passwords in `.env`
2. Set up firewall rules
3. Use HTTPS with reverse proxy (nginx/caddy)
4. Never commit `.env` file

## 🔄 Updates & Maintenance

### Update Exchange Connectors
```bash
# Pull latest changes
git pull

# Rebuild backend
docker-compose build backend

# Restart
docker-compose up -d
```

### Backup Database
```bash
# Backup
docker-compose exec postgres pg_dump -U admin market_analytics > backup.sql

# Restore
docker-compose exec -T postgres psql -U admin market_analytics < backup.sql
```

### Clean Old Data
Data older than 90 days is automatically cleaned (configured in SQL schema).

## 📊 Grafana Tips

### Create Custom Dashboard
1. Click + → Create Dashboard
2. Add visualization
3. Use SQL queries from existing panels as templates

### Export Dashboard
1. Dashboard settings → JSON Model
2. Copy JSON
3. Save to `grafana/dashboards/`

### Share Dashboard
1. Dashboard → Share
2. Export → Save to file
3. Share JSON file

## 🐛 Debug Mode

### Enable Detailed Logging
Edit `backend/main.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Test Individual Exchanges
```python
# In backend/test_exchange.py
import asyncio
from exchanges.binance_perps import BinancePerpsConnector

async def test():
    async with BinancePerpsConnector() as exchange:
        data = await exchange.get_24hr_ticker('BTCUSDT')
        print(data)

asyncio.run(test())
```

## 📞 Support

### Common Issues
- **Rate Limits**: Add API keys or reduce collection frequency
- **Memory Issues**: Increase Docker memory limit
- **Slow Queries**: Check database indexes

### Get Help
- Check logs: `docker-compose logs`
- Database status: `docker-compose exec postgres pg_isready`
- API health: http://localhost:8000/

---

**Ready to Monitor Markets!** 🚀

Your market analytics platform is now running. Access Grafana at http://localhost:3000 to see real-time market data.