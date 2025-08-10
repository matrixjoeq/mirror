#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试策略服务的覆盖率
"""

import unittest
from unittest.mock import Mock, patch
from services.strategy_service import StrategyService


class TestStrategyServiceCoverage(unittest.TestCase):
    """测试策略服务的覆盖率"""
    
    def setUp(self):
        self.mock_db = Mock()
        self.service = StrategyService(self.mock_db)
    
    def test_get_all_strategies_include_inactive(self):
        mock_strategies = [
            {'id': 1, 'name': '活跃策略', 'tag_names': '标签1,标签2'},
            {'id': 2, 'name': '非活跃策略', 'tag_names': None}
        ]
        self.mock_db.execute_query.return_value = mock_strategies
        result = self.service.get_all_strategies(include_inactive=True)
        query_call = self.mock_db.execute_query.call_args[0][0]
        self.assertNotIn('WHERE s.is_active = 1', query_call)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['tags'], ['标签1', '标签2'])
        self.assertEqual(result[1]['tags'], [])
    
    def test_get_strategy_by_id_not_found(self):
        self.mock_db.execute_query.return_value = None
        result = self.service.get_strategy_by_id(999)
        self.assertIsNone(result)
    
    def test_create_strategy_empty_name(self):
        result, message = self.service.create_strategy('', '描述')
        self.assertFalse(result)
        self.assertIn('策略名称不能为空', message)
    
    def test_create_strategy_whitespace_name(self):
        result, message = self.service.create_strategy('   ', '描述')
        self.assertFalse(result)
        self.assertIn('策略名称不能为空', message)
    
    def test_create_strategy_name_exists(self):
        self.mock_db.execute_query.return_value = {'id': 1}
        result, message = self.service.create_strategy('已存在策略', '描述')
        self.assertFalse(result)
        self.assertIn('已存在', message)
    
    def test_create_strategy_with_tags(self):
        self.mock_db.execute_query.return_value = None
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 1
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=None)
        self.mock_db.get_connection.return_value = mock_context
        with patch.object(self.service, '_get_or_create_tag', return_value=1):
            result, message = self.service.create_strategy('测试策略', '描述', ['标签1', '标签2'])
        self.assertTrue(result)
        self.assertIn('创建成功', message)
    
    def test_update_strategy_empty_name(self):
        result, message = self.service.update_strategy(1, '', '新描述')
        self.assertFalse(result)
        self.assertIn('策略名称不能为空', message)
    
    def test_update_strategy_not_found(self):
        self.mock_db.execute_query.return_value = None
        result, message = self.service.update_strategy(999, '新名称', '新描述')
        self.assertFalse(result)
        self.assertIn('不存在', message)
    
    def test_update_strategy_name_exists(self):
        self.mock_db.execute_query.side_effect = [
            {'id': 1, 'name': '旧名称', 'tag_names': None},
            {'id': 2, 'name': '新名称'}
        ]
        result, message = self.service.update_strategy(1, '新名称', '新描述')
        self.assertFalse(result)
        self.assertIn('已被其他策略使用', message)
    
    def test_delete_strategy_not_found(self):
        self.mock_db.execute_query.return_value = None
        result, message = self.service.delete_strategy(999)
        self.assertFalse(result)
        self.assertIn('不存在', message)
    
    def test_disable_strategy_by_name_empty_name(self):
        result, message = self.service.disable_strategy_by_name('')
        self.assertFalse(result)
        self.assertIn('策略名称不能为空', message)
    
    def test_disable_strategy_by_name_no_active(self):
        self.mock_db.execute_query.return_value = []
        result, message = self.service.disable_strategy_by_name('测试策略')
        self.assertTrue(result)
        self.assertIn('无需处理', message)
    
    def test_create_tag_empty_name(self):
        result, message = self.service.create_tag('')
        self.assertFalse(result)
        self.assertIn('标签名称不能为空', message)
    
    def test_create_tag_whitespace_name(self):
        result, message = self.service.create_tag('   ')
        self.assertFalse(result)
        self.assertIn('标签名称不能为空', message)
    
    def test_create_tag_name_exists(self):
        self.mock_db.execute_query.return_value = {'id': 1}
        result, message = self.service.create_tag('已存在标签')
        self.assertFalse(result)
        self.assertIn('已存在', message)
    
    def test_update_tag_empty_name(self):
        result, message = self.service.update_tag(1, '')
        self.assertFalse(result)
        self.assertIn('标签名称不能为空', message)
    
    def test_update_tag_not_found(self):
        self.mock_db.execute_query.return_value = None
        result, message = self.service.update_tag(999, '新名称')
        self.assertFalse(result)
        self.assertIn('不存在', message)
    
    def test_update_tag_predefined(self):
        self.mock_db.execute_query.return_value = {'name': '轮动'}
        result, message = self.service.update_tag(1, '新名称')
        self.assertFalse(result)
        self.assertIn('预定义标签不能修改', message)
    
    def test_update_tag_name_conflict(self):
        self.mock_db.execute_query.side_effect = [
            {'name': '旧标签'},
            {'id': 2}
        ]
        result, message = self.service.update_tag(1, '新名称')
        self.assertFalse(result)
        self.assertIn('已存在', message)
    
    def test_delete_tag_not_found(self):
        self.mock_db.execute_query.return_value = None
        result, message = self.service.delete_tag(999)
        self.assertFalse(result)
        self.assertIn('不存在', message)
    
    def test_delete_tag_predefined(self):
        self.mock_db.execute_query.return_value = {'name': '择时'}
        result, message = self.service.delete_tag(1)
        self.assertFalse(result)
        self.assertIn('预定义标签不能删除', message)
    
    def test_delete_tag_in_use(self):
        self.mock_db.execute_query.side_effect = [
            {'name': '测试标签'},
            {'count': 3}
        ]
        result, message = self.service.delete_tag(1)
        self.assertFalse(result)
        self.assertIn('正在被策略使用', message)
    
    def test_get_or_create_tag_existing(self):
        mock_cursor = Mock()
        # 第一次 SELECT 返回已有记录
        mock_cursor.fetchone.side_effect = [
            {'id': 1}
        ]
        result = self.service._get_or_create_tag(mock_cursor, '已存在标签')
        self.assertEqual(result, 1)
    
    def test_get_or_create_tag_new(self):
        mock_cursor = Mock()
        # 第一次 SELECT 返回 None，随后 INSERT，再次不调用 fetchone
        mock_cursor.fetchone.side_effect = [None]
        mock_cursor.lastrowid = 2
        result = self.service._get_or_create_tag(mock_cursor, '新标签')
        self.assertEqual(result, 2)
        # 验证出现了 INSERT 调用
        self.assertTrue(any('INSERT INTO strategy_tags' in c[0][0] for c in mock_cursor.execute.call_args_list))


if __name__ == '__main__':
    unittest.main(verbosity=2)
