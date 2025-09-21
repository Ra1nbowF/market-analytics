# Deployment Guide for Market Analytics Platform

## Railway.app Deployment (Recommended - Free Tier)

### Prerequisites
1. GitHub account
2. Railway account (sign up at https://railway.app)

### Step 1: Prepare Your Repository

1. Create a new GitHub repository
2. Push your code:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/market-analytics.git
git push -u origin main
```

### Step 2: Deploy on Railway

1. **Login to Railway**: https://railway.app

2. **Create New Project**: Click "New Project" → "Deploy from GitHub repo"

3. **Connect GitHub**: Authorize Railway to access your repository

4. **Deploy Services**:

   a. **PostgreSQL with TimescaleDB**:
   - Click "New" → "Database" → "PostgreSQL"
   - After creation, click on the database
   - Go to "Variables" tab and note the DATABASE_URL
   - Connect to database and run the init.sql script

   b. **Redis**:
   - Click "New" → "Database" → "Redis"
   - Note the REDIS_URL from Variables tab

   c. **Backend Service**:
   - Click "New" → "GitHub Repo" → Select your repo
   - Add environment variables:
     ```
     DATABASE_URL=<from PostgreSQL>
     REDIS_URL=<from Redis>
     BINANCE_API_KEY=<your key>
     BINANCE_SECRET=<your secret>
     # Add other exchange keys...
     ```

   d. **Grafana** (Optional - Use Grafana Cloud Free):
   - Sign up at https://grafana.com/auth/sign-up/create-user
   - Get free tier (10k metrics, 50GB logs, 50GB traces)
   - Add PostgreSQL datasource with Railway connection string

### Step 3: Environment Variables

Create these in Railway's Variables section:
```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/railway

# Redis
REDIS_URL=redis://default:pass@host:6379

# Exchange APIs (optional for public data)
BINANCE_API_KEY=
BINANCE_SECRET=
BITGET_API_KEY=
BITGET_SECRET=
BITGET_PASSPHRASE=
GATE_API_KEY=
GATE_SECRET=
KUCOIN_API_KEY=
KUCOIN_SECRET=
KUCOIN_PASSPHRASE=

# Symbol to track
TRACK_SYMBOL=BTCUSDT
```

### Step 4: Initialize Database

1. Connect to PostgreSQL using Railway's connection string:
```bash
psql $DATABASE_URL
```

2. Run the initialization script:
```sql
\i sql/init.sql
```

## Alternative: Fly.io Deployment

### Prerequisites
1. Install Fly CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Sign up (requires credit card but won't charge)

### Deploy with Fly.io

1. **Login**:
```bash
flyctl auth login
```

2. **Create fly.toml**:
```toml
app = "market-analytics"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8000"

[[services]]
  internal_port = 8000
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

3. **Deploy**:
```bash
flyctl launch
flyctl postgres create
flyctl redis create
flyctl deploy
```

## Alternative: Render.com Deployment

### Pros
- Free PostgreSQL for 90 days
- Free web services (with limitations)
- Easy deployment from GitHub

### Cons
- Services sleep after 15 minutes of inactivity
- Limited to 750 hours/month

### Steps
1. Sign up at https://render.com
2. Connect GitHub repository
3. Create:
   - PostgreSQL database (free 90 days)
   - Redis instance
   - Web Service (backend)
4. Add environment variables
5. Deploy

## Using Grafana Cloud (Recommended for All)

Instead of self-hosting Grafana, use Grafana Cloud free tier:

1. **Sign up**: https://grafana.com/auth/sign-up/
2. **Get free forever plan**:
   - 10,000 series for metrics
   - 50 GB for logs
   - 50 GB for traces
   - 3 users

3. **Configure datasource**:
   - Add PostgreSQL datasource
   - Use Railway/Fly.io database connection string
   - Import your dashboards

## Local Development with Ngrok (Testing Only)

For temporary public access to local deployment:

1. Install ngrok: https://ngrok.com/download
2. Run your docker-compose locally
3. Expose with ngrok:
```bash
ngrok http 3000  # For Grafana
ngrok http 8000  # For API
```

## Important Notes

1. **API Keys**: Most public market data doesn't require API keys
2. **Rate Limits**: Be aware of free tier limitations
3. **Data Retention**: Free tiers may have limited data retention
4. **Scaling**: Free tiers are for development/small projects

## Monitoring & Maintenance

1. Set up health checks in Railway/Fly.io
2. Use Grafana alerts for monitoring
3. Implement data retention policies for free tier limits
4. Consider upgrading if you exceed free tier limits

## Security Considerations

1. Never commit API keys to GitHub
2. Use environment variables for all secrets
3. Enable 2FA on all services
4. Restrict database access to service IPs only