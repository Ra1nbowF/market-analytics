# Exchange API Endpoints Comprehensive Report

## Executive Summary
This report provides a detailed analysis of available API endpoints across four major cryptocurrency exchanges: Binance, Bitget, Gate.io, and KuCoin. Each exchange offers extensive REST and WebSocket APIs for spot, futures, and specialized trading features.

---

## 1. Binance Derivatives API

### API Categories
- **USDⓈ-M Futures** - USDT-margined perpetual and quarterly futures
- **COIN-M Futures** - Coin-margined contracts
- **Options** - European-style options
- **Portfolio Margin** - Cross-margined account management
- **Portfolio Margin Pro** - Advanced margin features
- **Futures Data** - Historical and analytical data

### Currently Used Endpoints (in our system)
```
/fapi/v1/depth                     - Order book depth (100 levels)
/fapi/v1/trades                    - Recent trades list
/fapi/v1/ticker/24hr               - 24-hour ticker statistics
/fapi/v1/premiumIndex              - Mark price and index price
/fapi/v1/fundingRate               - Funding rate history
/fapi/v1/openInterest              - Open interest data
/futures/data/globalLongShortAccountRatio  - Long/short ratio
/futures/data/topLongShortAccountRatio     - Top trader positions
```

### Additional Available Endpoints
#### Market Data
- `/fapi/v1/klines` - Kline/candlestick data
- `/fapi/v1/continuousKlines` - Continuous contract kline data
- `/fapi/v1/indexPriceKlines` - Index price kline data
- `/fapi/v1/markPriceKlines` - Mark price kline data
- `/fapi/v1/aggTrades` - Compressed/aggregate trades
- `/fapi/v1/historicalTrades` - Historical trades
- `/fapi/v1/ticker/bookTicker` - Best price/qty on order book
- `/fapi/v1/ticker/price` - Latest price for symbol(s)
- `/fapi/v1/time` - Server time

#### Account & Trading
- `/fapi/v2/account` - Account information
- `/fapi/v2/balance` - Account balance
- `/fapi/v2/positionRisk` - Position information
- `/fapi/v1/order` - Place/cancel/query orders
- `/fapi/v1/batchOrders` - Batch orders
- `/fapi/v1/allOrders` - Query all orders
- `/fapi/v1/openOrders` - Query open orders
- `/fapi/v1/leverage` - Change leverage
- `/fapi/v1/marginType` - Change margin type
- `/fapi/v1/positionMargin` - Modify isolated position margin
- `/fapi/v1/userTrades` - Account trade list

#### Advanced Features
- `/fapi/v1/income` - Transaction history
- `/fapi/v1/commissionRate` - User commission rate
- `/fapi/v1/adlQuantile` - Position ADL quantile estimation
- `/fapi/v1/apiTradingStatus` - Account API trading status
- `/fapi/v1/multiAssetsMargin` - Multi-assets mode

---

## 2. Bitget API v2

### API Structure
- **Base URL**: `https://api.bitget.com`
- **Version**: V2 (Released October 2023)
- **Rate Limits**: 20 requests/second for most endpoints

### Currently Used Endpoints (in our system)
```
/api/v2/spot/market/tickers        - Market ticker
/api/v2/spot/market/orderbook      - Order book
/api/v2/spot/market/whale-net-flow - Whale activity tracking
/api/v2/spot/market/fund-flow      - Fund flow analysis
```

### Additional Available Endpoints

#### Spot Trading
- `/api/v2/spot/market/candles` - Candlestick data
- `/api/v2/spot/market/fills-history` - Market trades
- `/api/v2/spot/market/depth` - Order book depth
- `/api/v2/spot/trade/place-order` - Place order
- `/api/v2/spot/trade/cancel-order` - Cancel order
- `/api/v2/spot/trade/orders-pending` - Pending orders
- `/api/v2/spot/trade/orders-history` - Order history
- `/api/v2/spot/trade/fills` - Trade fills
- `/api/v2/spot/account/info` - Account information
- `/api/v2/spot/account/assets` - Asset balances

