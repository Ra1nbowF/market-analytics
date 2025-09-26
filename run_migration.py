import asyncio
import asyncpg
import os

async def run_migration():
    """Apply migration to Railway database"""

    # Railway database URL
    db_url = 'postgresql://postgres:zcePuQAopNvkXSuudTUMqZMJTfzOuApd@turntable.proxy.rlwy.net:56429/railway'

    print("Connecting to Railway database...")
    conn = await asyncpg.connect(db_url)

    try:
        # Read migration script
        with open('database/migration_fix_schema.sql', 'r') as f:
            migration_sql = f.read()

        # Split into individual statements and execute
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

        for i, statement in enumerate(statements):
            if statement:
                try:
                    print(f"Executing statement {i+1}/{len(statements)}...")
                    await conn.execute(statement)
                    print(f"  Success")
                except Exception as e:
                    print(f"  Error: {e}")
                    if "already exists" not in str(e).lower():
                        print(f"    Statement: {statement[:100]}...")

        print("\nVerifying schema changes...")

        # Check market_data columns
        print("\n=== market_data table columns ===")
        result = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'market_data'
            ORDER BY ordinal_position
        """)
        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']}")

        # Check mm_metrics columns
        print("\n=== mm_metrics table columns ===")
        result = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'mm_metrics'
            ORDER BY ordinal_position
        """)
        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']}")

        # Check mm_performance columns
        print("\n=== mm_performance table columns ===")
        result = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'mm_performance'
            ORDER BY ordinal_position
        """)
        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']}")

        # Check if liquidity_depth exists
        print("\n=== liquidity_depth table ===")
        result = await conn.fetchval("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'liquidity_depth'
        """)
        if result > 0:
            print("  Table exists")
            result = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'liquidity_depth'
                ORDER BY ordinal_position
            """)
            for row in result:
                print(f"  - {row['column_name']}: {row['data_type']}")
        else:
            print("  Table does not exist")

        print("\nMigration completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())