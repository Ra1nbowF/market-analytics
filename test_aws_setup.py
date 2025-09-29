#!/usr/bin/env python3
"""
Test AWS RDS setup for Market Analytics
"""
import psycopg2
import sys
from datetime import datetime

# AWS RDS connection
AWS_RDS_DB = {
    'host': 'dex-analytics-db.ckh8iqooci55.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'market_analytics',
    'user': 'dbadmin',
    'password': '123456789'  # Update with your actual password
}

def test_connection():
    """Test database connection and tables"""
    try:
        print("Testing AWS RDS Market Analytics Setup")
        print("=" * 50)

        # Connect
        print(f"\nConnecting to {AWS_RDS_DB['host']}...")
        conn = psycopg2.connect(**AWS_RDS_DB)
        cur = conn.cursor()
        print("✓ Connection successful")

        # Check PostgreSQL version
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print(f"✓ PostgreSQL: {version.split(',')[0]}")

        # Check tables
        print("\nChecking tables:")
        cur.execute("""
            SELECT table_name,
                   pg_size_pretty(pg_total_relation_size(table_schema||'.'||table_name)) as size
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        tables = cur.fetchall()
        if not tables:
            print("✗ No tables found! Run aws_migration_fixed.py first")
            return False

        for table, size in tables:
            print(f"  ✓ {table:<25} {size}")

        # Check critical columns for dashboard
        print("\nChecking dashboard requirements:")

        checks = [
            ("market_data", ["bid_price", "ask_price", "last_price", "volume_24h"]),
            ("trades", ["price", "quantity", "side", "trade_id"]),
            ("mm_metrics", ["spread_bps", "bid_depth_1pct", "uptime_pct"]),
            ("long_short_ratio", ["long_account_ratio", "short_account_ratio"])
        ]

        all_good = True
        for table, required_cols in checks:
            cur.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table}'
            """)

            existing = {row[0] for row in cur.fetchall()}

            if not existing:
                print(f"  ✗ {table}: Table doesn't exist")
                all_good = False
                continue

            missing = [col for col in required_cols if col not in existing]
            if missing:
                print(f"  ⚠ {table}: Missing {missing}")
                all_good = False
            else:
                print(f"  ✓ {table}: All required columns present")

        # Check data
        print("\nChecking data:")

        tables_to_check = ['market_data', 'trades', 'mm_metrics']
        for table in tables_to_check:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]

                if count > 0:
                    cur.execute(f"SELECT MAX(timestamp) FROM {table}")
                    latest = cur.fetchone()[0]
                    print(f"  {table}: {count:,} records (latest: {latest})")
                else:
                    print(f"  {table}: No data yet (will be populated by Lambda)")
            except:
                print(f"  {table}: Not found")

        # Test insert capability
        print("\nTesting write capability:")
        try:
            cur.execute("""
                INSERT INTO market_data (
                    exchange, symbol, last_price, bid_price, ask_price,
                    volume_24h, timestamp
                ) VALUES (
                    'test', 'TESTUSDT', 100, 99, 101, 1000, %s
                )
            """, (datetime.now(),))

            conn.commit()
            print("  ✓ Successfully wrote test data")

            # Clean up test data
            cur.execute("DELETE FROM market_data WHERE exchange = 'test'")
            conn.commit()

        except Exception as e:
            print(f"  ✗ Write failed: {e}")
            all_good = False

        cur.close()
        conn.close()

        print("\n" + "=" * 50)
        if all_good:
            print("✅ AWS RDS is ready for Market Analytics!")
            print("\nNext steps:")
            print("1. Deploy Lambda: .\\deploy_to_aws.ps1")
            print("2. Set up Grafana (see grafana_aws_setup.md)")
        else:
            print("⚠ Some issues detected. Run aws_migration_fixed.py to fix")

        return all_good

    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check password in the script")
        print("2. Verify RDS is running (check AWS console)")
        print("3. Check security group allows your IP")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)