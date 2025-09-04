### 中观观察：多市场相对强弱（RS）设计与趋势跟踪对比

#### 背景与目标
- 在 A 股、港股、美股内对大量指数进行相对强弱跟踪，形成横向（选筹）与纵向（择时）两类决策支持。
- 指标思想参考 O’Neil/IBD 的相对强弱（Relative Strength，RS），并与现代趋势跟踪方法互补。

---

#### 需求分析
- 指数范围：
  - A 股：上证综指、沪深300、中证1000等主宽基与行业子指数
  - 港股：恒生指数、国企指数、科技指数及行业子指数
  - 美股：S&P 500、NASDAQ 100、道指及行业指数
- 数据需求：
  - 日收盘价（本币）与 USD 换算价（用于跨市场比较）
  - 基准指数（市场内与全局），用于构建 RS 线
  - 交易日错配与缺失值处理策略
- 输出与可视化：
  - 横向：当日或区间的市场内/全局 RS 排行（Top N）
  - 纵向：单指数 RS 等级时间序列、RS 线、信号（入场/止损/止盈）
  - 对比：多指数 RS 序列对比（同市场/跨市场）
- 稳定性与性能：
  - 批量计算与增量刷新，仅计算新交易日
  - 统一货币（USD）做跨市场比较；对极端值与缺失做鲁棒处理

---

#### 指标与算法设计
- 统一口径：
  - 价格按收盘价；跨市场比较使用 close_usd（当日 Frankfurter 汇率换算）
  - 日频计算，支持周频平滑（可选）
- O’Neil 风格 RS 等级（1–99）：
  - 计算 1/3/6/12 个月累计收益 r1m、r3m、r6m、r12m
  - 组合分数 composite = Σ wi·r_i（近期权重更高；默认 12m=0.4, 6m=0.3, 3m=0.2, 1m=0.1，可配置）
  - 在比较集合（市场内/全局）按当日 composite 做百分位 RankPct∈[0,1]
  - RS_Rank = floor(RankPct×99)+1 → 1..99
- RS 线（相对价格强弱）
  - RS_Line(t) = Price_symbol_USD(t) / Price_benchmark_USD(t)
  - 趋势度量：MA(21/50)、线性回归斜率、近期新高/新低；可计算斜率 z-score 作为趋势强度
- 交易信号（纵向择时）：
  - 入场候选：RS_Rank_Market ≥ 85 且 5–10 日上升；RS_Line > MA(50) 且斜率为正
  - 止损：RS_Rank_Market 连续跌破 70（或阈值）且 RS_Line < MA(50)
  - 止盈/减仓：RS_Rank 跌落峰值≥15 或 RS_Line 连续数日斜率为负
  - 参数全部可配置（市场差异化）
- 噪音与缺失处理：
  - 日期并集对齐，缺失日前值延用或改周频
  - 端点裁剪（winsorization）可选，减弱极端值影响
  - 最小数据长度：优先 ≥252 交易日（12m），不足则按可得窗口降级

---

#### 跨/内市场比较口径
- 市场内（横向）：在同市场指数集合中计算分位（RS_Rank_Market）
- 全局（横向）：在所有指数集合中按 USD 收益计算分位（RS_Rank_Global）
- 纵向：单指数时间序列跟踪 RS_Rank_Market、RS_Rank_Global、RS_Line

---

#### 比较日历对齐规则（重要）
- 大类资产横向对比：仅使用“从全局起始日期（global start date）至今，所有纳入对比市场共同开市”的交易日集合进行计算与排序（日期交集）。
- 目的：消除市场间交易日差异带来的偏差，确保同一组日期上的可比性。
- 实施要点：
  - 在刷新/计算阶段预先查询日期交集；缺任一市场当日数据则该日排除。
  - USD 口径：当日 FX 缺失时当天 USD 价视为无效，不参与交集。
  - 对比窗口从 `meso_settings.global_start_date` 起算（或 API 参数覆盖）。

---

#### 数据模型与存储（建议）
- index_metadata(symbol, market, name, currency, region, is_active)
- index_prices(symbol, date, close, currency, close_usd, UNIQUE(symbol,date))
- rs_scores（新增）：
  - symbol, date
  - r1m, r3m, r6m, r12m, composite_score
  - rs_rank_market, rs_rank_global
  - rs_line, rs_line_ma_21, rs_line_ma_50, rs_line_slope
  - entry_signal, exit_signal, stop_level, target_level
  - 索引：date、symbol、(market,date)
- refresh_meta：记录刷新历史

---

#### 计算流程与增量刷新
1) 初始化：
   - 读取 index_metadata 活跃列表；若缺历史价，从 yfinance 拉取并写入 index_prices
2) 每日增量：
   - 对每个 symbol 从 last_calc_date+1 到 asof 计算 r1m/r3m/r6m/r12m 与 composite
   - 构建“市场内集合”“全局集合”，计算当日分位 → 写入 rs_scores
   - 计算 RS_Line 与均线/斜率 → 写入
   - 推导入场/出场/止损/止盈位 → 写入
3) 性能：
   - pandas 向量化，分批；当日仅做横截面分位一次
   - 幂等：INSERT OR REPLACE，失败可重试

---

#### API 设计（新增）
- GET /api/meso/rs/rankings?market=CN|HK|US|ALL&asof=YYYY-MM-DD&top=50&scope=market|global
- GET /api/meso/rs/series?symbol=^GSPC&window=1y&scope=market|global
- GET /api/meso/rs/compare?symbols=^GSPC,^NDX&metric=rs_rank|composite|rs_line&window=1y
- POST /api/meso/rs/refresh?market=CN&since=YYYY-MM-DD

---

#### 与现代趋势跟踪方法的对比
- 目标：RS 偏横截面“挑强者”；趋势跟踪偏时间序列“跟趋势”
- 基准：RS 强依赖基准（同业/大盘）；趋势多为绝对动量（不依赖基准）
- 信号：RS 以复合动量分数做 1–99 排名；趋势以突破/均线/时间序列动量为主
- 风控：RS 常见简单阈值与定期调仓；趋势强调波动率目标、ATR/波动止损、风险预算
- 资产：RS 多用于股/行业横向；趋势跨股指/债/商品/外汇，做多做空兼备
- 执行：RS 周/月调仓；趋势日/周频执行、顺势加减仓，交易成本管理更关键
- 建议：RS 做选筹 + 趋势做择时 + 波动率目标做仓位

---

#### 测试与验证
- 单元：收益/分位/RS_Line/均线/斜率计算正确性
- 功能：排行/series/compare API 在不同 market/scope 的一致性
- 集成：0→1 刷新流程、增量幂等、跨市场 USD 口径
- 性能：上千指数×1–3 年数据的吞吐与内存

---

#### 可配置项
- 权重：W12/W6/W3/W1
- 阈值：入场/退出/止损分位、斜率门槛、确认天数
- 基准：市场内与全局基准符号
- 频率：日/周

#### 货币统一规则
- 市场内比较：使用该市场本币价格序列（price→close，total→close_tr），不换算 USD。
- 跨市场比较：统一换算为 USD 序列（price→close_usd，total→close_usd_tr），显式反映汇率对资产价格的影响。
- 时间尺度仍使用共同开市日交集；价格指标严格二选一 `price|total`。

#### MVP 页面与接口（资产大类）
- 页面：`/meso` → 展示资产大类横向榜单（强度分），支持切换 `price|total`。
- 接口：`GET /api/meso/rankings/asset_class?return_mode=price|total&top=20`
- 口径：跨市场统一 USD；共同开市日交集；价格指标严格二选一。
