-- DEX-specific tables for PancakeSwap and other DEX monitoring

-- Liquidity pools tracking
CREATE TABLE IF NOT EXISTS liquidity_pools (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    pair_address VARCHAR(100) UNIQUE NOT NULL,
    token0_address VARCHAR(100) NOT NULL,
    token1_address VARCHAR(100) NOT NULL,
    token0_symbol VARCHAR(20),
    token1_symbol VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Pool metrics over time
CREATE TABLE IF NOT EXISTS pool_metrics (
    id SERIAL PRIMARY KEY,
    pair_address VARCHAR(100) NOT NULL,
    reserve0 NUMERIC(30, 18),
    reserve1 NUMERIC(30, 18),
    liquidity_usd NUMERIC(20, 2),
    price NUMERIC(20, 10),
    volume_24h NUMERIC(20, 2),
    fee_24h NUMERIC(20, 2),
    tvl NUMERIC(20, 2),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pair_address) REFERENCES liquidity_pools(pair_address)
);

-- Swap transactions
CREATE TABLE IF NOT EXISTS swap_transactions (
    id SERIAL PRIMARY KEY,
    pair_address VARCHAR(100) NOT NULL,
    tx_hash VARCHAR(100) UNIQUE NOT NULL,
    block_number INTEGER,
    sender_address VARCHAR(100),
    to_address VARCHAR(100),
    amount_in NUMERIC(30, 18),
    amount_out NUMERIC(30, 18),
    token_in VARCHAR(100),
    token_out VARCHAR(100),
    swap_type VARCHAR(10), -- 'buy' or 'sell'
    price_impact NUMERIC(10, 4),
    gas_used NUMERIC(20, 0),
    timestamp TIMESTAMP,
    FOREIGN KEY (pair_address) REFERENCES liquidity_pools(pair_address)
);

-- Wallet tracking
CREATE TABLE IF NOT EXISTS wallet_tracking (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(100) NOT NULL,
    label VARCHAR(100), -- 'whale', 'bot', 'smart_money', etc.
    first_seen TIMESTAMP,
    last_activity TIMESTAMP,
    total_volume NUMERIC(20, 2),
    profit_loss NUMERIC(20, 2),
    win_rate NUMERIC(5, 2),
    avg_hold_time INTERVAL,
    risk_score INTEGER DEFAULT 0,
    is_contract BOOLEAN DEFAULT false,
    metadata JSONB
);

-- Wallet transactions summary
CREATE TABLE IF NOT EXISTS wallet_transactions (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(100) NOT NULL,
    pair_address VARCHAR(100) NOT NULL,
    buy_count INTEGER DEFAULT 0,
    sell_count INTEGER DEFAULT 0,
    total_buy_volume NUMERIC(30, 18),
    total_sell_volume NUMERIC(30, 18),
    realized_pnl NUMERIC(20, 2),
    unrealized_pnl NUMERIC(20, 2),
    avg_buy_price NUMERIC(20, 10),
    avg_sell_price NUMERIC(20, 10),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wallet_address) REFERENCES wallet_tracking(wallet_address),
    FOREIGN KEY (pair_address) REFERENCES liquidity_pools(pair_address)
);

-- Liquidity events (adds/removes)
CREATE TABLE IF NOT EXISTS liquidity_events (
    id SERIAL PRIMARY KEY,
    pair_address VARCHAR(100) NOT NULL,
    tx_hash VARCHAR(100) UNIQUE NOT NULL,
    event_type VARCHAR(20), -- 'add' or 'remove'
    provider_address VARCHAR(100),
    amount0 NUMERIC(30, 18),
    amount1 NUMERIC(30, 18),
    liquidity_tokens NUMERIC(30, 18),
    share_of_pool NUMERIC(10, 6),
    timestamp TIMESTAMP,
    FOREIGN KEY (pair_address) REFERENCES liquidity_pools(pair_address)
);

-- Token holder distribution
CREATE TABLE IF NOT EXISTS holder_distribution (
    id SERIAL PRIMARY KEY,
    token_address VARCHAR(100) NOT NULL,
    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_holders INTEGER,
    top_10_concentration NUMERIC(5, 2),
    top_50_concentration NUMERIC(5, 2),
    top_100_concentration NUMERIC(5, 2),
    whale_count INTEGER, -- holders with > 1% supply
    retail_count INTEGER, -- holders with < 0.01% supply
    distribution_data JSONB -- detailed holder breakdown
);

-- Suspicious activity detection
CREATE TABLE IF NOT EXISTS suspicious_activity (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(100),
    pair_address VARCHAR(100),
    activity_type VARCHAR(50), -- 'sandwich', 'wash_trade', 'pump_dump', 'bot_trading'
    risk_score INTEGER,
    evidence JSONB,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_confirmed BOOLEAN DEFAULT false
);

-- Smart money tracking
CREATE TABLE IF NOT EXISTS smart_money_wallets (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(100) UNIQUE NOT NULL,
    reputation_score NUMERIC(5, 2),
    total_profit NUMERIC(20, 2),
    success_rate NUMERIC(5, 2),
    avg_roi NUMERIC(10, 2),
    tokens_traded INTEGER,
    profitable_trades INTEGER,
    loss_trades INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Price impact analysis
CREATE TABLE IF NOT EXISTS price_impact_analysis (
    id SERIAL PRIMARY KEY,
    pair_address VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    buy_pressure NUMERIC(10, 2),
    sell_pressure NUMERIC(10, 2),
    large_tx_impact NUMERIC(10, 2),
    slippage_1k NUMERIC(10, 4),
    slippage_10k NUMERIC(10, 4),
    slippage_100k NUMERIC(10, 4),
    FOREIGN KEY (pair_address) REFERENCES liquidity_pools(pair_address)
);

-- Create indexes for performance
CREATE INDEX idx_swap_tx_wallet ON swap_transactions(to_address, timestamp);
CREATE INDEX idx_swap_tx_pair ON swap_transactions(pair_address, timestamp);
CREATE INDEX idx_wallet_activity ON wallet_tracking(last_activity);
CREATE INDEX idx_pool_metrics_time ON pool_metrics(pair_address, timestamp);
CREATE INDEX idx_liquidity_events_provider ON liquidity_events(provider_address);
CREATE INDEX idx_suspicious_activity_wallet ON suspicious_activity(wallet_address);
CREATE INDEX idx_smart_money_score ON smart_money_wallets(reputation_score DESC);