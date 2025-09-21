"""
Market Maker Detection and Analysis Tools
Identifies potential market maker activity through order book patterns
"""

import numpy as np
from typing import Dict, List, Tuple
import asyncpg
from datetime import datetime, timedelta

class MarketMakerDetector:
    """Detect and analyze market maker behavior from order book data"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def analyze_order_patterns(self, symbol: str, exchange: str) -> Dict:
        """
        Analyze order book patterns to identify potential market maker activity
        """
        # Get recent orderbook snapshots
        snapshots = await self.db.fetch("""
            SELECT timestamp, bids::text, asks::text
            FROM orderbook_snapshots
            WHERE symbol = $1 AND exchange = $2
            AND timestamp > NOW() - INTERVAL '30 minutes'
            ORDER BY timestamp DESC
            LIMIT 100
        """, symbol, exchange)

        analysis = {
            'round_number_orders': [],
            'symmetric_orders': [],
            'order_walls': [],
            'spoofing_candidates': [],
            'persistent_levels': [],
            'rapid_changes': []
        }

        for i in range(len(snapshots) - 1):
            current = snapshots[i]
            previous = snapshots[i + 1]

            # Analyze current snapshot
            current_analysis = self._analyze_single_snapshot(
                current['bids'],
                current['asks'],
                current['timestamp']
            )

            # Detect changes between snapshots
            changes = self._detect_rapid_changes(
                current['bids'], current['asks'],
                previous['bids'], previous['asks'],
                current['timestamp'], previous['timestamp']
            )

            # Aggregate results
            for key in current_analysis:
                if current_analysis[key]:
                    analysis[key].extend(current_analysis[key])

            if changes:
                analysis['rapid_changes'].extend(changes)

        # Calculate MM probability score
        analysis['mm_probability_score'] = self._calculate_mm_score(analysis)

        return analysis

    def _analyze_single_snapshot(self, bids_json: str, asks_json: str, timestamp: datetime) -> Dict:
        """Analyze a single orderbook snapshot for MM patterns"""
        import json

        bids = json.loads(bids_json)
        asks = json.loads(asks_json)

        analysis = {
            'round_number_orders': [],
            'symmetric_orders': [],
            'order_walls': [],
            'spoofing_candidates': [],
            'persistent_levels': []
        }

        # 1. Detect Round Number Orders (MMs often place at round prices)
        for bid in bids[:20]:
            price = float(bid[0])
            volume = float(bid[1])
            if price % 10 == 0 or price % 100 == 0:
                analysis['round_number_orders'].append({
                    'side': 'bid',
                    'price': price,
                    'volume': volume,
                    'timestamp': timestamp
                })

        for ask in asks[:20]:
            price = float(ask[0])
            volume = float(ask[1])
            if price % 10 == 0 or price % 100 == 0:
                analysis['round_number_orders'].append({
                    'side': 'ask',
                    'price': price,
                    'volume': volume,
                    'timestamp': timestamp
                })

        # 2. Detect Symmetric Orders (Same volume on both sides)
        bid_volumes = {float(bid[1]): float(bid[0]) for bid in bids[:20]}
        ask_volumes = {float(ask[1]): float(ask[0]) for ask in asks[:20]}

        for volume in bid_volumes:
            if volume in ask_volumes:
                # Found same volume on both sides
                analysis['symmetric_orders'].append({
                    'volume': volume,
                    'bid_price': bid_volumes[volume],
                    'ask_price': ask_volumes[volume],
                    'spread': ask_volumes[volume] - bid_volumes[volume],
                    'timestamp': timestamp
                })

        # 3. Detect Order Walls (Large orders that might be fake)
        avg_volume = np.mean([float(bid[1]) for bid in bids[:10]] +
                            [float(ask[1]) for ask in asks[:10]])

        for bid in bids[:20]:
            volume = float(bid[1])
            if volume > avg_volume * 5:  # 5x average = potential wall
                analysis['order_walls'].append({
                    'side': 'bid',
                    'price': float(bid[0]),
                    'volume': volume,
                    'volume_ratio': volume / avg_volume,
                    'timestamp': timestamp
                })

        for ask in asks[:20]:
            volume = float(ask[1])
            if volume > avg_volume * 5:
                analysis['order_walls'].append({
                    'side': 'ask',
                    'price': float(ask[0]),
                    'volume': volume,
                    'volume_ratio': volume / avg_volume,
                    'timestamp': timestamp
                })

        return analysis

    def _detect_rapid_changes(self, bids1: str, asks1: str, bids2: str, asks2: str,
                              time1: datetime, time2: datetime) -> List[Dict]:
        """Detect rapid order changes (potential spoofing)"""
        import json

        changes = []
        time_diff = (time1 - time2).total_seconds()

        if time_diff > 0:
            bids1_dict = {b[0]: float(b[1]) for b in json.loads(bids1)[:20]}
            bids2_dict = {b[0]: float(b[1]) for b in json.loads(bids2)[:20]}

            # Find orders that appeared and disappeared quickly
            for price, volume in bids2_dict.items():
                if price not in bids1_dict and volume > 1:  # Large order disappeared
                    changes.append({
                        'type': 'disappeared_order',
                        'side': 'bid',
                        'price': float(price),
                        'volume': volume,
                        'duration_seconds': time_diff
                    })

        return changes

    def _calculate_mm_score(self, analysis: Dict) -> float:
        """Calculate probability score of market maker presence (0-100)"""
        score = 0

        # Round number orders (common MM pattern)
        if len(analysis['round_number_orders']) > 5:
            score += 20

        # Symmetric orders (very strong MM indicator)
        if len(analysis['symmetric_orders']) > 3:
            score += 30

        # Order walls (possible MM or whale)
        if len(analysis['order_walls']) > 0:
            score += 15

        # Rapid changes (possible spoofing)
        if len(analysis['rapid_changes']) > 10:
            score += 20

        # Persistent levels (MM maintaining quotes)
        if len(analysis['persistent_levels']) > 5:
            score += 15

        return min(score, 100)


class OrderFlowAnalyzer:
    """Analyze order flow to identify market maker strategies"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def analyze_trade_patterns(self, symbol: str, exchange: str) -> Dict:
        """Analyze trade patterns to identify MM behavior"""

        trades = await self.db.fetch("""
            SELECT timestamp, price, quantity, side
            FROM trades
            WHERE symbol = $1 AND exchange = $2
            AND timestamp > NOW() - INTERVAL '1 hour'
            ORDER BY timestamp DESC
        """, symbol, exchange)

        analysis = {
            'ping_pong_trades': [],  # Buy and sell at similar prices repeatedly
            'size_patterns': [],      # Consistent trade sizes (MM signature)
            'time_patterns': [],      # Regular time intervals
            'price_improvement': []   # Trades inside the spread
        }

        # Detect ping-pong trading (MM recycling inventory)
        for i in range(len(trades) - 10):
            window = trades[i:i+10]
            buys = [t for t in window if t['side'] == 'buy']
            sells = [t for t in window if t['side'] == 'sell']

            if len(buys) > 3 and len(sells) > 3:
                avg_buy_price = np.mean([float(b['price']) for b in buys])
                avg_sell_price = np.mean([float(s['price']) for s in sells])

                if abs(avg_buy_price - avg_sell_price) / avg_buy_price < 0.001:  # 0.1% difference
                    analysis['ping_pong_trades'].append({
                        'timestamp': window[0]['timestamp'],
                        'avg_buy_price': avg_buy_price,
                        'avg_sell_price': avg_sell_price,
                        'trade_count': len(window)
                    })

        # Detect consistent trade sizes (MM signature)
        trade_sizes = [float(t['quantity']) for t in trades]
        size_counts = {}
        for size in trade_sizes:
            rounded_size = round(size, 4)
            size_counts[rounded_size] = size_counts.get(rounded_size, 0) + 1

        # Find sizes that appear frequently
        for size, count in size_counts.items():
            if count > 5:  # Same size appears >5 times
                analysis['size_patterns'].append({
                    'size': size,
                    'frequency': count,
                    'percentage': (count / len(trades)) * 100
                })

        return analysis


