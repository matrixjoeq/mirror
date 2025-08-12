#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from typing import Any, Optional, Tuple

from services.analysis_service import AnalysisService


class _FakeDb:
    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch_one: bool = False, fetch_all: bool = True):
        q = " ".join(query.split())
        # list strategies: return two symbols for strategy
        if q.startswith('SELECT DISTINCT symbol_code, symbol_name FROM trades'):
            return [{'symbol_code': 'AAA', 'symbol_name': '甲'}, {'symbol_code': 'BBB', 'symbol_name': '乙'}]
        # strategy list (get_all_strategies called inside some paths)
        if q.startswith('SELECT s.*, GROUP_CONCAT(st.name) as tag_names FROM strategies s'):
            return [{'id': 1, 'name': 'Alpha', 'description': '', 'is_active': 1, 'tag_names': None}]
        # trades for calculate_strategy_score
        if q.startswith('SELECT t.*, s.name as strategy_name FROM trades t'):
            return []
        # default
        return None if fetch_one else []


class TestAnalysisServiceScoreEndpoints(unittest.TestCase):
    def setUp(self):
        self.svc = AnalysisService(_FakeDb())

    def test_get_strategy_scores_return_dto(self):
        res = self.svc.get_strategy_scores(return_dto=True)
        self.assertIsInstance(res, list)

    def test_get_symbol_scores_by_strategy_return_dto(self):
        res = self.svc.get_symbol_scores_by_strategy(strategy_id=1, return_dto=True)
        self.assertIsInstance(res, list)

    def test_get_strategies_scores_by_symbol_return_dto(self):
        res = self.svc.get_strategies_scores_by_symbol('AAA', return_dto=True)
        self.assertIsInstance(res, list)

    def test_get_strategies_scores_by_time_period_return_dto(self):
        res = self.svc.get_strategies_scores_by_time_period('2024', 'year', return_dto=True)
        self.assertIsInstance(res, list)


