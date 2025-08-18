#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据提供者适配层（MVP脚手架）

约定：每个 Provider 暴露 fetch_xxx 方法，返回标准化记录列表。
"""

__all__ = ["sample_provider"]


def sample_provider() -> list[dict]:
    """返回少量示例数据，供 MVP 引导。
    真实实现将在后续迭代中替换。
    """
    return [
        {"economy": "US", "indicator": "cpi_yoy", "date": "2024-12-01", "value": 3.4, "provider": "sample", "revised_at": None},
        {"economy": "US", "indicator": "unemployment", "date": "2024-12-01", "value": 3.9, "provider": "sample", "revised_at": None},
    ]


