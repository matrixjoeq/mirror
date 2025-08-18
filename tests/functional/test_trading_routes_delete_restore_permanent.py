#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from app import create_app


class TestTradingRoutesDeleteRestorePermanent(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

        # 创建策略
        ok, msg = self.app.strategy_service.create_strategy('功能-删除恢复-策略', 'for func tests')
        self.assertTrue(ok, msg)
        # 获取策略ID
        strategies = self.app.strategy_service.get_all_strategies()
        sid = None
        for s in strategies:
            if s['name'] == '功能-删除恢复-策略':
                sid = s['id']
                break
        self.assertIsNotNone(sid)
        self.strategy_id = sid

        # 通过路由添加一笔买入交易
        r = self.client.post('/add_buy', data={
            'strategy': str(self.strategy_id),
            'symbol_code': 'FUNC001',
            'symbol_name': 'FuncName',
            'price': '10.00',
            'quantity': '100',
            'transaction_date': '2024-01-01',
            'transaction_fee': '1.00',
            'buy_reason': 'func'
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)

        # 查询刚插入的交易ID
        row = self.app.db_service.execute_query('SELECT id FROM trades ORDER BY id DESC LIMIT 1', (), fetch_one=True)
        self.assertIsNotNone(row)
        self.trade_id = int(row['id'])

    def test_delete_restore_permanent(self):
        # 删除需要确认码
        resp_del = self.client.post(f'/delete_trade/{self.trade_id}', data={'confirmation_code': 'code123', 'delete_reason': 'test', 'operator_note': 'n'})
        self.assertEqual(resp_del.status_code, 200)
        self.assertIn(b'success', resp_del.data)

        # 恢复
        resp_res = self.client.post(f'/restore_trade/{self.trade_id}', data={'confirmation_code': 'code123', 'operator_note': 'back'})
        self.assertEqual(resp_res.status_code, 200)

        # 生成确认码（覆盖端点）
        cc = self.client.get('/generate_confirmation_code')
        self.assertEqual(cc.status_code, 200)

        # 永久删除
        resp_perm = self.client.post(f'/permanently_delete_trade/{self.trade_id}', data={'confirmation_code': 'code123', 'confirmation_text': 'CONFIRM', 'delete_reason': 'r', 'operator_note': 'o'})
        self.assertEqual(resp_perm.status_code, 200)


if __name__ == '__main__':
    unittest.main()


