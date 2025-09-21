-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Main market data table for all exchanges
CREATE TABLE market_data (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bid_price DECIMAL(20, 8),
    ask_price DECIMAL(20, 8),
    bid_volume DECIMAL(20, 8),
    ask_volume DECIMAL(20, 8),
    last_price DECIMAL(20, 8),
    volume_24h DECIMAL(20, 8),
    quote_volume_24h DECIMAL(20, 8),
    price_change_24h DECIMAL(10, 4),
    price_change_pct_24h DECIMAL(10, 4),
    high_24h DECIMAL(20, 8),
    low_24h DECIMAL(20, 8),
    PRIMARY KEY (id, timestamp)
);

-- Order book snapshots
CREATE TABLE orderbook_snapshots (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bids JSONB NOT NULL,  -- Array of [price, volume] pairs
    asks JSONB NOT NULL,  -- Array of [price, volume] pairs
    PRIMARY KEY (id, timestamp)
);

-- Trades table
CREATE TABLE trades (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    side VARCHAR(4) NOT NULL,  -- 'buy' or 'sell'
    trade_id VARCHAR(100),
    is_maker BOOLEAN,
    PRIMARY KEY (id, timestamp)
);

-- Binance Perps specific data
CREATE TABLE binance_perps_data (
    id SERIAL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    mark_price DECIMAL(20, 8),
    index_price DECIMAL(20, 8),
    funding_rate DECIMAL(10, 8),
    next_funding_time TIMESTAMPTZ,
    open_interest DECIMAL(20, 8),
    open_interest_value DECIMAL(20, 8),
    max_open_interest DECIMAL(20, 8),
    PRIMARY KEY (id, timestamp)
);

-- Long/Short ratio data
CREATE TABLE long_short_ratio (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    long_short_ratio DECIMAL(10, 4),
    long_account_ratio DECIMAL(10, 4),
    short_account_ratio DECIMAL(10, 4),
    top_trader_long_ratio DECIMAL(10, 4),
    top_trader_short_ratio DECIMAL(10, 4),
    PRIMARY KEY (id, timestamp)
);

-- Bitget whale data
CREATE TABLE whale_data (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    whale_net_flow DECIMAL(20, 8),
    whale_buy_volume DECIMAL(20, 8),
    whale_sell_volume DECIMAL(20, 8),
    spot_fund_flow DECIMAL(20, 8),
    PRIMARY KEY (id, timestamp)
);

-- Market maker metrics
CREATE TABLE mm_metrics (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    spread_bps DECIMAL(10, 4),
    bid_depth_1pct DECIMAL(20, 8),
    ask_depth_1pct DECIMAL(20, 8),
    bid_depth_2pct DECIMAL(20, 8),
    ask_depth_2pct DECIMAL(20, 8),
    quote_count INTEGER,
    uptime_pct DECIMAL(5, 2),
    PRIMARY KEY (id, timestamp)
);

-- Market maker performance metrics
CREATE TABLE mm_performance (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    market_presence DECIMAL(5, 2),  -- Percentage of time with active orders
    avg_spread_bps DECIMAL(10, 4),  -- Average spread in basis points
    min_spread_bps DECIMAL(10, 4),  -- Minimum spread
    max_spread_bps DECIMAL(10, 4),  -- Maximum spread
    total_volume DECIMAL(20, 2),  -- Total volume traded
    order_count INTEGER,  -- Number of orders/quotes
    liquidity_2pct DECIMAL(20, 8),  -- Liquidity at 2% depth
    liquidity_4pct DECIMAL(20, 8),  -- Liquidity at 4% depth
    liquidity_8pct DECIMAL(20, 8),  -- Liquidity at 8% depth
    bid_ask_imbalance DECIMAL(10, 4),  -- Bid/ask volume imbalance
    PRIMARY KEY (id, timestamp)
);

