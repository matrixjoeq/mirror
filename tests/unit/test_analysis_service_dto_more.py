#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, Optional, Tuple

from services.analysis_service import AnalysisService


class _FakeDb:
    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch_one: bool = False, fetch_all: bool = True):
        # 所有查询均返回空，便于触发服务层逻辑分支
        if fetch_one:
            return None
        return []


def test_time_periods_all_variants():
    svc = AnalysisService(_FakeDb())
    assert isinstance(svc.get_time_periods('year'), list)
    assert isinstance(svc.get_time_periods('quarter'), list)
    assert isinstance(svc.get_time_periods('month'), list)
    assert svc.get_time_periods('invalid') == []


def test_score_lists_return_dto_variants():
    svc = AnalysisService(_FakeDb())
    assert isinstance(svc.get_strategy_scores(return_dto=True), list)
    assert isinstance(svc.get_symbol_scores_by_strategy(return_dto=True), list)
    assert isinstance(svc.get_strategies_scores_by_symbol('X', return_dto=True), list)
    assert isinstance(svc.get_strategies_scores_by_time_period('2024', 'year', return_dto=True), list)


def test_period_summary_return_dto():
    svc = AnalysisService(_FakeDb())
    summary = svc.get_period_summary('2024', 'year', return_dto=True)
    assert hasattr(summary, 'stats')
    assert summary.stats.get('total_trades') == 0


def test_attach_legacy_score_fields_branches():
    svc = AnalysisService(_FakeDb())

    # 无交易
    s0 = {'stats': {'total_trades': 0, 'win_rate': 0, 'avg_holding_days': 0, 'avg_profit_loss_ratio': 0}}
    r0 = svc.attach_legacy_score_fields(s0)
    assert r0['frequency_score'] == 0

    # 正常盈亏比
    s1 = {'stats': {'total_trades': 10, 'win_rate': 60, 'avg_holding_days': 5, 'avg_profit_loss_ratio': 2.5}}
    r1 = svc.attach_legacy_score_fields(s1)
    assert 0 < r1['profit_loss_ratio_score'] <= 10
    assert r1['frequency_score'] == 7

    # 极大盈亏比（无亏损）
    s2 = {'stats': {'total_trades': 5, 'win_rate': 90, 'avg_holding_days': 45, 'avg_profit_loss_ratio': 9999.0}}
    r2 = svc.attach_legacy_score_fields(s2)
    assert r2['profit_loss_ratio_score'] == 10
    assert r2['frequency_score'] < 6


