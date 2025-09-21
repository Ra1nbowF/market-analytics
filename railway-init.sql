-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Market data table
CREATE TABLE IF NOT EXISTS market_data (
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

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    side VARCHAR(4) NOT NULL,
    trade_id VARCHAR(100),
    is_maker BOOLEAN,
    PRIMARY KEY (id, timestamp)
);

-- Order book snapshots
CREATE TABLE IF NOT EXISTS orderbook_snapshots (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bids TEXT,
    asks TEXT,
    PRIMARY KEY (id, timestamp)
);

-- Binance perpetuals specific data
CREATE TABLE IF NOT EXISTS binance_perps_data (
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
CREATE TABLE IF NOT EXISTS long_short_ratio (
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

-- Whale data
CREATE TABLE IF NOT EXISTS whale_data (
    id SERIAL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    whale_buy_volume DECIMAL(20, 8),
    whale_sell_volume DECIMAL(20, 8),
    net_flow DECIMAL(20, 8),
    PRIMARY KEY (id, timestamp)
);

-- Market maker metrics
CREATE TABLE IF NOT EXISTS mm_metrics (
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

-- Market maker performance
CREATE TABLE IF NOT EXISTS mm_performance (
    id SERIAL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    market_presence DECIMAL(5, 2),
    avg_spread_bps DECIMAL(10, 4),
    min_spread_bps DECIMAL(10, 4),
    max_spread_bps DECIMAL(10, 4),
    total_volume DECIMAL(20, 2),
    order_count INTEGER,
    liquidity_2pct DECIMAL(20, 8),
    liquidity_4pct DECIMAL(20, 8),
    liquidity_8pct DECIMAL(20, 8),
    bid_ask_imbalance DECIMAL(10, 4),
    PRIMARY KEY (id, timestamp)
);

-- Liquidity depth
CREATE TABLE IF NOT EXISTS liquidity_depth (
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

-- Create hypertables for time-series optimization
SELECT create_hypertable('market_data', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('trades', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('orderbook_snapshots', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('binance_perps_data', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('long_short_ratio', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('whale_data', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('mm_metrics', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('mm_performance', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('liquidity_depth', 'timestamp', if_not_exists => TRUE);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_orderbook_symbol ON orderbook_snapshots(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_binance_perps_symbol ON binance_perps_data(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_long_short_symbol ON long_short_ratio(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_whale_symbol ON whale_data(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_mm_symbol ON mm_metrics(symbol, timestamp DESC);