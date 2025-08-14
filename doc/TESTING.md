# 测试文档 - 多策略系统分析

## 📋 测试概述（阶段性进度）

本目录包含多策略系统分析的完整测试套件，旨在确保系统功能的正确性、可用性和可靠性。

## 🧪 测试类型

### 1. 单元测试 (`unit/`)
测试系统的各个组件和方法的独立功能。

**覆盖范围**：
- 策略管理功能（CRUD操作）
- 标签系统管理
- 交易计算逻辑
- 策略评分算法
- 数据验证逻辑

**主要测试文件**：
- `test_trading_tracker.py`: TradingTracker核心功能测试

### 2. 功能测试 (`functional/`)
测试完整的业务流程和用户工作流。

**覆盖范围**：
- 完整交易生命周期
- 多标的组合管理
- 策略对比分析
- 交易修改流程
- 软删除和恢复

**主要测试文件**：
- `test_trading_workflows.py`: 交易工作流测试

### 3. 集成测试 (`integration/`)
测试系统各模块间的集成和端到端功能。

**覆盖范围**：
- Flask应用集成
- API接口功能
- 数据库集成
- Web界面集成
- 错误处理机制

**主要测试文件**：
- `test_system_integration.py`: 系统集成测试

## 🚀 运行测试

### 快速开始

```bash
# 运行所有测试
python3 run_tests.py

# 或者运行特定类型的测试
python3 run_tests.py unit        # 单元测试
python3 run_tests.py functional  # 功能测试
python3 run_tests.py integration # 集成测试
python3 run_tests.py performance # 性能测试（discover 全量收集，阈值50%）
```

阈值校验（由 `run_tests.py` 强制）：单元≥90%，功能≥80%，集成≥67%，性能≥50%。脚本还会运行模板/JS/CSS 静态检查与 MyPy（不阻塞通过）。

### 环境准备（测试隔离）

1. **激活虚拟环境**（推荐）：
   ```bash
   source venv/bin/activate
   ```

2. **安装依赖**（运行脚本将强制 `FLASK_ENV=testing`，并在应用工厂中为每次运行创建独立临时DB，杜绝污染产品库；符合“测试永不使用生产数据库”的约束）：
   ```bash
    python3 -m pip install -r requirements.txt
   ```

### 详细运行方式

#### 1. 使用测试运行脚本（推荐）

```bash
# 查看帮助
    python3 run_tests.py help

# 运行所有测试（默认）
    python3 run_tests.py all

# 运行单元测试
    python3 run_tests.py unit

# 运行功能测试
    python3 run_tests.py functional

# 运行集成测试
    python3 run_tests.py integration
    
# 运行性能测试（基于 discover，自动收集 tests/performance/ 全部用例；阈值50%）
    python3 run_tests.py performance
```

#### 2. 直接使用unittest

```bash
# 运行单个测试文件
python3 -m unittest tests.unit.test_trading_tracker -v

# 运行特定测试类
python3 -m unittest tests.unit.test_trading_tracker.TestTradingTracker -v

# 运行特定测试方法
python3 -m unittest tests.unit.test_trading_tracker.TestTradingTracker.test_create_strategy -v

# 发现并运行所有测试
python3 -m unittest discover tests/ -v
```

#### 3. 在项目根目录运行

```bash
# 从项目根目录运行
cd /path/to/mirror
python3 tests/unit/test_trading_tracker.py
python3 tests/functional/test_trading_workflows.py
python3 tests/integration/test_system_integration.py
```

## 📊 测试覆盖范围（阶段性指标）

### 功能需求覆盖

| 功能模块 | 单元测试 | 功能测试 | 集成测试 | 覆盖率 |
|---------|---------|---------|---------|--------|
| 策略管理 | ✅ | ✅ | ✅ | 100% |
| 交易记录 | ✅ | ✅ | ✅ | 100% |
| 数据保护 | ✅ | ✅ | ✅ | 100% |
| 财务计算 | ✅ | ✅ | ✅ | 100% |
| 策略评分 | ✅ | ✅ | ✅ | 100% |
| Web界面 | 部分 | ✅ | ✅ | 80% |
| API接口 | 部分 | 部分 | ✅ | 67% |

