# Railway Quick Setup Guide

## Option 1: Through Railway Dashboard (Visual)

1. Go to your project on Railway
2. You'll see your deployed app from GitHub
3. Click **"+ New"** → **"Database"** → **"PostgreSQL"**
4. Click **"+ New"** → **"Database"** → **"Redis"**
5. Click on your main app service
6. Go to **Variables** tab
7. Add these variable references:
   - DATABASE_URL (from PostgreSQL)
   - REDIS_URL (from Redis)

## Option 2: Using Railway CLI (Faster)

Install Railway CLI:
```bash
# Windows (PowerShell)
iwr -useb https://raw.githubusercontent.com/railwayapp/cli/master/install.ps1 | iex

# Or with npm
npm install -g @railway/cli
```

Then run:
```bash
# Login
railway login

# Link to your project
railway link

# Add PostgreSQL
railway add postgresql

# Add Redis
railway add redis

# View all services
railway status
```

## Initialize Database

After PostgreSQL is created:

1. Click on the PostgreSQL service in Railway
2. Click **"Connect"** tab
3. Copy the connection string
4. Use it to connect and run your init.sql:

```bash
# Using psql
psql "postgresql://postgres:password@host.railway.app:5432/railway" -f sql/init.sql

# Or use Railway's query interface in the dashboard
```

## Environment Variables to Add

In your main app's Variables tab, add:

```env
# These will be auto-linked from services:
DATABASE_URL=${PGDATABASE_URL}
REDIS_URL=${REDIS_URL}

# Add these manually:
POSTGRES_DB=railway
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${PGPASSWORD}
TRACK_SYMBOL=BTCUSDT

# Optional exchange keys (for private data):
BINANCE_API_KEY=
BINANCE_SECRET=
```

## Verify Deployment

1. Check logs: Click on service → "Logs" tab
2. Your backend should connect to PostgreSQL and Redis
3. Access your API at: `your-app.railway.app`

## Connect Grafana Cloud

Since Railway doesn't easily support Grafana:

1. Sign up at https://grafana.com/auth/sign-up/
2. Create free account
3. Add PostgreSQL data source
4. Use Railway's PostgreSQL connection string
5. Import your dashboards (JSON files in grafana/dashboards/)