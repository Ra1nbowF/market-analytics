import aiohttp
import time
import hmac
import hashlib
import json
from typing import Dict, List, Optional
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

class GateConnector:
    """Gate.io Spot connector"""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.gateio.ws"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        if self.session:
            await self.session.close()

    def _sign(self, method: str, url: str, query_string: str = '', body: str = '') -> Dict[str, str]:
        """Generate signature for Gate.io API"""
        if not self.api_key or not self.api_secret:
            return {}

        t = str(int(time.time()))
        message = f"{method}\n{url}\n{query_string}\n{hashlib.sha512(body.encode()).hexdigest()}\n{t}"

        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()

        return {
            'KEY': self.api_key,
            'Timestamp': t,
            'SIGN': signature
        }

    async def _request(self, method: str, endpoint: str, params: Dict = None, body: Dict = None):
        """Make HTTP request to Gate.io API"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}{endpoint}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        # Add authentication if needed
        if self.api_key and self.api_secret:
            query_string = urlencode(params) if params else ''
            body_str = json.dumps(body) if body else ''
            auth_headers = self._sign(method, endpoint, query_string, body_str)
            headers.update(auth_headers)

        try:
            kwargs = {'headers': headers}
            if method == 'GET' and params:
                kwargs['params'] = params
            elif body:
                kwargs['json'] = body

            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"API Error {response.status}: {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    async def get_market_depth(self, symbol: str, limit: int = 100) -> Dict:
        """Get market depth information (order book)"""
        # Convert symbol format (e.g., BTCUSDT -> BTC_USDT)
        currency_pair = self._format_symbol(symbol)
        params = {'currency_pair': currency_pair, 'limit': limit}
        result = await self._request('GET', '/api/v4/spot/order_book', params)

        if result:
            return {
                'bids': result.get('bids', []),
                'asks': result.get('asks', []),
                'timestamp': result.get('current', 0)
            }
        return {}

    async def get_trade_records(self, symbol: str, limit: int = 100) -> List:
        """Query market transaction records"""
        currency_pair = self._format_symbol(symbol)
        params = {'currency_pair': currency_pair, 'limit': limit}
        result = await self._request('GET', '/api/v4/spot/trades', params)
        return result if result else []

    async def get_ticker(self, symbol: str) -> Dict:
        """Get ticker information"""
        currency_pair = self._format_symbol(symbol)
        params = {'currency_pair': currency_pair}
        result = await self._request('GET', '/api/v4/spot/tickers', params)
        if result and len(result) > 0:
            return result[0]
        return {}

    async def get_candlesticks(self, symbol: str, interval: str = '1m', limit: int = 100) -> List:
        """Get candlestick data"""
        currency_pair = self._format_symbol(symbol)
        params = {
            'currency_pair': currency_pair,
            'interval': interval,
            'limit': limit
        }
        result = await self._request('GET', '/api/v4/spot/candlesticks', params)
        return result if result else []

    async def get_futures_stats(self, contract: str = None) -> List:
        """Get futures trading statistics"""
        endpoint = '/api/v4/futures/usdt/contracts'
        if contract:
            endpoint = f'{endpoint}/{contract}/stats'
        result = await self._request('GET', endpoint)
        return result if result else []

    def _format_symbol(self, symbol: str) -> str:
        """Convert symbol format for Gate.io (e.g., BTCUSDT -> BTC_USDT)"""
        # Simple conversion - might need adjustment based on actual pairs
        if 'USDT' in symbol:
            base = symbol.replace('USDT', '')
            return f"{base}_USDT"
        elif 'USDC' in symbol:
            base = symbol.replace('USDC', '')
            return f"{base}_USDC"
        elif 'BTC' in symbol and symbol.endswith('BTC'):
            base = symbol.replace('BTC', '')
            return f"{base}_BTC"
        else:
            # Default format
            return symbol

    async def get_24hr_ticker(self, symbol: str) -> Dict:
        """Get 24hr ticker statistics"""
        ticker = await self.get_ticker(symbol)
        if ticker:
            return {
                'symbol': ticker.get('currency_pair'),
                'lastPrice': ticker.get('last'),
                'bidPrice': ticker.get('highest_bid'),
                'askPrice': ticker.get('lowest_ask'),
                'volume': ticker.get('base_volume'),
                'quoteVolume': ticker.get('quote_volume'),
                'priceChangePercent': ticker.get('change_percentage'),
                'high24h': ticker.get('high_24h'),
                'low24h': ticker.get('low_24h')
            }
        return {}