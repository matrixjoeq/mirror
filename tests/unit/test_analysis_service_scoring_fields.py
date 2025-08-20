#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from services.analysis_service import AnalysisService


def test_compute_score_fields_rating_boundaries():
    svc = AnalysisService()

    # total_score = 26 -> A+
    stats_aplus = {
        'win_rate': 100.0,                 # win_rate_score = 10
        'avg_profit_loss_ratio': 10.0,     # profit_loss_ratio_score = 10
        'total_trades': 10,
        'avg_holding_days': 1,             # frequency_score = 8
    }
    r_aplus = svc.compute_score_fields(stats_aplus)
    assert r_aplus['rating'] == 'A+'
    assert round(r_aplus['total_score'], 2) >= 26.0

    # total_score = 23 -> A
    stats_a = {
        'win_rate': 90.0,                  # 9
        'avg_profit_loss_ratio': 8.0,      # 8
        'total_trades': 10,
        'avg_holding_days': 7,             # 7
    }
    r_a = svc.compute_score_fields(stats_a)
    assert r_a['rating'] == 'A'
    assert 23.0 <= r_a['total_score'] < 26.0

    # total_score = 20 -> B
    stats_b = {
        'win_rate': 80.0,                  # 8
        'avg_profit_loss_ratio': 6.0,      # 6
        'total_trades': 10,
        'avg_holding_days': 30,            # 6
    }
    r_b = svc.compute_score_fields(stats_b)
    assert r_b['rating'] == 'B'

    # total_score = 18 -> C
    stats_c = {
        'win_rate': 70.0,                  # 7
        'avg_profit_loss_ratio': 5.0,      # 5
        'total_trades': 10,
        'avg_holding_days': 30,            # 6
    }
    r_c = svc.compute_score_fields(stats_c)
    assert r_c['rating'] == 'C'

    # total_score < 18 -> D
    stats_d = {
        'win_rate': 0.0,                   # 0
        'avg_profit_loss_ratio': 0.0,      # 0
        'total_trades': 0,                 # 0
        'avg_holding_days': 100,
    }
    r_d = svc.compute_score_fields(stats_d)
    assert r_d['rating'] == 'D'


def test_attach_legacy_and_attach_score_fields_merge():
    svc = AnalysisService()
    base = {'stats': {'win_rate': 50.0, 'avg_profit_loss_ratio': 2.0, 'total_trades': 5, 'avg_holding_days': 10}}
    out = svc.attach_legacy_score_fields(dict(base))
    assert 'total_score' in out and out['total_score'] > 0
    out2 = svc.attach_score_fields(dict(base))
    assert 'total_score' in out2 and out2['total_score'] > 0


def test_get_time_periods_invalid_type_returns_empty():
    svc = AnalysisService()
    assert svc.get_time_periods('invalid_type') == []


