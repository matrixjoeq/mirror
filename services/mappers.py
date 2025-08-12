#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
领域模型映射：将数据库行/字典映射为 dataclass 模型。
不改变现有对外接口，供内部或新接口按需使用。
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Iterable, List
from typing import Optional

from models.trading import Trade, TradeDetail
from models.strategy import Strategy, Tag


def _parse_dt(v):
    if v in (None, "", 0):
        return None
    if isinstance(v, datetime):
        return v
    try:
        # 支持 "YYYY-MM-DD" 或完整时间戳
        if isinstance(v, str) and len(v) == 10:
            return datetime.strptime(v, '%Y-%m-%d')
        return datetime.fromisoformat(str(v))
    except Exception:
        return None


def map_trade_row_to_model(row: Dict[str, Any]) -> Trade:
    return Trade(
        id=row.get('id'),
        strategy_id=row.get('strategy_id'),
        strategy=row.get('strategy', 'trend'),
        symbol_code=row.get('symbol_code', ''),
        symbol_name=row.get('symbol_name', ''),
        open_date=row.get('open_date'),
        close_date=row.get('close_date'),
        status=row.get('status', 'open'),
        total_buy_amount=Decimal(str(row.get('total_buy_amount', 0) or 0)),
        total_buy_quantity=int(row.get('total_buy_quantity', 0) or 0),
        total_sell_amount=Decimal(str(row.get('total_sell_amount', 0) or 0)),
        total_sell_quantity=int(row.get('total_sell_quantity', 0) or 0),
        remaining_quantity=int(row.get('remaining_quantity', 0) or 0),
        total_profit_loss=Decimal(str(row.get('total_profit_loss', 0) or 0)),
        total_profit_loss_pct=Decimal(str(row.get('total_profit_loss_pct', 0) or 0)),
        holding_days=int(row.get('holding_days', 0) or 0),
        trade_log=row.get('trade_log', ''),
        created_at=_parse_dt(row.get('created_at')),
        updated_at=_parse_dt(row.get('updated_at')),
        is_deleted=int(row.get('is_deleted', 0) or 0),
        delete_date=_parse_dt(row.get('delete_date')),
        delete_reason=row.get('delete_reason', ''),
        operator_note=row.get('operator_note', ''),
    )


def map_detail_row_to_model(row: Dict[str, Any]) -> TradeDetail:
    return TradeDetail(
        id=row.get('id'),
        trade_id=int(row.get('trade_id', 0) or 0),
        transaction_type=row.get('transaction_type', 'buy'),
        price=Decimal(str(row.get('price', 0) or 0)),
        quantity=int(row.get('quantity', 0) or 0),
        amount=Decimal(str(row.get('amount', 0) or 0)),
        transaction_date=row.get('transaction_date'),
        transaction_fee=Decimal(str(row.get('transaction_fee', 0) or 0)),
        buy_reason=row.get('buy_reason', ''),
        sell_reason=row.get('sell_reason', ''),
        profit_loss=Decimal(str(row.get('profit_loss', 0) or 0)),
        profit_loss_pct=Decimal(str(row.get('profit_loss_pct', 0) or 0)),
        created_at=_parse_dt(row.get('created_at')),
        is_deleted=int(row.get('is_deleted', 0) or 0),
        delete_date=_parse_dt(row.get('delete_date')),
        delete_reason=row.get('delete_reason', ''),
        operator_note=row.get('operator_note', ''),
    )


def to_dict_dataclass(obj) -> Dict[str, Any]:
    try:
        return asdict(obj)
    except Exception:
        return dict(obj)  # fallback


# -------- DTO helpers for routes --------
@dataclass
class TradeDTO:
    id: int
    strategy_id: int
    strategy_name: str
    symbol_code: str
    symbol_name: str
    status: str
    remaining_quantity: int
    holding_days: int
    total_buy_amount: float
    total_sell_amount: float
    total_profit_loss: float
    total_profit_loss_pct: float
    total_gross_profit: float
    total_net_profit: float
    total_net_profit_pct: float
    total_buy_fees: float
    total_sell_fees: float
    total_fees: float
    total_fee_ratio_pct: float
    # 允许模板读取这些标识（在某些页面渲染用到）
    open_date: Optional[str] = None
    close_date: Optional[str] = None


@dataclass
class TradeDetailDTO:
    id: int
    trade_id: int
    transaction_type: str
    price: float
    quantity: int
    amount: float
    transaction_date: str
    transaction_fee: float
    buy_reason: str
    sell_reason: str
    profit_loss: float
    profit_loss_pct: float
    created_at: str
    is_deleted: int
    delete_date: Optional[str]
    delete_reason: str
    operator_note: str
    gross_profit: float = 0.0
    gross_profit_pct: float = 0.0
    net_profit: float = 0.0
    net_profit_pct: float = 0.0
    remaining_for_quick: int = 0
    can_quick_sell: bool = False


def dict_to_trade_dto(t: Dict[str, Any]) -> TradeDTO:
    n = normalize_trade_row(t)
    return TradeDTO(
        id=int(n.get('id', 0) or 0),
        strategy_id=int(n.get('strategy_id', 0) or 0),
        strategy_name=n.get('strategy_name', ''),
        symbol_code=n.get('symbol_code', ''),
        symbol_name=n.get('symbol_name', ''),
        status=n.get('status', 'open'),
        remaining_quantity=int(n.get('remaining_quantity', 0) or 0),
        holding_days=int(n.get('holding_days', 0) or 0),
        total_buy_amount=float(n.get('total_buy_amount', 0) or 0),
        total_sell_amount=float(n.get('total_sell_amount', 0) or 0),
        total_profit_loss=float(n.get('total_profit_loss', 0) or 0),
        total_profit_loss_pct=float(n.get('total_profit_loss_pct', 0) or 0),
        total_gross_profit=float(n.get('total_gross_profit', 0) or 0),
        total_net_profit=float(n.get('total_net_profit', 0) or 0),
        total_net_profit_pct=float(n.get('total_net_profit_pct', 0) or 0),
        total_buy_fees=float(n.get('total_buy_fees', 0) or 0),
        total_sell_fees=float(n.get('total_sell_fees', 0) or 0),
        total_fees=float(n.get('total_fees', 0) or 0),
        total_fee_ratio_pct=float(n.get('total_fee_ratio_pct', 0) or 0),
        open_date=str(n.get('open_date')) if n.get('open_date') is not None else None,
        close_date=str(n.get('close_date')) if n.get('close_date') is not None else None,
    )


