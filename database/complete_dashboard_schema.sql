-- Complete Database Schema for Market Analytics Dashboard
-- This includes ALL fields required by the Grafana dashboard
-- Use this file after wiping Railway volume

-- Enable TimescaleDB extension if available
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Market data table with ALL required fields
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    bid_price DECIMAL(20, 8),
    ask_price DECIMAL(20, 8),
    last_price DECIMAL(20, 8),
    bid_size DECIMAL(20, 8),
    ask_size DECIMAL(20, 8),
    bid_volume DECIMAL(20, 8),
    ask_volume DECIMAL(20, 8),
    volume_24h DECIMAL(30, 8),
    quote_volume_24h DECIMAL(30, 8),
    price_change_24h DECIMAL(20, 8),
    price_change_pct_24h DECIMAL(10, 4),
    high_24h DECIMAL(20, 8),
    low_24h DECIMAL(20, 8),
    open_interest DECIMAL(30, 8),
    funding_rate DECIMAL(10, 8),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    side VARCHAR(10),
    trade_time TIMESTAMPTZ,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trade_id VARCHAR(100),
    PRIMARY KEY (id, timestamp)
);

-- Orderbook snapshots
CREATE TABLE IF NOT EXISTS orderbook_snapshots (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    bids JSONB,
    asks JSONB,
    bid_depth DECIMAL(30, 8),
    ask_depth DECIMAL(30, 8),
    spread DECIMAL(20, 8),
    mid_price DECIMAL(20, 8),
    depth_bid_10 DECIMAL(30, 8),
    depth_ask_10 DECIMAL(30, 8),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Market Maker metrics with ALL required fields
CREATE TABLE IF NOT EXISTS mm_metrics (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    spread_consistency DECIMAL(10, 4),
    order_book_symmetry DECIMAL(10, 4),
    quote_stuffing_score DECIMAL(10, 4),
    spoofing_detection DECIMAL(10, 4),
    mm_probability DECIMAL(10, 4),
    spread_bps DECIMAL(10, 4),
    quote_count INTEGER DEFAULT 0,
    bid_depth_1pct DECIMAL(20, 8),
    ask_depth_1pct DECIMAL(20, 8),
    bid_depth_2pct DECIMAL(20, 8),
    ask_depth_2pct DECIMAL(20, 8),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Market Maker performance with ALL required fields
CREATE TABLE IF NOT EXISTS mm_performance (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    spread_capture DECIMAL(20, 8),
    inventory_turnover DECIMAL(10, 4),
    volume_participation DECIMAL(10, 4),
    price_improvement DECIMAL(20, 8),
    market_presence DECIMAL(10, 4),
    avg_spread_bps DECIMAL(10, 4),
    min_spread_bps DECIMAL(10, 4),
    max_spread_bps DECIMAL(10, 4),
    total_volume DECIMAL(30, 8),
    order_count INTEGER DEFAULT 0,
    liquidity_2pct DECIMAL(20, 8),
    liquidity_4pct DECIMAL(20, 8),
    liquidity_8pct DECIMAL(20, 8),
    bid_ask_imbalance DECIMAL(10, 4),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Long/Short Ratio with CORRECT field names
CREATE TABLE IF NOT EXISTS long_short_ratio (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    long_account DECIMAL(10, 4),
    short_account DECIMAL(10, 4),
    long_short_ratio DECIMAL(10, 4),
    long_account_ratio DECIMAL(10, 4),  -- Dashboard uses this
    short_account_ratio DECIMAL(10, 4), -- Dashboard uses this
    long_position_ratio DECIMAL(10, 4), -- Dashboard might use this
    short_position_ratio DECIMAL(10, 4), -- Dashboard might use this
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Binance Perpetuals data
CREATE TABLE IF NOT EXISTS binance_perps_data (
    id SERIAL,
    symbol VARCHAR(20) NOT NULL,
    open_interest DECIMAL(30, 8),
    funding_rate DECIMAL(10, 8),
    mark_price DECIMAL(20, 8),
    index_price DECIMAL(20, 8),
    estimated_settle_price DECIMAL(20, 8),
    last_funding_time TIMESTAMPTZ,
    next_funding_time TIMESTAMPTZ,
    long_short_ratio DECIMAL(10, 4),
    top_trader_ratio DECIMAL(10, 4),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Liquidity depth table (required by dashboard)
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

-- Whale data table
CREATE TABLE IF NOT EXISTS whale_data (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    whale_net_flow DECIMAL(30, 8),
    whale_buy_volume DECIMAL(30, 8),
    whale_sell_volume DECIMAL(30, 8),
    spot_fund_flow DECIMAL(30, 8),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Additional tables for completeness
CREATE TABLE IF NOT EXISTS mm_probability_score (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    probability_score DECIMAL(5, 4),
    confidence_level DECIMAL(5, 4),
    detection_factors JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

CREATE TABLE IF NOT EXISTS price_impact_analysis (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    order_size DECIMAL(20, 8),
    price_impact_bps DECIMAL(10, 4),
    side VARCHAR(10),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

CREATE TABLE IF NOT EXISTS suspicious_activity (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    activity_type VARCHAR(50),
    severity VARCHAR(20),
    details JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Try to convert tables to hypertables if TimescaleDB is available
DO $$
DECLARE
    tbl RECORD;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        FOR tbl IN
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename IN (
                'market_data', 'trades', 'orderbook_snapshots', 'mm_metrics',
                'mm_performance', 'long_short_ratio', 'binance_perps_data',
                'liquidity_depth', 'whale_data', 'mm_probability_score',
                'price_impact_analysis', 'suspicious_activity'
            )
        LOOP
            BEGIN
                PERFORM create_hypertable(tbl.tablename::regclass, 'timestamp', if_not_exists => TRUE);
                RAISE NOTICE 'Converted % to hypertable', tbl.tablename;
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Could not convert % to hypertable: %', tbl.tablename, SQLERRM;
            END;
        END LOOP;
    END IF;
END $$;

-- Create all necessary indexes
CREATE INDEX IF NOT EXISTS idx_market_data_exchange_symbol_time ON market_data (exchange, symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time ON market_data (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_exchange_symbol_time ON trades (exchange, symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_orderbook_exchange_symbol_time ON orderbook_snapshots (exchange, symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_mm_metrics_exchange_symbol_time ON mm_metrics (exchange, symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_mm_performance_exchange_symbol_time ON mm_performance (exchange, symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_long_short_ratio_symbol_time ON long_short_ratio (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_binance_perps_symbol_time ON binance_perps_data (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_liquidity_depth_exchange_symbol_time ON liquidity_depth (exchange, symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_whale_data_symbol_time ON whale_data (symbol, timestamp DESC);

-- Grant permissions (adjust user as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Verify schema
SELECT
    'Schema created successfully!' as message,
    COUNT(*) as table_count
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE';