import os
import asyncio
import logging
import json
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
import numpy as np

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# Import exchange connectors
from exchanges.binance_perps import BinancePerpsConnector
from exchanges.binance_spot import BinanceSpotConnector
from exchanges.bitget import BitgetConnector
from exchanges.gate import GateConnector
from exchanges.kucoin import KucoinConnector

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None
scheduler = AsyncIOScheduler()

# Exchange instances
exchanges = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db_pool, redis_client, exchanges

    # Startup
    logger.info("Starting Market Analytics API...")

    # Wait for database to be ready
    from wait_for_db import wait_for_postgres
    db_ready = await wait_for_postgres()
    if not db_ready:
        logger.error("Database not ready, exiting...")
        raise Exception("Database connection failed")

    # Initialize database pool
    db_url = (
        os.getenv('DATABASE_URL') or
        os.getenv('DATABASE_PUBLIC_URL') or
        os.getenv('PGDATABASE_URL') or
        'postgresql://admin:admin123@postgres:5432/market_analytics'
    )

    # Railway uses postgres:// prefix, we need postgresql://
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    db_pool = await asyncpg.create_pool(
        db_url,
        min_size=5,
        max_size=20
    )

    # Initialize Redis
    redis_url = os.getenv('REDIS_URL') or 'redis://redis:6379'
    redis_client = await redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True
    )

    # Initialize exchange connectors
    exchanges = {
        'binance_perps': BinancePerpsConnector(
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_SECRET')
        ),
        'binance_spot': BinanceSpotConnector(
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_SECRET')
        ),
        'bitget': BitgetConnector(
            api_key=os.getenv('BITGET_API_KEY'),
            api_secret=os.getenv('BITGET_SECRET'),
            passphrase=os.getenv('BITGET_PASSPHRASE')
        ),
        'gate': GateConnector(
            api_key=os.getenv('GATE_API_KEY'),
            api_secret=os.getenv('GATE_SECRET')
        ),
        'kucoin': KucoinConnector(
            api_key=os.getenv('KUCOIN_API_KEY'),
            api_secret=os.getenv('KUCOIN_SECRET'),
            passphrase=os.getenv('KUCOIN_PASSPHRASE')
        )
    }

    # Schedule data collection jobs
    scheduler.start()
    schedule_data_collection()

    yield

    # Shutdown
    logger.info("Shutting down Market Analytics API...")
    scheduler.shutdown()

    if db_pool:
        await db_pool.close()

    if redis_client:
        await redis_client.close()

    # Close exchange connections
    for exchange in exchanges.values():
        await exchange.close()

