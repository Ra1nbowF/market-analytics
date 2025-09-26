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

        # Read the production schema file
        schema_file = Path('database/production_schema.sql')
        if not schema_file.exists():
            # Try alternative schema without TimescaleDB
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
                        print(f"  [{i}/{len(statements)}] Executed: {statement[:50]}...")
                except Exception as e:
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

        # Apply migration fixes if needed
        migration_file = Path('database/migration_fix_schema.sql')
        if migration_file.exists():
            print("\nApplying migration fixes...")
            with open(migration_file, 'r') as f:
                migration_sql = f.read()

            migration_statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
            for statement in migration_statements:
                if statement and not statement.startswith('--'):
                    try:
                        cur.execute(statement)
                    except Exception as e:
                        # Ignore errors for already existing columns
                        pass
            print("Migration fixes applied.")

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