class LiquidityProfiler:
    """Profile liquidity provision patterns"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def calculate_liquidity_metrics(self, symbol: str, exchange: str) -> Dict:
        """Calculate detailed liquidity metrics"""

        # Get recent orderbook data
        orderbooks = await self.db.fetch("""
            SELECT timestamp, bids::text, asks::text
            FROM orderbook_snapshots
            WHERE symbol = $1 AND exchange = $2
            AND timestamp > NOW() - INTERVAL '1 hour'
            ORDER BY timestamp DESC
        """, symbol, exchange)

        metrics = {
            'avg_spread_bps': 0,
            'spread_volatility': 0,
            'bid_depth_levels': {},  # Depth at 0.1%, 0.5%, 1%, 2%
            'ask_depth_levels': {},
            'order_book_imbalance': [],
            'liquidity_score': 0,
            'quote_stability': 0
        }

        spreads = []
        imbalances = []

        for ob in orderbooks:
            import json
            bids = json.loads(ob['bids'])
            asks = json.loads(ob['asks'])

            if bids and asks:
                # Calculate spread
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                spread_bps = ((best_ask - best_bid) / best_bid) * 10000
                spreads.append(spread_bps)

                # Calculate imbalance
                total_bid_volume = sum(float(b[1]) for b in bids[:20])
                total_ask_volume = sum(float(a[1]) for a in asks[:20])

                if total_bid_volume + total_ask_volume > 0:
                    imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
                    imbalances.append(imbalance)

                # Calculate depth at price levels
                mid_price = (best_bid + best_ask) / 2

                for level_name, level_pct in [('0.1%', 0.001), ('0.5%', 0.005), ('1%', 0.01), ('2%', 0.02)]:
                    bid_depth = sum(float(b[1]) for b in bids
                                  if float(b[0]) >= mid_price * (1 - level_pct))
                    ask_depth = sum(float(a[1]) for a in asks
                                  if float(a[0]) <= mid_price * (1 + level_pct))

                    if level_name not in metrics['bid_depth_levels']:
                        metrics['bid_depth_levels'][level_name] = []
                        metrics['ask_depth_levels'][level_name] = []

                    metrics['bid_depth_levels'][level_name].append(bid_depth)
                    metrics['ask_depth_levels'][level_name].append(ask_depth)

        # Calculate summary metrics
        if spreads:
            metrics['avg_spread_bps'] = np.mean(spreads)
            metrics['spread_volatility'] = np.std(spreads)

        if imbalances:
            metrics['order_book_imbalance'] = {
                'mean': np.mean(imbalances),
                'std': np.std(imbalances),
                'current': imbalances[0] if imbalances else 0
            }

        # Average depth at each level
        for level in metrics['bid_depth_levels']:
            metrics['bid_depth_levels'][level] = np.mean(metrics['bid_depth_levels'][level])
            metrics['ask_depth_levels'][level] = np.mean(metrics['ask_depth_levels'][level])

        # Calculate liquidity score (0-100)
        liquidity_score = 0
        if metrics['avg_spread_bps'] < 10:
            liquidity_score += 30
        if metrics['spread_volatility'] < 5:
            liquidity_score += 20
        if metrics['bid_depth_levels'].get('1%', 0) > 10:
            liquidity_score += 25
        if abs(metrics['order_book_imbalance'].get('mean', 1)) < 0.2:
            liquidity_score += 25

        metrics['liquidity_score'] = liquidity_score

        return metrics


# API endpoint additions for main.py
async def get_mm_analysis(symbol: str, exchange: str, db_pool):
    """Get comprehensive market maker analysis"""

    detector = MarketMakerDetector(db_pool)
    flow_analyzer = OrderFlowAnalyzer(db_pool)
    profiler = LiquidityProfiler(db_pool)

    analysis = {
        'timestamp': datetime.utcnow(),
        'symbol': symbol,
        'exchange': exchange,
        'pattern_analysis': await detector.analyze_order_patterns(symbol, exchange),
        'trade_flow': await flow_analyzer.analyze_trade_patterns(symbol, exchange),
        'liquidity_profile': await profiler.calculate_liquidity_metrics(symbol, exchange)
    }

    return analysis