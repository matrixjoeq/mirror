#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile

from services import DatabaseService, StrategyService


class TestStrategyServiceUpdateConflicts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.strategy = StrategyService(self.db)

    def test_create_duplicate_and_update_name_conflict(self):
        ok, _ = self.strategy.create_strategy('S1', 'desc')
        self.assertTrue(ok)
        ok, _ = self.strategy.create_strategy('S2', 'desc')
        self.assertTrue(ok)

        s1 = next(s for s in self.strategy.get_all_strategies() if s['name'] == 'S1')
        s2 = next(s for s in self.strategy.get_all_strategies() if s['name'] == 'S2')

        # 创建重名
        ok, msg = self.strategy.create_strategy('S1', 'again')
        self.assertFalse(ok)
        self.assertIn('已存在', msg)

        # 更新为与他人重名应失败
        ok, msg = self.strategy.update_strategy(s2['id'], name='S1', description='x', tag_names=[])
        self.assertFalse(ok)
        self.assertIn('已被其他策略使用', msg)

        # 通过名称禁用：存在时成功
        ok, msg = self.strategy.disable_strategy_by_name('S1')
        self.assertTrue(ok)
        # 不存在活跃：返回无需处理
        ok, msg = self.strategy.disable_strategy_by_name('不存在的')
        self.assertTrue(ok)


if __name__ == '__main__':
    unittest.main(verbosity=2)