-- Liquidity depth comparison table
CREATE TABLE liquidity_depth (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    depth_2pct_bid DECIMAL(20, 8),
    depth_2pct_ask DECIMAL(20, 8),
    depth_4pct_bid DECIMAL(20, 8),
    depth_4pct_ask DECIMAL(20, 8),
    depth_8pct_bid DECIMAL(20, 8),
    depth_8pct_ask DECIMAL(20, 8),
    total_bid_volume DECIMAL(20, 8),
    total_ask_volume DECIMAL(20, 8),
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertables
SELECT create_hypertable('market_data', 'timestamp');
SELECT create_hypertable('orderbook_snapshots', 'timestamp');
SELECT create_hypertable('trades', 'timestamp');
SELECT create_hypertable('binance_perps_data', 'timestamp');
SELECT create_hypertable('long_short_ratio', 'timestamp');
SELECT create_hypertable('whale_data', 'timestamp');
SELECT create_hypertable('mm_metrics', 'timestamp');
SELECT create_hypertable('mm_performance', 'timestamp');
SELECT create_hypertable('liquidity_depth', 'timestamp');

-- Create indexes for faster queries
CREATE INDEX idx_market_data_symbol ON market_data (symbol, timestamp DESC);
CREATE INDEX idx_orderbook_symbol ON orderbook_snapshots (symbol, timestamp DESC);
CREATE INDEX idx_trades_symbol ON trades (symbol, timestamp DESC);
CREATE INDEX idx_binance_perps_symbol ON binance_perps_data (symbol, timestamp DESC);
CREATE INDEX idx_long_short_symbol ON long_short_ratio (symbol, timestamp DESC);
CREATE INDEX idx_whale_symbol ON whale_data (symbol, timestamp DESC);
CREATE INDEX idx_mm_symbol ON mm_metrics (symbol, timestamp DESC);
CREATE INDEX idx_mm_perf_symbol ON mm_performance (symbol, timestamp DESC);
CREATE INDEX idx_liquidity_symbol ON liquidity_depth (symbol, timestamp DESC);

-- Create continuous aggregates for Grafana
CREATE MATERIALIZED VIEW market_stats_5m
WITH (timescaledb.continuous) AS
SELECT
    exchange,
    symbol,
    time_bucket('5 minutes', timestamp) AS bucket,
    AVG(bid_price) as avg_bid,
    AVG(ask_price) as avg_ask,
    AVG((ask_price - bid_price) / NULLIF(bid_price, 0) * 10000) as avg_spread_bps,
    SUM(volume_24h) as total_volume,
    AVG(price_change_pct_24h) as avg_price_change
FROM market_data
GROUP BY exchange, symbol, bucket
WITH NO DATA;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('market_stats_5m',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes');

-- Data retention policies (keep 90 days of detailed data)
SELECT add_retention_policy('market_data', INTERVAL '90 days');
SELECT add_retention_policy('orderbook_snapshots', INTERVAL '7 days');  -- Orderbook data is heavy
SELECT add_retention_policy('trades', INTERVAL '30 days');
SELECT add_retention_policy('binance_perps_data', INTERVAL '90 days');
SELECT add_retention_policy('long_short_ratio', INTERVAL '90 days');
SELECT add_retention_policy('whale_data', INTERVAL '90 days');
SELECT add_retention_policy('mm_metrics', INTERVAL '90 days');
SELECT add_retention_policy('mm_performance', INTERVAL '90 days');
SELECT add_retention_policy('liquidity_depth', INTERVAL '30 days');

-- Helper function to calculate market maker compliance
CREATE OR REPLACE FUNCTION calculate_mm_compliance(
    p_symbol VARCHAR,
    p_exchange VARCHAR,
    p_hours INTEGER DEFAULT 24
)
RETURNS TABLE (
    compliance_rate DECIMAL,
    avg_spread_bps DECIMAL,
    min_spread_bps DECIMAL,
    max_spread_bps DECIMAL,
    uptime_pct DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) FILTER (WHERE spread_bps < 50) * 100.0 / NULLIF(COUNT(*), 0) as compliance_rate,
        AVG(spread_bps) as avg_spread_bps,
        MIN(spread_bps) as min_spread_bps,
        MAX(spread_bps) as max_spread_bps,
        AVG(uptime_pct) as uptime_pct
    FROM mm_metrics
    WHERE symbol = p_symbol
        AND exchange = p_exchange
        AND timestamp > NOW() - INTERVAL '1 hour' * p_hours;
END;
$$ LANGUAGE plpgsql;