#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试 - TradingTracker核心功能测试

测试范围：
- 策略管理功能
- 交易计算方法
- 数据验证逻辑
- 评分计算功能
"""

import unittest
import tempfile
import os
import sys
from decimal import Decimal
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import TradingTracker


class TestTradingTracker(unittest.TestCase):
    """TradingTracker核心功能单元测试"""
    
    def setUp(self):
        """测试前准备 - 创建临时数据库"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.tracker = TradingTracker(self.temp_db.name)
        
        # 创建测试策略
        success, message = self.tracker.create_strategy(
            name="测试策略",
            description="用于单元测试的策略",
            tag_names=["测试"]
        )
        if success:
            # 获取创建的策略ID
            strategies = self.tracker.get_all_strategies()
            test_strategy = next((s for s in strategies if s['name'] == "测试策略"), None)
            self.test_strategy_id = test_strategy['id'] if test_strategy else 1
        else:
            self.test_strategy_id = 1
    
    def tearDown(self):
        """测试后清理 - 删除临时数据库"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    # ========================================
    # 策略管理功能测试
    # ========================================
    
    def test_create_strategy(self):
        """测试策略创建功能"""
        strategy_id = self.tracker.create_strategy(
            name="新测试策略",
            description="策略描述",
            tag_names=["轮动", "测试"]
        )
        
        self.assertIsNotNone(strategy_id)
        
        # 验证策略是否正确创建
        strategy = self.tracker.get_strategy_by_id(strategy_id)
        self.assertEqual(strategy['name'], "新测试策略")
        self.assertEqual(strategy['description'], "策略描述")
        self.assertIn("轮动", strategy['tags'])
        self.assertIn("测试", strategy['tags'])
    
    def test_create_strategy_duplicate_name(self):
        """测试创建重复策略名称"""
        with self.assertRaises(ValueError):
            self.tracker.create_strategy(
                name="测试策略",  # 与setUp中创建的策略同名
                description="重复名称测试"
            )
    
    def test_update_strategy(self):
        """测试策略更新功能"""
        success = self.tracker.update_strategy(
            self.test_strategy_id,
            name="更新后的测试策略",
            description="更新后的描述",
            tag_names=["趋势", "更新"]
        )
        
        self.assertTrue(success)
        
        # 验证更新是否生效
        strategy = self.tracker.get_strategy_by_id(self.test_strategy_id)
        self.assertEqual(strategy['name'], "更新后的测试策略")
        self.assertEqual(strategy['description'], "更新后的描述")
        self.assertIn("趋势", strategy['tags'])
        self.assertIn("更新", strategy['tags'])
    
    def test_delete_strategy(self):
        """测试策略删除功能"""
        # 创建一个新策略用于删除测试
        strategy_id = self.tracker.create_strategy(
            name="待删除策略",
            description="将被删除的策略"
        )
        
        success = self.tracker.delete_strategy(strategy_id)
        self.assertTrue(success)
        
        # 验证策略是否被软删除
        strategy = self.tracker.get_strategy_by_id(strategy_id)
        self.assertIsNone(strategy)  # 软删除后查询不到
    
    def test_get_all_strategies(self):
        """测试获取所有策略"""
        strategies = self.tracker.get_all_strategies()
        
        # 应该包含setUp中创建的测试策略
        strategy_names = [s['name'] for s in strategies]
        self.assertIn("测试策略", strategy_names)
        
        # 验证策略数据完整性
        for strategy in strategies:
            self.assertIn('id', strategy)
            self.assertIn('name', strategy)
            self.assertIn('description', strategy)
            self.assertIn('tags', strategy)
            self.assertIn('trade_count', strategy)
    
    # ========================================
    # 标签管理功能测试
    # ========================================
    
    def test_create_tag(self):
        """测试标签创建功能"""
        tag_id = self.tracker.create_tag("新测试标签")
        self.assertIsNotNone(tag_id)
        
        # 验证标签是否正确创建
        tags = self.tracker.get_all_tags()
        tag_names = [tag['name'] for tag in tags]
        self.assertIn("新测试标签", tag_names)
    
    def test_create_duplicate_tag(self):
        """测试创建重复标签"""
        self.tracker.create_tag("重复标签")
        
        with self.assertRaises(ValueError):
            self.tracker.create_tag("重复标签")
    
    def test_update_tag(self):
        """测试标签更新功能"""
        tag_id = self.tracker.create_tag("原标签名")
        
        success = self.tracker.update_tag(tag_id, "新标签名")
        self.assertTrue(success)
        
        # 验证更新是否生效
        tags = self.tracker.get_all_tags()
        tag_names = [tag['name'] for tag in tags]
        self.assertIn("新标签名", tag_names)
        self.assertNotIn("原标签名", tag_names)
    
    def test_update_predefined_tag(self):
        """测试更新预定义标签（应该失败）"""
        # 预定义标签ID通常是1-4
        with self.assertRaises(ValueError):
            self.tracker.update_tag(1, "修改预定义标签")
    
    def test_delete_tag(self):
        """测试标签删除功能"""
        tag_id = self.tracker.create_tag("待删除标签")
        
        success = self.tracker.delete_tag(tag_id)
        self.assertTrue(success)
        
        # 验证标签是否被删除
        tags = self.tracker.get_all_tags()
        tag_names = [tag['name'] for tag in tags]
        self.assertNotIn("待删除标签", tag_names)
    
    # ========================================
    # 交易计算功能测试
    # ========================================
    
    def test_add_buy_transaction(self):
        """测试买入交易添加"""
        trade_id = self.tracker.add_buy_transaction(
            strategy=self.test_strategy_id,
            symbol_code="TEST001",
            symbol_name="测试标的",
            price=Decimal('10.50'),
            quantity=1000,
            transaction_date='2025-01-01',
            buy_reason="测试买入",
            transaction_fee=Decimal('5.00')
        )
        
        self.assertIsNotNone(trade_id)
        
        # 验证交易是否正确创建
        # 获取交易记录
        trades = self.tracker.get_all_trades()
        trade = next((t for t in trades if t['id'] == trade_id), None)
        self.assertEqual(trade['symbol_code'], "TEST001")
        self.assertEqual(trade['symbol_name'], "测试标的")
        self.assertEqual(trade['strategy_id'], self.test_strategy_id)
        self.assertEqual(trade['status'], 'open')
        self.assertEqual(float(trade['total_buy_amount']), 10500.0)  # 10.50 * 1000
    
    def test_add_sell_transaction(self):
        """测试卖出交易和盈亏计算"""
        # 先添加买入交易
        trade_id = self.tracker.add_buy_transaction(
            strategy=self.test_strategy_id,
            symbol_code="TEST002",
            symbol_name="测试卖出标的",
            price=Decimal('20.00'),
            quantity=500,
            transaction_date='2025-01-01',
            transaction_fee=Decimal('10.00')
        )
        
        # 添加卖出交易
        self.tracker.add_sell_transaction(
            trade_id=trade_id,
            price=Decimal('25.00'),
            quantity=500,
            transaction_date='2025-01-15',
            sell_reason="测试卖出",
            trade_log="测试交易日志",
            transaction_fee=Decimal('12.50')
        )
        
        # 验证盈亏计算
        # 获取交易记录
        trades = self.tracker.get_all_trades()
        trade = next((t for t in trades if t['id'] == trade_id), None)
        self.assertEqual(trade['status'], 'closed')
        
        # 预期盈亏：(25.00 - 20.00) * 500 - 10.00 - 12.50 = 2500 - 22.50 = 2477.50
        expected_profit = Decimal('2477.50')
        self.assertEqual(trade['total_profit_loss'], expected_profit)
        
        # 验证盈亏比例
        expected_ratio = (expected_profit / Decimal('10000')) * 100  # 投入10000元
        self.assertAlmostEqual(float(trade['total_profit_loss_pct']), float(expected_ratio), places=2)
    
    def test_partial_sell_transaction(self):
        """测试部分卖出交易"""
        # 添加买入交易
        trade_id = self.tracker.add_buy_transaction(
            strategy=self.test_strategy_id,
            symbol_code="TEST003",
            symbol_name="部分卖出测试",
            price=Decimal('15.00'),
            quantity=1000,
            transaction_date='2025-01-01',
            transaction_fee=Decimal('7.50')
        )
        
        # 部分卖出500股
        self.tracker.add_sell_transaction(
            trade_id=trade_id,
            price=Decimal('18.00'),
            quantity=500,
            transaction_date='2025-01-10',
            sell_reason="部分卖出",
            transaction_fee=Decimal('9.00')
        )
        
        # 验证交易状态和数量
        # 获取交易记录
        trades = self.tracker.get_all_trades()
        trade = next((t for t in trades if t['id'] == trade_id), None)
        self.assertEqual(trade['status'], 'open')  # 还有500股未卖出
        self.assertEqual(trade['remaining_quantity'], 500)
        self.assertEqual(trade['total_sell_quantity'], 500)
    
    def test_multiple_buy_same_strategy_symbol(self):
        """测试同一策略下同一标的的多次买入合并"""
        # 第一次买入
        trade_id = self.tracker.add_buy_transaction(
            strategy=self.test_strategy_id,
            symbol_code="TEST004",
            symbol_name="多次买入测试",
            price=Decimal('12.00'),
            quantity=300,
            transaction_date='2025-01-01',
            transaction_fee=Decimal('3.60')
        )
        
        # 第二次买入（应该合并到同一交易记录）
        second_trade_id = self.tracker.add_buy_transaction(
            strategy=self.test_strategy_id,
            symbol_code="TEST004",
            symbol_name="多次买入测试",
            price=Decimal('13.00'),
            quantity=200,
            date='2025-01-05',
            transaction_fee=Decimal('2.60')
        )
        
        # 应该是同一个交易ID
        self.assertEqual(trade_id, second_trade_id)
        
        # 验证合并后的数据
        # 获取交易记录
        trades = self.tracker.get_all_trades()
        trade = next((t for t in trades if t['id'] == trade_id), None)
        self.assertEqual(trade['total_buy_quantity'], 500)  # 300 + 200
        expected_total_amount = Decimal('12.00') * 300 + Decimal('13.00') * 200  # 3600 + 2600 = 6200
        self.assertEqual(trade['total_buy_amount'], expected_total_amount)
    
    # ========================================
    # 策略评分功能测试
    # ========================================
    
    def test_calculate_strategy_score_no_trades(self):
        """测试无交易策略的评分"""
        score = self.tracker.calculate_strategy_score(strategy_id=self.test_strategy_id)
        
        self.assertEqual(score['win_rate_score'], 0.0)
        self.assertEqual(score['profit_loss_ratio_score'], 0.0)
        self.assertEqual(score['frequency_score'], 0.0)
        self.assertEqual(score['total_score'], 0.0)
        self.assertEqual(score['rating'], '无数据')
        self.assertEqual(score['stats']['total_trades'], 0)
    
    def test_calculate_strategy_score_with_trades(self):
        """测试有交易策略的评分计算"""
        # 添加一个盈利交易
        trade_id1 = self.tracker.add_buy_transaction(
            strategy=self.test_strategy_id,
            symbol_code="SCORE001",
            symbol_name="评分测试1",
            price=Decimal('10.00'),
            quantity=100,
            transaction_date='2025-01-01',
            transaction_fee=Decimal('1.00')
        )
        
        self.tracker.add_sell_transaction(
            trade_id=trade_id1,
            price=Decimal('15.00'),
            quantity=100,
            transaction_date='2025-01-02',  # 持仓1天
            sell_reason="评分测试卖出",
            trade_log="盈利交易",
            transaction_fee=Decimal('1.50')
        )
        
        # 添加一个亏损交易
        trade_id2 = self.tracker.add_buy_transaction(
            strategy=self.test_strategy_id,
            symbol_code="SCORE002",
            symbol_name="评分测试2",
            price=Decimal('20.00'),
            quantity=100,
            date='2025-01-05',
            transaction_fee=Decimal('2.00')
        )
        
        self.tracker.add_sell_transaction(
            trade_id=trade_id2,
            price=Decimal('18.00'),
            quantity=100,
            date='2025-01-07',  # 持仓2天
            sell_reason="评分测试卖出",
            trade_log="亏损交易",
            transaction_fee=Decimal('1.80')
        )
        
        # 计算评分
        score = self.tracker.calculate_strategy_score(strategy_id=self.test_strategy_id)
        
        # 验证统计数据
        self.assertEqual(score['stats']['total_trades'], 2)
        self.assertEqual(score['stats']['winning_trades'], 1)
        self.assertEqual(score['stats']['losing_trades'], 1)
        
        # 验证胜率评分 (50% -> 5.0分)
        self.assertEqual(score['win_rate_score'], 5.0)
        
        # 验证频率评分 (平均1.5天，应该是7分)
        self.assertEqual(score['frequency_score'], 7.0)
        
        # 验证总评分
        expected_total = score['win_rate_score'] + score['profit_loss_ratio_score'] + score['frequency_score']
        self.assertEqual(score['total_score'], expected_total)
    
    def test_strategy_score_edge_cases(self):
        """测试策略评分的边界情况"""
        # 创建一个只有亏损交易的策略
        success, message = self.tracker.create_strategy(
            name="纯亏损策略",
            description="只有亏损交易的策略"
        )
        # 获取创建的策略ID
        strategies = self.tracker.get_all_strategies()
        loss_strategy = next((s for s in strategies if s['name'] == "纯亏损策略"), None)
        loss_strategy_id = loss_strategy['id'] if loss_strategy else 2
        
        trade_id = self.tracker.add_buy_transaction(
            strategy=loss_strategy_id,
            symbol_code="LOSS001",
            symbol_name="亏损测试",
            price=Decimal('50.00'),
            quantity=100,
            transaction_date='2025-01-01',
            transaction_fee=Decimal('5.00')
        )
        
        self.tracker.add_sell_transaction(
            trade_id=trade_id,
            price=Decimal('40.00'),
            quantity=100,
            transaction_date='2025-01-02',
            sell_reason="亏损卖出",
            trade_log="测试亏损",
            transaction_fee=Decimal('4.00')
        )
        
        score = self.tracker.calculate_strategy_score(strategy_id=loss_strategy_id)
        
        # 纯亏损策略的胜率评分应该是0
        self.assertEqual(score['win_rate_score'], 0.0)
        # 盈亏比评分应该是0（亏损比<1）
        self.assertEqual(score['profit_loss_ratio_score'], 0.0)
    
    # ========================================
    # 数据验证功能测试
    # ========================================
    
    def test_validate_buy_transaction_data(self):
        """测试买入交易数据验证"""
        # 测试无效价格
        with self.assertRaises((ValueError, TypeError)):
            self.tracker.add_buy_transaction(
                strategy=self.test_strategy_id,
                symbol_code="INVALID",
                symbol_name="无效测试",
                price=Decimal('-10.00'),  # 负价格
                quantity=100,
                transaction_date='2025-01-01'
            )
        
        # 测试无效数量
        with self.assertRaises((ValueError, TypeError)):
            self.tracker.add_buy_transaction(
                strategy=self.test_strategy_id,
                symbol_code="INVALID",
                symbol_name="无效测试",
                price=Decimal('10.00'),
                quantity=-100,  # 负数量
                transaction_date='2025-01-01'
            )
    
    def test_validate_sell_transaction_data(self):
        """测试卖出交易数据验证"""
        # 先创建一个买入交易
        trade_id = self.tracker.add_buy_transaction(
            strategy=self.test_strategy_id,
            symbol_code="VALID",
            symbol_name="有效测试",
            price=Decimal('10.00'),
            quantity=100,
            transaction_date='2025-01-01'
        )
        
        # 测试卖出数量超过持仓
        with self.assertRaises(ValueError):
            self.tracker.add_sell_transaction(
                trade_id=trade_id,
                price=Decimal('12.00'),
                quantity=200,  # 超过持仓100股
                transaction_date='2025-01-02'
            )
    
    def test_date_validation(self):
        """测试日期格式验证"""
        # 这个测试取决于具体的日期验证实现
        # 如果系统支持多种日期格式，需要相应调整测试
        trade_id = self.tracker.add_buy_transaction(
            strategy=self.test_strategy_id,
            symbol_code="DATE_TEST",
            symbol_name="日期测试",
            price=Decimal('10.00'),
            quantity=100,
            transaction_date='2025-01-01'  # 标准格式
        )
        
        self.assertIsNotNone(trade_id)
        
        # 获取交易记录
        trades = self.tracker.get_all_trades()
        trade = next((t for t in trades if t['id'] == trade_id), None)
        self.assertEqual(trade['open_date'], '2025-01-01')


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)