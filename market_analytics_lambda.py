"""
AWS Lambda handler for Market Analytics data collection
Runs on schedule to collect CEX data
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
import aiohttp

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Database configuration from environment
DATABASE_URL = os.environ.get('DATABASE_URL',
    'postgresql://dbadmin:123456789@dex-analytics-db.ckh8iqooci55.us-east-1.rds.amazonaws.com:5432/market_analytics')

# Exchange API endpoints (public, no auth needed)
EXCHANGES = {
    'binance_perps': {
        'ticker': 'https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=',
        'orderbook': 'https://fapi.binance.com/fapi/v1/depth?symbol=',
        'trades': 'https://fapi.binance.com/fapi/v1/aggTrades?symbol=',
        'funding': 'https://fapi.binance.com/fapi/v1/fundingRate?symbol='
    },
    'gate': {
        'ticker': 'https://api.gateio.ws/api/v4/futures/usdt/tickers?contract=',
        'orderbook': 'https://api.gateio.ws/api/v4/futures/usdt/order_book?contract=',
        'trades': 'https://api.gateio.ws/api/v4/futures/usdt/trades?contract='
    },
    'kucoin': {
        'ticker': 'https://api-futures.kucoin.com/api/v1/ticker?symbol=',
        'orderbook': 'https://api-futures.kucoin.com/api/v1/level2/snapshot?symbol=',
        'trades': 'https://api-futures.kucoin.com/api/v1/trade/history?symbol='
    },
    'bitget': {
        'ticker': 'https://api.bitget.com/api/mix/v1/market/ticker?symbol=',
        'orderbook': 'https://api.bitget.com/api/mix/v1/market/depth?symbol=',
        'trades': 'https://api.bitget.com/api/mix/v1/market/fills?symbol='
    }
}

# Symbols to track
SYMBOLS = ['BTCUSDT', 'ETHUSDT']

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

async def fetch_market_data(session, exchange, symbol):
    """Fetch market data from exchange"""
    try:
        # Map symbol format for each exchange
        exchange_symbol = symbol
        if exchange == 'gate':
            exchange_symbol = f"{symbol[:-4]}_{symbol[-4:]}"  # BTCUSDT -> BTC_USDT
        elif exchange == 'kucoin':
            exchange_symbol = f"{symbol[:-4]}USDTM"  # BTCUSDT -> BTCUSDTM

        # Fetch ticker data
        url = EXCHANGES[exchange]['ticker'] + exchange_symbol
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                return process_ticker_data(exchange, symbol, data)

    except Exception as e:
        logger.error(f"Error fetching {exchange} {symbol}: {e}")
        return None

def process_ticker_data(exchange, symbol, data):
    """Process ticker data into standard format"""
    result = {
        'exchange': exchange,
        'symbol': symbol,
        'timestamp': datetime.now(timezone.utc)
    }

    try:
        if exchange == 'binance_perps':
            result.update({
                'last_price': float(data.get('lastPrice', 0)),
                'bid_price': float(data.get('bidPrice', 0)),
                'ask_price': float(data.get('askPrice', 0)),
                'volume_24h': float(data.get('volume', 0)),
                'quote_volume_24h': float(data.get('quoteVolume', 0)),
                'price_change_pct_24h': float(data.get('priceChangePercent', 0)),
                'high_24h': float(data.get('highPrice', 0)),
                'low_24h': float(data.get('lowPrice', 0))
            })

        elif exchange == 'gate':
            if isinstance(data, list) and data:
                d = data[0]
                result.update({
                    'last_price': float(d.get('last', 0)),
                    'bid_price': float(d.get('highest_bid', 0)),
                    'ask_price': float(d.get('lowest_ask', 0)),
                    'volume_24h': float(d.get('volume_24h', 0)),
                    'price_change_pct_24h': float(d.get('change_percentage', 0))
                })

        elif exchange == 'kucoin':
            if 'data' in data:
                d = data['data']
                result.update({
                    'last_price': float(d.get('price', 0)),
                    'bid_price': float(d.get('bestBidPrice', 0)),
                    'ask_price': float(d.get('bestAskPrice', 0)),
                    'volume_24h': float(d.get('volume24h', 0))
                })

        elif exchange == 'bitget':
            if 'data' in data:
                d = data['data']
                result.update({
                    'last_price': float(d.get('last', 0)),
                    'bid_price': float(d.get('bid1', 0)),
                    'ask_price': float(d.get('ask1', 0)),
                    'volume_24h': float(d.get('volume24h', 0)),
                    'high_24h': float(d.get('high24h', 0)),
                    'low_24h': float(d.get('low24h', 0))
                })

    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Error processing {exchange} data: {e}")

    return result

async def collect_all_market_data():
    """Collect market data from all exchanges"""
    results = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        for exchange in EXCHANGES:
            for symbol in SYMBOLS:
                tasks.append(fetch_market_data(session, exchange, symbol))

        results = await asyncio.gather(*tasks)

    # Filter out None results
    return [r for r in results if r is not None]

def store_market_data(conn, data_points):
    """Store market data in database"""
    if not data_points:
        return 0

    cur = conn.cursor()
    inserted = 0

    for data in data_points:
        try:
            cur.execute("""
                INSERT INTO market_data (
                    exchange, symbol, last_price, bid_price, ask_price,
                    volume_24h, quote_volume_24h, price_change_pct_24h,
                    high_24h, low_24h, timestamp
                ) VALUES (
                    %(exchange)s, %(symbol)s, %(last_price)s, %(bid_price)s, %(ask_price)s,
                    %(volume_24h)s, %(quote_volume_24h)s, %(price_change_pct_24h)s,
                    %(high_24h)s, %(low_24h)s, %(timestamp)s
                )
            """, data)
            inserted += 1
        except Exception as e:
            logger.error(f"Error inserting data: {e}")

    conn.commit()
    cur.close()
    return inserted

def lambda_handler(event, context):
    """Main Lambda handler"""
    logger.info(f"Market Analytics Lambda started: {event}")

    try:
        # Connect to database
        conn = get_db_connection()

        # Check if tables exist
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'market_data'
        """)

        if cur.fetchone()[0] == 0:
            logger.error("market_data table not found. Run migration first!")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Database not initialized'})
            }

        cur.close()

        # Collect market data
        logger.info("Collecting market data...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data_points = loop.run_until_complete(collect_all_market_data())
        loop.close()

        # Store in database
        inserted = store_market_data(conn, data_points)
        logger.info(f"Inserted {inserted} market data points")

        # Get summary statistics
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT exchange) as exchanges,
                COUNT(DISTINCT symbol) as symbols,
                MAX(timestamp) as latest_update
            FROM market_data
            WHERE timestamp > NOW() - INTERVAL '1 hour'
        """)

        stats = cur.fetchone()
        cur.close()
        conn.close()

        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Market data collection completed',
                'inserted': inserted,
                'stats': {
                    'total_records': stats['total_records'],
                    'exchanges': stats['exchanges'],
                    'symbols': stats['symbols'],
                    'latest_update': stats['latest_update'].isoformat() if stats['latest_update'] else None
                }
            }, default=str)
        }

        logger.info(f"Lambda completed: {response}")
        return response

    except Exception as e:
        logger.error(f"Lambda error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

# For local testing
if __name__ == "__main__":
    import sys

    # Set up logging for local testing
    logging.basicConfig(level=logging.INFO)

    # Test event
    test_event = {'test': True}

    # Run handler
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))