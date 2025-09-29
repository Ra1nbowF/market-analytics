# Grafana Setup on AWS Free Tier

## Option 1: Grafana Cloud Free (Recommended)

### Pros:
- ✅ Completely free (10k metrics, 50GB logs, 3 users)
- ✅ No EC2 instance needed
- ✅ Automatic updates and backups
- ✅ Built-in alerting

### Setup Steps:

1. **Sign up for Grafana Cloud Free**
   - Go to https://grafana.com/auth/sign-up/create-user
   - Choose "Free Forever" plan
   - Create your account

2. **Add PostgreSQL Data Source**
   ```
   Host: dex-analytics-db.ckh8iqooci55.us-east-1.rds.amazonaws.com:5432
   Database: market_analytics
   User: dbadmin
   Password: [your-password]
   SSL Mode: require
   ```

3. **Import Dashboard**
   - Copy content from `grafana/provisioning/dashboards/market-analytics copy.json`
   - Go to Dashboards → Import
   - Paste JSON and import

---

## Option 2: EC2 t2.micro with Docker (Free Tier)

### Setup Script:

```bash
#!/bin/bash

# Launch EC2 instance (Amazon Linux 2023)
aws ec2 run-instances \
    --image-id ami-0c02fb55731490381 \
    --instance-type t2.micro \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxx \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=grafana-server}]' \
    --user-data file://grafana-setup.sh \
    --region us-east-1
```

### User Data Script (grafana-setup.sh):

```bash
#!/bin/bash

# Update system
yum update -y

# Install Docker
yum install -y docker
service docker start
usermod -a -G docker ec2-user

# Run Grafana
docker run -d \
  --name=grafana \
  -p 3000:3000 \
  --restart=always \
  -e "GF_INSTALL_PLUGINS=grafana-postgresql-datasource" \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin123" \
  -v grafana-storage:/var/lib/grafana \
  grafana/grafana-oss:latest

# Configure firewall
# Allow port 3000 from anywhere (update security group)
```

### Security Group Rules:
```
Inbound:
- Port 3000: From your IP (Grafana)
- Port 22: From your IP (SSH)

Outbound:
- All traffic allowed
```

---

## Option 3: Local Grafana with SSH Tunnel (Zero Cost)

### Setup:

1. **Run Grafana locally**:
   ```powershell
   docker run -d `
     --name=grafana `
     -p 3000:3000 `
     -e "GF_INSTALL_PLUGINS=grafana-postgresql-datasource" `
     grafana/grafana-oss:latest
   ```

2. **Create SSH tunnel to RDS** (if RDS is not publicly accessible):
   ```powershell
   # Use EC2 instance as jump host
   ssh -L 5432:dex-analytics-db.ckh8iqooci55.us-east-1.rds.amazonaws.com:5432 ec2-user@your-ec2-ip
   ```

3. **Configure data source**:
   ```
   Host: localhost:5432 (if using tunnel)
   OR
   Host: dex-analytics-db.ckh8iqooci55.us-east-1.rds.amazonaws.com:5432 (if public)
   Database: market_analytics
   User: dbadmin
   Password: [your-password]
   ```

---

## Dashboard Configuration

### Update Data Source in JSON:

1. Open `grafana/provisioning/dashboards/market-analytics copy.json`

2. Replace all occurrences of:
   ```json
   "datasource": "grafana-postgresql-datasource"
   ```
   With:
   ```json
   "datasource": "AWS-RDS-PostgreSQL"
   ```

3. Update SQL queries if needed (should work as-is)

### Required Tables:
All tables are created by migration script:
- ✅ market_data
- ✅ trades
- ✅ orderbook_snapshots
- ✅ mm_metrics
- ✅ mm_performance
- ✅ long_short_ratio
- ✅ binance_perps_data
- ✅ liquidity_depth

---

## Testing the Setup

### 1. Verify Data Collection:
```sql
-- Connect to RDS
psql -h dex-analytics-db.ckh8iqooci55.us-east-1.rds.amazonaws.com \
     -U dbadmin -d market_analytics

-- Check recent data
SELECT COUNT(*), MAX(timestamp)
FROM market_data
WHERE timestamp > NOW() - INTERVAL '1 hour';
```

### 2. Check Lambda Logs:
```powershell
aws logs tail /aws/lambda/market-analytics-collector --follow
```

### 3. Test Dashboard Panels:
- Current Price (stat panel)
- Price Change % (stat panel)
- Bid/Ask Spreads (time series)
- Last 25 Trades (table)
- Trading Volume (bar chart)

---

## Cost Summary

### Grafana Cloud Free:
- **Cost**: $0/month forever
- **Limits**: 10k metrics, 3 users, 14 day retention

### EC2 t2.micro:
- **Cost**: $0/month (first 12 months)
- **After free tier**: ~$8/month

### RDS db.t3.micro:
- **Cost**: $0/month (first 12 months)
- **After free tier**: ~$12.50/month

### Lambda:
- **Cost**: $0/month (1M requests free)
- **5-min schedule**: ~8,640 requests/month

### **Total Cost During Free Tier**: $0/month
### **Total Cost After Free Tier**: ~$20.50/month (with EC2) or ~$12.50/month (with Grafana Cloud)

---

## Migration Checklist

- [ ] Run `migrate_railway_to_aws.py` to migrate data
- [ ] Deploy Lambda with `deploy_to_aws.ps1`
- [ ] Verify Lambda is collecting data (check CloudWatch logs)
- [ ] Set up Grafana (choose option above)
- [ ] Configure PostgreSQL data source in Grafana
- [ ] Import dashboard JSON
- [ ] Verify all panels show data
- [ ] Set up alerts (optional)
- [ ] Stop Railway services to avoid charges

---

## Rollback Plan

If issues occur:

1. **Keep Railway running** until AWS is verified
2. **Export Railway data**:
   ```sql
   pg_dump postgresql://user:pass@railway > backup.sql
   ```
3. **Test AWS thoroughly** before stopping Railway
4. **Keep backups** of both databases for 7 days

---

## Support Commands

### Check RDS Status:
```powershell
aws rds describe-db-instances `
    --db-instance-identifier dex-analytics-db `
    --query "DBInstances[0].DBInstanceStatus"
```

### Check Lambda Executions:
```powershell
aws cloudwatch get-metric-statistics `
    --namespace AWS/Lambda `
    --metric-name Invocations `
    --dimensions Name=FunctionName,Value=market-analytics-collector `
    --start-time 2024-01-01T00:00:00Z `
    --end-time 2024-12-31T23:59:59Z `
    --period 3600 `
    --statistics Sum
```

### Manual Lambda Trigger:
```powershell
aws lambda invoke `
    --function-name market-analytics-collector `
    --payload '{"manual": true}' `
    response.json
```

---

*Last Updated: September 2024*