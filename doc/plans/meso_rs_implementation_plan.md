### 中观观察（RS）实施计划

#### 目标与范围
- 根据 `doc/meso_rs_design.md` 实现 A/HK/US 多市场指数的相对强弱（RS）计算、排名与序列对比能力。
- 输出 API：排行、单标的/多标的序列、刷新；UI：`/meso` 仪表盘展示 RS 排行与对比图。

---

#### 数据层改造
- 新增表 `rs_scores`（独立于 `trend_scores`，用于 O’Neil 风格 RS 等级与 RS 线及信号）：
  - 主键：`(symbol, date)` 唯一
  - 字段：`symbol, date, r1m, r3m, r6m, r12m, composite_score, rs_rank_market, rs_rank_global, rs_line, rs_line_ma_21, rs_line_ma_50, rs_line_slope, entry_signal, exit_signal, stop_level, target_level`
  - 索引：`date`、`symbol`、`(symbol,date)`、可选 `(market,date)` 通过联表或冗余列实现
- `services/meso_repository.py`：
  - ensure 表创建：`_ensure_tables()` 中添加 `CREATE TABLE IF NOT EXISTS rs_scores(...)`
  - 批量 upsert：`upsert_rs_scores(rows: List[Dict[str, Any]]) -> int`
  - 查询：`fetch_rs_scores(symbol, start=None)`、`get_latest_rs_date(symbol)`

---

#### 服务层实现
- `services/meso_service.py`：
  - 计算收益窗口：`r1m/r3m/r6m/r12m`（按交易日近 21/63/126/252 日，降级处理不足窗口）
  - 复合分：`composite = Σ wi·r_i`，默认权重 `12m=0.4, 6m=0.3, 3m=0.2, 1m=0.1`（可配置）
  - 分位与等级：在集合内（`market|global`）按当日 `composite` 计算百分位 RankPct∈[0,1] → `RS_Rank=⌊RankPct×99⌋+1`
  - RS 线：`RS_Line(t)=Price_symbol_USD(t)/Price_benchmark_USD(t)`；派生 `MA(21/50)`、线性回归斜率与 z-score（先实现斜率）
  - 信号：基于 `RS_Rank` 与 `RS_Line`（>MA50 且斜率>0）给出 `entry/exit`；阈值可配置
  - 刷新流程：
    1) 抓取指数历史（`yfinance`）→ `index_prices`
    2) 汇率（Frankfurter）→ `close_usd`
    3) 计算 `r* / composite / RS_Rank_{market,global} / RS_Line + MAs + slope` → 写入 `rs_scores`
    4) 幂等增量：按各 symbol 最新日期之后补算；失败可重试（`INSERT OR REPLACE`）
  - 查询：
    - `get_rs_rankings(market, asof, top, scope)` 返回横截面排行（Top N）
    - `get_rs_series(symbol, window, scope)` 返回单标的时间序列
    - `get_rs_compare(symbols, metric, window)` 返回多标的对比序列

---

#### API 设计
- 新建 `routes/api_meso.py`：
  - `GET /api/meso/rs/rankings?market=CN|HK|US|ALL&asof=YYYY-MM-DD&top=50&scope=market|global`
  - `GET /api/meso/rs/series?symbol=^GSPC&window=1y&scope=market|global`
  - `GET /api/meso/rs/compare?symbols=^GSPC,^NDX&metric=rs_rank|composite|rs_line&window=1y`
  - `POST /api/meso/rs/refresh?market=CN&since=YYYY-MM-DD`（按市场过滤可选）

---

#### 配置与基准
- `services/meso_config.py`：
  - 扩展 `INDEX_DEFS` 增加 `market` 与默认 `benchmark` 映射（如 CN→`000300.SS`，HK→`^HSI`，US→`^GSPC`）。
  - 提供 `market_of(symbol)`、`benchmark_of(market)` 辅助函数。

---

#### UI 增强
- `templates/meso_dashboard.html`：
  - 增加 RS 排行表（Top N）、筛选 `market/scope`、`asof` 日期选择
  - 增加单标的 RS 线与 `RS_Rank` 叠加图；多标的对比折线
  - 交互：切换 market/scope 时异步请求对应 API

---

#### 测试策略（严格遵循项目约束）
- 单元测试（阈值≥90%）：
  - 收益窗口与复合分计算、分位/等级映射、RS 线及 MA/斜率
  - 仓储 upsert/fetch 幂等与边界
- 集成测试（阈值≥67%）：
  - 刷新流程 0→1 与增量幂等；跨市场 USD 口径一致
  - API 冒烟与参数校验（rankings/series/compare/refresh）
- 功能测试（阈值≥80%）：
  - `/meso` 页面加载、筛选切换、表格与图表渲染
- 性能测试：
  - 上千指数×1–3 年数据吞吐与内存，确保横截面分位单日仅计算一次
- 注意：所有测试使用独立测试数据库，运行后清理；不使用生产库。

---

#### 任务拆解与里程碑
1) 仓储扩展：`rs_scores` 表与 CRUD（含索引）
2) 服务实现：收益窗口、composite、分位/等级、RS 线与斜率、信号
3) 刷新流程：增量拉取、USD 换算、批量写入
4) API：rankings/series/compare/refresh
5) UI：`/meso` 排行与对比图
6) 测试：单元/集成/功能/性能全覆盖，保持阈值

---

#### 风险与对策
- yfinance/Frankfurter 网络依赖：在服务内延迟 import，失败时记录并跳过；测试环境使用本地样本/Mock。
- 跨市场交易日错配：按日期并集对齐，缺失延用前值（或可配置为周频）。
- 极端值与噪音：提供 winsorization 可选参数（后续迭代）。

---

#### 后续扩展（可选）
- 斜率 z-score、新高/新低突破、基于波动的仓位建议
- 市场/板块分组与滚动再平衡建议


