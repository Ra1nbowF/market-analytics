#!/usr/bin/env python3
"""
Migrate Market Analytics from Railway to AWS RDS
Preserves existing AWS infrastructure for DEX Analytics
"""
import psycopg2
import sys
import os
from datetime import datetime
from pathlib import Path

# Source: Railway PostgreSQL
RAILWAY_DB = {
    'host': 'turntable.proxy.rlwy.net',
    'port': 56429,
    'database': 'railway',
    'user': 'postgres',
    'password': 'zcePuQAopNvkXSuudTUMqZMJTfzOuApd'
}

# Target: AWS RDS PostgreSQL (already created for DEX)
AWS_RDS_DB = {
    'host': 'dex-analytics-db.ckh8iqooci55.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'market_analytics',  # Will create separate database
    'user': 'dbadmin',
    'password': '123456789'  # Update with your actual password
}

# Tables to migrate (Market Analytics specific)
MARKET_TABLES = [
    'market_data',
    'trades',
    'orderbook_snapshots',
    'mm_metrics',
    'mm_performance',
    'long_short_ratio',
    'binance_perps_data',
    'liquidity_depth',
    'whale_data',
    'mm_probability_score',
    'price_impact_analysis',
    'suspicious_activity'
]

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

def get_table_ddl(source_conn, table_name):
    """Extract CREATE TABLE statement from Railway"""
    cur = source_conn.cursor()

    # Get column definitions
    cur.execute("""
        SELECT
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))

    columns = []
    for row in cur.fetchall():
        col_name, data_type, char_len, num_prec, num_scale, nullable, default = row

        # Build column definition
        col_def = f'    {col_name} '

        # Handle data types
        if data_type == 'character varying':
            col_def += f'VARCHAR({char_len if char_len else 255})'
        elif data_type == 'numeric':
            if num_prec and num_scale:
                col_def += f'DECIMAL({num_prec}, {num_scale})'
            else:
                col_def += 'DECIMAL(20, 8)'
        elif data_type == 'timestamp with time zone':
            col_def += 'TIMESTAMPTZ'
        elif data_type == 'integer':
            col_def += 'INTEGER'
        elif data_type == 'bigint':
            col_def += 'BIGINT'
        elif data_type == 'jsonb':
            col_def += 'JSONB'
        elif data_type == 'boolean':
            col_def += 'BOOLEAN'
        else:
            col_def += data_type.upper()

        # Add constraints
        if nullable == 'NO':
            col_def += ' NOT NULL'

        if default:
            if 'nextval' in default:
                col_def = f'    {col_name} SERIAL'
                if nullable == 'NO':
                    col_def += ' NOT NULL'
            elif default != 'NULL':
                col_def += f' DEFAULT {default}'

        columns.append(col_def)

    # Get primary key
    cur.execute("""
        SELECT column_name
        FROM information_schema.key_column_usage
        WHERE table_name = %s
        AND constraint_name = %s || '_pkey'
    """, (table_name, table_name))

    pk_columns = [row[0] for row in cur.fetchall()]

    ddl = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    ddl += ',\n'.join(columns)

    if pk_columns:
        ddl += f",\n    PRIMARY KEY ({', '.join(pk_columns)})"

    ddl += "\n)"

    cur.close()
    return ddl

def migrate_table_data(source_conn, target_conn, table_name):
    """Copy data from Railway to AWS RDS"""
    try:
        source_cur = source_conn.cursor()
        target_cur = target_conn.cursor()

        # Get total count
        source_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = source_cur.fetchone()[0]

        if total_rows == 0:
            print(f"  No data to migrate in {table_name}")
            return True

        print(f"  Migrating {total_rows:,} rows from {table_name}...")

        # Get column names
        source_cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            AND column_name != 'id'
            ORDER BY ordinal_position
        """, (table_name,))

        columns = [row[0] for row in source_cur.fetchall()]
        column_list = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))

        # Migrate in batches
        batch_size = 10000
        offset = 0

        while offset < total_rows:
            # Fetch batch from source
            source_cur.execute(f"""
                SELECT {column_list}
                FROM {table_name}
                ORDER BY timestamp
                LIMIT {batch_size} OFFSET {offset}
            """)

            rows = source_cur.fetchall()

            # Insert batch into target
            insert_query = f"""
                INSERT INTO {table_name} ({column_list})
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """

            target_cur.executemany(insert_query, rows)
            target_conn.commit()

            offset += batch_size
            progress = min(100, (offset / total_rows) * 100)
            print(f"    Progress: {progress:.1f}% ({min(offset, total_rows):,}/{total_rows:,} rows)")

        source_cur.close()
        target_cur.close()
        return True

    except Exception as e:
        print(f"  Error migrating {table_name}: {e}")
        target_conn.rollback()
        return False

