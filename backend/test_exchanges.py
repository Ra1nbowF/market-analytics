"""Test script to check what each exchange API returns"""
import asyncio
import os
from dotenv import load_dotenv

from exchanges.binance_perps import BinancePerpsConnector
from exchanges.binance_spot import BinanceSpotConnector
from exchanges.bitget import BitgetConnector
from exchanges.gate import GateConnector
from exchanges.kucoin import KucoinConnector

load_dotenv()

async def test_binance_perps():
    print("\n=== Testing Binance Perps ===")
    try:
        exchange = BinancePerpsConnector()
        ticker = await exchange.get_24hr_ticker('BTCUSDT')
        print(f"Ticker response: {ticker}")
        if ticker:
            print(f"Bid: {ticker.get('bidPrice')}, Ask: {ticker.get('askPrice')}")
        await exchange.close()
    except Exception as e:
        print(f"Error: {e}")

async def test_binance_spot():
    print("\n=== Testing Binance Spot ===")
    try:
        exchange = BinanceSpotConnector()
        ticker = await exchange.get_ticker('BTCUSDT')
        print(f"Ticker response: {ticker}")
        if ticker:
            print(f"Bid: {ticker.get('bidPrice')}, Ask: {ticker.get('askPrice')}")
        await exchange.close()
    except Exception as e:
        print(f"Error: {e}")

async def test_bitget():
    print("\n=== Testing Bitget ===")
    try:
        exchange = BitgetConnector()
        ticker = await exchange.get_ticker('BTCUSDT')
        print(f"Ticker response: {ticker}")
        if ticker:
            print(f"Available fields: {ticker.keys() if isinstance(ticker, dict) else 'Not a dict'}")
        await exchange.close()
    except Exception as e:
        print(f"Error: {e}")

async def test_gate():
    print("\n=== Testing Gate.io ===")
    try:
        exchange = GateConnector()

        # Test ticker
        ticker = await exchange.get_ticker('BTCUSDT')
        print(f"Ticker response: {ticker}")

        # Test market depth
        depth = await exchange.get_market_depth('BTCUSDT')
        print(f"Market depth response: {depth}")
        if depth and depth.get('bids'):
            print(f"Best bid: {depth['bids'][0] if depth['bids'] else 'No bids'}")
            print(f"Best ask: {depth['asks'][0] if depth['asks'] else 'No asks'}")

        await exchange.close()
    except Exception as e:
        print(f"Error: {e}")

async def test_kucoin():
    print("\n=== Testing KuCoin ===")
    try:
        exchange = KucoinConnector()

        # Test ticker
        ticker = await exchange.get_ticker('BTCUSDT')
        print(f"Ticker response: {ticker}")

        # Test orderbook
        orderbook = await exchange.get_full_orderbook('BTCUSDT')
        print(f"Orderbook response: {orderbook}")
        if orderbook and orderbook.get('bids'):
            print(f"Best bid: {orderbook['bids'][0] if orderbook['bids'] else 'No bids'}")

        await exchange.close()
    except Exception as e:
        print(f"Error: {e}")

async def main():
    print("Testing all exchange connectors...")

    await test_binance_perps()
    await test_binance_spot()
    await test_bitget()
    await test_gate()
    await test_kucoin()

if __name__ == "__main__":
    asyncio.run(main())