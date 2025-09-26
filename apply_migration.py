import asyncio
import asyncpg

async def apply_migration():
    """Apply migration to Railway database"""

    db_url = 'postgresql://postgres:zcePuQAopNvkXSuudTUMqZMJTfzOuApd@turntable.proxy.rlwy.net:56429/railway'

    print("Connecting to Railway database...")
    conn = await asyncpg.connect(db_url)

    try:
        # List of columns to add to market_data
        market_data_columns = [
            ("bid_volume", "DECIMAL(20, 8)"),
            ("ask_volume", "DECIMAL(20, 8)"),
            ("quote_volume_24h", "DECIMAL(30, 8)"),
            ("price_change_24h", "DECIMAL(20, 8)"),
            ("price_change_pct_24h", "DECIMAL(10, 4)"),
            ("high_24h", "DECIMAL(20, 8)"),
            ("low_24h", "DECIMAL(20, 8)")
        ]

        print("\n=== Adding columns to market_data ===")
        for col_name, col_type in market_data_columns:
            try:
                await conn.execute(f"ALTER TABLE market_data ADD COLUMN {col_name} {col_type}")
                print(f"  Added {col_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  {col_name} already exists")
                else:
                    print(f"  Error adding {col_name}: {e}")

        # List of columns to add to mm_metrics
        mm_metrics_columns = [
            ("spread_bps", "DECIMAL(10, 4)"),
            ("quote_count", "INTEGER DEFAULT 0"),
            ("bid_depth_1pct", "DECIMAL(20, 8)"),
            ("ask_depth_1pct", "DECIMAL(20, 8)"),
            ("bid_depth_2pct", "DECIMAL(20, 8)"),
            ("ask_depth_2pct", "DECIMAL(20, 8)"),
            ("uptime_pct", "DECIMAL(10, 4)")
        ]

        print("\n=== Adding columns to mm_metrics ===")
        for col_name, col_type in mm_metrics_columns:
            try:
                await conn.execute(f"ALTER TABLE mm_metrics ADD COLUMN {col_name} {col_type}")
                print(f"  Added {col_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  {col_name} already exists")
                else:
                    print(f"  Error adding {col_name}: {e}")

        # List of columns to add to mm_performance
        mm_performance_columns = [
            ("market_presence", "DECIMAL(10, 4)"),
            ("avg_spread_bps", "DECIMAL(10, 4)"),
            ("min_spread_bps", "DECIMAL(10, 4)"),
            ("max_spread_bps", "DECIMAL(10, 4)"),
            ("total_volume", "DECIMAL(30, 8)"),
            ("order_count", "INTEGER DEFAULT 0"),
            ("liquidity_2pct", "DECIMAL(20, 8)"),
            ("liquidity_4pct", "DECIMAL(20, 8)"),
            ("liquidity_8pct", "DECIMAL(20, 8)"),
            ("bid_ask_imbalance", "DECIMAL(10, 4)")
        ]

        print("\n=== Adding columns to mm_performance ===")
        for col_name, col_type in mm_performance_columns:
            try:
                await conn.execute(f"ALTER TABLE mm_performance ADD COLUMN {col_name} {col_type}")
                print(f"  Added {col_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  {col_name} already exists")
                else:
                    print(f"  Error adding {col_name}: {e}")

        # Create liquidity_depth table
        print("\n=== Creating liquidity_depth table ===")
        try:
            await conn.execute("""
                CREATE TABLE liquidity_depth (
                    id SERIAL PRIMARY KEY,
                    exchange VARCHAR(50) NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    depth_2pct_bid DECIMAL(20, 8),
                    depth_2pct_ask DECIMAL(20, 8),
                    depth_4pct_bid DECIMAL(20, 8),
                    depth_4pct_ask DECIMAL(20, 8),
                    depth_8pct_bid DECIMAL(20, 8),
                    depth_8pct_ask DECIMAL(20, 8),
                    total_bid_volume DECIMAL(30, 8),
                    total_ask_volume DECIMAL(30, 8),
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            print("  Table created successfully")

            # Create index
            await conn.execute("""
                CREATE INDEX idx_liquidity_depth_exchange_symbol_time
                ON liquidity_depth (exchange, symbol, timestamp DESC)
            """)
            print("  Index created successfully")

            # Try to convert to hypertable if TimescaleDB is available
            try:
                await conn.execute("""
                    SELECT create_hypertable('liquidity_depth', 'timestamp', if_not_exists => TRUE)
                """)
                print("  Converted to hypertable")
            except:
                print("  TimescaleDB not available, using regular table")

        except Exception as e:
            if "already exists" in str(e).lower():
                print("  Table already exists")
            else:
                print(f"  Error creating table: {e}")

        # Verify final schema
        print("\n=== Verifying final schema ===")

        # Check market_data
        result = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'market_data'
            AND column_name IN ('bid_volume', 'ask_volume', 'quote_volume_24h', 'price_change_24h',
                              'price_change_pct_24h', 'high_24h', 'low_24h')
        """)
        print(f"  market_data: {len(result)} new columns added")

        # Check mm_metrics
        result = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'mm_metrics'
            AND column_name IN ('spread_bps', 'quote_count', 'bid_depth_1pct', 'ask_depth_1pct',
                              'bid_depth_2pct', 'ask_depth_2pct', 'uptime_pct')
        """)
        print(f"  mm_metrics: {len(result)} new columns added")

        # Check mm_performance
        result = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'mm_performance'
            AND column_name IN ('market_presence', 'avg_spread_bps', 'min_spread_bps', 'max_spread_bps',
                              'total_volume', 'order_count', 'liquidity_2pct', 'liquidity_4pct',
                              'liquidity_8pct', 'bid_ask_imbalance')
        """)
        print(f"  mm_performance: {len(result)} new columns added")

        # Check liquidity_depth
        result = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'liquidity_depth'
        """)
        if result > 0:
            print("  liquidity_depth: Table exists")

        print("\nMigration completed!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())