def create_indexes(target_conn, table_name):
    """Create indexes on AWS RDS tables"""
    cur = target_conn.cursor()

    indexes = {
        'market_data': [
            'CREATE INDEX IF NOT EXISTS idx_market_data_exchange_symbol_time ON market_data (exchange, symbol, timestamp DESC)',
            'CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time ON market_data (symbol, timestamp DESC)'
        ],
        'trades': [
            'CREATE INDEX IF NOT EXISTS idx_trades_exchange_symbol_time ON trades (exchange, symbol, timestamp DESC)',
            'CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades (symbol, timestamp DESC)'
        ],
        'orderbook_snapshots': [
            'CREATE INDEX IF NOT EXISTS idx_orderbook_exchange_symbol_time ON orderbook_snapshots (exchange, symbol, timestamp DESC)'
        ],
        'mm_metrics': [
            'CREATE INDEX IF NOT EXISTS idx_mm_metrics_exchange_symbol_time ON mm_metrics (exchange, symbol, timestamp DESC)'
        ],
        'mm_performance': [
            'CREATE INDEX IF NOT EXISTS idx_mm_performance_exchange_symbol_time ON mm_performance (exchange, symbol, timestamp DESC)'
        ],
        'long_short_ratio': [
            'CREATE INDEX IF NOT EXISTS idx_long_short_ratio_symbol_time ON long_short_ratio (symbol, timestamp DESC)'
        ],
        'binance_perps_data': [
            'CREATE INDEX IF NOT EXISTS idx_binance_perps_symbol_time ON binance_perps_data (symbol, timestamp DESC)'
        ]
    }

    if table_name in indexes:
        for idx_sql in indexes[table_name]:
            try:
                cur.execute(idx_sql)
                print(f"    Created index for {table_name}")
            except Exception as e:
                print(f"    Index might already exist: {e}")

    cur.close()
    target_conn.commit()

def main():
    """Main migration function"""
    print("=" * 60)
    print("Railway to AWS RDS Migration Tool")
    print("=" * 60)

    # Step 1: Create database on AWS RDS
    if not create_database_if_not_exists():
        print("Failed to create database. Exiting.")
        return 1

    try:
        # Connect to Railway
        print("\nConnecting to Railway database...")
        source_conn = psycopg2.connect(**RAILWAY_DB)
        print("Connected to Railway successfully!")

        # Connect to AWS RDS
        print("\nConnecting to AWS RDS...")
        target_conn = psycopg2.connect(**AWS_RDS_DB)
        print("Connected to AWS RDS successfully!")

        # Check what tables exist in Railway
        cur = source_conn.cursor()
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        railway_tables = [row[0] for row in cur.fetchall()]
        cur.close()

        print(f"\nFound {len(railway_tables)} tables in Railway")

        # Filter to only market analytics tables
        tables_to_migrate = [t for t in MARKET_TABLES if t in railway_tables]

        print(f"Will migrate {len(tables_to_migrate)} market analytics tables")

        # Migrate each table
        for table_name in tables_to_migrate:
            print(f"\nMigrating table: {table_name}")

            # Get and execute DDL
            ddl = get_table_ddl(source_conn, table_name)
            cur = target_conn.cursor()

            try:
                cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                cur.execute(ddl)
                target_conn.commit()
                print(f"  Table structure created")
            except Exception as e:
                print(f"  Error creating table: {e}")
                target_conn.rollback()
                continue

            # Migrate data
            if migrate_table_data(source_conn, target_conn, table_name):
                print(f"  Data migration completed")

            # Create indexes
            create_indexes(target_conn, table_name)

        # Verify migration
        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)

        cur = target_conn.cursor()
        for table_name in tables_to_migrate:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            print(f"  {table_name}: {count:,} rows")

        cur.close()

        # Close connections
        source_conn.close()
        target_conn.close()

        print("\n[SUCCESS] Migration completed!")
        print("\nNext steps:")
        print("1. Update backend configuration to use AWS RDS")
        print("2. Deploy backend to AWS Lambda or EC2")
        print("3. Update Grafana data source to AWS RDS")

        return 0

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())