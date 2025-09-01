## Changelog

### 2025-08-30
- tools: 新增 `tools/cn10yt_tool.py` 小工具，可抓取中国十年期国债收益率（`HQ.CN10YT`）历史数据（优先 TradingEconomics，回退 Investing.com），导出 CSV 并生成日度 K 线图，同时计算“当前收益率在历史中的百分位”用于性价比衡量。
- 依赖：新增 `requests` 与 `mplfinance`（绘制 K 线）。
- tools: 新增 `tools/cn30yt_tool.py` 小工具，抓取中国三十年期国债收益率历史数据，生成 CSV 与 K 线，并输出当前收益率历史百分位；仅使用合规数据源（TradingEconomics 来宾接口，回退至 Investing 历史表格）。
  - 调整：移除 TradingEconomics 抓取尝试（该服务需要付费 API Key），改为优先使用 AkShare（`bond_china_yield`），失败时回退 Investing 历史表格。
  - 增强：`tools/cn10yt_tool.py` 与 `tools/cn30yt_tool.py` 支持增量写入本地 SQLite（默认 `database/bond_yields.db`），基线起始日期固定为 2009-07-01；新增 CLI：`--db` 与 `--force-full`。

### 2025-08-30 (later)
- tools: 新增统一脚本 `tools/bond_yield_tool.py`，合并 CN10Y / CN30Y，并新增 US10Y；
  - 起始日期统一调整为 2006-03-01；
  - 保持增量入库到 `database/bond_yields.db`，各自表名：`cn10y_yield`、`cn30y_yield`、`us10y_yield`；
  - 数据源：CN 使用 AkShare；US10Y 仅使用 FRED API（`fredapi`，系列 DGS10）；移除所有网页爬取备用路径与代理设置。
  - CLI: `--instruments CN10Y,CN30Y,US10Y|all`，`--source auto|akshare|investing`，`--db`，`--no-plot`，`--full-update`，`--fred-api-key`；
  - 输出各自 CSV 与可选 K 线 PNG。

#### 2025-08-30 (window)
- tools: `bond_yield_tool.py` 新增绘图/百分位窗口选项 `--window`（`all`|`10y`|`5y`|`1y`，默认 `all`）。
  - 仅影响绘图与当前值百分位统计所使用的数据窗口，不影响数据库的全量历史与增量写入。
  - K 线图标题包含窗口标签；控制台输出新增 `Window` 与窗口内百分位。

## feat: 宏观观察体系 MVP 脚手架
- 新增文档 `doc/plans/macro_observation_mvp.md`，定义目标、指标、数据源、API 与页面。
- 新增服务层 `services/macro_service.py`、仓储层 `services/macro_repository.py`、Provider 适配目录 `services/data_providers/`。
- 新增页面路由 `routes/macro_routes.py` 与 API 路由 `routes/api_macro.py`（/api/macro/snapshot|country|score）。
- 新增模板 `templates/macro_dashboard.html` 与 `templates/macro_country.html`。
- 在 `app.py` 注册 `macro_bp` 与 `api_macro_bp`，并在应用实例上挂载 `macro_service`。
- 兼容数据库层：新增宏观/商品/汇率/评分表结构的幂等创建逻辑（在仓储初始化中确保）。
  - 增量实现：
    - `MacroRepository` 新增 `bulk_upsert_macro_series`、`fetch_macro_series_by_economy`、`has_any_data`、`upsert_score`；
    - `MacroRepository` 继续增强：`bulk_upsert_commodity_series`、`bulk_upsert_fx_series`、`fetch_latest_by_indicator`；
    - `MacroService` 集成仓储与配置，首次访问自动写入最小样本数据；`get_snapshot` 基于最新值做方向一致的 min-max 聚合输出矩阵与排行；`get_country` 返回序列与占位综合分；新增 `refresh_all()`；
    - `routes/api_macro.py` 新增 `POST /api/macro/refresh`；
    - 新增配置与Provider：`services/macro_config.py`（经济体/指标方向/开关）、`services/data_providers/market_provider.py`（商品/汇率样本+预留联网路径）；
    - 评分与可视化：`MacroService.get_snapshot` 支持 `zscore`、`percentile`、`trend`，加入权重与分项 `by_indicator`；`templates/macro_dashboard.html` 增加视图/窗口切换、热力矩阵与排行；
    - 测试增强：扩展 `tests/unit/test_macro_mvp_scaffolding.py`；新增 `tests/unit/test_macro_repository_and_service.py`、`tests/unit/test_macro_providers_and_repo_readers.py`、`tests/unit/test_macro_scoring_methods.py`、`tests/functional/test_macro_routes_and_api.py` 覆盖刷新与评分路径、API 与页面。
    - 刷新与缓存：新增 `refresh_meta` 表记录刷新历史；`POST /api/macro/refresh` 写入记录；`GET /api/macro/status` 查询刷新历史；`/api/macro/snapshot` 支持 `window`/`economies`/`indicators` 过滤，并引入进程内5分钟TTL缓存与 `nocache=1` 绕过；刷新后自动失效缓存。
    - 数据库完全隔离：`MacroRepository` 强制使用 `MACRO_DB_PATH`（默认 `database/macro_observation.db`），与交易库 `DB_PATH` 物理隔离；测试环境下在应用工厂为两者分别分配独立临时文件。

