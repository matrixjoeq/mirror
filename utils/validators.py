#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入校验工具：集中化常用校验与解析，便于服务层与路由复用。
保持简单（KISS），避免重复（DRY）。
"""

from decimal import Decimal, InvalidOperation
from typing import Tuple
from datetime import datetime


def validate_positive_decimal(value) -> Tuple[bool, str]:
    try:
        d = Decimal(str(value))
        if d > 0:
            return True, ""
        return False, "价格必须大于0"
    except (InvalidOperation, ValueError):
        return False, "价格格式不正确"


def validate_positive_int(value) -> Tuple[bool, str]:
    try:
        i = int(value)
        if i > 0:
            return True, ""
        return False, "数量必须大于0"
    except (TypeError, ValueError):
        return False, "数量格式不正确"


def validate_date_yyyy_mm_dd(value: str) -> Tuple[bool, str]:
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return True, ""
    except ValueError:
        return False, "日期格式应为 YYYY-MM-DD"


