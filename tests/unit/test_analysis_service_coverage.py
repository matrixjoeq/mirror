#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试分析服务的覆盖率
"""

import unittest
from unittest.mock import Mock
from services.analysis_service import AnalysisService


class TestAnalysisServiceCoverage(unittest.TestCase):
    """测试分析服务的覆盖率"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_db = Mock()
        self.mock_strategy_service = Mock()
        self.service = AnalysisService(self.mock_db)
        self.service.strategy_service = self.mock_strategy_service
        # 默认返回一个策略，避免未设置时迭代Mock错误
        self.mock_strategy_service.get_all_strategies.return_value = [
            {'id': 1, 'name': '测试策略'}
        ]
    
    def _fees_side_effect(self, *args, **kwargs):
        """根据SQL返回适配的数据结构：
        - 交易查询：返回包含'id'等字段的列表
        - 手续费查询（fetch_one=True）：返回{'total_fees': ...}
        - 符号去重查询：返回列表 [{'symbol_code', 'symbol_name'}]
        """
        query = args[0]
        if 'FROM trade_details' in query:
            # 手续费汇总，代码使用 fetch_one=True，返回dict
            return {'total_fees': 5.0}
        if 'SELECT DISTINCT symbol_code' in query:
            return [{'symbol_code': 'TEST001', 'symbol_name': '测试股票'}]
        # 默认交易列表
        return [{
            'id': 1, 'strategy_id': 1, 'strategy_name': '测试策略',
            'symbol_code': 'TEST001', 'symbol_name': '测试股票',
            'status': 'closed', 'total_buy_amount': 1000.0,
            'total_profit_loss': 100.0, 'holding_days': 10
        }]
    
    def test_calculate_strategy_score_with_strategy_name(self):
        """测试通过策略名称计算评分"""
        # 交易查询为空，fees不会被调用
        self.mock_db.execute_query.return_value = []
        
        result = self.service.calculate_strategy_score(strategy='测试策略')
        
        self.assertIn('stats', result)
        self.assertEqual(result['stats']['total_trades'], 0)
    
    def test_calculate_strategy_score_with_symbol_filter(self):
        """测试带股票代码筛选的评分计算（并验证查询包含symbol_code）"""
        self.mock_db.execute_query.side_effect = self._fees_side_effect
        
        result = self.service.calculate_strategy_score(symbol_code='TEST001')
        
        # 验证返回结果
        self.assertEqual(result['stats']['total_trades'], 1)
        self.assertEqual(result['stats']['winning_trades'], 1)
        
        # 验证首次针对 trades 的查询包含 symbol_code 条件
        from_trades_calls = [c for c in self.mock_db.execute_query.call_args_list if 'FROM trades' in c[0][0]]
        self.assertTrue(any('symbol_code' in c[0][0] for c in from_trades_calls))
    
    def test_get_symbol_scores_by_strategy_with_strategy_name(self):
        """测试通过策略名称获取股票评分"""
        self.mock_db.execute_query.side_effect = self._fees_side_effect
        
        result = self.service.get_symbol_scores_by_strategy(strategy='测试策略')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['stats']['total_trades'], 1)
        self.assertEqual(result[0]['symbol_code'], 'TEST001')
    
    def test_get_strategies_scores_by_symbol(self):
        """测试获取指定股票的策略评分"""
        self.mock_db.execute_query.side_effect = self._fees_side_effect
        
        result = self.service.get_strategies_scores_by_symbol('TEST001')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['stats']['total_trades'], 1)
    
    def test_get_time_periods_quarter(self):
        """测试获取季度时间周期"""
        self.mock_db.execute_query.return_value = [
            {'period': '2024-Q1'}, {'period': '2024-Q2'}
        ]
        result = self.service.get_time_periods('quarter')
        self.assertEqual(result, ['2024-Q1', '2024-Q2'])
    
    def test_get_time_periods_month(self):
        """测试获取月度时间周期"""
        self.mock_db.execute_query.return_value = [
            {'period': '2024-01'}, {'period': '2024-02'}
        ]
        result = self.service.get_time_periods('month')
        self.assertEqual(result, ['2024-01', '2024-02'])
    
    def test_get_strategies_scores_by_time_period(self):
        """测试获取指定时间周期的策略评分"""
        self.mock_db.execute_query.side_effect = self._fees_side_effect
        result = self.service.get_strategies_scores_by_time_period('2024', 'year')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['stats']['total_trades'], 1)
    
    def test_get_period_summary(self):
        """测试获取时间周期汇总"""
        self.mock_db.execute_query.return_value = []
        result = self.service.get_period_summary('2024', 'year')
        self.assertIn('stats', result)
        self.assertEqual(result['stats']['total_trades'], 0)
    
    def test_performance_metrics_edge_cases(self):
        """测试性能指标计算的边界情况（盈亏为0）"""
        def side_effect(*args, **kwargs):
            query = args[0]
            if 'FROM trade_details' in query:
                return {'total_fees': 5.0}
            return [{
                'id': 1, 'strategy_id': 1, 'strategy_name': '测试策略',
                'symbol_code': 'TEST001', 'symbol_name': '测试股票',
                'status': 'closed', 'total_buy_amount': 1000.0,
                'total_profit_loss': 0.0, 'holding_days': 10
            }]
        self.mock_db.execute_query.side_effect = side_effect
        
        result = self.service.calculate_strategy_score()
        self.assertEqual(result['stats']['winning_trades'], 0)
        self.assertEqual(result['stats']['losing_trades'], 0)
        self.assertEqual(result['stats']['win_rate'], 0.0)
    
    def test_performance_metrics_infinite_profit_ratio(self):
        """测试无限盈亏比的处理（只有盈利，无亏损）"""
        def side_effect(*args, **kwargs):
            query = args[0]
            if 'FROM trade_details' in query:
                return {'total_fees': 5.0}
            return [{
                'id': 1, 'strategy_id': 1, 'strategy_name': '测试策略',
                'symbol_code': 'TEST001', 'symbol_name': '测试股票',
                'status': 'closed', 'total_buy_amount': 1000.0,
                'total_profit_loss': 100.0, 'holding_days': 10
            }]
        self.mock_db.execute_query.side_effect = side_effect
        
        result = self.service.calculate_strategy_score()
        self.assertEqual(result['stats']['avg_profit_loss_ratio'], 9999.0)
    
    def test_get_period_date_range_methods(self):
        """测试时间周期日期范围方法"""
        # 季度
        self.assertEqual(self.service._get_period_date_range('2024-Q1', 'quarter'), ('2024-01-01', '2024-03-31'))
        # 月度
        self.assertEqual(self.service._get_period_date_range('2024-02', 'month'), ('2024-02-01', '2024-02-28'))
        # 年度
        self.assertEqual(self.service._get_period_date_range('2024', 'year'), ('2024-01-01', '2024-12-31'))
        # 无效
        self.assertEqual(self.service._get_period_date_range('2024', 'invalid'), ('1900-01-01', '2099-12-31'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
