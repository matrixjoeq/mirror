#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易相关数据模型
"""

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List


@dataclass
class Trade:
    """交易主记录"""
    id: Optional[int] = None
    strategy_id: Optional[int] = None
    strategy: str = 'trend'
    symbol_code: str = ''
    symbol_name: str = ''
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    status: str = 'open'  # open, closed
    total_buy_amount: Decimal = Decimal('0')
    total_buy_quantity: int = 0
    total_sell_amount: Decimal = Decimal('0')
    total_sell_quantity: int = 0
    remaining_quantity: int = 0
    total_profit_loss: Decimal = Decimal('0')
    total_profit_loss_pct: Decimal = Decimal('0')
    holding_days: int = 0
    trade_log: str = ''
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_deleted: int = 0
    delete_date: Optional[datetime] = None
    delete_reason: str = ''
    operator_note: str = ''


@dataclass
class TradeDetail:
    """交易明细记录"""
    id: Optional[int] = None
    trade_id: int = 0
    transaction_type: str = 'buy'  # buy, sell
    price: Decimal = Decimal('0')
    quantity: int = 0
    amount: Decimal = Decimal('0')
    transaction_date: Optional[date] = None
    transaction_fee: Decimal = Decimal('0')
    buy_reason: str = ''
    sell_reason: str = ''
    profit_loss: Decimal = Decimal('0')
    profit_loss_pct: Decimal = Decimal('0')
    created_at: Optional[datetime] = None
    is_deleted: int = 0
    delete_date: Optional[datetime] = None
    delete_reason: str = ''
    operator_note: str = ''


@dataclass
class TradeModification:
    """交易修改历史记录"""
    id: Optional[int] = None
    trade_id: int = 0
    detail_id: Optional[int] = None
    modification_type: str = 'trade'  # trade, detail
    field_name: str = ''
    old_value: str = ''
    new_value: str = ''
    modification_reason: str = ''
    created_at: Optional[datetime] = None
