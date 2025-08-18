#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile

from services.database_service import DatabaseService
from services.analysis_service import AnalysisService


def _tmp_db() -> str:
    fd, path = tempfile.mkstemp(prefix='analysis_cov_', suffix='.db')
    os.close(fd)
    return path


def test_analysis_service_empty_db_paths_and_helpers():
    db_path = _tmp_db()
    try:
        db = DatabaseService(db_path)
        svc = AnalysisService(db)

        # get_time_periods 分支覆盖（year/quarter/month/invalid）
        assert isinstance(svc.get_time_periods('year'), list)
        assert isinstance(svc.get_time_periods('quarter'), list)
        assert isinstance(svc.get_time_periods('month'), list)
        assert svc.get_time_periods('invalid') == []

        # 计算得分（空库兜底）
        score = svc.calculate_strategy_score()
        assert 'stats' in score and isinstance(score['stats'], dict)

        # 周期汇总 DTO 路径
        ps = svc.get_period_summary('2024', 'year', return_dto=True)
        # ScoreDTO 是 dataclass，可转字典但此处只断言属性存在
        assert hasattr(ps, 'stats')

        # 旧字段附加与计算器
        attached = svc.attach_legacy_score_fields({'stats': {'win_rate': 50, 'avg_profit_loss_ratio': 2, 'avg_holding_days': 5, 'total_trades': 10}})
        assert 'total_score' in attached
        fields = svc.compute_score_fields({'win_rate': 50, 'avg_profit_loss_ratio': 2, 'avg_holding_days': 5, 'total_trades': 10})
        assert 'rating' in fields

        # 高级指标空输入短路
        ann_vol, ann_ret, mdd, sharpe, calmar = svc._compute_advanced_metrics([], None, None)
        assert (ann_vol, ann_ret, mdd, sharpe, calmar) == (0.0, 0.0, 0.0, 0.0, 0.0)
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


