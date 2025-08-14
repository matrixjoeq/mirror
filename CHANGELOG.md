## Changelog

### 2025-08-14
- 文档同步与校准
  - 更新根 `README.md`：项目导航、核心特性、测试阈值（单元≥90%/功能≥80%/集成≥67%/性能≥50%）、管理工具 `/admin/db/diagnose`、项目结构与运行说明。
  - 更新 `doc/README.md`：加入 `admin_service.py` 与 `admin_routes.py`，补充最新 REST API 端点表（tags/symbol_lookup/quick_sell/strategy_score/strategy_trend 等），数据表说明包含费用与净利字段。
  - 更新 `doc/ARCHITECTURE.md`：补充 admin 路由，记录数据库 SQL 预执行安全校验与费用字段口径。
  - 更新 `doc/REQUIREMENTS.md`：修正“实现位置”到具体 services/routes/templates；明确计算模块 `trade_calculation.py` 与自动校准 `admin_service.py:auto_fix`。
  - 更新 `doc/TESTING.md`：明确各测试套件覆盖率阈值、静态检查（djlint/eslint/stylelint）与 MyPy 执行说明；强调测试数据库隔离。
  - 更新 `doc/TESTING_REPORT.md`：在覆盖概述中加入阈值说明。
  - 更新 `doc/PROGRESS.md`：覆盖率数字与软删除实现描述对齐现状（TOTAL≈53% 性能覆盖达标）。

### 2025-08-13
- 性能覆盖与测试
  - 性能测试改为基于 discover 方式收集整个 `tests/performance/`，自动纳入新增用例
  - 新增 `tests/performance/test_perf_api_smoke.py` 涵盖核心 API 的性能/冒烟路径，提升 routes 覆盖
  - 性能覆盖阈值提升至 50%，现性能覆盖 TOTAL ≈ 53%，通过阈值校验
- 导航与可用性
  - 在顶部导航与首页“快速操作”增加“数据库管理”入口，指向 `/admin/db/diagnose`
- 数据一致性校验/校准（以明细为准）
  - 统一口径：总买入/卖出金额为不含费成交额，费用单列（买入费/卖出费/总费用/费用占比）
  - 修复二次校验将费用计入“总买入金额”的错误；比较引入字段级精度（金额3位小数、比例2位、数量整数）
  - 自动校准与再次校验口径一致，不再出现“校准正确但复检错误”的问题
- 服务与数据库
  - `TradingService.update_trade_record` 重算汇总：修正买卖金额与费用派生、净利率分母使用“已卖出部分买入成本”
  - `TradingService.get_all_trades` 返回补齐费用相关字段，前端列表直接显示
  - 迁移：为 `trades` 表增加 `total_buy_fees`、`total_sell_fees`、`total_fees`、`total_fee_ratio_pct`

### 2025-08-12 (夜间)
- 交易与展示对齐（WAC 口径）
  - 快捷卖出对话框文案改为加权平均成本法（WAC）说明，和系统实际口径一致
  - 交易详情页“卖出交易金额”改为显示未扣费成交额：价格 × 数量；卖出费用单独一列展示
  - 保持首页概览为四张卡片（移除总净利率卡片展示），首页统计仍按统一口径聚合
- 统一净利润口径与兜底
  - 已平仓交易净利润按“毛利 − 买入费 − 卖出费”，必要时兜底以避免历史数据卖出份额异常导致净利为 0 的情况
- 测试
  - 全量测试均通过；覆盖率（阶段性）单元 91% / 功能 81% / 集成 66% / 性能 45%
  - 规范：在 venv 中运行测试（Windows: `.\\venv\\Scripts\\activate`；macOS/Linux: `source venv/bin/activate`）

### 2025-08-11 (晚间)
- 交易盈亏口径与统计增强：
  - 新增明细级字段：`gross_profit`/`gross_profit_pct`、`net_profit`/`net_profit_pct`
  - 新增主表聚合字段：`total_gross_profit`、`total_net_profit`、`total_net_profit_pct`；旧字段 `total_profit_loss` 继续表示毛利
  - 卖出盈亏改为不含费用的价差口径：盈亏金额=(卖价−买入均价[不含费])×份额；盈亏比例=(卖价−买入均价[不含费])/买入均价×100%
  - 快捷卖出与常规卖出统一使用上述口径
- 交易详情概览重构：
  - 买入：展示总成交（不含费）、总买入费用、平均价（不含费）
  - 卖出：展示总成交（不含费）、总卖出费用、平均价（不含费）
  - 盈利：展示毛利润/毛利率、净利润/净利率（净利润=毛利润−总买入费用−总卖出费用）
- 快捷卖出改进：
  - 支持手动份额输入，默认日期为当天，比例按钮“1/5、1/4、1/3、1/2、全部”
  - 超额校验：基于FIFO的明细级剩余校验；剩余为0禁用按钮
- 分析统计增强：
  - 统计返回中新增：`total_gross_return`、`total_net_return`、`total_net_return_rate`、`avg_net_return_per_trade`
  - 兼容单元测试的Mock路径
- 测试与隔离：
  - 运行脚本强制 `FLASK_ENV=testing`；应用工厂在testing环境为每次运行生成独立临时DB，彻底隔离产品库
  - 全量测试通过：单元/功能/集成/性能

### 2025-08-11
- 文档对齐最新实现与覆盖率：
  - 更新 `doc/REQUIREMENTS.md` 至 v3.0，测试需求全部标记为已实现；总体完成度 100%。
  - 更新 `doc/README.md`、根 `README.md`：统一使用 python3 命令；环境要求 Python 3.9+；补充阶段性覆盖率。
  - 更新 `doc/PROGRESS.md` 与 `doc/TESTING_REPORT.md`：同步覆盖率（行/分支）与测试日期。
- 覆盖率（来自 `reports/` 最新报告）：
  - 单元：行92.7% / 分支92.4%
  - 功能：行82.8% / 分支78.8%
  - 集成：行74.0% / 分支69.5%
  - 性能：行49.4% / 分支31.9%（用例已全通过，覆盖率后续提升）


