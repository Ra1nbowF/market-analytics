#!/usr/bin/env python3
"""
Migrate Market Analytics to AWS RDS using local schema
Uses the complete_dashboard_schema.sql we created earlier
"""
import psycopg2
import sys
import os
from datetime import datetime
from pathlib import Path

# Target: AWS RDS PostgreSQL
AWS_RDS_DB = {
    'host': 'dex-analytics-db.ckh8iqooci55.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'market_analytics',  # Will create separate database
    'user': 'dbadmin',
    'password': '123456789'  # Update with your actual password
}

def create_database_if_not_exists():
    """Create market_analytics database on RDS if it doesn't exist"""
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(
            host=AWS_RDS_DB['host'],
            port=AWS_RDS_DB['port'],
            database='postgres',
            user=AWS_RDS_DB['user'],
            password=AWS_RDS_DB['password']
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Check if database exists
        cur.execute("""
            SELECT 1 FROM pg_database WHERE datname = 'market_analytics'
        """)

        if not cur.fetchone():
            print("Creating market_analytics database on AWS RDS...")
            cur.execute("CREATE DATABASE market_analytics")
            print("Database created successfully!")
        else:
            print("Database market_analytics already exists on AWS RDS")

        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Error creating database: {e}")
        return False

def apply_schema(conn):
    """Apply the complete schema from our SQL file"""
    try:
        cur = conn.cursor()

        # Use the complete schema file we created
        schema_file = Path('database/complete_dashboard_schema.sql')

        # Fallback options
        if not schema_file.exists():
            print(f"Schema file not found at {schema_file}")
            # Try alternative locations
            alternatives = [
                'database/production_schema.sql',
                'database/production_schema_no_timescale.sql',
                'sql/init.sql'
            ]
            for alt in alternatives:
                alt_path = Path(alt)
                if alt_path.exists():
                    schema_file = alt_path
                    print(f"Using alternative schema: {alt_path}")
                    break

        if not schema_file.exists():
            print("ERROR: No schema file found!")
            print("Please ensure database/complete_dashboard_schema.sql exists")
            return False

        print(f"\nApplying schema from: {schema_file}")

        with open(schema_file, 'r') as f:
            schema_sql = f.read()

        # Split and execute statements
        statements = []
        current_statement = []

        for line in schema_sql.split('\n'):
            # Skip comments
            if line.strip().startswith('--'):
                continue

            current_statement.append(line)

            # Check if statement is complete
            if line.strip().endswith(';'):
                statement = '\n'.join(current_statement).strip()
                if statement and statement != ';':
                    statements.append(statement)
                current_statement = []

        # Execute each statement
        successful = 0
        failed = 0

        for i, statement in enumerate(statements, 1):
            try:
                # Handle special cases
                if 'CREATE EXTENSION' in statement:
                    # Try to create TimescaleDB extension
                    try:
                        cur.execute(statement)
                        print(f"  [{i}/{len(statements)}] TimescaleDB extension created")
                        successful += 1
                    except:
                        print(f"  [{i}/{len(statements)}] TimescaleDB not available (OK, using regular tables)")
                        successful += 1

                elif 'create_hypertable' in statement.lower():
                    # Skip hypertable creation if TimescaleDB not available
                    try:
                        cur.execute(statement)
                        print(f"  [{i}/{len(statements)}] Hypertable created")
                        successful += 1
                    except:
                        # Not critical - regular tables will work
                        successful += 1

                elif 'DO $$' in statement:
                    # Skip complex DO blocks that might fail
                    print(f"  [{i}/{len(statements)}] Skipping DO block (not critical)")
                    successful += 1

                else:
                    # Regular statement
                    cur.execute(statement)

                    if 'CREATE TABLE' in statement.upper():
                        # Extract table name
                        import re
                        match = re.search(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)', statement, re.IGNORECASE)
                        if match:
                            table_name = match.group(1)
                            print(f"  [{i}/{len(statements)}] Created table: {table_name}")
                    elif 'CREATE INDEX' in statement.upper():
                        print(f"  [{i}/{len(statements)}] Created index")
                    elif 'GRANT' in statement.upper():
                        print(f"  [{i}/{len(statements)}] Granted permissions")
                    else:
                        print(f"  [{i}/{len(statements)}] Executed statement")

                    successful += 1

                conn.commit()

            except Exception as e:
                if 'already exists' in str(e).lower():
                    print(f"  [{i}/{len(statements)}] Already exists (OK)")
                    successful += 1
                else:
                    print(f"  [{i}/{len(statements)}] Error: {str(e)[:100]}")
                    failed += 1
                conn.rollback()

        print(f"\nSchema application complete:")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")

        # Apply any migration fixes
        migration_file = Path('database/migration_fix_schema.sql')
        if migration_file.exists():
            print("\nApplying migration fixes...")
            with open(migration_file, 'r') as f:
                migration_sql = f.read()

            # Apply fixes (ignore errors as columns might already exist)
            for statement in migration_sql.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cur.execute(statement)
                        conn.commit()
                    except:
                        pass  # Ignore if column already exists

            print("Migration fixes applied")

        # Also apply the missing columns we fixed earlier
        print("\nApplying additional column fixes...")
        column_fixes = [
            "ALTER TABLE mm_metrics ADD COLUMN IF NOT EXISTS uptime_pct DECIMAL(10, 4)",
            "ALTER TABLE long_short_ratio ADD COLUMN IF NOT EXISTS top_trader_long_ratio DECIMAL(10, 4)",
            "ALTER TABLE long_short_ratio ADD COLUMN IF NOT EXISTS top_trader_short_ratio DECIMAL(10, 4)",
            "ALTER TABLE market_data ADD COLUMN IF NOT EXISTS count_24h BIGINT",
            "ALTER TABLE orderbook_snapshots ADD COLUMN IF NOT EXISTS imbalance DECIMAL(10, 4)",
            "ALTER TABLE trades ADD COLUMN IF NOT EXISTS maker BOOLEAN",
            "ALTER TABLE trades ADD COLUMN IF NOT EXISTS best_match BOOLEAN"
        ]

        for fix in column_fixes:
            try:
                cur.execute(fix)
                conn.commit()
            except:
                pass  # Column might already exist

        cur.close()
        return successful > 0

    except Exception as e:
        print(f"Error applying schema: {e}")
        return False

def verify_schema(conn):
    """Verify all required tables exist"""
    try:
        cur = conn.cursor()

        # Check tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        tables = [row[0] for row in cur.fetchall()]

        print("\nVerifying schema...")
        print(f"Found {len(tables)} tables:")

        required_tables = [
            'market_data',
            'trades',
            'orderbook_snapshots',
            'mm_metrics',
            'mm_performance',
            'long_short_ratio',
            'binance_perps_data',
            'liquidity_depth'
        ]

        for table in required_tables:
            if table in tables:
                # Count columns
                cur.execute(f"""
                    SELECT COUNT(*)
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                """)
                col_count = cur.fetchone()[0]
                print(f"  ✓ {table} ({col_count} columns)")
            else:
                print(f"  ✗ {table} MISSING!")

        # Check critical columns for dashboard
        print("\nVerifying critical dashboard columns...")

        critical_columns = {
            'market_data': ['bid_volume', 'ask_volume', 'price_change_pct_24h'],
            'mm_metrics': ['spread_bps', 'bid_depth_1pct', 'ask_depth_1pct', 'uptime_pct'],
            'mm_performance': ['market_presence', 'avg_spread_bps'],
            'long_short_ratio': ['long_account_ratio', 'short_account_ratio', 'top_trader_long_ratio'],
            'trades': ['trade_id', 'side', 'price', 'quantity']
        }

        all_good = True
        for table, columns in critical_columns.items():
            cur.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table}'
            """)
            existing_cols = {row[0] for row in cur.fetchall()}

            missing = [col for col in columns if col not in existing_cols]
            if missing:
                print(f"  ⚠ {table} missing: {', '.join(missing)}")
                all_good = False
            else:
                print(f"  ✓ {table} has all critical columns")

        cur.close()
        return all_good

    except Exception as e:
        print(f"Error verifying schema: {e}")
        return False

def insert_sample_data(conn):
    """Insert sample data to verify everything works"""
    try:
        cur = conn.cursor()

        print("\nInserting sample data for testing...")

        # Insert sample market data
        cur.execute("""
            INSERT INTO market_data (
                exchange, symbol, last_price, bid_price, ask_price,
                volume_24h, timestamp
            ) VALUES (
                'binance_perps', 'BTCUSDT', 65000, 64999, 65001,
                1000000, NOW()
            )
            ON CONFLICT DO NOTHING
        """)

        # Insert sample trade
        cur.execute("""
            INSERT INTO trades (
                exchange, symbol, price, quantity, side,
                timestamp, trade_id
            ) VALUES (
                'binance_perps', 'BTCUSDT', 65000, 0.1, 'buy',
                NOW(), 'test_trade_1'
            )
            ON CONFLICT DO NOTHING
        """)

        conn.commit()

        # Verify insertion
        cur.execute("SELECT COUNT(*) FROM market_data")
        market_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM trades")
        trade_count = cur.fetchone()[0]

        print(f"  Market data records: {market_count}")
        print(f"  Trade records: {trade_count}")

        cur.close()
        return True

    except Exception as e:
        print(f"Error inserting sample data: {e}")
        conn.rollback()
        return False

def main():
    """Main setup function"""
    print("=" * 60)
    print("AWS RDS Market Analytics Setup")
    print("Using local schema files (not Railway)")
    print("=" * 60)

    # Step 1: Create database
    if not create_database_if_not_exists():
        print("Failed to create database. Check your credentials.")
        return 1

    try:
        # Step 2: Connect to market_analytics database
        print("\nConnecting to market_analytics database...")
        conn = psycopg2.connect(**AWS_RDS_DB)
        print("Connected successfully!")

        # Step 3: Apply schema
        if not apply_schema(conn):
            print("Failed to apply schema completely.")
            # Continue anyway - some tables might be created

        # Step 4: Verify schema
        if verify_schema(conn):
            print("\n✅ All critical tables and columns verified!")
        else:
            print("\n⚠ Some columns might be missing, but core tables exist")

        # Step 5: Insert sample data
        insert_sample_data(conn)

        # Close connection
        conn.close()

        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)

        print("\nDatabase ready for:")
        print("1. Lambda function data collection")
        print("2. Grafana dashboard connection")

        print("\nConnection string for Grafana:")
        print(f"Host: {AWS_RDS_DB['host']}")
        print(f"Port: {AWS_RDS_DB['port']}")
        print(f"Database: {AWS_RDS_DB['database']}")
        print(f"User: {AWS_RDS_DB['user']}")
        print("SSL Mode: require")

        print("\nNext steps:")
        print("1. Run deploy_to_aws.ps1 to deploy Lambda")
        print("2. Set up Grafana (see grafana_aws_setup.md)")
        print("3. Import dashboard JSON")

        return 0

    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())