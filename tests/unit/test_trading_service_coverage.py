#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试交易服务的覆盖率
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from services.trading_service import TradingService


class TestTradingServiceCoverage(unittest.TestCase):
    """测试交易服务的覆盖率"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_db = Mock()
        self.mock_strategy_service = Mock()
        self.service = TradingService(self.mock_db)
        self.service.strategy_service = self.mock_strategy_service
        # 默认策略列表，避免迭代Mock错误
        self.mock_strategy_service.get_all_strategies.return_value = [{'id': 1, 'name': '测试策略', 'is_active': 1}]
    
    def test_add_buy_transaction_empty_symbol_code(self):
        result, message = self.service.add_buy_transaction(
            strategy=1, symbol_code='', symbol_name='测试股票',
            price=Decimal('10.00'), quantity=100, transaction_date='2024-01-01'
        )
        self.assertFalse(result)
        self.assertIn('股票代码和名称不能为空', message)
    
    def test_add_buy_transaction_empty_symbol_name(self):
        result, message = self.service.add_buy_transaction(
            strategy=1, symbol_code='TEST001', symbol_name='',
            price=Decimal('10.00'), quantity=100, transaction_date='2024-01-01'
        )
        self.assertFalse(result)
        self.assertIn('股票代码和名称', message)
    
    def test_add_buy_transaction_invalid_price(self):
        result, message = self.service.add_buy_transaction(
            strategy=1, symbol_code='TEST001', symbol_name='测试股票',
            price=Decimal('0'), quantity=100, transaction_date='2024-01-01'
        )
        self.assertFalse(result)
        self.assertIn('价格和数量必须大于0', message)
    
    def test_add_buy_transaction_invalid_quantity(self):
        result, message = self.service.add_buy_transaction(
            strategy=1, symbol_code='TEST001', symbol_name='测试股票',
            price=Decimal('10.00'), quantity=0, transaction_date='2024-01-01'
        )
        self.assertFalse(result)
        self.assertIn('价格和数量必须大于0', message)
    
    def test_add_buy_transaction_strategy_not_found(self):
        self.mock_strategy_service.get_strategy_by_id.return_value = None
        result, message = self.service.add_buy_transaction(
            strategy=999, symbol_code='TEST001', symbol_name='测试股票',
            price=Decimal('10.00'), quantity=100, transaction_date='2024-01-01'
        )
        self.assertFalse(result)
        self.assertIn('不存在或已被禁用', message)
    
    def test_add_sell_transaction_invalid_price(self):
        result, message = self.service.add_sell_transaction(
            trade_id=1, price=Decimal('0'), quantity=100,
            transaction_date='2024-01-01'
        )
        self.assertFalse(result)
        self.assertIn('价格和数量必须大于0', message)
    
    def test_add_sell_transaction_invalid_quantity(self):
        result, message = self.service.add_sell_transaction(
            trade_id=1, price=Decimal('10.00'), quantity=0,
            transaction_date='2024-01-01'
        )
        self.assertFalse(result)
        self.assertIn('价格和数量必须大于0', message)
    
    def test_add_sell_transaction_trade_not_found(self):
        with patch.object(self.service, 'get_trade_by_id', return_value=None):
            result, message = self.service.add_sell_transaction(
                trade_id=999, price=Decimal('10.00'), quantity=100,
                transaction_date='2024-01-01'
            )
        self.assertFalse(result)
        self.assertIn('不存在', message)
    
    def test_get_all_trades_with_filters(self):
        self.mock_db.execute_query.return_value = [
            {'id': 1, 'symbol_code': 'TEST001', 'status': 'open'},
            {'id': 2, 'symbol_code': 'TEST002', 'status': 'closed'}
        ]
        result = self.service.get_all_trades(status='open')
        self.assertEqual(len(result), 2)
        query_call = self.mock_db.execute_query.call_args[0][0]
        self.assertIn('status =', query_call)
    
    def test_get_all_trades_include_deleted(self):
        self.mock_db.execute_query.return_value = [
            {'id': 1, 'symbol_code': 'TEST001', 'is_deleted': 0},
            {'id': 2, 'symbol_code': 'TEST002', 'is_deleted': 1}
        ]
        result = self.service.get_all_trades(include_deleted=True)
        query_call = self.mock_db.execute_query.call_args[0][0]
        self.assertNotIn('is_deleted = 0', query_call)
    
    def test_get_trade_details_include_deleted(self):
        self.mock_db.execute_query.return_value = [
            {'id': 1, 'transaction_type': 'buy', 'is_deleted': 0},
            {'id': 2, 'transaction_type': 'sell', 'is_deleted': 1}
        ]
        result = self.service.get_trade_details(1, include_deleted=True)
        query_call = self.mock_db.execute_query.call_args[0][0]
        self.assertNotIn('is_deleted = 0', query_call)
    
    def test_update_trade_record_missing_detail_id(self):
        # 配置上下文管理器和游标
        cursor = Mock()
        conn = Mock()
        conn.cursor.return_value = cursor
        cm = MagicMock()
        cm.__enter__.return_value = conn
        cm.__exit__.return_value = False
        self.mock_db.get_connection.return_value = cm
        # trades 存在
        cursor.fetchone.return_value = {'id': 1, 'open_date': '2024-01-01', 'holding_days': 0}
        
        updates = [{'price': '10.00'}]  # 缺少 detail_id
        result, message = self.service.update_trade_record(1, updates)
        self.assertFalse(result)
        self.assertIn('detail_id 缺失', message)
    
    def test_update_trade_record_trade_not_found(self):
        cursor = Mock()
        conn = Mock()
        conn.cursor.return_value = cursor
        cm = MagicMock()
        cm.__enter__.return_value = conn
        cm.__exit__.return_value = False
        self.mock_db.get_connection.return_value = cm
        # trades 查询返回 None
        cursor.fetchone.return_value = None
        
        updates = [{'detail_id': 1, 'price': '10.00'}]
        result, message = self.service.update_trade_record(1, updates)
        self.assertFalse(result)
        self.assertIn('不存在', message)
    
    def test_resolve_strategy_by_id(self):
        self.mock_strategy_service.get_strategy_by_id.return_value = {'id': 1, 'name': '测试策略', 'is_active': 1}
        result = self.service._resolve_strategy(1)
        self.assertEqual(result, 1)
        self.mock_strategy_service.get_strategy_by_id.assert_called_once_with(1)
    
    def test_resolve_strategy_by_name(self):
        # 按实现，使用 get_all_strategies 迭代匹配
        self.mock_strategy_service.get_all_strategies.return_value = [{'id': 1, 'name': '测试策略'}]
        result = self.service._resolve_strategy('测试策略')
        self.assertEqual(result, 1)
        self.mock_strategy_service.get_all_strategies.assert_called_once()
    
    def test_update_existing_trade_for_buy(self):
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {
            'total_buy_amount': 100.0,
            'total_buy_quantity': 10,
            'remaining_quantity': 10
        }
        self.service._update_existing_trade_for_buy(
            mock_cursor, trade_id=1, price=Decimal('10.00'), 
            quantity=100, transaction_date='2024-01-01',
            transaction_fee=Decimal('5.00'), amount=Decimal('1005.00')
        )
        # 第一次执行是 SELECT，第二次是 UPDATE
        self.assertGreaterEqual(len(mock_cursor.execute.call_args_list), 2)
        call_args = mock_cursor.execute.call_args_list[1][0]
        self.assertIn('UPDATE trades', call_args[0])
    
    def test_create_new_trade(self):
        mock_cursor = Mock()
        mock_cursor.lastrowid = 1
        result = self.service._create_new_trade(
            mock_cursor, strategy_id=1, symbol_code='TEST001',
            symbol_name='测试股票', transaction_date='2024-01-01'
        )
        self.assertEqual(result, 1)
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        self.assertIn('INSERT INTO trades', call_args[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
