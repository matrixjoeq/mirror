#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易计算工具：集中处理成本、毛利、净利与比例等可复用计算逻辑。
符合单一职责与DRY，供服务层复用。
"""

from decimal import Decimal
from typing import Dict


def compute_trade_profit_metrics(
    gross_buy_total: Decimal,
    buy_fees_total: Decimal,
    gross_sell_total: Decimal,
    sell_fees_total: Decimal,
    sold_qty: Decimal,
    buy_qty: Decimal,
) -> Dict[str, float]:
    """基于总额与数量聚合，计算可复用的利润指标。

    返回字段：
    - avg_buy_price_ex_fee: 不含费加权买入均价
    - buy_cost_for_sold: 已卖出部分对应的买入成本（不含费）
    - allocated_buy_fees_for_sold: 分摊到已卖出部分的买入手续费
    - gross_profit_for_sold: 毛利润（不含费用）
    - net_profit: 净利润（扣卖出费与分摊买入费）
    - net_profit_pct: 净利率（分母=已卖出部分买入成本）
    - total_buy_amount_incl_fee: 买入总额（含手续费）
    - total_sell_amount_net: 卖出总额（净额，扣卖出手续费）
    - total_fees: 总费用（买入+卖出）
    - total_fee_ratio_pct: 费用占比（相对买入不含费总额）
    """
    avg_buy_price_ex_fee = (gross_buy_total / buy_qty) if buy_qty > 0 else Decimal('0')
    buy_cost_for_sold = avg_buy_price_ex_fee * sold_qty
    allocated_buy_fees_for_sold = (buy_fees_total * (sold_qty / buy_qty)) if buy_qty > 0 else Decimal('0')
    gross_profit_for_sold = gross_sell_total - buy_cost_for_sold
    net_profit = gross_profit_for_sold - sell_fees_total - allocated_buy_fees_for_sold
    denom = buy_cost_for_sold
    net_profit_pct = (net_profit / denom * 100) if denom > 0 else Decimal('0')

    total_buy_amount_incl_fee = gross_buy_total + buy_fees_total
    total_sell_amount_net = gross_sell_total - sell_fees_total
    total_fees = buy_fees_total + sell_fees_total
    total_fee_ratio = (total_fees / gross_buy_total * 100) if gross_buy_total > 0 else Decimal('0')

    return {
        'avg_buy_price_ex_fee': float(avg_buy_price_ex_fee),
        'buy_cost_for_sold': float(buy_cost_for_sold),
        'allocated_buy_fees_for_sold': float(allocated_buy_fees_for_sold),
        'gross_profit_for_sold': float(gross_profit_for_sold),
        'net_profit': float(net_profit),
        'net_profit_pct': float(net_profit_pct),
        'total_buy_amount_incl_fee': float(total_buy_amount_incl_fee),
        'total_sell_amount_net': float(total_sell_amount_net),
        'total_fees': float(total_fees),
        'total_fee_ratio_pct': float(total_fee_ratio),
    }