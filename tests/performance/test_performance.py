#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能测试 - 数据库、路由与UI响应速度

说明：
- 使用临时SQLite数据库，测试后删除，确保无残留数据（遵循项目测试清理约定）。
- 目标阈值以秒为单位，结合当前实现给出合理上限，可按需要在不同环境下调整。
"""

import unittest
import tempfile
import os
import sys
import time
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestPerformance(unittest.TestCase):
    """覆盖数据库、路由、UI响应的性能测试"""

    def setUp(self):
        # 独立临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        # Flask 应用（测试模式，强制 testing 配置）
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.temp_db.name

        # 注入服务（使用临时库）
        self.db_service = DatabaseService(self.temp_db.name)
        self.trading_service = TradingService(self.db_service)
        self.strategy_service = StrategyService(self.db_service)
        self.analysis_service = AnalysisService(self.db_service)

        self.app.db_service = self.db_service
        self.app.trading_service = self.trading_service
        self.app.strategy_service = self.strategy_service
        self.app.analysis_service = self.analysis_service

        self.client = self.app.test_client()

        # 基础数据：创建策略
        ok, _ = self.strategy_service.create_strategy(name="性能基准策略", description="性能测试用")
        self.assertTrue(ok)
        strategies = self.strategy_service.get_all_strategies()
        self.strategy_id = next(s['id'] for s in strategies if s['name'] == '性能基准策略')

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    # -----------------------------
    # 数据库写入与查询性能
    # -----------------------------
    def test_database_bulk_insert_and_query(self):
        start = time.perf_counter()
        # 批量写入 N=500（包含部分卖出）
        N = 500
        for i in range(N):
            ok, trade_id = self.trading_service.add_buy_transaction(
                strategy=self.strategy_id,
                symbol_code=f"PF{i:04d}",
                symbol_name=f"性能股{i}",
                price=Decimal('10.00') + Decimal(i % 7),
                quantity=100 + (i % 5) * 10,
                transaction_date='2025-01-01',
                transaction_fee=Decimal('0.30')
            )
            self.assertTrue(ok)
            if i % 10 == 9:
                ok, _ = self.trading_service.add_sell_transaction(
                    trade_id=trade_id,
                    price=Decimal('11.50'),
                    quantity=100 + (i % 5) * 10,
                    transaction_date='2025-01-10',
                    transaction_fee=Decimal('0.35'),
                    sell_reason='性能测试'
                )
                self.assertTrue(ok)
        write_elapsed = time.perf_counter() - start

        # 评价：500 次写入（含 50 次卖出）应在 25 秒内完成（SQLite、解释器环境）
        self.assertLess(write_elapsed, 25.0, f"批量写入耗时过长: {write_elapsed:.2f}s")

        # 查询所有交易
        start = time.perf_counter()
        rows = self.trading_service.get_all_trades(compute_metrics=False)
        read_elapsed = time.perf_counter() - start
        self.assertGreaterEqual(len(rows), N)
        # 评价：一次全表查询应在 1.5 秒内完成
        self.assertLess(read_elapsed, 1.5, f"查询耗时过长: {read_elapsed:.3f}s")

        # 评分计算
        start = time.perf_counter()
        _ = self.analysis_service.calculate_strategy_score(strategy_id=self.strategy_id)
        score_elapsed = time.perf_counter() - start
        # 评价：评分计算应在 3 秒内完成
        self.assertLess(score_elapsed, 3.0, f"评分计算耗时过长: {score_elapsed:.3f}s")

    # -----------------------------
    # 路由性能（API + 页面）
    # -----------------------------
    def test_route_response_latency(self):
        # 预热
        self.client.get('/')

        def measure(path: str, method: str = 'GET', data=None, repeat: int = 10):
            total = 0.0
            for _ in range(repeat):
                t0 = time.perf_counter()
                if method == 'GET':
                    resp = self.client.get(path)
                else:
                    resp = self.client.post(path, data=data or {})
                self.assertIn(resp.status_code, (200, 302))
                total += (time.perf_counter() - t0)
            return total / repeat

        # 页面
        home_avg = measure('/')
        trades_avg = measure('/trades')
        strategies_avg = measure('/strategies')

        # API（策略评分）
        api_avg = measure(f'/api/strategy_score?strategy_id={self.strategy_id}')

        # 评价：单次渲染/API应在 120ms 内（平均）
        self.assertLess(home_avg, 0.12, f"首页平均响应过慢: {home_avg:.3f}s")
        self.assertLess(trades_avg, 0.12, f"交易页平均响应过慢: {trades_avg:.3f}s")
        self.assertLess(strategies_avg, 0.12, f"策略页平均响应过慢: {strategies_avg:.3f}s")
        self.assertLess(api_avg, 0.12, f"评分API平均响应过慢: {api_avg:.3f}s")

    # -----------------------------
    # UI交互（表单提交）
    # -----------------------------
    def test_ui_form_submit_latency(self):
        # 提交买入表单
        def post_buy():
            data = {
                'strategy': self.strategy_id,
                'symbol_code': 'UI001',
                'symbol_name': 'UI响应测试股',
                'price': '15.80',
                'quantity': '300',
                'transaction_date': '2025-01-01',
                'buy_reason': 'UI性能测试',
                'transaction_fee': '0.90'
            }
            t0 = time.perf_counter()
            resp = self.client.post('/add_buy', data=data)
            dt = time.perf_counter() - t0
            self.assertEqual(resp.status_code, 302)
            return dt

        # 连续提交 5 次，记录平均
        times = [post_buy() for _ in range(5)]
        avg = sum(times) / len(times)
        # 评价：表单提交-重定向往返应在 200ms 内（平均）
        self.assertLess(avg, 0.2, f"买入表单平均响应过慢: {avg:.3f}s")


if __name__ == '__main__':
    unittest.main(verbosity=2)


