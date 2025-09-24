-- Production Database Schema for Market Analytics (Railway)
-- CEX-only version without DEX/onchain tables
-- No TimescaleDB version

-- Drop existing tables if they exist
DROP TABLE IF EXISTS whale_data CASCADE;
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS suspicious_activity CASCADE;
DROP TABLE IF EXISTS price_impact_analysis CASCADE;
DROP TABLE IF EXISTS pool_metrics CASCADE;
DROP TABLE IF EXISTS orderbook_snapshots CASCADE;
DROP TABLE IF EXISTS mm_probability_score CASCADE;
DROP TABLE IF EXISTS mm_performance CASCADE;
DROP TABLE IF EXISTS mm_metrics CASCADE;
DROP TABLE IF EXISTS market_data CASCADE;
DROP TABLE IF EXISTS long_short_ratio CASCADE;
DROP TABLE IF EXISTS holder_distribution CASCADE;
DROP TABLE IF EXISTS binance_perps_data CASCADE;

-- Market data table
CREATE TABLE market_data (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    bid_price DECIMAL(20, 8),
    ask_price DECIMAL(20, 8),
    last_price DECIMAL(20, 8),
    volume_24h DECIMAL(30, 8),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bid_size DECIMAL(20, 8),
    ask_size DECIMAL(20, 8),
    open_interest DECIMAL(30, 8),
    funding_rate DECIMAL(10, 8)
);

-- Create indexes
CREATE INDEX idx_market_data_exchange_symbol_time
    ON market_data (exchange, symbol, timestamp DESC);
CREATE INDEX idx_market_data_symbol_time
    ON market_data (symbol, timestamp DESC);
CREATE INDEX idx_market_data_timestamp
    ON market_data (timestamp DESC);

-- Orderbook snapshots table
CREATE TABLE orderbook_snapshots (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    bids JSONB,
    asks JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bid_depth DECIMAL(30, 8),
    ask_depth DECIMAL(30, 8),
    spread DECIMAL(20, 8),
    mid_price DECIMAL(20, 8)
);

CREATE INDEX idx_orderbook_exchange_symbol_time
    ON orderbook_snapshots (exchange, symbol, timestamp DESC);
CREATE INDEX idx_orderbook_timestamp
    ON orderbook_snapshots (timestamp DESC);

-- Trades table
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    side VARCHAR(10),
    trade_time TIMESTAMPTZ,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trade_id VARCHAR(100)
);

CREATE INDEX idx_trades_exchange_symbol_time
    ON trades (exchange, symbol, timestamp DESC);
CREATE INDEX idx_trades_symbol_time
    ON trades (symbol, timestamp DESC);
CREATE INDEX idx_trades_timestamp
    ON trades (timestamp DESC);

-- Binance Perpetuals specific data
CREATE TABLE binance_perps_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    open_interest DECIMAL(30, 8),
    funding_rate DECIMAL(10, 8),
    mark_price DECIMAL(20, 8),
    index_price DECIMAL(20, 8),
    estimated_settle_price DECIMAL(20, 8),
    last_funding_time TIMESTAMPTZ,
    next_funding_time TIMESTAMPTZ,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    long_short_ratio DECIMAL(10, 4),
    top_trader_ratio DECIMAL(10, 4)
);

CREATE INDEX idx_binance_perps_symbol_time
    ON binance_perps_data (symbol, timestamp DESC);
CREATE INDEX idx_binance_perps_timestamp
    ON binance_perps_data (timestamp DESC);

-- Long/Short Ratio data
CREATE TABLE long_short_ratio (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    long_account DECIMAL(10, 4),
    short_account DECIMAL(10, 4),
    long_short_ratio DECIMAL(10, 4),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_long_short_ratio_symbol_time
    ON long_short_ratio (symbol, timestamp DESC);
CREATE INDEX idx_long_short_ratio_timestamp
    ON long_short_ratio (timestamp DESC);

-- Whale data table
CREATE TABLE whale_data (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    whale_net_flow DECIMAL(30, 8),
    whale_buy_volume DECIMAL(30, 8),
    whale_sell_volume DECIMAL(30, 8),
    spot_fund_flow DECIMAL(30, 8),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_whale_data_symbol_time
    ON whale_data (symbol, timestamp DESC);
CREATE INDEX idx_whale_data_timestamp
    ON whale_data (timestamp DESC);

-- Market Maker metrics
CREATE TABLE mm_metrics (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    spread_consistency DECIMAL(10, 4),
    order_book_symmetry DECIMAL(10, 4),
    quote_stuffing_score DECIMAL(10, 4),
    spoofing_detection DECIMAL(10, 4),
    mm_probability DECIMAL(10, 4),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mm_metrics_exchange_symbol_time
    ON mm_metrics (exchange, symbol, timestamp DESC);
CREATE INDEX idx_mm_metrics_timestamp
    ON mm_metrics (timestamp DESC);

-- Market Maker performance
CREATE TABLE mm_performance (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    spread_capture DECIMAL(20, 8),
    inventory_turnover DECIMAL(10, 4),
    volume_participation DECIMAL(10, 4),
    price_improvement DECIMAL(20, 8),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mm_performance_exchange_symbol_time
    ON mm_performance (exchange, symbol, timestamp DESC);
CREATE INDEX idx_mm_performance_timestamp
    ON mm_performance (timestamp DESC);

-- Market Maker probability score
CREATE TABLE mm_probability_score (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    probability_score DECIMAL(5, 4),
    confidence_level DECIMAL(5, 4),
    detection_factors JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mm_probability_exchange_symbol_time
    ON mm_probability_score (exchange, symbol, timestamp DESC);
CREATE INDEX idx_mm_probability_timestamp
    ON mm_probability_score (timestamp DESC);

-- Price impact analysis
CREATE TABLE price_impact_analysis (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    order_size DECIMAL(20, 8),
    price_impact_bps DECIMAL(10, 4),
    side VARCHAR(10),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_price_impact_exchange_symbol_time
    ON price_impact_analysis (exchange, symbol, timestamp DESC);
CREATE INDEX idx_price_impact_timestamp
    ON price_impact_analysis (timestamp DESC);

-- Suspicious activity detection
CREATE TABLE suspicious_activity (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    activity_type VARCHAR(50),
    severity VARCHAR(20),
    details JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_suspicious_activity_exchange_symbol_time
    ON suspicious_activity (exchange, symbol, timestamp DESC);
CREATE INDEX idx_suspicious_activity_timestamp
    ON suspicious_activity (timestamp DESC);

-- Pool metrics (for future use, but CEX-focused)
CREATE TABLE pool_metrics (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    liquidity_depth DECIMAL(30, 8),
    volume_24h DECIMAL(30, 8),
    fee_tier DECIMAL(10, 6),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pool_metrics_exchange_symbol_time
    ON pool_metrics (exchange, symbol, timestamp DESC);
CREATE INDEX idx_pool_metrics_timestamp
    ON pool_metrics (timestamp DESC);

-- Holder distribution (for future use)
CREATE TABLE holder_distribution (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    holder_category VARCHAR(50),
    holder_count INTEGER,
    total_balance DECIMAL(30, 8),
    percentage DECIMAL(10, 4),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_holder_distribution_symbol_time
    ON holder_distribution (symbol, timestamp DESC);
CREATE INDEX idx_holder_distribution_timestamp
    ON holder_distribution (timestamp DESC);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;