# 宏观观察体系 MVP 计划（Macro + Commodity + 可扩展中观）

## 目标与范围
- 目标：建立可持续运行的“投资观察体系”，覆盖宏观（经济体+大宗商品）并可平滑扩展到中观（经济体内部股/债/汇/商品），输出对实盘有指导意义的性价比与趋势视角。
- 首批经济体：美国、德国、日本、中国、香港。
- 两类视角：
  - 性价比（Value-for-money）：在风险/成本维度下的相对吸引力。
  - 趋势（Trend）：改善/恶化动能与持续性（短中期动量/斜率+扩散）。
- 结果可视化：横向（同一时间各经济体/商品横比）与纵向（单体历史）。
- 实盘导向：评分与趋势最终映射到可交易的 ETF 篮子与权重建议（中期迭代实现）。

## MVP 指标清单（每类 8±2，可按数据可得性微调）
- 宏观（每个经济体）
  - 增长/景气：工业产出 YoY 或 GDP YoY、PMI（制造或综合，若免费可得）
  - 物价/货币：CPI YoY、M2 YoY（或广义流动性代理）
  - 劳动力：失业率
  - 利率/曲线：政策利率、10Y-2Y 利差
  - 资产/估值：主要股指 PE（TTM 代理）
  - 汇率：对 USD 名义汇率（或 ECB 简化代理）
- 大宗商品（全球维度）
  - 能源：Brent/WTI 原油、Henry Hub 天然气
  - 金属：黄金、白银、铜
  - 选配：铁矿石/BDI/农产品（玉米、豆粕）按数据可得性逐步纳入

## 数据源与可得性
- 宏观：World Bank / OECD / FRED / Eurostat / ECB / BoJ / 香港统计处（优先免费、稳定来源）。
- 市场与汇率：Yahoo Finance / Stooq / ECB 汇率。
- 统一由 Provider 适配层封装（拉取、频率、单位、缺失兜底），允许后续替换为商业数据（TradingEconomics/Refinitiv）。

## 评分方法（MVP 等权，可配置化）
- 标准化与方向一致：
  - z-score 或 历史百分位（建议 10 年窗或自 2000 年起）。
  - 方向统一：通胀/失业率高→不利（取反），PMI高→有利。
- 性价比视角（示例）
  - 真实收益：10Y 国债收益率 − CPI（越高越好）。
  - 股权相对吸引力：盈利收益率（1/PE） − 政策利率/通胀（越高越好）。
  - 估值偏离：股指 PE 相对 3 年均值的 z 分（越低越好）。
  - 汇率偏离：对 USD 名义汇率相对历史均值偏离（越低越“便宜”）。
- 趋势视角
  - 核心指标的 3-6 月动量/斜率，扩散指数（向好指标占比）。
- 综合得分：两视角各输出 0-100（线性映射），MVP 先等权，后续开放权重配置。

## 系统设计与扩展
- Provider 适配（services/data_providers/*）：worldbank_provider、fred_provider、ecb_provider、yahoo_provider …
- 服务层：
  - macro_service：拉取→标准化→评分→快照；
  - macro_repository：读写 macro_series / macro_score 等表；
  - meso_service（预留）：经济体内部股/债/商品/汇率评分与 ETF 映射（后台计算）。
- 路由与页面：
  - routes/macro_routes.py、routes/api_macro.py；
  - templates/macro_dashboard.html（总览热力+排行）、macro_country.html（经济体纵向）、macro_compare.html（多国对比）。
- 缓存与调度：SQLite 本地缓存 + 拉取时间戳；MVP 手动刷新，后续加定时任务。

## 数据表结构（草案）
- macro_series(economy, indicator, date, value, provider, revised_at)
- commodity_series(commodity, date, value, currency, provider)
- asset_index_series(economy, index_code, index_name, date, price, pe_ttm, div_yield, currency)
- bond_series(economy, tenor, type(gov/credit/conv), date, yield, spread, currency)
- fx_series(pair, date, price)
- scores(view(value|trend), entity_type(macro|commodity|index|bond|etf), entity_id, date, score, components_json)
- etf_mapping(index_code → etf_ticker, market, expense, liquidity)

## API 契约（MVP）
- GET /api/macro/snapshot?date=YYYY-MM-DD&view=value|trend
  - 返回：各经济体与商品的热力矩阵、排行、时间戳。
- GET /api/macro/country?economy=US&window=3y
  - 返回：该经济体关键指标时间序列、综合分曲线、贡献分解。
- GET /api/macro/score?entity_type=commodity&entity_id=gold&view=trend
  - 返回：指定实体的综合评分与构成。

## 中观首期（后台计算，页面展示 Beta 标识，不隐藏）
- 每个经济体计算：长/短久期国债（10Y vs 2Y/3M）与主股指的 RS 评分；
- 输出接口（/api/meso/allocation），页面以 Beta 区块展示矩阵和基础图表；
- ETF 映射优先：**国内公募ETF** 与 **港股ETF**（跨市场以此二者为主）。

## 交付边界（MVP）
- 经济体：美国、德国、日本、中国、香港；
- 指标：宏观 6-8 项 + 商品 6-8 项 + 汇率；
- 视图：总览热力 + 国家详情 + 简易对比；
- API：snapshot/country/score；
- 中观：后台计算“长/短久期债 + 主股指 RS评分”，页面 Beta 展示；
- 缓存：本地 SQLite，手动刷新。

## 时间线与里程碑（建议）
- W1：冻结指标与权重；完成 Provider 适配与表结构迁移；拉通拉取-标准化-评分管道；
- W2：完成三个 API 与两张页面；接入大宗商品与汇率；
- W3：接入中观后台计算与 Beta 页面；ETF 映射（国内公募 + 港股）最小清单；
- W4：联调/测试/文档，试运行与反馈迭代。

## 验收标准
- 数据刷新成功率 ≥95%，关键指标缺失有兜底与告警；
- snapshot/country/score API 正确返回；
- 热力与趋势线与原始数据一致性校验通过；
- 中观 Beta 正常展示，并能返回基础评分；
- 文档（README/ARCHITECTURE/TESTING/PLAN）齐备；

## 风险与缓解
- 数据源不可用/延迟：多源备份、超时降级、上期数据 fallback；
- 指标口径差异：统一方向与单位，文档披露，允许窗口/权重配置；
- 估值数据质量：MVP 用 TTM 近似与公开源，后续可接商业数据；

## 迭代路线（向 95% 使用场景靠拢）
- 迭代1：债券（利差/期限结构）与股票（风格/行业）评分做厚；ETF 清单扩充与质量分；
- 迭代2：建议权重（目标波动/动量加权/风险平价），回测与监控；任务编排与数据质量报警。