### 测试场景覆盖

#### 正常场景 ✅
- 完整交易流程
- 策略管理操作
- 数据修改和恢复
- 多维度分析

#### 边界场景 ✅
- 零交易策略评分
- 纯亏损交易计算
- 部分卖出处理
- 数量边界验证

#### 异常场景 ✅
- 无效数据处理
- 外键约束测试
- 错误处理机制
- 404页面处理

#### 性能场景 ✅
- 大量数据处理
- 查询响应时间
- 批量操作性能
 - 核心 API 冒烟（覆盖路由与错误分支，用于提升 routes 覆盖）

## 📝 测试数据

### 测试数据管理
- 每个测试使用独立的临时数据库
- 测试完成后自动清理数据
- 不影响生产数据

### 测试数据特点
- **策略数据**: 包含各种类型的测试策略
- **交易数据**: 涵盖盈利、亏损、部分卖出等场景
- **标签数据**: 预定义和自定义标签
- **历史数据**: 修改记录和删除历史

## 🔍 测试验证点

### 数据完整性验证
- [x] 数据库约束检查
- [x] 外键关系验证
- [x] 事务一致性确认
- [x] 软删除数据保护

### 计算准确性验证
- [x] 盈亏计算准确性
- [x] 费用扣除正确性
- [x] 评分算法准确性
- [x] 统计数据一致性

### 用户体验验证
- [x] 页面响应正常
- [x] 表单验证有效
- [x] 错误提示清晰
- [x] 操作流程顺畅

### API功能验证
- [x] 接口返回正确
- [x] JSON格式规范
- [x] 错误处理合理
- [x] 性能指标达标

## 🐛 故障排除

### 常见问题

#### 1. 导入错误
```
ModuleNotFoundError: No module named 'app'
```
**解决方案**: 确保在项目根目录运行测试，或使用测试运行脚本。

#### 2. 数据库错误
```
sqlite3.OperationalError: no such table: trades
```
**解决方案**: 数据库初始化问题，检查TradingTracker构造函数调用。

#### 3. 端口占用
```
Address already in use
```
**解决方案**: 检查8383端口是否被占用，或修改测试配置。

#### 4. 权限错误
```
PermissionError: [Errno 13] Permission denied
```
**解决方案**: 检查临时文件目录权限，或在虚拟环境中运行。

### 调试技巧

1. **增加详细输出**:
   ```bash
   python3 run_tests.py unit -v
   ```

2. **单独运行失败的测试**:
   ```bash
   python3 -m unittest tests.unit.test_trading_tracker.TestTradingTracker.test_specific_method -v
   ```

3. **查看测试数据**:
   在测试方法中添加断点或打印语句。

4. **检查日志输出**:
   测试过程中的详细输出包含调试信息。

## 📈 测试报告

### 运行结果示例
```
=== 测试总体摘要 ===
测试结束时间: 2025-08-06 14:30:15

各测试套件结果:
  ✅ 单元测试: 通过
  ✅ 功能测试: 通过  
  ✅ 集成测试: 通过

整体测试结果: ✅ 全部通过

🎉 恭喜！所有测试都通过了！
系统功能正常，质量达标。
```

### 测试指标
- **测试覆盖率**: 89% (44/49 需求项)
- **自动化程度**: 100%
- **执行时间**: < 60秒
- **测试用例数**: 50+

## 🔄 持续改进

### 测试维护
- 新功能开发时同步添加测试
- 定期review测试覆盖率
- 优化测试性能和稳定性
- 更新测试文档

### 扩展计划
- [ ] 添加性能压力测试
- [ ] 增加安全性测试
- [ ] 实现测试报告生成
- [ ] 集成CI/CD管道

---

**测试是质量保证的基石，让我们一起维护高质量的代码！** 🚀