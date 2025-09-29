"""
Simplified Lambda for market data collection
Uses urllib instead of external dependencies for AWS Lambda compatibility
"""
import json
import urllib.request
import urllib.parse
import os
from datetime import datetime
from decimal import Decimal

def lambda_handler(event, context):
    """Collect market data without external dependencies"""

    print(f"Market data collection started: {event}")

    # Collect data from exchanges
    results = []

    # Binance Futures API (no auth needed)
    try:
        symbol = "BTCUSDT"
        url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"

        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())

            market_data = {
                'exchange': 'binance_perps',
                'symbol': symbol,
                'last_price': float(data.get('lastPrice', 0)),
                'bid_price': float(data.get('bidPrice', 0)),
                'ask_price': float(data.get('askPrice', 0)),
                'volume_24h': float(data.get('volume', 0)),
                'high_24h': float(data.get('highPrice', 0)),
                'low_24h': float(data.get('lowPrice', 0)),
                'timestamp': datetime.utcnow().isoformat()
            }

            results.append(market_data)
            print(f"Collected Binance data: {market_data['last_price']}")

    except Exception as e:
        print(f"Error collecting Binance data: {e}")

    # Gate.io API
    try:
        symbol = "BTC_USDT"
        url = f"https://api.gateio.ws/api/v4/futures/usdt/tickers?contract={symbol}"

        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

            if data and isinstance(data, list):
                d = data[0]
                market_data = {
                    'exchange': 'gate',
                    'symbol': 'BTCUSDT',
                    'last_price': float(d.get('last', 0)),
                    'bid_price': float(d.get('highest_bid', 0)),
                    'ask_price': float(d.get('lowest_ask', 0)),
                    'volume_24h': float(d.get('volume_24h', 0)),
                    'timestamp': datetime.utcnow().isoformat()
                }

                results.append(market_data)
                print(f"Collected Gate.io data: {market_data['last_price']}")

    except Exception as e:
        print(f"Error collecting Gate.io data: {e}")

    # Store in DynamoDB (alternative to RDS for Lambda)
    # Or return data for processing

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Market data collection completed',
            'collected': len(results),
            'data': results,
            'timestamp': datetime.utcnow().isoformat()
        }, default=str)
    }

    print(f"Collection complete: {len(results)} data points")

    return response

# For local testing
if __name__ == "__main__":
    result = lambda_handler({'test': True}, None)
    print(json.dumps(json.loads(result['body']), indent=2))