import aiohttp
import asyncio
import json
import hmac
import hashlib
import time
from typing import Dict, List, Optional
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

class BinancePerpsConnector:
    """Binance Perpetual Futures connector with all required endpoints"""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://fapi.binance.com"
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

    async def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book depth"""
        params = {'symbol': symbol, 'limit': limit}
        return await self._request('GET', '/fapi/v1/depth', params)

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List:
        """Get recent trades list"""
        params = {'symbol': symbol, 'limit': limit}
        result = await self._request('GET', '/fapi/v1/trades', params)
        return result if result else []

    async def get_mark_price(self, symbol: str) -> Dict:
        """Get mark price and funding rate"""
        params = {'symbol': symbol}
        return await self._request('GET', '/fapi/v1/premiumIndex', params)

    async def get_funding_rate(self, symbol: str, limit: int = 1) -> Dict:
        """Get funding rate history"""
        params = {'symbol': symbol, 'limit': limit}
        result = await self._request('GET', '/fapi/v1/fundingRate', params)
        return result[0] if result else {}

    async def get_24hr_ticker(self, symbol: str) -> Dict:
        """Get 24hr ticker price change statistics"""
        params = {'symbol': symbol}
        return await self._request('GET', '/fapi/v1/ticker/24hr', params)

    async def get_open_interest(self, symbol: str) -> Dict:
        """Get open interest"""
        params = {'symbol': symbol}
        return await self._request('GET', '/fapi/v1/openInterest', params)

    async def get_open_interest_stats(self, symbol: str, period: str = '5m', limit: int = 30) -> List:
        """Get open interest statistics"""
        params = {
            'symbol': symbol,
            'period': period,
            'limit': limit
        }
        result = await self._request('GET', '/futures/data/openInterestHist', params)
        return result if result else []

    async def get_long_short_ratio(self, symbol: str, period: str = '5m', limit: int = 30) -> Dict:
        """Get long/short account ratio"""
        params = {
            'symbol': symbol,
            'period': period,
            'limit': limit
        }
        result = await self._request('GET', '/futures/data/globalLongShortAccountRatio', params)
        if result and len(result) > 0:
            # Return the most recent data point
            return result[0]
        return {}

    async def get_top_trader_ratio(self, symbol: str, period: str = '5m', limit: int = 30) -> Dict:
        """Get top trader long/short position ratio"""
        params = {
            'symbol': symbol,
            'period': period,
            'limit': limit
        }
        result = await self._request('GET', '/futures/data/topLongShortPositionRatio', params)
        if result and len(result) > 0:
            # Return the most recent data point
            return result[0]
        return {}

    async def get_taker_volume(self, symbol: str, period: str = '5m', limit: int = 30) -> List:
        """Get taker buy/sell volume"""
        params = {
            'symbol': symbol,
            'period': period,
            'limit': limit
        }
        result = await self._request('GET', '/futures/data/takerlongshortRatio', params)
        return result if result else []

    async def get_basis(self, symbol: str, period: str = '5m', limit: int = 30) -> List:
        """Get basis (spot-futures price difference)"""
        params = {
            'pair': symbol.replace('USDT', '_USDT'),  # Convert symbol format
            'contractType': 'PERPETUAL',
            'period': period,
            'limit': limit
        }
        result = await self._request('GET', '/futures/data/basis', params)
        return result if result else []