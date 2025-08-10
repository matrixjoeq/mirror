#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile

from services import DatabaseService, StrategyService


class TestStrategyServiceFillGaps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.strategy = StrategyService(self.db)

    def test_create_update_delete_tag_flows_and_conflicts(self):
        # 创建标签
        ok, msg = self.strategy.create_tag('自定义一')
        self.assertTrue(ok or '已存在' in msg)
        tag = next(t for t in self.strategy.get_all_tags() if t['name'] == '自定义一')

        # 重名创建应失败
        ok2, msg2 = self.strategy.create_tag('自定义一')
        self.assertFalse(ok2)

        # 更新为新名称
        ok3, msg3 = self.strategy.update_tag(tag['id'], '自定义一改')
        self.assertTrue(ok3)

        # 冲突更新（准备另外一个标签）
        ok4, _ = self.strategy.create_tag('自定义二')
        self.assertTrue(ok4 or '已存在' in _)
        tag2 = next(t for t in self.strategy.get_all_tags() if t['name'] == '自定义二')
        ok5, msg5 = self.strategy.update_tag(tag2['id'], '自定义一改')
        self.assertFalse(ok5)

        # 删除标签
        ok6, msg6 = self.strategy.delete_tag(tag['id'])
        self.assertTrue(ok6)

    def test_disable_strategy_by_name_noop_and_success(self):
        ok, _ = self.strategy.create_strategy('清理策略', '')
        self.assertTrue(ok or '已存在' in _)
        ok2, msg2 = self.strategy.disable_strategy_by_name('清理策略')
        self.assertTrue(ok2)
        # 再次禁用应为无操作
        ok3, msg3 = self.strategy.disable_strategy_by_name('清理策略')
        self.assertTrue(ok3)


if __name__ == '__main__':
    unittest.main(verbosity=2)


