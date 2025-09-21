import aiohttp
import time
import hmac
import hashlib
import base64
import json
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class BitgetConnector:
    """Bitget Spot connector with whale data endpoints"""

    def __init__(self, api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.base_url = "https://api.bitget.com"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        if self.session:
            await self.session.close()

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """Generate signature for Bitget API"""
        if not self.api_secret:
            return ''

        message = timestamp + method + request_path + body
        mac = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()

    async def _request(self, method: str, endpoint: str, params: Dict = None, body: Dict = None):
        """Make HTTP request to Bitget API"""
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
                'ACCESS-KEY': self.api_key,
                'ACCESS-SIGN': signature,
                'ACCESS-TIMESTAMP': timestamp,
                'ACCESS-PASSPHRASE': self.passphrase or '',
                'locale': 'en-US'
            })

        try:
            kwargs = {'headers': headers}
            if method == 'GET' and params:
                kwargs['params'] = params
            elif body:
                kwargs['json'] = body

            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '00000':
                        return data.get('data')
                    else:
                        logger.error(f"Bitget API error: {data}")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"API Error {response.status}: {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    async def get_ticker(self, symbol: str) -> Dict:
        """Get ticker information"""
        params = {'symbol': self._format_symbol(symbol)}
        result = await self._request('GET', '/api/v2/spot/market/tickers', params)
        if result and len(result) > 0:
            return result[0]
        return {}

    async def get_spot_fund_flow(self, symbol: str) -> Dict:
        """Get spot fund flow data"""
        # Note: This endpoint might require specific formatting or permissions
        params = {'symbol': self._format_symbol(symbol)}
        return await self._request('GET', '/api/v2/spot/market/fund-flow', params)

    async def get_whale_net_flow(self, symbol: str) -> Dict:
        """Get whale net flow data"""
        # Note: This endpoint might require specific formatting or permissions
        params = {'symbol': self._format_symbol(symbol)}
        return await self._request('GET', '/api/v2/spot/market/whale-net-flow', params)

    async def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book"""
        params = {
            'symbol': self._format_symbol(symbol),
            'limit': str(limit)
        }
        return await self._request('GET', '/api/v2/spot/market/orderbook', params)

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List:
        """Get recent trades"""
        params = {
            'symbol': self._format_symbol(symbol),
            'limit': str(limit)
        }
        result = await self._request('GET', '/api/v2/spot/market/fills', params)
        return result if result else []

    async def get_candles(self, symbol: str, granularity: str = '1min', limit: int = 100) -> List:
        """Get candlestick data"""
        params = {
            'symbol': self._format_symbol(symbol),
            'granularity': granularity,
            'limit': str(limit)
        }
        result = await self._request('GET', '/api/v2/spot/market/candles', params)
        return result if result else []

    def _format_symbol(self, symbol: str) -> str:
        """Convert symbol format for Bitget (e.g., BTCUSDT -> BTCUSDT)"""
        # Bitget typically uses the same format as Binance for spot
        # But might need adjustment based on actual API requirements
        return symbol

    async def get_24hr_ticker(self, symbol: str) -> Dict:
        """Get 24hr ticker statistics"""
        ticker = await self.get_ticker(symbol)
        if ticker:
            return {
                'symbol': ticker.get('symbol'),
                'lastPrice': ticker.get('lastPr'),
                'bidPrice': ticker.get('bidPr'),
                'askPrice': ticker.get('askPr'),
                'volume': ticker.get('baseVolume'),
                'quoteVolume': ticker.get('quoteVolume'),
                'priceChangePercent': ticker.get('changePercentage'),
                'high24h': ticker.get('high24h'),
                'low24h': ticker.get('low24h')
            }
        return {}