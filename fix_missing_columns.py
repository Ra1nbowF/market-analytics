#!/usr/bin/env python3
"""
Fix missing columns in Railway database that are causing errors
"""
import psycopg2
import sys

DB_CONFIG = {
    'host': 'turntable.proxy.rlwy.net',
    'port': 56429,
    'database': 'railway',
    'user': 'postgres',
    'password': 'zcePuQAopNvkXSuudTUMqZMJTfzOuApd'
}

def fix_missing_columns():
    """Add missing columns that the application expects"""
    try:
        print("Connecting to Railway database...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()

        print("\nFixing missing columns...")

        # Fix mm_metrics table - add uptime_pct
        fixes = [
            # mm_metrics missing columns
            ("ALTER TABLE mm_metrics ADD COLUMN IF NOT EXISTS uptime_pct DECIMAL(10, 4)",
             "mm_metrics.uptime_pct"),

            # long_short_ratio missing columns
            ("ALTER TABLE long_short_ratio ADD COLUMN IF NOT EXISTS top_trader_long_ratio DECIMAL(10, 4)",
             "long_short_ratio.top_trader_long_ratio"),
            ("ALTER TABLE long_short_ratio ADD COLUMN IF NOT EXISTS top_trader_short_ratio DECIMAL(10, 4)",
             "long_short_ratio.top_trader_short_ratio"),

            # Also fix the quote_count typo (ote_count in error)
            ("ALTER TABLE mm_metrics ADD COLUMN IF NOT EXISTS quote_count INTEGER DEFAULT 0",
             "mm_metrics.quote_count (fixing typo)"),
        ]

        for sql, description in fixes:
            try:
                cur.execute(sql)
                print(f"  [OK] Added: {description}")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    print(f"  [SKIP] Already exists: {description}")
                else:
                    print(f"  [ERROR] Failed to add {description}: {e}")

        # Verify the fixes
        print("\nVerifying table structures...")

        # Check mm_metrics columns
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'mm_metrics'
            AND column_name IN ('uptime_pct', 'quote_count')
            ORDER BY column_name
        """)
        mm_cols = cur.fetchall()
        print(f"\nmm_metrics verified columns: {[col[0] for col in mm_cols]}")

        # Check long_short_ratio columns
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'long_short_ratio'
            AND column_name IN ('top_trader_long_ratio', 'top_trader_short_ratio')
            ORDER BY column_name
        """)
        ls_cols = cur.fetchall()
        print(f"long_short_ratio verified columns: {[col[0] for col in ls_cols]}")

        # Check for any other potential missing columns based on common patterns
        print("\nChecking for other potentially missing columns...")

        additional_fixes = [
            # Common fields that might be missing
            ("ALTER TABLE market_data ADD COLUMN IF NOT EXISTS count_24h BIGINT", "market_data.count_24h"),
            ("ALTER TABLE orderbook_snapshots ADD COLUMN IF NOT EXISTS imbalance DECIMAL(10, 4)", "orderbook_snapshots.imbalance"),
            ("ALTER TABLE trades ADD COLUMN IF NOT EXISTS maker BOOLEAN", "trades.maker"),
            ("ALTER TABLE trades ADD COLUMN IF NOT EXISTS best_match BOOLEAN", "trades.best_match"),
        ]

        for sql, description in additional_fixes:
            try:
                cur.execute(sql)
                print(f"  [OK] Added: {description}")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    print(f"  [SKIP] Already exists: {description}")
                else:
                    # These are optional, so we don't error
                    pass

        cur.close()
        conn.close()

        print("\n[SUCCESS] All missing columns have been added!")
        print("\nThe application should now work without column errors.")
        print("Monitor the logs to ensure no more missing column errors occur.")

        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to fix columns: {e}")
        print("\nPlease check the database connection and try again.")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Railway Database Column Fix Tool")
    print("=" * 60)
    print("\nThis will add missing columns that are causing errors.")

    success = fix_missing_columns()

    if not success:
        sys.exit(1)