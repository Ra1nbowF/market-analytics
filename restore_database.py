#!/usr/bin/env python3
"""
Script to restore database schema after Railway volume wipe
"""
import psycopg2
import os
import sys
from pathlib import Path

# Railway database connection
DB_CONFIG = {
    'host': 'turntable.proxy.rlwy.net',
    'port': 56429,
    'database': 'railway',
    'user': 'postgres',
    'password': 'zcePuQAopNvkXSuudTUMqZMJTfzOuApd'
}

def restore_database():
    """Restore database schema after wipe"""
    try:
        print("Connecting to Railway database...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()

        # Use the complete schema file that includes all dashboard fields
        schema_file = Path('database/complete_dashboard_schema.sql')

        # Fallback to original schema files if complete schema doesn't exist
        if not schema_file.exists():
            schema_file = Path('database/production_schema.sql')
            if not schema_file.exists():
                schema_file = Path('database/production_schema_no_timescale.sql')

        if not schema_file.exists():
            print("ERROR: No schema file found!")
            return False

        print(f"Reading schema from {schema_file}...")
        with open(schema_file, 'r') as f:
            schema_sql = f.read()

        # Execute schema creation
        print("Creating database schema...")

        # Split by semicolons and execute each statement
        statements = [s.strip() for s in schema_sql.split(';') if s.strip()]

        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    # Skip TimescaleDB-specific commands if they fail
                    if 'CREATE EXTENSION' in statement or 'create_hypertable' in statement:
                        try:
                            cur.execute(statement)
                            print(f"  [{i}/{len(statements)}] TimescaleDB: OK")
                        except Exception as e:
                            print(f"  [{i}/{len(statements)}] TimescaleDB not available, using regular tables")
                    else:
                        cur.execute(statement)
                        if 'CREATE TABLE' in statement:
                            table_name = statement.split('CREATE TABLE IF NOT EXISTS ')[1].split(' ')[0] if 'IF NOT EXISTS' in statement else statement.split('CREATE TABLE ')[1].split(' ')[0]
                            print(f"  [{i}/{len(statements)}] Created table: {table_name}")
                        elif 'CREATE INDEX' in statement:
                            print(f"  [{i}/{len(statements)}] Created index")
                        else:
                            print(f"  [{i}/{len(statements)}] Executed: {statement[:50]}...")
                except Exception as e:
                    if 'already exists' not in str(e).lower():
                        print(f"  Warning on statement {i}: {e}")

        # Verify tables were created
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cur.fetchall()
        print(f"\nSuccessfully created {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")

        # Verify critical fields for dashboard
        print("\nVerifying dashboard-critical fields...")
        critical_checks = [
            ('market_data', ['bid_volume', 'ask_volume', 'price_change_pct_24h']),
            ('mm_metrics', ['spread_bps', 'bid_depth_1pct', 'ask_depth_1pct']),
            ('mm_performance', ['market_presence', 'avg_spread_bps']),
            ('long_short_ratio', ['long_account_ratio', 'short_account_ratio']),
            ('liquidity_depth', ['depth_2pct_bid', 'depth_2pct_ask'])
        ]

        all_good = True
        for table_name, required_fields in critical_checks:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
            """, (table_name,))

            existing_columns = {row[0] for row in cur.fetchall()}
            missing = [f for f in required_fields if f not in existing_columns]

            if missing:
                print(f"  ⚠️  {table_name}: Missing fields: {', '.join(missing)}")
                all_good = False
            else:
                print(f"  ✅ {table_name}: All critical fields present")

        if all_good:
            print("\n✅ All dashboard requirements verified!")

        cur.close()
        conn.close()

        print("\n✅ Database schema restored successfully!")
        print("\nNext steps:")
        print("1. Restart your backend service to begin data collection")
        print("2. The dashboard will start showing data as it's collected")
        print("3. Monitor logs to ensure collectors are working")

        return True

    except Exception as e:
        print(f"\n❌ Error restoring database: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure the database is accessible")
        print("2. Check if the wipe has completed")
        print("3. Verify connection credentials")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Railway Database Schema Restoration Tool")
    print("=" * 60)
    print("\n⚠️  This should be run AFTER wiping the volume")
    print("⚠️  All previous data will be lost\n")

    response = input("Have you already wiped the Railway volume? (yes/no): ")
    if response.lower() != 'yes':
        print("\nPlease wipe the volume first from Railway dashboard:")
        print("Settings -> Wipe Volume (NOT Delete Volume)")
        sys.exit(0)

    print("\nStarting restoration process...")
    success = restore_database()

    if not success:
        sys.exit(1)