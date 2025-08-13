#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助工具函数
"""

import random
import string
from datetime import datetime, date
from typing import Tuple


def generate_confirmation_code(length: int = 6) -> str:
    """生成确认码"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def get_period_date_range(period: str, period_type: str = 'year') -> Tuple[str, str]:
    """获取时间周期的日期范围"""
    if period_type == 'year':
        start_date = f"{period}-01-01"
        end_date = f"{period}-12-31"
    elif period_type == 'quarter':
        # 格式: 2024-Q1
        year, quarter = period.split('-Q')
        q = int(quarter)
        
        if q == 1:
            start_date = f"{year}-01-01"
            end_date = f"{year}-03-31"
        elif q == 2:
            start_date = f"{year}-04-01"
            end_date = f"{year}-06-30"
        elif q == 3:
            start_date = f"{year}-07-01"
            end_date = f"{year}-09-30"
        else:  # quarter == 4
            start_date = f"{year}-10-01"
            end_date = f"{year}-12-31"
    elif period_type == 'month':
        # 格式: 2024-01
        year, month = period.split('-')
        start_date = f"{year}-{month}-01"
        
        # 计算月末日期
        if month in ['01', '03', '05', '07', '08', '10', '12']:
            end_date = f"{year}-{month}-31"
        elif month in ['04', '06', '09', '11']:
            end_date = f"{year}-{month}-30"
        else:  # 2月
            # 简单处理，不考虑闰年
            end_date = f"{year}-{month}-28"
    else:
        start_date = '1900-01-01'
        end_date = '2099-12-31'
    
    return start_date, end_date


def format_currency(amount: float, currency: str = '¥') -> str:
    """格式化货币显示"""
    return f"{currency}{amount:,.2f}"


def format_percentage(rate: float, precision: int = 2) -> str:
    """格式化百分比显示"""
    return f"{rate:.{precision}f}%"


def parse_decimal_input(value: str) -> float:
    """解析用户输入的数字"""
    try:
        return float(value.replace(',', ''))
    except (ValueError, AttributeError):
        return 0.0


def validate_date_format(date_str: str) -> bool:
    """验证日期格式 YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def get_trading_days_between(start_date: str, end_date: str) -> int:
    """计算两个日期之间的交易日数（简化版，不考虑节假日）"""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        total_days = (end - start).days
        
        # 简化计算：假设一周5个交易日
        weeks = total_days // 7
        remaining_days = total_days % 7
        
        # 粗略估算交易日
        trading_days = weeks * 5 + min(remaining_days, 5)
        return max(trading_days, 0)
        
    except ValueError:
        return 0
