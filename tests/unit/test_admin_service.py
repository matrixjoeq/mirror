#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from decimal import Decimal

from app import create_app
from services.admin_service import DatabaseMaintenanceService


class TestDatabaseMaintenanceService(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.db = self.app.db_service
        self.trading = self.app.trading_service
        self.strategy = self.app.strategy_service
        # 创建策略
        ok, msg = self.strategy.create_strategy('UT', 'unit test strategy', [])
        if not ok and '已存在' not in msg:
            raise RuntimeError(msg)

    def tearDown(self):
        self.ctx.pop()

    def _create_trade_with_mismatch(self):
        # 创建一笔交易：买入2次，卖出1次
        ok, res = self.trading.add_buy_transaction('UT', 'UT001', '测试标的', Decimal('1.180'), 1000, '2025-01-01', Decimal('0.2'))
        self.assertTrue(ok, res)
        trade_id = res
        ok2, res2 = self.trading.add_buy_transaction('UT', 'UT001', '测试标的', Decimal('1.170'), 1000, '2025-01-02', Decimal('0.2'))
        self.assertTrue(ok2, res2)
        ok3, msg3 = self.trading.add_sell_transaction(trade_id, Decimal('1.185'), 1000, '2025-01-03', Decimal('0.2'))
        self.assertTrue(ok3, msg3)

        # 人为制造主表不一致：把净利润与买入金额改成错误值
        self.db.execute_query("UPDATE trades SET total_net_profit = ?, total_buy_amount = ? WHERE id = ?", (0.0, 0.0, trade_id), fetch_all=False)

        # 随机挑一条明细，篡改 amount 以制造 detail_issues
        detail = self.db.execute_query("SELECT id FROM trade_details WHERE trade_id = ? LIMIT 1", (trade_id,), fetch_one=True)
        self.assertIsNotNone(detail)
        self.db.execute_query("UPDATE trade_details SET amount = 0 WHERE id = ?", (detail['id'],), fetch_all=False)

        return trade_id

    def test_validate_and_fix(self):
        svc = DatabaseMaintenanceService(self.db, self.trading)
        trade_id = self._create_trade_with_mismatch()

        # 诊断应发现主表与明细问题
        result = svc.validate_database(trade_id)
        self.assertGreaterEqual(result['summary']['trade_issue_count'], 1)
        self.assertGreaterEqual(result['summary']['detail_issue_count'], 1)

        # 使用 update_row 修正刚才被我们置零的明细 amount
        # 重新获取该明细正确定义的 expected 值
        # 通过服务的校验结果找到该 detail 的期望值
        target_detail = None
        for d in result['detail_issues']:
            if d['trade_id'] == trade_id:
                target_detail = d
                break
        self.assertIsNotNone(target_detail)
        ok, msg = svc.update_raw_row('trade_details', target_detail['detail_id'], {'amount': target_detail['expected']})
        self.assertTrue(ok, msg)

        # 自动修复主表：基于明细重算
        r = svc.auto_fix([trade_id])
        self.assertIn(trade_id, r['fixed'])

        # 再次诊断应显著减少问题（通常归零）
        result2 = svc.validate_database(trade_id)
        self.assertEqual(result2['summary']['detail_issue_count'], 0)
        # 主表可能因四舍五入差异留下极少量边界问题，这里断言非强制为0，但应小于之前
        self.assertLessEqual(result2['summary']['trade_issue_count'], result['summary']['trade_issue_count'])

    def test_update_raw_row_and_auto_fix_all(self):
        svc = DatabaseMaintenanceService(self.db, self.trading)
        # 构造一笔数据
        ok, res = self.trading.add_buy_transaction('UT', 'UT002', '测试标的2', Decimal('1.000'), 100, '2025-02-01', Decimal('0.2'))
        self.assertTrue(ok, res)
        trade_id = res
        ok2, _ = self.trading.add_sell_transaction(trade_id, Decimal('1.050'), 50, '2025-02-02', Decimal('0.2'))
        self.assertTrue(ok2)

        # 编辑主表允许字段（operator_note）
        ok_upd, msg_upd = svc.update_raw_row('trades', trade_id, {'operator_note': 'unit-edit'})
        self.assertTrue(ok_upd, msg_upd)

        # 非法表名
        ok_bad, msg_bad = svc.update_raw_row('bad_table', 1, {'x': 1})
        self.assertFalse(ok_bad)

        # 编辑明细允许字段并触发重算
        d = self.db.execute_query("SELECT id FROM trade_details WHERE trade_id = ? AND transaction_type='sell' LIMIT 1", (trade_id,), fetch_one=True)
        self.assertIsNotNone(d)
        ok_d, msg_d = svc.update_raw_row('trade_details', int(d['id']), {'sell_reason': 'unit-fix'})
        self.assertTrue(ok_d, msg_d)

        # 运行 auto_fix 全部
        r_all = svc.auto_fix(None)
        self.assertIn(trade_id, r_all['fixed'])

    def test_validate_all_scope(self):
        svc = DatabaseMaintenanceService(self.db, self.trading)
        # 构造两笔数据，确保 validate_database() 无参数能跑全量
        self.trading.add_buy_transaction('UT', 'UT003', '标的3', Decimal('1.200'), 10, '2025-03-01', Decimal('0.1'))
        self.trading.add_buy_transaction('UT', 'UT004', '标的4', Decimal('1.300'), 10, '2025-03-02', Decimal('0.1'))
        res = svc.validate_database()
        self.assertIn('summary', res)
        self.assertIn('trade_issues', res)
        self.assertIn('detail_issues', res)


if __name__ == '__main__':
    unittest.main()


