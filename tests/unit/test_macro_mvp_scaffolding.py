#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile

from services.database_service import DatabaseService
from services.macro_repository import MacroRepository
from services.macro_service import MacroService


def _temp_db_path() -> str:
    fd, path = tempfile.mkstemp(prefix="macro_mvp_", suffix=".db")
    os.close(fd)
    return path


def test_macro_repository_tables_created():
    db_path = _temp_db_path()
    try:
        db = DatabaseService(db_path)
        # 初始化仓储将创建表
        MacroRepository(db)

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cur.fetchall()}
        assert 'macro_series' in tables
        assert 'commodity_series' in tables
        assert 'fx_series' in tables
        assert 'scores' in tables
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_macro_service_snapshot_country_score_shapes():
    db_path = _temp_db_path()
    try:
        db = DatabaseService(db_path)
        # 确保表存在（虽然当前服务不依赖，但保证路径一致）
        MacroRepository(db)
        svc = MacroService(db)

        snap = svc.get_snapshot(view='value', date='2024-12-31')
        assert isinstance(snap, dict)
        for key in ('as_of', 'view', 'economies', 'commodities', 'matrix', 'ranking'):
            assert key in snap

        country = svc.get_country('US', window='3y')
        assert isinstance(country, dict)
        for key in ('economy', 'window', 'series', 'composite_score', 'components'):
            assert key in country

        score = svc.get_score('commodity', 'gold', view='trend')
        assert isinstance(score, dict)
        for key in ('entity_type', 'entity_id', 'view', 'score', 'components'):
            assert key in score

        # MVP: snapshot ranking should have 5 items and scores non-negative
        assert len(snap['ranking']) == 5
        assert all(item['score'] >= 0 for item in snap['ranking'])
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


