#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试 - 系统集成测试

测试范围：
- Flask应用集成测试
- API接口功能测试
- 数据库集成测试
- 端到端用户流程测试
"""

import unittest
import tempfile
import os
import sys
import json
from decimal import Decimal

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestSystemIntegration(unittest.TestCase):
    """系统集成测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # 创建Flask应用实例
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.temp_db.name
        
        # 重新初始化应用的数据库服务以使用测试数据库
        self.app.db_service = DatabaseService(self.temp_db.name)
        self.app.trading_service = TradingService(self.app.db_service)
        self.app.strategy_service = StrategyService(self.app.db_service)
        self.app.analysis_service = AnalysisService(self.app.db_service)
        self.app.tracker = self.app.trading_service
        
        # 创建应用上下文
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # 创建测试客户端
        self.client = self.app.test_client()
        
        # 使用应用实例的服务
        self.db_service = self.app.db_service
        self.trading_service = self.app.trading_service
        self.strategy_service = self.app.strategy_service
        self.analysis_service = self.app.analysis_service
        
        # 保持向后兼容，创建tracker别名
        self.tracker = self.trading_service
        
        # 将服务注入到app实例，这样路由中的current_app就能访问到
        # 这模拟了create_app()中的服务初始化
        
        # 创建测试策略
        success, message = self.strategy_service.create_strategy(
            name="集成测试策略",
            description="用于集成测试的策略",
            tag_names=["测试"]
        )
        if not success:
            print(f"策略创建失败: {message}")
        # 获取策略ID
        strategies = self.strategy_service.get_all_strategies()
        strategy = next((s for s in strategies if s['name'] == "集成测试策略"), None)
        self.test_strategy_id = strategy['id'] if strategy else None
        if not strategy:
            print("警告: 集成测试策略创建失败或未找到")
    
    def tearDown(self):
        """测试后清理"""
        # 清理应用上下文
        if hasattr(self, 'app_context'):
            self.app_context.pop()
        
        # 清理临时数据库
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    # ========================================
    # Web应用集成测试
    # ========================================
    
    def test_homepage_integration(self):
        """测试首页集成功能"""
        print("\n=== 测试首页集成功能 ===")
        
        # 访问首页
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'\xe9\xa6\x96\xe9\xa1\xb5', response.data)  # "首页" 的UTF-8编码
        print("✓ 首页访问正常")
        
        # 验证首页包含策略信息
        response_text = response.data.decode('utf-8')
        self.assertIn('集成测试策略', response_text)
        print("✓ 首页显示策略信息")
        
        # 验证首页包含必要的导航元素
        self.assertIn('新建买入', response_text)
        self.assertIn('查看交易', response_text)
        self.assertIn('策略管理', response_text)
        print("✓ 首页导航元素完整")
    
    def test_strategy_management_integration(self):
        """测试策略管理页面集成"""
        print("\n=== 测试策略管理集成 ===")
        
        # 访问策略管理页面
        response = self.client.get('/strategies')
        self.assertEqual(response.status_code, 200)
        
        response_text = response.data.decode('utf-8')
        self.assertIn('策略管理', response_text)
        self.assertIn('集成测试策略', response_text)
        print("✓ 策略管理页面正常")
        
        # 测试创建策略
        response = self.client.post('/strategy/create', data={
            'name': 'Web测试策略',
            'description': '通过Web界面创建的测试策略',
            'tag_names': ['测试', '集成']
        })
        
        # 应该重定向到策略管理页面
        self.assertEqual(response.status_code, 302)
        print("✓ 策略创建功能正常")
        
        # 验证策略是否成功创建
        response = self.client.get('/strategies')
        response_text = response.data.decode('utf-8')
        self.assertIn('Web测试策略', response_text)
        print("✓ 新策略显示正常")
    
    def test_trading_pages_integration(self):
        """测试交易页面集成"""
        print("\n=== 测试交易页面集成 ===")
        
        # 访问买入页面
        response = self.client.get('/add_buy')
        self.assertEqual(response.status_code, 200)
        
        response_text = response.data.decode('utf-8')
        self.assertIn('新建买入', response_text)
        self.assertIn('集成测试策略', response_text)  # 策略选择框应该包含测试策略
        print("✓ 买入页面正常")
        
        # 测试买入交易提交
        response = self.client.post('/add_buy', data={
            'strategy': self.test_strategy_id,
            'symbol_code': 'TEST001',
            'symbol_name': '集成测试股票',
            'price': '15.50',
            'quantity': '1000',
            'transaction_date': '2025-01-01',
            'buy_reason': 'Web界面测试买入',
            'transaction_fee': '4.65'
        })
        
        # 应该重定向到交易列表页面
        self.assertEqual(response.status_code, 302)
        print("✓ 买入交易提交正常")
        
        # 访问交易列表页面
        response = self.client.get('/trades')
        self.assertEqual(response.status_code, 200)
        
        response_text = response.data.decode('utf-8')
        self.assertIn('TEST001', response_text)
        self.assertIn('集成测试股票', response_text)
        print("✓ 交易列表显示正常")
    
    def test_strategy_scores_integration(self):
        """测试策略评分页面集成"""
        print("\n=== 测试策略评分集成 ===")
        
        # 先创建一些测试数据
        success, trade_id = self.tracker.add_buy_transaction(
            strategy=self.test_strategy_id,
            symbol_code="SCORE001",
            symbol_name="评分测试股",
            price=Decimal('10.00'),
            quantity=500,
            transaction_date='2025-01-01',
            transaction_fee=Decimal('1.50')
        )
        self.assertTrue(success)
        
        self.tracker.add_sell_transaction(
            trade_id=trade_id,
            price=Decimal('12.50'),
            quantity=500,
            transaction_date='2025-01-05',
            sell_reason="测试卖出",
            trade_log="评分测试交易",
            transaction_fee=Decimal('1.88')
        )
        
        # 访问策略评分页面
        response = self.client.get('/strategy_scores')
        self.assertEqual(response.status_code, 200)
        
        response_text = response.data.decode('utf-8')
        self.assertIn('策略评分', response_text)
        self.assertIn('集成测试策略', response_text)
        print("✓ 策略评分页面正常")
        
        # 访问策略详情页面
        response = self.client.get(f'/strategy_detail/{self.test_strategy_id}')
        self.assertEqual(response.status_code, 200)
        
        response_text = response.data.decode('utf-8')
        self.assertIn('总体表现', response_text)
        self.assertIn('集成测试策略', response_text)
        print("✓ 策略详情页面正常")
    
    # ========================================
    # API接口集成测试
    # ========================================
    
    def test_api_strategy_score(self):
        """测试策略评分API"""
        print("\n=== 测试策略评分API ===")
        
        # 测试API调用
        response = self.client.get(f'/api/strategy_score?strategy_id={self.test_strategy_id}')
        self.assertEqual(response.status_code, 200)
        
        # 验证返回的JSON数据
        response_data = json.loads(response.data)
        self.assertIn('success', response_data)
        self.assertTrue(response_data['success'])
        self.assertIn('data', response_data)
        
        data = response_data['data']
        self.assertIn('stats', data)
        # 新的API格式只返回统计数据，不返回评分
        stats = data['stats']
        self.assertIn('total_trades', stats)
        self.assertIn('win_rate', stats)
        print("✓ 策略评分API返回数据正确")
        
        # 测试带日期范围的API调用
        response = self.client.get(
            f'/api/strategy_score?strategy_id={self.test_strategy_id}'
            '&start_date=2025-01-01&end_date=2025-12-31'
        )
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.data)
        self.assertIn('success', response_data)
        self.assertTrue(response_data['success'])
        self.assertIn('data', response_data)
        data = response_data['data']
        self.assertIn('total_score', data)
        print("✓ 带日期范围的策略评分API正常")
    
    def test_api_strategies(self):
        """测试策略列表API"""
        print("\n=== 测试策略列表API ===")
        
        response = self.client.get('/api/strategies')
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.data)
        self.assertIn('success', response_data)
        self.assertTrue(response_data['success'])
        self.assertIn('data', response_data)
        
        data = response_data['data']
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        
        # 验证策略数据结构
        strategy = data[0]
        self.assertIn('id', strategy)
        self.assertIn('name', strategy)
        self.assertIn('description', strategy)
        self.assertIn('tags', strategy)
        print("✓ 策略列表API返回数据正确")
    
    def test_api_tags(self):
        """测试标签管理API"""
        print("\n=== 测试标签管理API ===")
        
        # 获取标签列表
        response = self.client.get('/api/tags')
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.data)
        self.assertIn('success', response_data)
        self.assertTrue(response_data['success'])
        self.assertIn('data', response_data)
        
        data = response_data['data']
        self.assertIsInstance(data, list)
        print("✓ 标签列表API正常")
        
        # TODO: 标签管理API未实现，跳过相关测试
        print("✓ 标签CRUD API功能待实现，跳过测试")
    
    def test_api_strategy_trend(self):
        """测试策略趋势API"""
        print("\n=== 测试策略趋势API ===")
        
        response = self.client.get(f'/api/strategy_trend?strategy_id={self.test_strategy_id}&period_type=year')
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.data)
        self.assertIn('success', response_data)
        self.assertTrue(response_data['success'])
        self.assertIn('data', response_data)
        data = response_data['data']
        self.assertIsInstance(data, list)
        print("✓ 策略趋势API返回数据正确")
    
    # ========================================
    # 数据库集成测试
    # ========================================
    
    def test_database_transaction_integrity(self):
        """测试数据库事务完整性"""
        print("\n=== 测试数据库事务完整性 ===")
        
        # 创建关联数据
        success, message = self.strategy_service.create_strategy(
            name="事务测试策略",
            description="测试数据库事务",
            tag_names=["事务", "测试"]
        )
        
        # 获取策略ID
        strategies = self.strategy_service.get_all_strategies()
        strategy = next((s for s in strategies if s['name'] == "事务测试策略"), None)
        strategy_id = strategy['id']
        
        success, trade_id = self.tracker.add_buy_transaction(
            strategy=strategy_id,
            symbol_code="TX001",
            symbol_name="事务测试股",
            price=Decimal('20.00'),
            quantity=100,
            transaction_date='2025-01-01',
            transaction_fee=Decimal('0.60')
        )
        
        # 验证数据关联性
        trade = self.tracker.get_trade_by_id(trade_id)
        self.assertEqual(trade['strategy_id'], strategy_id)
        
        strategy = self.strategy_service.get_strategy_by_id(strategy_id)
        # trade_count字段不存在，使用策略评分来验证交易数量
        score = self.analysis_service.calculate_strategy_score(strategy_id=strategy['id'])
        self.assertEqual(score['stats']['total_trades'], 0)  # 开仓交易不计入评分
        print("✓ 数据库关联数据正确")
        
        # 测试外键约束（尝试引用不存在的策略）
        success, message = self.tracker.add_buy_transaction(
            strategy=99999,  # 不存在的策略ID
            symbol_code="INVALID",
            symbol_name="无效测试",
            price=Decimal('10.00'),
            quantity=100,
            transaction_date='2025-01-01'
        )
        self.assertFalse(success)
        self.assertIn("不存在", message)
        print("✓ 外键约束正常工作")
        
        # 测试软删除完整性
        result = self.tracker.soft_delete_trade(
            trade_id=trade_id,
            confirmation_code="TX123",
            delete_reason="事务测试删除",
            operator_note="测试用户"
        )
        self.assertTrue(result)
        
        # 验证软删除后数据状态
        active_trades = self.tracker.get_all_trades()
        active_trade_ids = [t['id'] for t in active_trades]
        self.assertNotIn(trade_id, active_trade_ids)
        print("✓ 软删除事务完整性正确")
    
    def test_database_performance(self):
        """测试数据库性能"""
        print("\n=== 测试数据库性能 ===")
        
        import time
        
        # 批量创建数据测试性能
        start_time = time.time()
        
        success, message = self.strategy_service.create_strategy(
            name="性能测试策略",
            description="用于性能测试"
        )
        
        # 获取策略ID
        strategies = self.strategy_service.get_all_strategies()
        strategy = next((s for s in strategies if s['name'] == "性能测试策略"), None)
        strategy_id = strategy['id']
        
        # 创建100笔交易测试性能
        for i in range(100):
            success, trade_id = self.tracker.add_buy_transaction(
                strategy=strategy_id,
                symbol_code=f"PERF{i:03d}",
                symbol_name=f"性能测试股{i}",
                price=Decimal('10.00') + (i % 10),
                quantity=100,
                transaction_date='2025-01-01',
                transaction_fee=Decimal('0.30')
            )
            
            # 每隔10笔做一次平仓
            if i % 10 == 9:
                self.tracker.add_sell_transaction(
                    trade_id=trade_id,
                    price=Decimal('12.00'),
                    quantity=100,
                    transaction_date='2025-01-15',
                    sell_reason="性能测试",
                    trade_log="性能测试交易",
                    transaction_fee=Decimal('0.36')
                )
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"✓ 创建100笔交易耗时：{elapsed_time:.2f}秒")
        self.assertLess(elapsed_time, 10.0)  # 应该在10秒内完成
        
        # 测试查询性能
        start_time = time.time()
        all_trades = self.tracker.get_all_trades()
        query_time = time.time() - start_time
        
        print(f"✓ 查询{len(all_trades)}笔交易耗时：{query_time:.3f}秒")
        self.assertLess(query_time, 1.0)  # 查询应该在1秒内完成
        
        # 测试评分计算性能
        start_time = time.time()
        score = self.analysis_service.calculate_strategy_score(strategy_id=strategy_id)
        calc_time = time.time() - start_time
        
        print(f"✓ 计算策略评分耗时：{calc_time:.3f}秒")
        self.assertLess(calc_time, 2.0)  # 评分计算应该在2秒内完成
    
    # ========================================
    # 端到端流程测试
    # ========================================
    
    def test_end_to_end_user_workflow(self):
        """测试端到端用户工作流"""
        print("\n=== 测试端到端用户工作流 ===")
        
        # 模拟完整用户操作流程
        
        # 1. 用户访问首页
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        print("✓ 步骤1：访问首页")
        
        # 2. 用户创建新策略
        response = self.client.post('/strategy/create', 
                                  data={
                                      'name': '端到端测试策略',
                                      'description': '完整流程测试策略',
                                      'tag_names': ['端到端', '测试']
                                  },
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(response.status_code, 200)
        # 验证创建成功
        response_data = response.get_json()
        self.assertTrue(response_data['success'])
        
        # 获取新创建的策略ID
        strategies = self.strategy_service.get_all_strategies()
        e2e_strategy = next(s for s in strategies if s['name'] == '端到端测试策略')
        e2e_strategy_id = e2e_strategy['id']
        print(f"✓ 步骤2：创建策略，ID: {e2e_strategy_id}")
        
        # 3. 用户添加买入交易
        response = self.client.post('/add_buy', data={
            'strategy': e2e_strategy_id,
            'symbol_code': 'E2E001',
            'symbol_name': '端到端测试股',
            'price': '25.00',
            'quantity': '200',
            'transaction_date': '2025-01-01',
            'buy_reason': '端到端测试买入',
            'transaction_fee': '1.50'
        })
        self.assertEqual(response.status_code, 302)
        print("✓ 步骤3：添加买入交易")
        
        # 4. 用户查看交易列表
        response = self.client.get('/trades')
        self.assertEqual(response.status_code, 200)
        
        response_text = response.data.decode('utf-8')
        self.assertIn('E2E001', response_text)
        print("✓ 步骤4：查看交易列表")
        
        # 5. 获取交易ID并执行卖出
        trades = self.tracker.get_all_trades()
        # 确保获取的是测试创建的交易（E2E001，端到端测试策略，200股）
        e2e_trade = next((t for t in trades 
                         if t['symbol_code'] == 'E2E001' 
                         and t['strategy_name'] == '端到端测试策略'
                         and t['total_buy_quantity'] == 200), None)
        if not e2e_trade:
            self.fail("未找到端到端测试创建的E2E001交易")
        e2e_trade_id = e2e_trade['id']
        print(f"找到端到端测试交易，ID: {e2e_trade_id}, 标的: {e2e_trade['symbol_code']}, 数量: {e2e_trade['total_buy_quantity']}")
        
        response = self.client.post(f'/add_sell/{e2e_trade_id}', data={
            'price': '28.50',
            'quantity': '200',
            'transaction_date': '2025-02-01',
            'sell_reason': '端到端测试卖出',
            'trade_log': '端到端测试完成',
            'transaction_fee': '1.71'
        })
        self.assertEqual(response.status_code, 302)
        print("✓ 步骤5：执行卖出交易")
        
        # 6. 用户查看交易详情
        response = self.client.get(f'/trade_details/{e2e_trade_id}')
        self.assertEqual(response.status_code, 200)
        
        response_text = response.data.decode('utf-8')
        self.assertIn('已平仓', response_text)
        print("✓ 步骤6：查看交易详情")
        
        # 7. 用户查看策略评分
        response = self.client.get('/strategy_scores')
        self.assertEqual(response.status_code, 200)
        
        response_text = response.data.decode('utf-8')
        self.assertIn('端到端测试策略', response_text)
        print("✓ 步骤7：查看策略评分")
        
        # 8. 用户查看策略详情
        response = self.client.get(f'/strategy_detail/{e2e_strategy_id}')
        self.assertEqual(response.status_code, 200)
        print("✓ 步骤8：查看策略详情")
        
        # 9. 验证最终数据一致性
        final_trade = self.tracker.get_trade_by_id(e2e_trade_id)
        self.assertEqual(final_trade['status'], 'closed')
        self.assertGreater(final_trade['total_profit_loss'], 0)  # 应该是盈利的
        
        final_strategy = self.strategy_service.get_strategy_by_id(e2e_strategy_id)
        self.assertIsNotNone(final_strategy)
        
        score = self.analysis_service.calculate_strategy_score(strategy_id=e2e_strategy_id)
        self.assertEqual(score['stats']['total_trades'], 1)
        self.assertEqual(score['stats']['winning_trades'], 1)
        
        print("✓ 步骤9：数据一致性验证通过")
        print("=== 端到端用户工作流测试完成 ===\n")
    
    def test_error_handling_integration(self):
        """测试错误处理集成"""
        print("\n=== 测试错误处理集成 ===")
        
        # 测试访问不存在的页面
        response = self.client.get('/nonexistent')
        self.assertEqual(response.status_code, 404)
        print("✓ 404错误处理正常")
        
        # 测试访问不存在的交易详情
        response = self.client.get('/trade/99999')
        # 根据具体实现，可能返回404或显示错误信息
        self.assertIn(response.status_code, [200, 404])
        print("✓ 不存在交易的错误处理正常")
        
        # 测试提交无效数据
        response = self.client.post('/add_buy', data={
            'strategy_id': 'invalid',  # 无效策略ID
            'symbol_code': '',  # 空值
            'price': 'not_a_number',  # 无效价格
        })
        # 应该返回400或重新显示表单with错误信息
        self.assertIn(response.status_code, [200, 400])
        print("✓ 无效数据错误处理正常")
        
        # 测试API错误处理
        response = self.client.get('/api/strategy_score?strategy_id=invalid')
        self.assertIn(response.status_code, [200, 400])
        print("✓ API错误处理正常")
        
        print("=== 错误处理集成测试完成 ===\n")


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)