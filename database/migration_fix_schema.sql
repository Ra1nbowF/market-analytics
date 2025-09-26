-- Migration script to fix schema mismatches on Railway PostgreSQL
-- This adds missing columns and tables that the application expects

-- Add missing columns to market_data table
ALTER TABLE market_data
ADD COLUMN IF NOT EXISTS bid_volume DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS ask_volume DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS quote_volume_24h DECIMAL(30, 8),
ADD COLUMN IF NOT EXISTS price_change_24h DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS price_change_pct_24h DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS high_24h DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS low_24h DECIMAL(20, 8);

-- Add missing columns to mm_metrics table
ALTER TABLE mm_metrics
ADD COLUMN IF NOT EXISTS spread_bps DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS quote_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS bid_depth_1pct DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS ask_depth_1pct DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS bid_depth_2pct DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS ask_depth_2pct DECIMAL(20, 8);

-- Add missing columns to mm_performance table
ALTER TABLE mm_performance
ADD COLUMN IF NOT EXISTS market_presence DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS avg_spread_bps DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS min_spread_bps DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS max_spread_bps DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS total_volume DECIMAL(30, 8),
ADD COLUMN IF NOT EXISTS order_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS liquidity_2pct DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS liquidity_4pct DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS liquidity_8pct DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS bid_ask_imbalance DECIMAL(10, 4);

-- Create liquidity_depth table if it doesn't exist
CREATE TABLE IF NOT EXISTS liquidity_depth (
    id SERIAL,
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
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable if TimescaleDB is available
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('liquidity_depth', 'timestamp', if_not_exists => TRUE);
    END IF;
END $$;

-- Create index for liquidity_depth
CREATE INDEX IF NOT EXISTS idx_liquidity_depth_exchange_symbol_time
    ON liquidity_depth (exchange, symbol, timestamp DESC);

-- Grant permissions
GRANT ALL PRIVILEGES ON liquidity_depth TO postgres;
GRANT ALL PRIVILEGES ON liquidity_depth_id_seq TO postgres;

-- Verify the changes
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name IN ('market_data', 'mm_metrics', 'mm_performance', 'liquidity_depth')
ORDER BY table_name, ordinal_position;