def dto_list_to_dicts(items: Iterable[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in items:
        out.append(to_dict_dataclass(it))
    return out


# Strategy/Tag DTOs
@dataclass
class StrategyDTO:
    id: int
    name: str
    description: str
    is_active: int
    tags: List[str]
    created_at: str = ''
    updated_at: str = ''


def dict_to_strategy_dto(s: Dict[str, Any]) -> StrategyDTO:
    return StrategyDTO(
        id=int(s.get('id', 0) or 0),
        name=s.get('name', ''),
        description=s.get('description', ''),
        is_active=int(s.get('is_active', 1) or 1),
        tags=list(s.get('tags', []) or []),
        created_at=str(s.get('created_at', '') or ''),
        updated_at=str(s.get('updated_at', '') or ''),
    )


@dataclass
class TagDTO:
    id: int
    name: str
    usage_count: int = 0


def dict_to_tag_dto(tag: Dict[str, Any]) -> TagDTO:
    return TagDTO(
        id=int(tag.get('id', 0) or 0),
        name=tag.get('name', ''),
        usage_count=int(tag.get('usage_count', 0) or 0),
    )


@dataclass
class ScoreDTO:
    strategy_id: int | None
    strategy_name: str | None
    stats: Dict[str, Any]
    symbol_code: str | None = None
    symbol_name: str | None = None
    total_score: float | None = None
    win_rate_score: float | None = None
    profit_loss_ratio_score: float | None = None
    frequency_score: float | None = None
    rating: str | None = None


TRADE_NUMERIC_DEFAULTS = [
    'total_gross_buy', 'total_buy_fees', 'total_sell_fees', 'total_gross_profit',
    'total_net_profit', 'total_net_profit_pct', 'total_profit_loss', 'total_profit_loss_pct',
    'total_buy_amount', 'total_sell_amount', 'total_fees', 'total_fee_ratio_pct',
]


def normalize_trade_row(trade: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all fields used by templates exist and have numeric defaults."""
    t = dict(trade)
    for key in TRADE_NUMERIC_DEFAULTS:
        t[key] = float(t.get(key, 0) or 0)
    # basic defaults
    t['strategy_name'] = t.get('strategy_name', t.get('strategy', ''))
    t['symbol_code'] = t.get('symbol_code', '')
    t['symbol_name'] = t.get('symbol_name', '')
    t['status'] = t.get('status', 'open')
    t['remaining_quantity'] = int(t.get('remaining_quantity', 0) or 0)
    t['holding_days'] = int(t.get('holding_days', 0) or 0)
    if 'open_date' in t and t['open_date'] is not None:
        t['open_date'] = str(t['open_date'])
    if 'close_date' in t and t['close_date'] is not None:
        t['close_date'] = str(t['close_date'])
    return t


# Deprecated map_* utilities were removed in favor of DTOs


def normalize_trade_detail_row(detail: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(detail)
    d['remaining_for_quick'] = int(d.get('remaining_for_quick', 0) or 0)
    d['can_quick_sell'] = bool(d.get('can_quick_sell', False))
    d['quantity'] = int(d.get('quantity', 0) or 0)
    d['price'] = float(d.get('price', 0) or 0)
    d['transaction_fee'] = float(d.get('transaction_fee', 0) or 0)
    return d


def dict_to_trade_detail_dto(d: Dict[str, Any]) -> TradeDetailDTO:
    n = normalize_trade_detail_row(d)
    return TradeDetailDTO(
        id=int(n.get('id', 0) or 0),
        trade_id=int(n.get('trade_id', 0) or 0),
        transaction_type=n.get('transaction_type', 'buy'),
        price=float(n.get('price', 0) or 0),
        quantity=int(n.get('quantity', 0) or 0),
        amount=float(n.get('amount', 0) or 0),
        transaction_date=str(n.get('transaction_date') or ''),
        transaction_fee=float(n.get('transaction_fee', 0) or 0),
        buy_reason=n.get('buy_reason', ''),
        sell_reason=n.get('sell_reason', ''),
        profit_loss=float(n.get('profit_loss', 0) or 0),
        profit_loss_pct=float(n.get('profit_loss_pct', 0) or 0),
        created_at=str(n.get('created_at') or ''),
        is_deleted=int(n.get('is_deleted', 0) or 0),
        delete_date=str(n.get('delete_date')) if n.get('delete_date') is not None else None,
        delete_reason=n.get('delete_reason', ''),
        operator_note=n.get('operator_note', ''),
        gross_profit=float(n.get('gross_profit', 0) or 0),
        gross_profit_pct=float(n.get('gross_profit_pct', 0) or 0),
        net_profit=float(n.get('net_profit', 0) or 0),
        net_profit_pct=float(n.get('net_profit_pct', 0) or 0),
        remaining_for_quick=int(n.get('remaining_for_quick', 0) or 0),
        can_quick_sell=bool(n.get('can_quick_sell', False)),
    )


# Deprecated


# Deprecated


# Deprecated


