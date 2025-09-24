"""
Trader Analytics and Profiling System
Uses The Graph API and on-chain data to track and analyze trader behavior
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import os
import json

logger = logging.getLogger(__name__)

class TraderAnalytics:
    """Analyzes trader behavior and calculates PnL from on-chain data"""

    def __init__(self):
        # The Graph Configuration
        self.graph_api_key = os.getenv('GRAPH_API_KEY', '2f0225a7557d61520cea73e6ac44083d')
        self.graph_base_url = os.getenv('GRAPH_BASE_URL', 'https://gateway.thegraph.com/api')
        self.graph_subgraph_id = os.getenv('GRAPH_SUBGRAPH_ID', 'A1fvJWQLBeUAggX2WQTMm3FKjXTekNXo77ZySun4YN2m')
        self.subgraph_url = f"{self.graph_base_url}/subgraphs/id/{self.graph_subgraph_id}"

        # Pool configuration
        self.pair_address = os.getenv('PANCAKE_PAIR_ADDRESS', '0x46cf1cf8c69595804ba91dfdd8d6b960c9b0a7c4').lower()
        self.btcb_address = os.getenv('BTCB_TOKEN_ADDRESS', '0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c').lower()
        self.usdt_address = os.getenv('USDT_TOKEN_ADDRESS', '0x55d398326f99059fF775485246999027B3197955').lower()

        self.session = None

    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

    async def fetch_recent_swaps(self, hours: int = 24, limit: int = 1000) -> List[Dict]:
        """Fetch recent swap transactions from The Graph"""
        try:
            if not self.session:
                await self.initialize()

            # Calculate timestamp for time filter
            timestamp_gte = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())

            query = '''
            {
                pool(id: "%s") {
                    swaps(
                        first: %d,
                        orderBy: timestamp,
                        orderDirection: desc
                    ) {
                        id
                        transaction {
                            id
                            blockNumber
                            gasUsed
                            gasPrice
                        }
                        timestamp
                        sender
                        recipient
                        origin
                        amount0
                        amount1
                        amountUSD
                        sqrtPriceX96
                        tick
                        logIndex
                    }
                }
            }
            ''' % (self.pair_address, limit)

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.graph_api_key}'
            }

            async with self.session.post(
                self.subgraph_url,
                json={"query": query},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('data') and data['data'].get('pool'):
                        swaps = data['data']['pool'].get('swaps', [])
                        logger.info(f"Fetched {len(swaps)} swaps from last {hours} hours")
                        return swaps

            return []
        except Exception as e:
            logger.error(f"Error fetching swaps: {e}")
            return []

    async def fetch_trader_history(self, wallet_address: str, days: int = 30) -> List[Dict]:
        """Fetch complete trading history for a specific wallet"""
        try:
            if not self.session:
                await self.initialize()

            timestamp_gte = int((datetime.utcnow() - timedelta(days=days)).timestamp())

            query = '''
            {
                swaps(
                    first: 1000,
                    orderBy: timestamp,
                    orderDirection: desc,
                    where: {
                        pool: "%s",
                        origin: "%s",
                        timestamp_gte: %d
                    }
                ) {
                    id
                    timestamp
                    amount0
                    amount1
                    amountUSD
                    sqrtPriceX96
                    tick
                    transaction {
                        blockNumber
                        gasUsed
                        gasPrice
                    }
                }
            }
            ''' % (self.pair_address, wallet_address.lower(), timestamp_gte)

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.graph_api_key}'
            }

            async with self.session.post(
                self.subgraph_url,
                json={"query": query},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('data') and data['data'].get('swaps'):
                        return data['data']['swaps']

            return []
        except Exception as e:
            logger.error(f"Error fetching trader history for {wallet_address}: {e}")
            return []

    def analyze_swap(self, swap: Dict) -> Dict:
        """Analyze a single swap transaction"""
        try:
            amount0 = float(swap.get('amount0', 0))
            amount1 = float(swap.get('amount1', 0))
            amount_usd = float(swap.get('amountUSD', 0))

            # Determine trade direction
            # amount0 negative = token0 going out (selling token0)
            # amount1 negative = token1 going out (selling token1)

            # For BTCB/USDT pair:
            # Token0 = USDT, Token1 = BTCB

            if amount1 < 0:  # Selling BTCB
                trade_type = 'sell'
                btc_amount = abs(amount1)
                usdt_amount = abs(amount0)
                price = usdt_amount / btc_amount if btc_amount > 0 else 0
            else:  # Buying BTCB
                trade_type = 'buy'
                btc_amount = abs(amount1)
                usdt_amount = abs(amount0)
                price = usdt_amount / btc_amount if btc_amount > 0 else 0

            return {
                'timestamp': int(swap.get('timestamp', 0)),
                'trade_type': trade_type,
                'btc_amount': btc_amount,
                'usdt_amount': usdt_amount,
                'amount_usd': amount_usd,
                'price': price,
                'tx_hash': swap.get('id', '').split('#')[0] if swap.get('id') else '',
                'wallet': swap.get('origin', '').lower()
            }
        except Exception as e:
            logger.error(f"Error analyzing swap: {e}")
            return {}

    def calculate_trader_pnl(self, trades: List[Dict]) -> Dict:
        """Calculate PnL for a trader based on their trades"""
        try:
            if not trades:
                return {}

            # Sort trades by timestamp
            sorted_trades = sorted(trades, key=lambda x: x['timestamp'])

            # Track position
            btc_position = 0
            total_cost_basis = 0
            realized_pnl = 0
            total_volume = 0
            buy_count = 0
            sell_count = 0

            trade_details = []

            for trade in sorted_trades:
                total_volume += trade['amount_usd']

                if trade['trade_type'] == 'buy':
                    # Buying BTC
                    btc_position += trade['btc_amount']
                    total_cost_basis += trade['usdt_amount']
                    buy_count += 1

                    trade_details.append({
                        'type': 'buy',
                        'timestamp': trade['timestamp'],
                        'btc_amount': trade['btc_amount'],
                        'price': trade['price'],
                        'cost': trade['usdt_amount']
                    })

                elif trade['trade_type'] == 'sell':
                    # Selling BTC
                    if btc_position > 0:
                        # Calculate average cost basis
                        avg_cost = total_cost_basis / btc_position if btc_position > 0 else 0

                        # Calculate profit/loss on this sale
                        sell_amount = min(trade['btc_amount'], btc_position)
                        cost_of_sold = avg_cost * sell_amount
                        revenue = trade['price'] * sell_amount
                        profit = revenue - cost_of_sold

                        realized_pnl += profit

                        # Update position
                        btc_position -= sell_amount
                        total_cost_basis -= cost_of_sold

                        trade_details.append({
                            'type': 'sell',
                            'timestamp': trade['timestamp'],
                            'btc_amount': sell_amount,
                            'price': trade['price'],
                            'revenue': revenue,
                            'profit': profit
                        })

                    sell_count += 1

            # Calculate unrealized PnL (mark-to-market)
            current_price = sorted_trades[-1]['price'] if sorted_trades else 0
            unrealized_pnl = (current_price * btc_position) - total_cost_basis if btc_position > 0 else 0

            # Calculate metrics
            total_pnl = realized_pnl + unrealized_pnl
            win_rate = (len([t for t in trade_details if t.get('profit', 0) > 0]) /
                       len([t for t in trade_details if 'profit' in t])) * 100 if sell_count > 0 else 0

            return {
                'wallet': trades[0]['wallet'] if trades else '',
                'total_trades': len(trades),
                'buy_count': buy_count,
                'sell_count': sell_count,
                'total_volume': total_volume,
                'current_position': btc_position,
                'realized_pnl': realized_pnl,
                'unrealized_pnl': unrealized_pnl,
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'avg_trade_size': total_volume / len(trades) if trades else 0,
                'first_trade': datetime.fromtimestamp(sorted_trades[0]['timestamp']),
                'last_trade': datetime.fromtimestamp(sorted_trades[-1]['timestamp']),
                'trade_details': trade_details[:10]  # Keep last 10 trades for detail
            }
        except Exception as e:
            logger.error(f"Error calculating PnL: {e}")
            return {}

    async def identify_top_traders(self, hours: int = 24, min_trades: int = 5) -> List[Dict]:
        """Identify top performing traders in recent period"""
        try:
            # Fetch recent swaps
            swaps = await self.fetch_recent_swaps(hours=hours)

            if not swaps:
                logger.warning("No swaps found")
                return []

            # Group swaps by trader
            traders = {}
            for swap in swaps:
                analyzed = self.analyze_swap(swap)
                if analyzed and analyzed.get('wallet'):
                    wallet = analyzed['wallet']
                    if wallet not in traders:
                        traders[wallet] = []
                    traders[wallet].append(analyzed)

            # Calculate PnL for each trader
            trader_stats = []
            for wallet, trades in traders.items():
                if len(trades) >= min_trades:
                    pnl_data = self.calculate_trader_pnl(trades)
                    if pnl_data:
                        trader_stats.append(pnl_data)

            # Sort by total PnL
            trader_stats.sort(key=lambda x: x['total_pnl'], reverse=True)

            logger.info(f"Analyzed {len(trader_stats)} traders with {min_trades}+ trades")

            return trader_stats[:20]  # Return top 20

        except Exception as e:
            logger.error(f"Error identifying top traders: {e}")
            return []

    async def analyze_smart_money(self) -> List[Dict]:
        """Identify smart money wallets based on trading patterns"""
        try:
            # Get top traders from last 7 days
            top_traders = await self.identify_top_traders(hours=168, min_trades=10)

            smart_money = []
            for trader in top_traders:
                # Smart money criteria:
                # 1. Positive PnL
                # 2. Win rate > 60%
                # 3. More than 10 trades
                # 4. Average trade size > $10k

                if (trader['total_pnl'] > 1000 and
                    trader['win_rate'] > 60 and
                    trader['total_trades'] > 10 and
                    trader['avg_trade_size'] > 10000):

                    # Get detailed history for smart money wallet
                    history = await self.fetch_trader_history(trader['wallet'], days=30)

                    smart_money.append({
                        'wallet': trader['wallet'],
                        'reputation_score': min(100, trader['win_rate'] * 1.2),
                        'total_profit': trader['total_pnl'],
                        'success_rate': trader['win_rate'],
                        'total_volume': trader['total_volume'],
                        'trade_count': trader['total_trades'],
                        'avg_trade_size': trader['avg_trade_size'],
                        'last_activity': trader['last_trade'],
                        'trading_style': 'high_frequency' if trader['total_trades'] > 50 else 'swing_trader'
                    })

            logger.info(f"Identified {len(smart_money)} smart money wallets")
            return smart_money

        except Exception as e:
            logger.error(f"Error analyzing smart money: {e}")
            return []

    async def store_trader_data(self, db_pool, trader_data: Dict) -> bool:
        """Store trader analytics in database"""
        try:
            async with db_pool.acquire() as conn:
                # Update wallet_tracking table
                await conn.execute("""
                    INSERT INTO wallet_tracking (
                        wallet_address, label, first_seen, last_activity,
                        total_volume, profit_loss, win_rate, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (wallet_address) DO UPDATE SET
                        last_activity = EXCLUDED.last_activity,
                        total_volume = EXCLUDED.total_volume,
                        profit_loss = EXCLUDED.profit_loss,
                        win_rate = EXCLUDED.win_rate,
                        metadata = EXCLUDED.metadata
                """,
                    trader_data['wallet'],
                    'active_trader',
                    trader_data['first_trade'],
                    trader_data['last_trade'],
                    trader_data['total_volume'],
                    trader_data['total_pnl'],
                    trader_data['win_rate'],
                    json.dumps({
                        'buy_count': trader_data['buy_count'],
                        'sell_count': trader_data['sell_count'],
                        'current_position': float(trader_data['current_position']),
                        'realized_pnl': float(trader_data['realized_pnl']),
                        'unrealized_pnl': float(trader_data['unrealized_pnl'])
                    })
                )

            return True
        except Exception as e:
            logger.error(f"Error storing trader data: {e}")
            return False

    async def run_analysis(self, db_pool):
        """Run complete trader analysis pipeline"""
        try:
            logger.info("Starting trader analysis...")

            # Get top traders
            top_traders = await self.identify_top_traders(hours=24, min_trades=3)

            # Store trader data
            for trader in top_traders[:50]:  # Store top 50
                await self.store_trader_data(db_pool, trader)

            # Analyze smart money
            smart_money = await self.analyze_smart_money()

            # Store smart money wallets
            if smart_money:
                async with db_pool.acquire() as conn:
                    for wallet_data in smart_money:
                        await conn.execute("""
                            INSERT INTO smart_money_wallets (
                                wallet_address, reputation_score, total_profit,
                                success_rate, avg_roi, tokens_traded,
                                profitable_trades, loss_trades, last_updated
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            ON CONFLICT (wallet_address) DO UPDATE SET
                                reputation_score = EXCLUDED.reputation_score,
                                total_profit = EXCLUDED.total_profit,
                                success_rate = EXCLUDED.success_rate,
                                last_updated = EXCLUDED.last_updated
                        """,
                            wallet_data['wallet'],
                            wallet_data['reputation_score'],
                            wallet_data['total_profit'],
                            wallet_data['success_rate'],
                            wallet_data['total_profit'] / wallet_data['total_volume'] * 100 if wallet_data['total_volume'] > 0 else 0,
                            1,  # Only tracking BTCB for now
                            int(wallet_data['trade_count'] * wallet_data['success_rate'] / 100),
                            int(wallet_data['trade_count'] * (100 - wallet_data['success_rate']) / 100),
                            datetime.utcnow()
                        )

            logger.info(f"Analysis complete. Processed {len(top_traders)} traders, {len(smart_money)} smart money wallets")

        except Exception as e:
            logger.error(f"Error in analysis pipeline: {e}")