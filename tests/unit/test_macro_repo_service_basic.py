#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app
from services.macro_repository import MacroRepository
from services.macro_service import MacroService


def test_macro_repository_seed_and_snapshot_views():
    app = create_app('testing')
    with app.app_context():
        repo = MacroRepository(app.db_service)
        # seed minimal data for two economies and two indicators
        repo.bulk_upsert_macro_series([
            {"economy": "US", "indicator": "cpi_yoy", "date": "2024-01-01", "value": 3.2},
            {"economy": "DE", "indicator": "cpi_yoy", "date": "2024-01-01", "value": 2.6},
            {"economy": "US", "indicator": "unemployment", "date": "2024-01-01", "value": 4.0},
            {"economy": "DE", "indicator": "unemployment", "date": "2024-01-01", "value": 5.5},
        ])
        svc = MacroService(app.db_service)
        for view in ("value", "zscore", "percentile", "trend"):
            snap = svc.get_snapshot(view=view, window='1y')
            assert snap['view'] == view
            assert 'economies' in snap and len(snap['economies']) >= 1
            assert 'matrix' in snap and isinstance(snap['matrix'], dict)


def test_macro_refresh_status_logging():
    app = create_app('testing')
    with app.app_context():
        repo = MacroRepository(app.db_service)
        repo.record_refresh('macro', '2024-01-01T00:00:00Z', 2)
        status = repo.get_refresh_status()
        assert 'history' in status and isinstance(status['history'], list)