app = FastAPI(
    title="Crypto Market Analytics API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def schedule_data_collection():
    """Schedule periodic data collection tasks"""

    # Collect market data every 30 seconds
    scheduler.add_job(
        collect_all_market_data,
        'interval',
        seconds=30,
        id='market_data',
        max_instances=1
    )

    # Collect order book every minute
    scheduler.add_job(
        collect_orderbook_data,
        'interval',
        minutes=1,
        id='orderbook_data',
        max_instances=1
    )

    # Collect Binance perps specific data every minute (for testing)
    scheduler.add_job(
        collect_binance_perps_data,
        'interval',
        minutes=1,
        id='binance_perps_data',
        max_instances=1
    )

    # Collect whale data every 2 minutes (for testing)
    scheduler.add_job(
        collect_whale_data,
        'interval',
        minutes=2,
        id='whale_data',
        max_instances=1
    )

    # Calculate MM metrics every minute (for testing)
    scheduler.add_job(
        calculate_mm_metrics,
        'interval',
        minutes=1,
        id='mm_metrics',
        max_instances=1
    )

    # Collect MM performance metrics every minute
    scheduler.add_job(
        collect_mm_performance_metrics,
        'interval',
        minutes=1,
        id='mm_performance',
        max_instances=1
    )

async def collect_all_market_data():
    """Collect market data from all exchanges"""
    symbols = os.getenv('TRACK_SYMBOL', 'BTCUSDT').split(',')

    for symbol in symbols:
        tasks = []

        # Collect from each exchange
        for exchange_name, exchange in exchanges.items():
            if exchange_name == 'binance_perps':
                tasks.append(collect_binance_perps_market(symbol))
            elif exchange_name == 'binance_spot':
                tasks.append(collect_binance_spot_market(symbol))
            elif exchange_name == 'bitget':
                tasks.append(collect_bitget_market(symbol))
            elif exchange_name == 'gate':
                tasks.append(collect_gate_market(symbol))
            elif exchange_name == 'kucoin':
                tasks.append(collect_kucoin_market(symbol))

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error collecting market data: {result}")

async def collect_binance_perps_market(symbol: str):
    """Collect Binance Perps market data"""
    try:
        exchange = exchanges['binance_perps']

        # Get 24hr ticker
        ticker = await exchange.get_24hr_ticker(symbol)

        # Get order book for bid/ask prices (futures ticker doesn't have them)
        orderbook = await exchange.get_order_book(symbol, limit=5)

        # Get recent trades
        trades = await exchange.get_recent_trades(symbol)

        # Store in database
        async with db_pool.acquire() as conn:
            # Store market data only if prices are valid
            # Futures ticker doesn't have bid/ask, get from orderbook
            bid_price = float(orderbook['bids'][0][0]) if orderbook and orderbook.get('bids') else 0
            ask_price = float(orderbook['asks'][0][0]) if orderbook and orderbook.get('asks') else 0

            if bid_price > 0 and ask_price > 0:  # Only store valid prices
                await conn.execute("""
                    INSERT INTO market_data (
                        exchange, symbol, timestamp,
                        bid_price, ask_price, last_price,
                        volume_24h, quote_volume_24h,
                        price_change_24h, price_change_pct_24h,
                        high_24h, low_24h
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    'binance_perps', symbol, datetime.utcnow(),
                    bid_price,
                    ask_price,
                    float(ticker.get('lastPrice', 0)),
                    float(ticker.get('volume', 0)),
                    float(ticker.get('quoteVolume', 0)),
                    float(ticker.get('priceChange', 0)),
                    float(ticker.get('priceChangePercent', 0)),
                    float(ticker.get('highPrice', 0)),
                    float(ticker.get('lowPrice', 0))
                )

            # Store trades
            for trade in trades[:100]:  # Store last 100 trades
                await conn.execute("""
                    INSERT INTO trades (
                        exchange, symbol, timestamp,
                        price, quantity, side, trade_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    'binance_perps', symbol,
                    datetime.fromtimestamp(trade['time'] / 1000),
                    float(trade['price']),
                    float(trade['qty']),
                    'sell' if trade['isBuyerMaker'] else 'buy',
                    str(trade['id'])
                )

        logger.info(f"Collected Binance Perps data for {symbol}")

    except Exception as e:
        logger.error(f"Error collecting Binance Perps data for {symbol}: {e}")

async def collect_binance_spot_market(symbol: str):
    """Collect Binance Spot market data"""
    try:
        exchange = exchanges['binance_spot']

        # Get ticker
        ticker = await exchange.get_ticker(symbol)

        # Get aggregated trades
        agg_trades = await exchange.get_aggregated_trades(symbol)

        # Store in database only if valid
        bid_price = float(ticker.get('bidPrice', 0))
        ask_price = float(ticker.get('askPrice', 0))

        if bid_price > 0 and ask_price > 0:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO market_data (
                        exchange, symbol, timestamp,
                        bid_price, ask_price, last_price,
                        volume_24h, quote_volume_24h,
                        price_change_pct_24h
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                    'binance_spot', symbol, datetime.utcnow(),
                    bid_price,
                    ask_price,
                    float(ticker.get('lastPrice', 0)),
                    float(ticker.get('volume', 0)),
                    float(ticker.get('quoteVolume', 0)),
                    float(ticker.get('priceChangePercent', 0))
                )

        logger.info(f"Collected Binance Spot data for {symbol}")

    except Exception as e:
        logger.error(f"Error collecting Binance Spot data for {symbol}: {e}")

async def collect_bitget_market(symbol: str):
    """Collect Bitget market data"""
    try:
        exchange = exchanges['bitget']

        # Get ticker and other data
        ticker = await exchange.get_ticker(symbol)

        # Store in database only if valid
        if ticker:
            # Bitget uses bidPr and askPr
            bid_price = float(ticker.get('bidPr', ticker.get('bestBid', 0)))
            ask_price = float(ticker.get('askPr', ticker.get('bestAsk', 0)))

            if bid_price > 0 and ask_price > 0:
                async with db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO market_data (
                            exchange, symbol, timestamp,
                            bid_price, ask_price, last_price,
                            volume_24h, price_change_pct_24h
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                        'bitget', symbol, datetime.utcnow(),
                        bid_price,
                        ask_price,
                        float(ticker.get('last', ticker.get('lastPr', 0))),
                        float(ticker.get('baseVolume', ticker.get('baseVolume', 0))),
                        float(ticker.get('changePercent', ticker.get('changePercentage', 0)))
                    )

        logger.info(f"Collected Bitget data for {symbol}")

    except Exception as e:
        logger.error(f"Error collecting Bitget data for {symbol}: {e}")

async def collect_gate_market(symbol: str):
    """Collect Gate.io market data"""
    try:
        exchange = exchanges['gate']

        # Get market depth
        depth = await exchange.get_market_depth(symbol)

        # Get trade records
        trades = await exchange.get_trade_records(symbol)

        # Store in database only if valid
        if depth and depth.get('bids') and depth.get('asks'):
            bid_price = float(depth['bids'][0][0]) if depth['bids'] else 0
            ask_price = float(depth['asks'][0][0]) if depth['asks'] else 0

            if bid_price > 0 and ask_price > 0:
                async with db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO market_data (
                            exchange, symbol, timestamp,
                            bid_price, ask_price, bid_volume, ask_volume
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        'gate', symbol, datetime.utcnow(),
                        bid_price,
                        ask_price,
                        float(depth['bids'][0][1]) if depth['bids'] else 0,
                        float(depth['asks'][0][1]) if depth['asks'] else 0
                    )

        logger.info(f"Collected Gate.io data for {symbol}")

    except Exception as e:
        logger.error(f"Error collecting Gate.io data for {symbol}: {e}")

async def collect_kucoin_market(symbol: str):
    """Collect KuCoin market data"""
    try:
        exchange = exchanges['kucoin']

        # Get ticker first (has bid/ask prices)
        ticker = await exchange.get_ticker(symbol)

        # Get orderbook
        orderbook = await exchange.get_full_orderbook(symbol)

        # Store in database
        if ticker:
            bid_price = float(ticker.get('bestBid', 0))
            ask_price = float(ticker.get('bestAsk', 0))

            if bid_price > 0 and ask_price > 0:
                async with db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO market_data (
                            exchange, symbol, timestamp,
                            bid_price, ask_price, last_price, bid_volume, ask_volume
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                        'kucoin', symbol, datetime.utcnow(),
                        bid_price,
                        ask_price,
                        float(ticker.get('price', 0)),
                        float(ticker.get('bestBidSize', 0)),
                        float(ticker.get('bestAskSize', 0))
                    )

        logger.info(f"Collected KuCoin data for {symbol}")

    except Exception as e:
        logger.error(f"Error collecting KuCoin data for {symbol}: {e}")

async def collect_orderbook_data():
    """Collect order book snapshots from ALL exchanges"""
    symbols = os.getenv('TRACK_SYMBOL', 'BTCUSDT').split(',')

    for symbol in symbols:
        tasks = []

        # Collect orderbooks from all exchanges in parallel
        for exchange_name, exchange in exchanges.items():
            tasks.append(collect_single_orderbook(exchange_name, exchange, symbol))

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in orderbook collection: {result}")

async def collect_single_orderbook(exchange_name: str, exchange, symbol: str):
    """Collect orderbook from a single exchange"""
    try:
        orderbook = None

        # Get orderbook based on exchange type
        if hasattr(exchange, 'get_order_book'):
            orderbook = await exchange.get_order_book(symbol)
        elif hasattr(exchange, 'get_full_orderbook'):
            orderbook = await exchange.get_full_orderbook(symbol)
        elif hasattr(exchange, 'get_market_depth'):
            orderbook = await exchange.get_market_depth(symbol)

        if orderbook and orderbook.get('bids') and orderbook.get('asks'):
            # Store raw orderbook
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO orderbook_snapshots (
                        exchange, symbol, timestamp, bids, asks
                    ) VALUES ($1, $2, $3, $4, $5)
                """,
                    exchange_name, symbol, datetime.utcnow(),
                    json.dumps(orderbook.get('bids', [])[:100]),  # Top 100 levels
                    json.dumps(orderbook.get('asks', [])[:100])   # Top 100 levels
                )

            # Calculate and store aggregated depth at different price levels
            await calculate_depth_levels(exchange_name, symbol, orderbook)

            logger.info(f"Collected orderbook from {exchange_name} for {symbol}")

    except Exception as e:
        logger.error(f"Error collecting orderbook from {exchange_name} for {symbol}: {e}")

async def calculate_depth_levels(exchange_name: str, symbol: str, orderbook: dict):
    """Calculate depth at different price percentage levels"""
    try:
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])

        if not bids or not asks:
            return

        # Get mid price
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid_price = (best_bid + best_ask) / 2

        # Calculate cumulative volumes at different price levels
        depth_levels = {
            '0.1%': {'bid_volume': 0, 'ask_volume': 0},
            '0.5%': {'bid_volume': 0, 'ask_volume': 0},
            '1%': {'bid_volume': 0, 'ask_volume': 0},
            '2%': {'bid_volume': 0, 'ask_volume': 0},
            '5%': {'bid_volume': 0, 'ask_volume': 0}
        }

        # Calculate bid depth
        for price, volume in bids[:100]:
            price = float(price)
            volume = float(volume)
            price_diff_pct = abs(price - mid_price) / mid_price * 100

            for level, pct in [('0.1%', 0.1), ('0.5%', 0.5), ('1%', 1), ('2%', 2), ('5%', 5)]:
                if price_diff_pct <= pct:
                    depth_levels[level]['bid_volume'] += volume

        # Calculate ask depth
        for price, volume in asks[:100]:
            price = float(price)
            volume = float(volume)
            price_diff_pct = abs(price - mid_price) / mid_price * 100

            for level, pct in [('0.1%', 0.1), ('0.5%', 0.5), ('1%', 1), ('2%', 2), ('5%', 5)]:
                if price_diff_pct <= pct:
                    depth_levels[level]['ask_volume'] += volume

        # Store depth metrics
        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE mm_metrics
                SET bid_depth_1pct = $1, ask_depth_1pct = $2,
                    bid_depth_2pct = $3, ask_depth_2pct = $4
                WHERE exchange = $5 AND symbol = $6
                AND timestamp = (SELECT MAX(timestamp) FROM mm_metrics WHERE exchange = $5 AND symbol = $6)
            """,
                depth_levels['1%']['bid_volume'], depth_levels['1%']['ask_volume'],
                depth_levels['2%']['bid_volume'], depth_levels['2%']['ask_volume'],
                exchange_name, symbol
            )

    except Exception as e:
        logger.error(f"Error calculating depth levels: {e}")

async def collect_binance_perps_data():
    """Collect Binance Perps specific data"""
    symbols = os.getenv('TRACK_SYMBOL', 'BTCUSDT').split(',')
    exchange = exchanges['binance_perps']

    for symbol in symbols:
        try:
            # Collect all perps-specific data
            tasks = [
                exchange.get_mark_price(symbol),
                exchange.get_funding_rate(symbol),
                exchange.get_open_interest(symbol),
                exchange.get_long_short_ratio(symbol),
                exchange.get_top_trader_ratio(symbol)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            mark_price_data = results[0] if not isinstance(results[0], Exception) else {}
            funding_data = results[1] if not isinstance(results[1], Exception) else {}
            oi_data = results[2] if not isinstance(results[2], Exception) else {}
            ls_ratio = results[3] if not isinstance(results[3], Exception) else {}
            top_trader = results[4] if not isinstance(results[4], Exception) else {}

            async with db_pool.acquire() as conn:
                # Store perps data
                await conn.execute("""
                    INSERT INTO binance_perps_data (
                        symbol, timestamp, mark_price, index_price,
                        funding_rate, open_interest
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    symbol, datetime.utcnow(),
                    float(mark_price_data.get('markPrice', 0)),
                    float(mark_price_data.get('indexPrice', 0)),
                    float(funding_data.get('fundingRate', 0)) if funding_data else 0,
                    float(oi_data.get('openInterest', 0)) if oi_data else 0
                )

                # Store long/short ratio
                if ls_ratio:
                    await conn.execute("""
                        INSERT INTO long_short_ratio (
                            exchange, symbol, timestamp,
                            long_short_ratio, long_account_ratio, short_account_ratio
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                        'binance_perps', symbol, datetime.utcnow(),
                        float(ls_ratio.get('longShortRatio', 0)),
                        float(ls_ratio.get('longAccount', 0)),
                        float(ls_ratio.get('shortAccount', 0))
                    )

                # Store top trader ratio
                if top_trader:
                    await conn.execute("""
                        UPDATE long_short_ratio
                        SET top_trader_long_ratio = $1, top_trader_short_ratio = $2
                        WHERE exchange = $3 AND symbol = $4
                        AND timestamp = (SELECT MAX(timestamp) FROM long_short_ratio WHERE exchange = $3 AND symbol = $4)
                    """,
                        float(top_trader.get('longAccount', 0)),
                        float(top_trader.get('shortAccount', 0)),
                        'binance_perps', symbol
                    )

            logger.info(f"Collected Binance Perps specific data for {symbol}")

        except Exception as e:
            logger.error(f"Error collecting Binance Perps data for {symbol}: {e}")

async def collect_whale_data():
    """Collect whale data from Bitget"""
    symbols = os.getenv('TRACK_SYMBOL', 'BTCUSDT').split(',')
    exchange = exchanges['bitget']

    for symbol in symbols:
        try:
            # Get whale net flow data
            whale_flow = await exchange.get_whale_net_flow(symbol)
            fund_flow = await exchange.get_spot_fund_flow(symbol)

            if whale_flow or fund_flow:
                async with db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO whale_data (
                            exchange, symbol, timestamp,
                            whale_net_flow, whale_buy_volume, whale_sell_volume,
                            spot_fund_flow
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        'bitget', symbol, datetime.utcnow(),
                        float(whale_flow.get('netFlow', 0)) if whale_flow else 0,
                        float(whale_flow.get('buyVolume', 0)) if whale_flow else 0,
                        float(whale_flow.get('sellVolume', 0)) if whale_flow else 0,
                        float(fund_flow.get('netFlow', 0)) if fund_flow else 0
                    )

            logger.info(f"Collected whale data for {symbol}")

        except Exception as e:
            logger.error(f"Error collecting whale data for {symbol}: {e}")

async def calculate_mm_metrics():
    """Calculate market maker metrics"""
    symbols = os.getenv('TRACK_SYMBOL', 'BTCUSDT').split(',')

    for symbol in symbols:
        try:
            async with db_pool.acquire() as conn:
                # Get recent market data
                data = await conn.fetch("""
                    SELECT exchange, bid_price, ask_price, bid_volume, ask_volume
                    FROM market_data
                    WHERE symbol = $1
                    AND timestamp > NOW() - INTERVAL '5 minutes'
                    ORDER BY timestamp DESC
                """, symbol)

                # Calculate metrics for each exchange
                exchanges_data = {}
                for row in data:
                    exchange = row['exchange']
                    if exchange not in exchanges_data:
                        exchanges_data[exchange] = []
                    exchanges_data[exchange].append(row)

                for exchange, rows in exchanges_data.items():
                    if rows:
                        # Calculate average spread in basis points
                        spreads = []
                        for row in rows:
                            if row['bid_price'] and row['ask_price'] and row['bid_price'] > 0:
                                spread_bps = ((row['ask_price'] - row['bid_price']) / row['bid_price']) * 10000
                                spreads.append(spread_bps)

                        avg_spread = sum(spreads) / len(spreads) if spreads else 0

                        # Calculate depth metrics
                        avg_bid_volume = sum(r['bid_volume'] or 0 for r in rows) / len(rows)
                        avg_ask_volume = sum(r['ask_volume'] or 0 for r in rows) / len(rows)

                        # Calculate uptime
                        expected_data_points = 10  # 5 minutes at 30-second intervals
                        uptime_pct = (len(rows) / expected_data_points) * 100

                        # Store metrics
                        await conn.execute("""
                            INSERT INTO mm_metrics (
                                exchange, symbol, timestamp,
                                spread_bps, bid_depth_1pct, ask_depth_1pct,
                                quote_count, uptime_pct
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                            exchange, symbol, datetime.utcnow(),
                            avg_spread, avg_bid_volume, avg_ask_volume,
                            len(rows), min(uptime_pct, 100)
                        )

                logger.info(f"Calculated MM metrics for {symbol}")

        except Exception as e:
            logger.error(f"Error calculating MM metrics for {symbol}: {e}")

# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Market Analytics API"}

@app.get("/api/market/{symbol}")
async def get_market_data(
    symbol: str,
    exchange: Optional[str] = None,
    hours: int = Query(default=24, ge=1, le=168)
):
    """Get market data for a symbol"""
    try:
        async with db_pool.acquire() as conn:
            query = """
                SELECT * FROM market_data
                WHERE symbol = $1
                AND timestamp > NOW() - INTERVAL '1 hour' * $2
            """
            params = [symbol, hours]

            if exchange:
                query += " AND exchange = $3"
                params.append(exchange)

            query += " ORDER BY timestamp DESC LIMIT 1000"

            data = await conn.fetch(query, *params)

            return {
                "symbol": symbol,
                "exchange": exchange,
                "data": [dict(row) for row in data]
            }
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orderbook/{symbol}")
async def get_orderbook(
    symbol: str,
    exchange: Optional[str] = None,
    aggregated: bool = False,
    depth_levels: int = 20
):
    """Get orderbook snapshot(s) - single exchange or aggregated"""
    try:
        async with db_pool.acquire() as conn:
            if aggregated or not exchange:
                # Get all orderbooks and aggregate them
                data = await conn.fetch("""
                    SELECT exchange, bids, asks, timestamp
                    FROM orderbook_snapshots
                    WHERE symbol = $1
                    AND timestamp > NOW() - INTERVAL '2 minutes'
                    ORDER BY exchange, timestamp DESC
                """, symbol)

                # Group by exchange and take latest for each
                latest_by_exchange = {}
                for row in data:
                    if row['exchange'] not in latest_by_exchange:
                        latest_by_exchange[row['exchange']] = row

                # Aggregate orderbooks
                all_bids = []
                all_asks = []

                for exchange_data in latest_by_exchange.values():
                    bids = json.loads(exchange_data['bids'])
                    asks = json.loads(exchange_data['asks'])

                    # Add exchange info to each order
                    for bid in bids[:depth_levels]:
                        all_bids.append({
                            'exchange': exchange_data['exchange'],
                            'price': float(bid[0]),
                            'volume': float(bid[1])
                        })

                    for ask in asks[:depth_levels]:
                        all_asks.append({
                            'exchange': exchange_data['exchange'],
                            'price': float(ask[0]),
                            'volume': float(ask[1])
                        })

                # Sort aggregated books
                all_bids.sort(key=lambda x: x['price'], reverse=True)
                all_asks.sort(key=lambda x: x['price'])

                # Group by price level
                grouped_bids = {}
                grouped_asks = {}

                for bid in all_bids:
                    price = bid['price']
                    if price not in grouped_bids:
                        grouped_bids[price] = {'price': price, 'total_volume': 0, 'exchanges': []}
                    grouped_bids[price]['total_volume'] += bid['volume']
                    grouped_bids[price]['exchanges'].append({
                        'exchange': bid['exchange'],
                        'volume': bid['volume']
                    })

                for ask in all_asks:
                    price = ask['price']
                    if price not in grouped_asks:
                        grouped_asks[price] = {'price': price, 'total_volume': 0, 'exchanges': []}
                    grouped_asks[price]['total_volume'] += ask['volume']
                    grouped_asks[price]['exchanges'].append({
                        'exchange': ask['exchange'],
                        'volume': ask['volume']
                    })

                return {
                    'symbol': symbol,
                    'aggregated': True,
                    'exchanges': list(latest_by_exchange.keys()),
                    'bids': list(grouped_bids.values())[:depth_levels],
                    'asks': list(grouped_asks.values())[:depth_levels],
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                # Single exchange orderbook
                data = await conn.fetchrow("""
                    SELECT * FROM orderbook_snapshots
                    WHERE symbol = $1 AND exchange = $2
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, symbol, exchange)

                if data:
                    return {
                        'symbol': symbol,
                        'exchange': exchange,
                        'bids': json.loads(data['bids'])[:depth_levels],
                        'asks': json.loads(data['asks'])[:depth_levels],
                        'timestamp': data['timestamp'].isoformat()
                    }
                else:
                    return {"error": "No orderbook data found"}
    except Exception as e:
        logger.error(f"Error fetching orderbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/perps/{symbol}")
async def get_perps_data(
    symbol: str,
    hours: int = Query(default=24, ge=1, le=168)
):
    """Get Binance Perps specific data"""
    try:
        async with db_pool.acquire() as conn:
            data = await conn.fetch("""
                SELECT * FROM binance_perps_data
                WHERE symbol = $1
                AND timestamp > NOW() - INTERVAL '1 hour' * $2
                ORDER BY timestamp DESC
            """, symbol, hours)

            return {
                "symbol": symbol,
                "data": [dict(row) for row in data]
            }
    except Exception as e:
        logger.error(f"Error fetching perps data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/whale/{symbol}")
async def get_whale_data(
    symbol: str,
    hours: int = Query(default=24, ge=1, le=168)
):
    """Get whale activity data"""
    try:
        async with db_pool.acquire() as conn:
            data = await conn.fetch("""
                SELECT * FROM whale_data
                WHERE symbol = $1
                AND timestamp > NOW() - INTERVAL '1 hour' * $2
                ORDER BY timestamp DESC
            """, symbol, hours)

            return {
                "symbol": symbol,
                "data": [dict(row) for row in data]
            }
    except Exception as e:
        logger.error(f"Error fetching whale data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mm/compliance/{symbol}")
async def get_mm_compliance(
    symbol: str,
    exchange: str,
    hours: int = Query(default=24, ge=1, le=168)
):
    """Get market maker compliance metrics"""
    try:
        async with db_pool.acquire() as conn:
            data = await conn.fetchrow("""
                SELECT * FROM calculate_mm_compliance($1, $2, $3)
            """, symbol, exchange, hours)

            if data:
                return dict(data)
            else:
                return {"error": "No compliance data found"}
    except Exception as e:
        logger.error(f"Error fetching MM compliance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mm/detection/{symbol}")
async def get_mm_detection(
    symbol: str,
    exchange: str
):
    """Detect market maker patterns and behavior"""
    try:
        from market_maker_detector import get_mm_analysis

        analysis = await get_mm_analysis(symbol, exchange, db_pool)

        return {
            "symbol": symbol,
            "exchange": exchange,
            "analysis": analysis,
            "summary": {
                "mm_probability": analysis['pattern_analysis']['mm_probability_score'],
                "liquidity_score": analysis['liquidity_profile']['liquidity_score'],
                "detected_patterns": {
                    "round_numbers": len(analysis['pattern_analysis']['round_number_orders']),
                    "symmetric_orders": len(analysis['pattern_analysis']['symmetric_orders']),
                    "order_walls": len(analysis['pattern_analysis']['order_walls']),
                    "ping_pong_trades": len(analysis['trade_flow']['ping_pong_trades'])
                }
            }
        }
    except Exception as e:
        logger.error(f"Error in MM detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/long-short/{symbol}")
async def get_long_short_ratio(
    symbol: str,
    hours: int = Query(default=24, ge=1, le=168)
):
    """Get long/short ratio data"""
    try:
        async with db_pool.acquire() as conn:
            data = await conn.fetch("""
                SELECT * FROM long_short_ratio
                WHERE symbol = $1
                AND timestamp > NOW() - INTERVAL '1 hour' * $2
                ORDER BY timestamp DESC
            """, symbol, hours)

            return {
                "symbol": symbol,
                "data": [dict(row) for row in data]
            }
    except Exception as e:
        logger.error(f"Error fetching long/short ratio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# MM Performance metrics calculation functions
async def calculate_market_presence(symbol: str, exchange: str, hours: int = 24) -> float:
    """Calculate market presence percentage based on orderbook activity"""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("""
                WITH time_slots AS (
                    SELECT generate_series(
                        NOW() - INTERVAL '%s hours',
                        NOW(),
                        INTERVAL '1 minute'
                    ) AS slot
                ),
                orderbook_presence AS (
                    SELECT DISTINCT
                        date_trunc('minute', timestamp) AS minute
                    FROM orderbook_snapshots
                    WHERE symbol = $1 AND exchange = $2
                        AND timestamp > NOW() - INTERVAL '%s hours'
                        AND jsonb_array_length(bids) > 0
                        AND jsonb_array_length(asks) > 0
                )
                SELECT
                    COUNT(DISTINCT op.minute) * 100.0 / NULLIF(COUNT(DISTINCT ts.slot), 0) AS uptime_pct
                FROM time_slots ts
                LEFT JOIN orderbook_presence op ON date_trunc('minute', ts.slot) = op.minute
            """ % (hours, hours), symbol, exchange)

            return float(result) if result else 0.0
    except Exception as e:
        logger.error(f"Error calculating market presence: {e}")
        return 0.0

async def calculate_liquidity_depth(orderbook: dict, mid_price: float, depth_pcts: List[float]) -> Dict[str, float]:
    """Calculate liquidity at various depth percentages"""
    liquidity = {}

    for pct in depth_pcts:
        bid_threshold = mid_price * (1 - pct / 100)
        ask_threshold = mid_price * (1 + pct / 100)

        bid_liquidity = sum(
            float(bid[1]) for bid in orderbook.get('bids', [])
            if float(bid[0]) >= bid_threshold
        )

        ask_liquidity = sum(
            float(ask[1]) for ask in orderbook.get('asks', [])
            if float(ask[0]) <= ask_threshold
        )

        liquidity[f'depth_{int(pct)}pct'] = bid_liquidity + ask_liquidity

    return liquidity

async def calculate_spread_metrics(symbol: str, exchange: str, hours: int = 1) -> Dict:
    """Calculate spread metrics over time period"""
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT
                    AVG((ask_price - bid_price) / NULLIF(bid_price, 0) * 10000) AS avg_spread_bps,
                    MIN((ask_price - bid_price) / NULLIF(bid_price, 0) * 10000) AS min_spread_bps,
                    MAX((ask_price - bid_price) / NULLIF(bid_price, 0) * 10000) AS max_spread_bps,
                    SUM(volume_24h) AS total_volume
                FROM market_data
                WHERE symbol = $1 AND exchange = $2
                    AND timestamp > NOW() - INTERVAL '%s hours'
                    AND bid_price > 0 AND ask_price > 0
            """ % hours, symbol, exchange)

            if result:
                return {
                    'avg_spread_bps': float(result['avg_spread_bps']) if result['avg_spread_bps'] else 0,
                    'min_spread_bps': float(result['min_spread_bps']) if result['min_spread_bps'] else 0,
                    'max_spread_bps': float(result['max_spread_bps']) if result['max_spread_bps'] else 0,
                    'total_volume': float(result['total_volume']) if result['total_volume'] else 0
                }
    except Exception as e:
        logger.error(f"Error calculating spread metrics: {e}")

    return {'avg_spread_bps': 0, 'min_spread_bps': 0, 'max_spread_bps': 0, 'total_volume': 0}

async def collect_mm_performance_metrics():
    """Collect MM performance metrics for all tracked symbols and exchanges"""
    try:
        symbols = os.getenv('TRACK_SYMBOL', 'BTCUSDT').split(',')
        exchange_list = ['binance_perps', 'binance_spot', 'bitget', 'gate', 'kucoin']

        for symbol in symbols:
            for exchange in exchange_list:
                try:
                    # Calculate market presence
                    market_presence = await calculate_market_presence(symbol, exchange, 1)

                    # Get spread metrics
                    spread_metrics = await calculate_spread_metrics(symbol, exchange, 1)

                    # Get latest orderbook for liquidity depth
                    async with db_pool.acquire() as conn:
                        orderbook_result = await conn.fetchrow("""
                            SELECT bids, asks
                            FROM orderbook_snapshots
                            WHERE symbol = $1 AND exchange = $2
                            ORDER BY timestamp DESC
                            LIMIT 1
                        """, symbol, exchange)

                        liquidity_data = {'depth_2pct': 0, 'depth_4pct': 0, 'depth_8pct': 0}
                        if orderbook_result:
                            bids = json.loads(orderbook_result['bids'])
                            asks = json.loads(orderbook_result['asks'])
                            if bids and asks and len(bids) > 0 and len(asks) > 0:
                                mid_price = (float(bids[0][0]) + float(asks[0][0])) / 2
                                orderbook = {'bids': bids, 'asks': asks}
                                liquidity_data = await calculate_liquidity_depth(orderbook, mid_price, [2, 4, 8])

                        # Get spread and order count
                        stats_result = await conn.fetchrow("""
                            SELECT
                                AVG(spread_bps) AS avg_spread,
                                SUM(quote_count) AS total_orders
                            FROM mm_metrics
                            WHERE symbol = $1 AND exchange = $2
                                AND timestamp > NOW() - INTERVAL '1 hour'
                        """, symbol, exchange)

                        avg_spread = float(stats_result['avg_spread']) if stats_result and stats_result['avg_spread'] else 0
                        order_count = int(stats_result['total_orders']) if stats_result and stats_result['total_orders'] else 0

                        # Calculate bid/ask imbalance
                        bid_ask_imbalance = 0
                        if orderbook_result:
                            total_bid_vol = sum(float(b[1]) for b in json.loads(orderbook_result['bids'])[:20])
                            total_ask_vol = sum(float(a[1]) for a in json.loads(orderbook_result['asks'])[:20])
                            if total_bid_vol + total_ask_vol > 0:
                                bid_ask_imbalance = (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol)

                        # Insert MM performance metrics
                        await conn.execute("""
                            INSERT INTO mm_performance (
                                exchange, symbol, market_presence, avg_spread_bps, min_spread_bps,
                                max_spread_bps, total_volume, order_count,
                                liquidity_2pct, liquidity_4pct, liquidity_8pct, bid_ask_imbalance
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        """, exchange, symbol, market_presence,
                            spread_metrics['avg_spread_bps'],
                            spread_metrics['min_spread_bps'],
                            spread_metrics['max_spread_bps'],
                            spread_metrics['total_volume'],
                            order_count,
                            liquidity_data.get('depth_2pct', 0),
                            liquidity_data.get('depth_4pct', 0),
                            liquidity_data.get('depth_8pct', 0),
                            bid_ask_imbalance
                        )

                        # Also update liquidity_depth table
                        if orderbook_result:
                            bids = json.loads(orderbook_result['bids'])
                            asks = json.loads(orderbook_result['asks'])
                            if bids and asks:
                                mid_price = (float(bids[0][0]) + float(asks[0][0])) / 2

                                # Calculate bid/ask liquidity at different depths
                                depth_levels = [2, 4, 8]
                                depth_data = {}

                                for pct in depth_levels:
                                    bid_threshold = mid_price * (1 - pct / 100)
                                    ask_threshold = mid_price * (1 + pct / 100)

                                    bid_depth = sum(float(b[1]) for b in bids if float(b[0]) >= bid_threshold)
                                    ask_depth = sum(float(a[1]) for a in asks if float(a[0]) <= ask_threshold)

                                    depth_data[f'depth_{pct}pct_bid'] = bid_depth
                                    depth_data[f'depth_{pct}pct_ask'] = ask_depth

                                total_bid_volume = sum(float(b[1]) for b in bids)
                                total_ask_volume = sum(float(a[1]) for a in asks)

                                await conn.execute("""
                                    INSERT INTO liquidity_depth (
                                        exchange, symbol,
                                        depth_2pct_bid, depth_2pct_ask,
                                        depth_4pct_bid, depth_4pct_ask,
                                        depth_8pct_bid, depth_8pct_ask,
                                        total_bid_volume, total_ask_volume
                                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                                """, exchange, symbol,
                                    depth_data.get('depth_2pct_bid', 0),
                                    depth_data.get('depth_2pct_ask', 0),
                                    depth_data.get('depth_4pct_bid', 0),
                                    depth_data.get('depth_4pct_ask', 0),
                                    depth_data.get('depth_8pct_bid', 0),
                                    depth_data.get('depth_8pct_ask', 0),
                                    total_bid_volume, total_ask_volume
                                )

                except Exception as e:
                    logger.error(f"Error collecting MM performance metrics for {exchange}: {e}")

        logger.info("MM performance metrics collection completed")
    except Exception as e:
        logger.error(f"Error in MM performance metrics collection: {e}")

@app.post("/api/collect/force")
async def force_collection():
    """Force immediate data collection"""
    try:
        await collect_all_market_data()
        return {"status": "Collection triggered"}
    except Exception as e:
        logger.error(f"Error forcing collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)