#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app
from services.macro_service import MacroService
from services.macro_repository import MacroRepository


def test_macro_service_views_and_country_and_score_and_cache():
    app = create_app('testing')
    with app.app_context():
        svc = MacroService(app.db_service)
        # ensure seed exists
        _ = svc.get_snapshot(view='value', window='1y', nocache=True)

        for view in ('value', 'zscore', 'percentile', 'trend'):
            snap = svc.get_snapshot(view=view, window='1y')
            assert snap['view'] == view

        # cache hit path (same key)
        snap2 = svc.get_snapshot(view='value', window='1y')
        assert snap2['view'] == 'value'

        # country
        country = svc.get_country('US', window='3y')
        assert country['economy'] == 'US'
        assert 'series' in country

        # score
        s = svc.get_score('macro', 'US', 'trend')
        assert s['entity_type'] == 'macro'


def test_macro_refresh_all_and_invalidate_cache():
    app = create_app('testing')
    with app.app_context():
        svc = MacroService(app.db_service)
        # prime cache
        _ = svc.get_snapshot(view='value', window='1y')
        res = svc.refresh_all()
        assert res['refreshed'] is True and res['cache_invalidated'] is True
        # after refresh, cache key should be invalidated so compute again
        snap = svc.get_snapshot(view='value', window='1y')
        assert 'matrix' in snap


