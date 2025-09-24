"""
Process real swap data from The Graph and calculate accurate PnL
"""

import asyncio
import asyncpg
import aiohttp
import json
from datetime import datetime
from decimal import Decimal

async def fetch_and_store_real_data():
    # Database connection
    db_url = 'postgresql://admin:admin123@postgres:5432/market_analytics'
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=10)

    # The Graph API
    api_key = '2f0225a7557d61520cea73e6ac44083d'
    subgraph_id = 'A1fvJWQLBeUAggX2WQTMm3FKjXTekNXo77ZySun4YN2m'
    url = f'https://gateway.thegraph.com/api/subgraphs/id/{subgraph_id}'

    # Fetch 500 recent swaps
    query = '''
    {
        pool(id: "0x46cf1cf8c69595804ba91dfdd8d6b960c9b0a7c4") {
            swaps(first: 500, orderBy: timestamp, orderDirection: desc) {
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
    '''

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={'query': query}, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get('data') and data['data'].get('pool'):
                    swaps = data['data']['pool'].get('swaps', [])
                    print(f'Fetched {len(swaps)} real swaps from The Graph')

                    # Clear old data
                    async with pool.acquire() as conn:
                        await conn.execute('TRUNCATE wallet_tracking, swap_transactions, smart_money_wallets, wallet_transactions CASCADE')
                        print('Cleared old data')

                    # Process swaps and build trader profiles
                    traders = {}

                    for swap in swaps:
                        origin = swap['origin'].lower()
                        amount0 = float(swap['amount0'])  # USDT
                        amount1 = float(swap['amount1'])  # BTCB
                        amount_usd = abs(float(swap['amountUSD']))
                        timestamp = int(swap['timestamp'])

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
                            async with pool.acquire() as conn:
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
                        except:
                            pass

                    # Calculate PnL for each trader
                    print('\nCalculating PnL for traders...')
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

                        # Store wallet tracking data
                        try:
                            async with pool.acquire() as conn:
                                await conn.execute('''
                                    INSERT INTO wallet_tracking (
                                        wallet_address, label, first_seen, last_activity,
                                        total_volume, profit_loss, win_rate
                                    ) VALUES ($1, $2, to_timestamp($3), to_timestamp($4), $5, $6, $7)
                                ''',
                                    wallet,
                                    'real_trader',
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
                            print(f'Error storing {wallet[:10]}: {e}')

                    print(f'\nStored {stored_count} real trader profiles')

                    # Show summary
                    async with pool.acquire() as conn:
                        stats = await conn.fetchrow('''
                            SELECT
                                COUNT(*) as total_traders,
                                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as profitable,
                                SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing,
                                AVG(win_rate) as avg_win_rate,
                                SUM(total_volume) as total_volume
                            FROM wallet_tracking
                        ''')

                        print('\n=== REAL DATA SUMMARY ===')
                        print(f'Total traders: {stats["total_traders"]}')
                        print(f'Profitable: {stats["profitable"]}')
                        print(f'Losing: {stats["losing"]}')
                        if stats['avg_win_rate']:
                            print(f'Avg win rate: {stats["avg_win_rate"]:.1f}%')
                        if stats['total_volume']:
                            print(f'Total volume: ${stats["total_volume"]:,.0f}')

    await pool.close()

if __name__ == "__main__":
    asyncio.run(fetch_and_store_real_data())