#### Futures Trading
- `/api/v2/mix/market/candles` - Futures candlestick data
- `/api/v2/mix/market/history-candles` - Historical candles (max 200)
- `/api/v2/mix/market/ticker` - Futures ticker
- `/api/v2/mix/market/tickers` - All futures tickers
- `/api/v2/mix/market/depth` - Futures order book
- `/api/v2/mix/market/trades` - Recent trades
- `/api/v2/mix/position/all-position` - All positions
- `/api/v2/mix/order/place-order` - Place futures order
- `/api/v2/mix/order/cancel-order` - Cancel futures order
- `/api/v2/mix/account/account` - Futures account info

#### Copy Trading (New V2)
- `/api/v2/copy/mix-trader/create-copy-api` - Create copy trading API
- `/api/v2/copy/mix-follower/copy-settings` - Follower settings
- `/api/v2/copy/mix-trader/order-total-detail` - Trader statistics
- `/api/v2/copy/mix-follower/query-current-orders` - Current copy orders
- `/api/v2/copy/mix-follower/query-history-orders` - Historical copy orders

#### Specialized Features
- `/api/v2/spot/market/vip-fee-rate` - VIP fee rates
- `/api/v2/spot/wallet/transfer` - Asset transfer
- `/api/v2/spot/wallet/deposit-address` - Deposit addresses
- `/api/v2/spot/wallet/withdrawal` - Withdrawals
- `/api/v2/margin/account/borrow` - Margin borrowing
- `/api/v2/margin/account/repay` - Margin repayment
- `/api/v2/earn/savings/subscribe` - Savings products
- `/api/v2/convert/quoted-price` - Convert quotes

---

## 3. Gate.io API v4

### API Structure
- **Base URL**: `https://api.gateio.ws/api/v4`
- **Authentication**: HMAC-SHA512
- **Rate Limits**: Varies by endpoint

### Currently Used Endpoints (in our system)
```
/spot/order_book                   - Market depth
/spot/tickers                      - Ticker data
/spot/trades                       - Recent trades
```

### Additional Available Endpoints

#### Spot Trading
- `/spot/currencies` - List all currencies
- `/spot/currency_pairs` - List all currency pairs
- `/spot/candlesticks` - Retrieve candlestick data
- `/spot/orders` - Create/cancel/list orders
- `/spot/batch_orders` - Batch order operations
- `/spot/my_trades` - Personal trading history
- `/spot/accounts` - Spot account info
- `/spot/price_orders` - Create price-triggered orders

#### Margin Trading
- `/margin/currency_pairs` - Margin trading pairs
- `/margin/funding_book` - Lending book
- `/margin/loans` - List/create loans
- `/margin/loan_records` - Loan records
- `/margin/auto_repay` - Auto-repayment settings
- `/margin/transferable` - Maximum transferable amount

#### Futures Trading
- `/futures/{settle}/contracts` - List all contracts
- `/futures/{settle}/order_book` - Futures order book
- `/futures/{settle}/trades` - Futures trades
- `/futures/{settle}/candlesticks` - Futures candlesticks
- `/futures/{settle}/tickers` - Futures tickers
- `/futures/{settle}/funding_rate` - Funding rate history
- `/futures/{settle}/insurance` - Insurance fund history
- `/futures/{settle}/orders` - Futures orders
- `/futures/{settle}/positions` - Position information

#### Options Trading
- `/options/underlyings` - List all underlyings
- `/options/expirations` - List all expiration times
- `/options/contracts` - List all option contracts
- `/options/settlements` - List settlement history
- `/options/order_book` - Options order book
- `/options/tickers` - Options tickers
- `/options/candlesticks` - Options candlesticks
- `/options/orders` - Options orders
- `/options/positions` - Options positions

#### Wallet & Account
- `/wallet/deposits` - Deposit history
- `/wallet/withdrawals` - Withdrawal history
- `/wallet/deposit_address` - Generate deposit address
- `/wallet/transfers` - Transfer between accounts
- `/wallet/sub_account_transfers` - Sub-account transfers
- `/wallet/fee` - Trading fee rates
- `/wallet/total_balance` - Total balance across accounts

