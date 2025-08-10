#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile

from services import DatabaseService, StrategyService, TradingService


class TestStrategyServiceMore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.strategy = StrategyService(self.db)
        self.trading = TradingService(self.db)

    def test_delete_strategy_blocked_when_has_trades(self):
        ok, _ = self.strategy.create_strategy('不可删除策略', '')
        self.assertTrue(ok)
        sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '不可删除策略')

        ok, trade_id = self.trading.add_buy_transaction(sid, 'SDEL', '删除验证', 10, 10, '2025-01-01')
        self.assertTrue(ok)

        success, msg = self.strategy.delete_strategy(sid)
        self.assertFalse(success)
        self.assertIn('无法删除', msg)

    def test_predefined_tag_protection(self):
        # 创建预定义标签名（按名称识别）
        ok, msg = self.strategy.create_tag('趋势')
        # 允许已存在则跳过
        self.assertTrue(ok or '已存在' in msg)
        # 读取该标签id
        tags = self.strategy.get_all_tags()
        tag = next(t for t in tags if t['name'] == '趋势')

        # 更新应失败
        success, message = self.strategy.update_tag(tag['id'], '新趋势')
        self.assertFalse(success)
        self.assertIn('不能修改', message)

        # 删除应失败
        success, message = self.strategy.delete_tag(tag['id'])
        self.assertFalse(success)
        self.assertIn('不能删除', message)


if __name__ == '__main__':
    unittest.main(verbosity=2)


