#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestAnalysisServiceCritical(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        self.db = DatabaseService(self.temp_db.name)
        self.strategy_service = StrategyService(self.db)
        self.trading = TradingService(self.db)
        self.analysis = AnalysisService(self.db)

        ok, _ = self.strategy_service.create_strategy('评分策略', '用于评分关键路径测试')
        self.assertTrue(ok or '已存在' in _)
        self.sid = next(s['id'] for s in self.strategy_service.get_all_strategies() if s['name'] == '评分策略')

    def test_profit_factor_and_closed_only(self):
        # 未平仓，不应计入
        ok, tid_open = self.trading.add_buy_transaction(self.sid, 'PF001', '仅开仓', Decimal('10.00'), 100, '2025-01-01')
        self.assertTrue(ok)

        # 有盈利的平仓
        ok, tid_win = self.trading.add_buy_transaction(self.sid, 'PF002', '盈利股', Decimal('10.00'), 100, '2025-01-01')
        self.assertTrue(ok)
        self.trading.add_sell_transaction(tid_win, Decimal('12.00'), 100, '2025-01-10')

        # 有亏损的平仓
        ok, tid_loss = self.trading.add_buy_transaction(self.sid, 'PF003', '亏损股', Decimal('10.00'), 100, '2025-01-01')
        self.assertTrue(ok)
        self.trading.add_sell_transaction(tid_loss, Decimal('9.00'), 100, '2025-01-05')

        score = self.analysis.calculate_strategy_score(strategy_id=self.sid)
        stats = score['stats']

        self.assertEqual(stats['total_trades'], 2)  # 仅闭合的两笔
        # Profit Factor = 总盈利(200) / 总亏损绝对值(100) = 2
        self.assertGreater(stats['avg_profit_loss_ratio'], 1.9)
        self.assertGreaterEqual(score['stats']['avg_holding_days'], 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)


