import aiohttp
import time
import hmac
import hashlib
from typing import Dict, List, Optional
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

class BinanceSpotConnector:
    """Binance Spot (including Alpha) connector"""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.binance.com"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        if self.session:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False):
        """Make HTTP request to Binance API"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}{endpoint}"
        headers = {}

        if self.api_key:
            headers['X-MBX-APIKEY'] = self.api_key

        if signed and self.api_secret:
            params = params or {}
            params['timestamp'] = int(time.time() * 1000)
            query_string = urlencode(params)
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            params['signature'] = signature

        try:
            async with self.session.request(method, url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"API Error {response.status}: {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    async def get_ticker(self, symbol: str) -> Dict:
        """Get 24hr ticker price change statistics"""
        params = {'symbol': symbol}
        return await self._request('GET', '/api/v3/ticker/24hr', params)

    async def get_aggregated_trades(self, symbol: str, limit: int = 100) -> List:
        """Get compressed/aggregated trades list"""
        params = {'symbol': symbol, 'limit': limit}
        result = await self._request('GET', '/api/v3/aggTrades', params)
        return result if result else []

    async def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book"""
        params = {'symbol': symbol, 'limit': limit}
        return await self._request('GET', '/api/v3/depth', params)

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List:
        """Get recent trades"""
        params = {'symbol': symbol, 'limit': limit}
        result = await self._request('GET', '/api/v3/trades', params)
        return result if result else []

    async def get_klines(self, symbol: str, interval: str = '1m', limit: int = 100) -> List:
        """Get kline/candlestick data"""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        result = await self._request('GET', '/api/v3/klines', params)
        return result if result else []

    async def get_avg_price(self, symbol: str) -> Dict:
        """Get current average price"""
        params = {'symbol': symbol}
        return await self._request('GET', '/api/v3/avgPrice', params)

    async def get_price(self, symbol: str = None) -> Dict:
        """Get latest price for a symbol or all symbols"""
        endpoint = '/api/v3/ticker/price'
        params = {'symbol': symbol} if symbol else {}
        return await self._request('GET', endpoint, params)