#### Earn Products
- `/earn/uni/currencies` - Available earn currencies
- `/earn/uni/lend` - Lend assets
- `/earn/uni/redeem` - Redeem assets
- `/earn/staking/currency_list` - Staking currencies
- `/earn/staking/stake` - Stake assets
- `/earn/dual/investment_plan` - Dual investment plans
- `/earn/structured/orders` - Structured product orders

---

## 4. KuCoin API

### API Structure
- **Base URL**: `https://api.kucoin.com`
- **Authentication**: HMAC-SHA256
- **API Version**: v1/v2/v3 (depending on endpoint)

### Currently Used Endpoints (in our system)
```
/api/v1/market/orderbook/level2_100  - Full order book
/api/v1/market/allTickers            - All ticker data
/api/v1/market/stats                 - 24-hour statistics
/api/v1/market/histories             - Trade history
```

### Additional Available Endpoints

#### Market Data
- `/api/v1/symbols` - Get symbols list
- `/api/v1/market/orderbook/level2_20` - Part order book (20 levels)
- `/api/v1/market/orderbook/level3` - Full order book v3
- `/api/v1/market/candles` - Get kline data
- `/api/v1/currencies` - Get currencies
- `/api/v1/prices` - Get fiat prices
- `/api/v1/mark-price/{symbol}/current` - Current mark price
- `/api/v1/margin/config` - Margin configuration

#### Spot Trading
- `/api/v1/orders` - Place order
- `/api/v1/order/client-order` - Place order with client OID
- `/api/v1/orders/multi` - Place bulk orders
- `/api/v1/orders/{orderId}` - Cancel order
- `/api/v1/order/cancel-all` - Cancel all orders
- `/api/v1/orders` - List orders
- `/api/v1/fills` - List fills
- `/api/v1/limit/orders` - Active order count

#### Stop Orders
- `/api/v1/stop-order` - Place stop order
- `/api/v1/stop-order/{orderId}` - Cancel stop order
- `/api/v1/stop-order/cancel` - Cancel stop orders
- `/api/v1/stop-order` - List stop orders

#### Margin Trading
- `/api/v1/margin/account` - Margin account info
- `/api/v1/margin/borrow` - Borrow assets
- `/api/v1/margin/repay` - Repay assets
- `/api/v1/margin/borrowed` - Get borrow history
- `/api/v1/margin/repay/all` - Repay all
- `/api/v1/isolated/accounts` - Isolated margin accounts
- `/api/v1/isolated/account/{symbol}` - Single isolated account

#### Futures Trading
- `/api/v1/contracts/active` - Get open contracts
- `/api/v1/contracts/{symbol}` - Get contract detail
- `/api/v1/ticker` - Real-time ticker
- `/api/v1/level2/snapshot` - Level 2 order book
- `/api/v1/trade/history` - Transaction history
- `/api/v1/interest/query` - Interest query
- `/api/v1/premium/query` - Premium index
- `/api/v1/funding-rate/{symbol}/current` - Current funding rate
- `/api/v1/positions` - Position list
- `/api/v1/position` - Get position details

#### Account Management
- `/api/v1/accounts` - List accounts
- `/api/v1/accounts/{accountId}` - Get account
- `/api/v1/accounts/ledgers` - Account ledgers
- `/api/v2/accounts/{accountId}` - Get account detail v2
- `/api/v1/sub/user` - Create sub-user
- `/api/v2/sub/user` - Create sub-user v2
- `/api/v1/sub-accounts` - List sub-accounts
- `/api/v2/sub-accounts` - List sub-accounts v2
- `/api/v1/sub/api-key` - Create sub API key

#### Advanced Trading
- `/api/v1/hf/orders` - HF place order
- `/api/v1/hf/orders/multi` - HF place multiple orders
- `/api/v1/hf/orders/alter` - HF modify order
- `/api/v1/hf/orders/{orderId}` - HF cancel order
- `/api/v1/oco/order` - Place OCO order
- `/api/v1/oco/orders` - List OCO orders

#### Copy Trading
- `/api/v1/copy-trading/traders` - List master traders
- `/api/v1/copy-trading/orders` - Copy trading orders
- `/api/v1/copy-trading/positions` - Copy positions
- `/api/v1/copy-trading/follows` - Following relationships

