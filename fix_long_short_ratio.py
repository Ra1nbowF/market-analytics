import asyncio
import asyncpg

async def fix_long_short_ratio():
    """Fix long_short_ratio table schema on Railway database"""

    db_url = 'postgresql://postgres:zcePuQAopNvkXSuudTUMqZMJTfzOuApd@turntable.proxy.rlwy.net:56429/railway'

    print("Connecting to Railway database...")
    conn = await asyncpg.connect(db_url)

    try:
        print("\n=== Checking current long_short_ratio columns ===")
        result = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'long_short_ratio'
            ORDER BY ordinal_position
        """)

        print("Current columns:")
        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']}")

        # Add missing columns
        columns_to_add = [
            ("long_account_ratio", "DECIMAL(10, 4)"),
            ("short_account_ratio", "DECIMAL(10, 4)")
        ]

        print("\n=== Adding missing columns ===")
        for col_name, col_type in columns_to_add:
            try:
                await conn.execute(f"ALTER TABLE long_short_ratio ADD COLUMN {col_name} {col_type}")
                print(f"  Added {col_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  {col_name} already exists")
                else:
                    print(f"  Error adding {col_name}: {e}")

        # Copy data from existing columns if needed
        print("\n=== Migrating data ===")
        try:
            await conn.execute("""
                UPDATE long_short_ratio
                SET long_account_ratio = long_account,
                    short_account_ratio = short_account
                WHERE long_account_ratio IS NULL
            """)
            print("  Migrated existing data to new columns")
        except Exception as e:
            print(f"  Error migrating data: {e}")

        # Verify changes
        print("\n=== Verifying changes ===")
        result = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'long_short_ratio'
            AND column_name IN ('long_account_ratio', 'short_account_ratio')
        """)

        if len(result) == 2:
            print("  SUCCESS: Both columns now exist")
        else:
            print(f"  WARNING: Only {len(result)} columns found")

        # Show final schema
        print("\n=== Final long_short_ratio schema ===")
        result = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'long_short_ratio'
            ORDER BY ordinal_position
        """)

        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']}")

        print("\nMigration completed!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_long_short_ratio())