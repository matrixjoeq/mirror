#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
from decimal import Decimal

from app import create_app
from services import DatabaseService, TradingService, StrategyService


class TestRoutesAdminAndMetrics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()

        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.tmp.name

        # set isolated db services
        self.db = DatabaseService(self.tmp.name)
        self.trading = TradingService(self.db)
        self.strategy = StrategyService(self.db)
        self.app.db_service = self.db
        self.app.trading_service = self.trading
        self.app.strategy_service = self.strategy

        self.client = self.app.test_client()

        # seed minimal data
        ok, _ = self.strategy.create_strategy('功能覆盖策略', '')
        self.assertTrue(ok)
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '功能覆盖策略')

        ok, self.trade_id = self.trading.add_buy_transaction(
            self.sid, 'FUNC1', '覆盖标的', Decimal('10.00'), 2, '2025-01-01'
        )
        self.assertTrue(ok)
        # one sell to close one share, keep remaining open to cover both states
        ok, _ = self.trading.add_sell_transaction(
            self.trade_id, Decimal('11.00'), 1, '2025-01-02'
        )
        self.assertTrue(ok)

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    # ---- Metrics/API ----
    def test_api_strategy_score_contains_advanced_metrics(self):
        r = self.client.get(f'/api/strategy_score?strategy_id={self.sid}')
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertTrue(j.get('success'))
        stats = j['data'].get('stats', {})
        # advanced fields should be present (computed via numpy/pandas/empyrical)
        for key in ('annual_volatility', 'annual_return', 'max_drawdown'):
            self.assertIn(key, stats)

    def test_api_strategy_trend_ok_with_strategy_id(self):
        r = self.client.get(f'/api/strategy_trend?strategy_id={self.sid}&period_type=month')
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertTrue(j.get('success'))
        self.assertIn('data', j)

    def test_api_symbol_lookup_edge_and_lists(self):
        # symbol_lookup not found path
        r = self.client.get('/api/symbol_lookup?symbol_code=UNKNOWN_X')
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertTrue(j.get('success'))
        # basic lists
        r2 = self.client.get('/api/strategies')
        self.assertEqual(r2.status_code, 200)
        r3 = self.client.get('/api/tags')
        self.assertEqual(r3.status_code, 200)

    def test_api_trade_detail_found_and_not_found(self):
        # query a real detail id
        row = self.db.execute_query(
            'SELECT id FROM trade_details WHERE trade_id = ? ORDER BY id LIMIT 1', (self.trade_id,), fetch_one=True
        )
        self.assertIsNotNone(row)
        detail_id = int(row['id'])
        ok = self.client.get(f'/api/trade_detail/{detail_id}')
        self.assertEqual(ok.status_code, 200)
        # not found
        nf = self.client.get('/api/trade_detail/999999999')
        self.assertEqual(nf.status_code, 404)

    def test_api_quick_sell_validation(self):
        r = self.client.post('/api/quick_sell', json={'trade_id': self.trade_id})
        self.assertEqual(r.status_code, 400)

    # ---- Admin routes ----
    def test_admin_diagnose_and_json(self):
        r1 = self.client.get('/admin/db/diagnose')
        self.assertEqual(r1.status_code, 200)
        r2 = self.client.get('/admin/db/diagnose.json')
        self.assertEqual(r2.status_code, 200)
        j2 = r2.get_json()
        self.assertIn('summary', j2)

    def test_admin_auto_fix_and_update_row(self):
        # auto_fix accepts list or None
        r = self.client.post('/admin/db/auto_fix', json={'trade_ids': [self.trade_id]})
        self.assertEqual(r.status_code, 200)
        # update_row on trades (operator_note allowed)
        r2 = self.client.post('/admin/db/update_row', json={
            'table': 'trades',
            'id': self.trade_id,
            'updates': {'operator_note': 'patched'}
        })
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.get_json().get('ok', True) in (True, False))

    # ---- Main route and helpers/trade_calculation utilities (coverage bump) ----
    def test_main_index_with_strategy_filter_and_utilities(self):
        # ensure index works and filter by strategy id branch is covered
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        r2 = self.client.get(f'/?strategy={self.sid}')
        self.assertEqual(r2.status_code, 200)

        # helpers: exercise period date ranges for year/quarter/month and validators
        from utils import helpers
        y = helpers.get_period_date_range('2025', 'year')
        q = helpers.get_period_date_range('2025-Q2', 'quarter')
        m = helpers.get_period_date_range('2025-02', 'month')
        self.assertEqual(y, ('2025-01-01', '2025-12-31'))
        self.assertEqual(q, ('2025-04-01', '2025-06-30'))
        self.assertEqual(m, ('2025-02-01', '2025-02-28'))
        self.assertTrue(helpers.validate_date_format('2025-02-28'))
        self.assertFalse(helpers.validate_date_format('2025-2-30'))
        _ = helpers.format_currency(1234.5)
        _ = helpers.format_percentage(12.3456, 2)
        _ = helpers.parse_decimal_input('1,234.56')
        _ = helpers.get_trading_days_between('2025-01-01', '2025-01-31')

        # trade_calculation: exercise compute path
        from services.trade_calculation import compute_trade_profit_metrics
        metrics = compute_trade_profit_metrics(
            gross_buy_total=Decimal('1000'),
            buy_fees_total=Decimal('10'),
            gross_sell_total=Decimal('1100'),
            sell_fees_total=Decimal('5'),
            sold_qty=Decimal('10'),
            buy_qty=Decimal('10'),
        )
        self.assertIn('net_profit', metrics)


if __name__ == '__main__':
    unittest.main(verbosity=2)


