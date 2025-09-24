"""
Real-time trader tracking with 5-minute updates
Fetches last 24 hours of data and updates every 5 minutes
"""

import asyncio
import asyncpg
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealTimeTracker:
    def __init__(self):
        self.db_url = 'postgresql://admin:admin123@postgres:5432/market_analytics'
        self.api_key = '2f0225a7557d61520cea73e6ac44083d'
        self.subgraph_id = 'A1fvJWQLBeUAggX2WQTMm3FKjXTekNXo77ZySun4YN2m'
        self.url = f'https://gateway.thegraph.com/api/subgraphs/id/{self.subgraph_id}'
        self.pool = None
        self.last_processed_timestamp = 0

    async def initialize(self):
        self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=10)
        logger.info("Database pool initialized")

    async def clear_old_data(self):
        """Clear data older than 24 hours"""
        async with self.pool.acquire() as conn:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            # Delete old swap transactions
            await conn.execute("""
                DELETE FROM swap_transactions 
                WHERE timestamp < $1
            """, cutoff_time)
            
            # Update wallet tracking to remove old entries
            await conn.execute("""
                DELETE FROM wallet_tracking 
                WHERE last_activity < $1
            """, cutoff_time)
            
            logger.info(f"Cleared data older than {cutoff_time}")

    async def fetch_recent_swaps(self, hours=24):
        """Fetch swaps from last N hours"""
        # Calculate timestamp for 24 hours ago
        timestamp_gte = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
        
        query = '''
        {
            pool(id: "0x46cf1cf8c69595804ba91dfdd8d6b960c9b0a7c4") {
                swaps(
                    first: 1000,
                    orderBy: timestamp,
                    orderDirection: desc,
                    where: { timestamp_gte: %d }
                ) {
                    id
                    transaction {
                        id
                        blockNumber
                    }
                    timestamp
                    origin
                    amount0
                    amount1
                    amountUSD
                    sqrtPriceX96
                    tick
                }
            }
        }
        ''' % timestamp_gte

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json={'query': query}, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('data') and data['data'].get('pool'):
                        swaps = data['data']['pool'].get('swaps', [])
                        logger.info(f'Fetched {len(swaps)} swaps from last {hours} hours')
                        return swaps
        return []

    async def process_swaps(self, swaps):
        """Process swaps and calculate trader PnL"""
        traders = {}
        new_swaps = 0

        for swap in swaps:
            timestamp = int(swap['timestamp'])
            
            # Skip if already processed
            if timestamp <= self.last_processed_timestamp:
                continue
                
            new_swaps += 1
            origin = swap['origin'].lower()
            amount0 = float(swap['amount0'])  # USDT
            amount1 = float(swap['amount1'])  # BTCB
            amount_usd = abs(float(swap['amountUSD']))

            # Determine trade type
            if amount0 > 0:  # USDT in = buying BTCB
                trade_type = 'buy'
                btcb_amount = abs(amount1)
                usdt_amount = abs(amount0)
            else:  # USDT out = selling BTCB
                trade_type = 'sell'
                btcb_amount = abs(amount1)
                usdt_amount = abs(amount0)

            price = usdt_amount / btcb_amount if btcb_amount > 0 else 0

            # Track trader data
            if origin not in traders:
                traders[origin] = {
                    'trades': [],
                    'btcb_balance': 0,
                    'total_spent': 0,
                    'total_received': 0,
                    'first_trade': timestamp,
                    'last_trade': timestamp
                }

            traders[origin]['trades'].append({
                'type': trade_type,
                'btcb': btcb_amount,
                'usdt': usdt_amount,
                'price': price,
                'timestamp': timestamp,
                'tx_hash': swap['id']
            })

            traders[origin]['last_trade'] = max(traders[origin]['last_trade'], timestamp)
            traders[origin]['first_trade'] = min(traders[origin]['first_trade'], timestamp)

            # Store swap transaction
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO swap_transactions (
                            pair_address, tx_hash, exchange, symbol,
                            timestamp, trader_address, amount_usd,
                            transaction_type, sender_address, amount0, amount1
                        ) VALUES ($1, $2, $3, $4, to_timestamp($5), $6, $7, $8, $9, $10, $11)
                        ON CONFLICT (tx_hash) DO NOTHING
                    ''',
                        '0x46cf1cf8c69595804ba91dfdd8d6b960c9b0a7c4',
                        swap['id'],
                        'pancakeswap',
                        'BTCUSDT',
                        timestamp,
                        origin,
                        amount_usd,
                        trade_type,
                        origin,
                        usdt_amount,
                        btcb_amount
                    )
            except Exception as e:
                logger.error(f"Error storing swap: {e}")

        # Update last processed timestamp
        if swaps:
            self.last_processed_timestamp = max(int(s['timestamp']) for s in swaps)

        logger.info(f"Processed {new_swaps} new swaps")
        return traders, new_swaps

    async def calculate_and_store_pnl(self, traders):
        """Calculate PnL for traders and store in database"""
        stored_count = 0

        for wallet, data in traders.items():
            trades = sorted(data['trades'], key=lambda x: x['timestamp'])

            btcb_position = 0
            cost_basis = 0
            realized_pnl = 0
            total_volume = 0
            buy_count = 0
            sell_count = 0
            profitable_trades = 0

            for trade in trades:
                total_volume += trade['usdt']

                if trade['type'] == 'buy':
                    btcb_position += trade['btcb']
                    cost_basis += trade['usdt']
                    buy_count += 1
                else:  # sell
                    if btcb_position > 0:
                        avg_buy_price = cost_basis / btcb_position
                        sell_revenue = trade['usdt']
                        sell_cost = avg_buy_price * min(trade['btcb'], btcb_position)
                        profit = sell_revenue - sell_cost
                        realized_pnl += profit
                        if profit > 0:
                            profitable_trades += 1

                        # Update position
                        sold_amount = min(trade['btcb'], btcb_position)
                        btcb_position -= sold_amount
                        cost_basis -= sell_cost
                    sell_count += 1

            # Calculate unrealized PnL
            if trades:
                current_price = trades[-1]['price']
                unrealized_pnl = (btcb_position * current_price) - cost_basis if btcb_position > 0 else 0
                total_pnl = realized_pnl + unrealized_pnl
            else:
                total_pnl = 0
                unrealized_pnl = 0

            win_rate = (profitable_trades / sell_count * 100) if sell_count > 0 else 0

            # Store or update wallet tracking data
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO wallet_tracking (
                            wallet_address, label, first_seen, last_activity,
                            total_volume, profit_loss, win_rate
                        ) VALUES ($1, $2, to_timestamp($3), to_timestamp($4), $5, $6, $7)
                        ON CONFLICT (wallet_address) DO UPDATE SET
                            last_activity = EXCLUDED.last_activity,
                            total_volume = wallet_tracking.total_volume + EXCLUDED.total_volume,
                            profit_loss = EXCLUDED.profit_loss,
                            win_rate = EXCLUDED.win_rate
                    ''',
                        wallet,
                        'active_trader',
                        data['first_trade'],
                        data['last_trade'],
                        total_volume,
                        total_pnl,
                        win_rate
                    )
                    stored_count += 1

                    # Add to smart money if profitable
                    if total_pnl > 1000 and win_rate > 50 and total_volume > 50000:
                        await conn.execute('''
                            INSERT INTO smart_money_wallets (
                                wallet_address, reputation_score, total_profit,
                                success_rate, avg_roi, tokens_traded,
                                profitable_trades, loss_trades, last_updated
                            ) VALUES ($1, $2, $3, $4, $5, 1, $6, $7, NOW())
                            ON CONFLICT (wallet_address) DO UPDATE SET
                                reputation_score = EXCLUDED.reputation_score,
                                total_profit = EXCLUDED.total_profit,
                                success_rate = EXCLUDED.success_rate,
                                last_updated = NOW()
                        ''',
                            wallet,
                            min(100, win_rate * 1.1),
                            total_pnl,
                            win_rate,
                            (total_pnl / total_volume * 100) if total_volume > 0 else 0,
                            profitable_trades,
                            sell_count - profitable_trades
                        )
            except Exception as e:
                logger.error(f'Error storing wallet {wallet[:10]}: {e}')

        return stored_count

    async def run_update_cycle(self):
        """Run a single update cycle"""
        try:
            # Fetch recent swaps (last 24 hours)
            swaps = await self.fetch_recent_swaps(hours=24)
            
            if not swaps:
                logger.info("No swaps found in last 24 hours")
                return
            
            # Process swaps
            traders, new_swaps = await self.process_swaps(swaps)
            
            if new_swaps > 0:
                # Calculate and store PnL
                stored = await self.calculate_and_store_pnl(traders)
                logger.info(f"Updated {stored} trader profiles")
            else:
                logger.info("No new swaps to process")
            
            # Clean old data
            await self.clear_old_data()
            
            # Show summary
            async with self.pool.acquire() as conn:
                stats = await conn.fetchrow('''
                    SELECT
                        COUNT(DISTINCT wallet_address) as total_traders,
                        COUNT(DISTINCT CASE WHEN profit_loss > 0 THEN wallet_address END) as profitable,
                        COUNT(DISTINCT CASE WHEN profit_loss < 0 THEN wallet_address END) as losing,
                        AVG(win_rate) as avg_win_rate,
                        SUM(total_volume) as total_volume,
                        COUNT(DISTINCT tx_hash) as total_swaps
                    FROM wallet_tracking wt
                    LEFT JOIN swap_transactions st ON wt.wallet_address = st.trader_address
                    WHERE wt.last_activity > NOW() - INTERVAL '24 hours'
                ''')
                
                logger.info('=== 24 HOUR SUMMARY ===')
                logger.info(f'Active traders: {stats["total_traders"]}')
                logger.info(f'Profitable: {stats["profitable"]}')
                logger.info(f'Losing: {stats["losing"]}')
                if stats['avg_win_rate']:
                    logger.info(f'Avg win rate: {stats["avg_win_rate"]:.1f}%')
                if stats['total_volume']:
                    logger.info(f'Total volume: ${stats["total_volume"]:,.0f}')
                if stats['total_swaps']:
                    logger.info(f'Total swaps: {stats["total_swaps"]}')
                    
        except Exception as e:
            logger.error(f"Error in update cycle: {e}")

    async def run_forever(self):
        """Run continuous updates every 5 minutes"""
        await self.initialize()
        
        # Initial data clear and fetch
        logger.info("Starting real-time tracker - clearing old data and fetching last 24 hours")
        async with self.pool.acquire() as conn:
            await conn.execute('TRUNCATE wallet_tracking, swap_transactions, smart_money_wallets, wallet_transactions CASCADE')
            logger.info('Cleared all old data')
        
        while True:
            try:
                logger.info(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running update cycle...")
                await self.run_update_cycle()
                
                # Wait 5 minutes before next update
                logger.info("Waiting 5 minutes until next update...")
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def cleanup(self):
        if self.pool:
            await self.pool.close()

async def main():
    tracker = RealTimeTracker()
    try:
        await tracker.run_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        await tracker.cleanup()

if __name__ == "__main__":
    asyncio.run(main())