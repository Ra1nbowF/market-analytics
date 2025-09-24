#!/usr/bin/env python3
"""
Update trader data every 5 minutes from The Graph
"""

import asyncio
import asyncpg
import aiohttp
from datetime import datetime, timedelta
import time

async def fetch_and_update():
    db_url = 'postgresql://admin:admin123@postgres:5432/market_analytics'
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=10)

    # First run - clear old data
    async with pool.acquire() as conn:
        await conn.execute('TRUNCATE wallet_tracking, swap_transactions, smart_money_wallets CASCADE')
        print('Cleared old data')

    api_key = '2f0225a7557d61520cea73e6ac44083d'
    subgraph_id = 'A1fvJWQLBeUAggX2WQTMm3FKjXTekNXo77ZySun4YN2m'
    url = f'https://gateway.thegraph.com/api/subgraphs/id/{subgraph_id}'

    while True:
        print(f'\n[{datetime.now()}] Fetching latest swaps...')

        query = '''
        {
            pool(id: "0x46cf1cf8c69595804ba91dfdd8d6b960c9b0a7c4") {
                swaps(first: 500, orderBy: timestamp, orderDirection: desc) {
                    id
                    timestamp
                    origin
                    amount0
                    amount1
                    amountUSD
                }
            }
        }
        '''

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={'query': query}, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('data') and data['data'].get('pool'):
                        swaps = data['data']['pool'].get('swaps', [])
                        print(f'Processing {len(swaps)} swaps')

                        new_count = 0
                        for swap in swaps:
                            origin = swap['origin'].lower()
                            timestamp = int(swap['timestamp'])
                            amount_usd = abs(float(swap['amountUSD']))
                            amount0 = float(swap['amount0'])
                            amount1 = float(swap['amount1'])

                            trade_type = 'buy' if amount0 > 0 else 'sell'

                            async with pool.acquire() as conn:
                                result = await conn.execute('''
                                    INSERT INTO swap_transactions (
                                        pair_address, tx_hash, exchange, symbol,
                                        timestamp, trader_address, amount_usd,
                                        transaction_type, sender_address, amount0, amount1
                                    ) VALUES ($1, $2, $3, $4, to_timestamp($5), $6, $7, $8, $9, $10, $11)
                                    ON CONFLICT (tx_hash) DO NOTHING
                                ''',
                                    '0x46cf1cf8c69595804ba91dfdd8d6b960c9b0a7c4',
                                    swap['id'], 'pancakeswap', 'BTCUSDT',
                                    timestamp, origin, amount_usd, trade_type, origin,
                                    abs(amount0), abs(amount1)
                                )
                                if result.split()[-1] == '1':
                                    new_count += 1

                        print(f'Added {new_count} new swaps')

                        # Update trader profiles
                        await conn.execute('''
                            INSERT INTO wallet_tracking (wallet_address, label, first_seen, last_activity, total_volume, profit_loss, win_rate)
                            SELECT
                                trader_address,
                                'trader',
                                MIN(timestamp),
                                MAX(timestamp),
                                SUM(amount_usd),
                                0,
                                50
                            FROM swap_transactions
                            GROUP BY trader_address
                            ON CONFLICT (wallet_address) DO UPDATE SET
                                last_activity = EXCLUDED.last_activity,
                                total_volume = EXCLUDED.total_volume
                        ''')

                        # Summary
                        stats = await conn.fetchrow('''
                            SELECT
                                COUNT(DISTINCT trader_address) as traders,
                                COUNT(*) as total_swaps
                            FROM swap_transactions
                        ''')

                        print(f'Total: {stats["traders"]} traders, {stats["total_swaps"]} swaps')

        print('Waiting 5 minutes...')
        await asyncio.sleep(300)

if __name__ == '__main__':
    asyncio.run(fetch_and_update())