#### Earn Products
- `/api/v1/earn/kcs-staking/products` - KCS staking products
- `/api/v1/earn/staking/products` - Staking products
- `/api/v1/earn/eth-staking/products` - ETH staking products
- `/api/v1/earn/promotion/products` - Promotional products
- `/api/v1/earn/hold/assets` - User holding assets

---

## WebSocket Endpoints

### Binance Futures
- `wss://fstream.binance.com/ws/` - Main futures WebSocket
- Streams: ticker, depth, trade, kline, markPrice, funding, liquidation

### Bitget
- `wss://ws.bitget.com/v2/ws/public` - Public WebSocket
- `wss://ws.bitget.com/v2/ws/private` - Private WebSocket
- Channels: ticker, depth, trade, candle, orders, positions

### Gate.io
- `wss://api.gateio.ws/ws/v4/` - WebSocket v4
- Channels: trades, depth, ticker, candlesticks, orders, balances

### KuCoin
- Public: Request token from `/api/v1/bullet-public`
- Private: Request token from `/api/v1/bullet-private`
- Channels: ticker, orderbook, match, snapshot, level2, level3

---

## Rate Limits Summary

| Exchange | Public Endpoints | Private Endpoints | WebSocket |
|----------|-----------------|-------------------|-----------|
| Binance | 2400/min (weight-based) | 1200/min (weight-based) | 300 connections |
| Bitget | 20/sec | 10/sec | 240 subscriptions |
| Gate.io | 900/min | 600/min | 200 subscriptions |
| KuCoin | 2000/min | 600/min | 100 connections |

---

## Recommendations for Enhancement

### 1. Unutilized High-Value Endpoints

#### Binance
- **Liquidation Orders** (`/fapi/v1/allForceOrders`) - Track large liquidations
- **Taker Buy/Sell Volume** (`/futures/data/takerlongshortRatio`) - Market sentiment
- **Basis** (`/futures/data/basis`) - Spot-futures arbitrage opportunities

#### Bitget
- **Copy Trading Analytics** - Leverage social trading data
- **Margin Status** - Track leverage usage across market
- **VIP Fee Rates** - Optimize trading costs

#### Gate.io
- **Options Flow** - Track large options trades
- **Lending Rates** - Monitor capital costs
- **Earn Products** - Track yield opportunities

#### KuCoin
- **HF Trading** - High-frequency trading endpoints for better execution
- **OCO Orders** - One-cancels-other for risk management
- **Isolated Margin** - Better risk isolation

### 2. Data Enhancement Opportunities

1. **Cross-Exchange Arbitrage**
   - Implement real-time price comparison
   - Track transfer costs and times
   - Monitor funding rate differentials

2. **Advanced Market Microstructure**
   - Level 3 order book data (KuCoin)
   - Order flow imbalance
   - Trade clustering analysis

3. **Social & Sentiment Data**
   - Copy trading statistics (Bitget, KuCoin)
   - Top trader positioning (Binance)
   - Liquidation cascades

4. **DeFi Integration**
   - Earn product yields comparison
   - Staking opportunities
   - Lending/borrowing rates

### 3. Implementation Priority

**High Priority:**
- Funding rate tracking across all exchanges
- Liquidation monitoring
- Options flow (Gate.io)
- Copy trading data (Bitget)

**Medium Priority:**
- Margin/lending rates
- Earn product yields
- Level 3 order book data
- HF trading endpoints

**Low Priority:**
- Sub-account management
- Fiat gateway integration
- Historical data downloads

---

## Conclusion

All four exchanges provide comprehensive API coverage for market data, trading, and account management. Our current implementation utilizes approximately 15-20% of available endpoints, focusing primarily on basic market data collection. Significant opportunities exist to enhance data collection, particularly in:

1. **Derivatives Analytics** - Funding rates, open interest, liquidations
2. **Social Trading** - Copy trading data and top trader analysis
3. **Market Microstructure** - Deeper order book analysis and trade flow
4. **Cross-Product Analytics** - Options, margin, and earn products

The infrastructure is well-positioned to expand data collection capabilities based on specific analytical requirements.

---
*Report Generated: September 23, 2025*
*API Versions: Binance (v1/v2), Bitget (v2), Gate.io (v4), KuCoin (v1/v2/v3)*