## feat: 中观观察体系（全球股指趋势）脚手架
- 配置：新增 `MESO_DB_PATH`（默认 `database/meso_observation.db`）。
- 仓储：`services/meso_repository.py`（`index_prices`/`trend_scores`/`refresh_meta`）。
- 服务：`services/meso_service.py` 提供最小 API：
  - 列表：`list_indexes()`（占位清单，后续从配置/provider 注入）
  - 序列：`get_trend_series(symbol, window, currency)`（读取已存储分数与价格）
  - 对比：`get_compare_series(symbols<=10, window, currency)`
- API：`/api/meso/indexes`、`/api/meso/trend_series`、`/api/meso/compare_series`
- 页面：`/meso` → `templates/meso_dashboard.html`（指数清单与 API 入口）

### 2025-08-16
- 分析指标增强：
  - 在策略评分计算中补充并返回夏普比率与卡玛比率字段，字段名分别为 `sharpe_ratio` 与 `calmar_ratio`；并确保 `annual_volatility`、`annual_return`、`max_drawdown`、`sharpe_ratio`、`calmar_ratio` 在异常时回退为 0.0，不阻塞页面显示。
  - 实现细节：`services/analysis_service.py` 扩展 `_compute_advanced_metrics` 返回 5 元组（年化波动率、年化收益率、最大回撤、夏普、卡玛），`calculate_strategy_score` 将其写入 `stats`。
  - 兼容两种依赖：优先使用 `empyrical`，失败时回退 `empyrical_reloaded`；若依赖缺失或计算异常，统一回退 0.0。
  - UI：`templates/strategy_detail.html` “各标的表现明细”表格新增列：年化波动率、年化收益率、最大回撤、夏普比率、卡玛比率。
- 新增指标：换手率
  - 口径：区间内买卖成交额（不含费）之和与总投入（不含费）的比值，以百分比显示（如 250.00% 表示 2.5 倍）。
  - 实现：在 `services/analysis_service.py` 聚合 `buy_gross` 和 `sell_gross` 计算 `turnover_rate` 字段；模板 `templates/strategy_detail.html` 增加“换手率”列。

### 2025-08-15
- 交易记录页新增分页与每页条数选择：
  - 前端 `templates/trades.html` 增加“每页显示 25/50/100”下拉与分页控件；切换条数回到第1页。
  - 路由 `routes/trading_routes.py:/trades` 支持查询参数 `page` 与 `page_size`（限定 25/50/100），向模板传递 `page`、`page_size`、`total_count`、`total_pages`。
  - 服务层新增 `TradingService.get_trades_paginated(...)`，返回 `(items, total_count)`；保持与列表一致的指标计算口径。
  - 仓储层 `services/trade_repository.py`：`fetch_trades` 支持 `offset`；新增 `count_trades` 统计总数。
  - 默认排序改为按开仓日期倒序显示最近交易（`t.open_date DESC`）。
- 交易记录页新增表头排序：
  - 新增查询参数 `sort` 与 `dir`（asc/desc），白名单字段映射到 `t.`/`s.` 列，避免 SQL 注入。
  - 模板表头（除“操作”外）均可点击切换升/降序，并显示方向图标；分页链接保留当前排序参数。
- 交易记录页新增“按标的代码过滤”（多代码）：
  - 路由解析 `symbols` 查询参数，支持逗号或空格分隔的多个代码，自动去重并大小写统一。
  - 服务/仓储新增 `symbols` 过滤：`UPPER(t.symbol_code) IN (?, ?, ...)`，用于 fetch 与 count。
  - 模板加入输入框与“应用/清除”按钮；所有分页、筛选、排序链接均保留当前 `symbols` 过滤状态。
  - 新增“按标的名称过滤”（多名称）：解析 `names` 参数，`UPPER(t.symbol_name) IN (?,...)`，与代码过滤取交集。
  - 新增“日期区间过滤”：`date_from`/`date_to`（YYYY-MM-DD），匹配开仓或平仓日期在区间内（含边界）；与代码/名称过滤取交集；提供快捷区间（最近7/30/60/90/180/360天）。
