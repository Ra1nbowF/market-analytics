import aiohttp
import time
import hmac
import hashlib
import base64
import json
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class KucoinConnector:
    """KuCoin Spot connector"""

    def __init__(self, api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.base_url = "https://api.kucoin.com"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        if self.session:
            await self.session.close()

    def _sign(self, timestamp: str, method: str, endpoint: str, body: str = '') -> str:
        """Generate signature for KuCoin API"""
        if not self.api_secret:
            return ''

        message = timestamp + method + endpoint + body
        mac = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()

    def _encrypt_passphrase(self) -> str:
        """Encrypt passphrase for KuCoin API v2"""
        if not self.passphrase or not self.api_secret:
            return ''

        mac = hmac.new(
            self.api_secret.encode('utf-8'),
            self.passphrase.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()

    async def _request(self, method: str, endpoint: str, params: Dict = None, body: Dict = None):
        """Make HTTP request to KuCoin API"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}{endpoint}"
        timestamp = str(int(time.time() * 1000))
        headers = {
            'Content-Type': 'application/json'
        }

        # Add authentication headers if API key is provided
        if self.api_key:
            body_str = json.dumps(body) if body else ''
            signature = self._sign(timestamp, method, endpoint, body_str)

            headers.update({
                'KC-API-KEY': self.api_key,
                'KC-API-SIGN': signature,
                'KC-API-TIMESTAMP': timestamp,
                'KC-API-PASSPHRASE': self._encrypt_passphrase(),
                'KC-API-KEY-VERSION': '2'  # API v2
            })

        try:
            kwargs = {'headers': headers}
            if method == 'GET' and params:
                # Build query string for GET requests
                if params:
                    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                    url = f"{url}?{query_string}"
            elif body:
                kwargs['json'] = body

            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '200000':
                        return data.get('data')
                    else:
                        logger.error(f"KuCoin API error: {data}")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"API Error {response.status}: {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    async def get_trade_history(self, symbol: str, limit: int = 100) -> List:
        """Get trade history"""
        # Convert symbol format (e.g., BTCUSDT -> BTC-USDT)
        formatted_symbol = self._format_symbol(symbol)
        endpoint = f"/api/v1/market/histories"
        params = {'symbol': formatted_symbol}
        result = await self._request('GET', endpoint, params)
        return result if result else []

    async def get_full_orderbook(self, symbol: str) -> Dict:
        """Get full orderbook (Level 2)"""
        formatted_symbol = self._format_symbol(symbol)
        endpoint = f"/api/v3/market/orderbook/level2"
        params = {'symbol': formatted_symbol}
        result = await self._request('GET', endpoint, params)

        if result:
            return {
                'bids': result.get('bids', []),
                'asks': result.get('asks', []),
                'timestamp': result.get('time', 0)
            }
        return {}

    async def get_ticker(self, symbol: str) -> Dict:
        """Get ticker information"""
        formatted_symbol = self._format_symbol(symbol)
        endpoint = "/api/v1/market/orderbook/level1"
        params = {'symbol': formatted_symbol}
        return await self._request('GET', endpoint, params)

    async def get_24hr_stats(self, symbol: str) -> Dict:
        """Get 24hr statistics"""
        formatted_symbol = self._format_symbol(symbol)
        endpoint = "/api/v1/market/stats"
        params = {'symbol': formatted_symbol}
        return await self._request('GET', endpoint, params)

    async def get_candles(self, symbol: str, type: str = '1min', limit: int = 100) -> List:
        """Get kline/candlestick data"""
        formatted_symbol = self._format_symbol(symbol)
        endpoint = "/api/v1/market/candles"
        start_at = int(time.time()) - (limit * 60)  # Calculate start time based on limit
        end_at = int(time.time())

        params = {
            'symbol': formatted_symbol,
            'type': type,
            'startAt': str(start_at),
            'endAt': str(end_at)
        }
        result = await self._request('GET', endpoint, params)
        return result if result else []

    async def get_all_tickers(self) -> List:
        """Get all tickers"""
        endpoint = "/api/v1/market/allTickers"
        result = await self._request('GET', endpoint)
        return result.get('ticker', []) if result else []

    def _format_symbol(self, symbol: str) -> str:
        """Convert symbol format for KuCoin (e.g., BTCUSDT -> BTC-USDT)"""
        # KuCoin uses hyphen-separated format
        if 'USDT' in symbol:
            base = symbol.replace('USDT', '')
            return f"{base}-USDT"
        elif 'USDC' in symbol:
            base = symbol.replace('USDC', '')
            return f"{base}-USDC"
        elif 'BTC' in symbol and symbol.endswith('BTC'):
            base = symbol.replace('BTC', '')
            return f"{base}-BTC"
        else:
            # Try to insert hyphen before last 3-4 characters
            if len(symbol) > 6:
                return f"{symbol[:-4]}-{symbol[-4:]}"
            return symbol

    async def get_market_data(self, symbol: str) -> Dict:
        """Get comprehensive market data"""
        ticker = await self.get_ticker(symbol)
        stats = await self.get_24hr_stats(symbol)

        if ticker and stats:
            return {
                'symbol': symbol,
                'lastPrice': ticker.get('price'),
                'bidPrice': ticker.get('bestBid'),
                'askPrice': ticker.get('bestAsk'),
                'bidSize': ticker.get('bestBidSize'),
                'askSize': ticker.get('bestAskSize'),
                'volume24h': stats.get('vol'),
                'volValue24h': stats.get('volValue'),
                'high24h': stats.get('high'),
                'low24h': stats.get('low'),
                'changeRate': stats.get('changeRate'),
                'changePrice': stats.get('changePrice')
            }
        return {}