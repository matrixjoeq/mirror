#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观观察体系 - 指标/实体配置

说明：
- 统一维护指标方向、默认窗口与实体清单
- 网络抓取与刷新开关通过环境变量控制，测试环境默认关闭
"""

from __future__ import annotations

import os
from typing import Dict, Tuple, List


# 经济体与商品/汇率实体
ECONOMIES: List[str] = ["US", "DE", "JP", "CN", "HK"]
COMMODITIES: List[str] = ["brent", "wti", "natgas", "gold", "silver", "copper"]
FX_PAIRS: List[str] = ["EURUSD", "USDJPY"]


# 指标配置：名称 -> (方向, 默认窗口)
# 方向：+1 越大越好；-1 越小越好
INDICATORS: Dict[str, Tuple[int, str]] = {
    "cpi_yoy": (-1, "10y"),
    "unemployment": (-1, "10y"),
    "pmi": (1, "5y"),
    "gdp_yoy": (1, "10y"),
    "industrial_prod_yoy": (1, "10y"),
    "retail_sales_yoy": (1, "10y"),
}


# 指标权重（用于加权综合分；未列出指标默认 1.0）
INDICATOR_WEIGHTS: Dict[str, float] = {
    "cpi_yoy": 1.0,
    "unemployment": 1.0,
    "pmi": 1.0,
    "gdp_yoy": 1.2,
    "industrial_prod_yoy": 1.0,
    "retail_sales_yoy": 0.8,
}


# 环境开关
ENABLE_NETWORK: bool = os.environ.get("MACRO_ENABLE_NETWORK", "0") in ("1", "true", "True")
FORCE_SAMPLE_ONLY: bool = os.environ.get("MACRO_FORCE_SAMPLE_ONLY", "0") in ("1", "true", "True")