- 策略评分页面格式修复：胜率显示保留两位小数，平均持仓天数四舍五入显示为整数天（模板格式化）。
- “按标的比较策略”页面改为列表形式：
  - 新模板 `templates/symbol_comparison_list.html`，替代卡片视图；支持表头排序（代码/名称/交易数）、按代码与名称过滤（取交集）、分页与每页 25/50/100 选择。
  - 路由 `analysis_routes.symbol_comparison` 重构：解析过滤、排序与分页参数，返回列表模板。

### 2025-08-14 (后续修复)
- 交易详情页修复：单笔持仓的交易明细列表中“交易金额”改为不含费用（价格×数量），不再将买入费用加到金额或将卖出费用从金额中扣除；概览区口径保持不变。
- 交易列表费用兜底：当计算指标异常时，列表页的 `total_sell_fees`、`total_buy_fees`、`total_fees` 与费用占比会从明细聚合直接回填，避免出现已平仓后卖出费用显示为 0 的情况；同时确认快捷卖出路径保持正确更新。
  - 修复卖出后费用即时更新：卖出事务内改为使用同一数据库连接聚合买/卖手续费与买入成交额，确保刚插入的卖出手续费立即计入 `trades.total_sell_fees`，避免列表页出现“总卖出费用不增加”的滞后。
- 新增 API：`POST /api/modify_trade_detail`，支撑交易详情页的“修改交易明细”弹窗，后端调用 `TradingService.update_trade_record` 完成明细更新与汇总重算，修复 404 错误。

### 2025-08-14
- 文档同步与校准
  - 更新根 `README.md`：项目导航、核心特性、测试阈值（单元≥90%/功能≥80%/集成≥67%/性能≥50%）、管理工具 `/admin/db/diagnose`、项目结构与运行说明。
  - 更新 `doc/README.md`：加入 `admin_service.py` 与 `admin_routes.py`，补充最新 REST API 端点表（tags/symbol_lookup/quick_sell/strategy_score/strategy_trend 等），数据表说明包含费用与净利字段。
  - 更新 `doc/ARCHITECTURE.md`：补充 admin 路由，记录数据库 SQL 预执行安全校验与费用字段口径。
  - 更新 `doc/REQUIREMENTS.md`：修正“实现位置”到具体 services/routes/templates；明确计算模块 `trade_calculation.py` 与自动校准 `admin_service.py:auto_fix`。
  - 更新 `doc/TESTING.md`：明确各测试套件覆盖率阈值、静态检查（djlint/eslint/stylelint）与 MyPy 执行说明；强调测试数据库隔离。
  - 更新 `doc/TESTING_REPORT.md`：在覆盖概述中加入阈值说明。
  - 更新 `doc/PROGRESS.md`：覆盖率数字与软删除实现描述对齐现状（TOTAL≈53% 性能覆盖达标）。
 - 测试用例规范化
   - 统一所有测试中对 `create_app()` 的调用为 `create_app('testing')`，确保手动运行测试时也强制使用测试配置与隔离数据库。
   - 小幅清理集成测试中的未使用变量与导入，降低静态检查噪声。
 - 分析能力增强（新指标）
   - 在策略评分中新增专业风险/收益指标：年化波动率、年化收益率、最大回撤。
   - 使用 `numpy`、`pandas`、`empyrical-reloaded` 计算，未自行实现算法；新增依赖：`numpy==1.26.4`、`pandas==2.2.2`、`empyrical-reloaded==0.5.10`。

 - 功能测试覆盖率修补
   - 新增功能测试：`tests/functional/test_routes_admin_and_metrics.py` 覆盖 `/admin/db/*` 管理端点、`/api/strategy_score` 新增指标字段存在性、`/api/strategy_trend`、`/api/trade_detail`、`/api/symbol_lookup`、主页 `/`、以及 `utils.helpers` 与 `services.trade_calculation` 的关键路径。
   - 新增轻量冒烟测试：`tests/functional/test_routes_api_smoke_additional.py` 覆盖首页 200。
   - 运行结果：功能测试行覆盖率从 78% 提升至 80%（达到阈值≥80%）。

  - 类型检查与集成覆盖率提升
    - 修复 `services/analysis_service.py` 中的 MyPy 报错，显式使用 float 转换，类型检查 0 错误。
    - 扩充集成测试：覆盖 `/admin/db/update_row`、`/admin/db/auto_fix`、`/api/quick_sell`、`/api/symbol_lookup`、`/admin/db/diagnose(.json)` 等路径；集成覆盖率由 62% 提升至 70%（达到阈值≥67%）。

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


