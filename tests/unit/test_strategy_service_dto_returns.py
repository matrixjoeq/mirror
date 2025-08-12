#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from typing import Any, Optional, Tuple

from services.strategy_service import StrategyService


class _FakeDb:
    def __init__(self):
        self._strategies = [
            {'id': 1, 'name': 'Alpha', 'description': 'd', 'is_active': 1, 'created_at': '2024-01-01', 'updated_at': '2024-01-02'},
            {'id': 2, 'name': 'Beta', 'description': 'd', 'is_active': 0, 'created_at': '2024-01-03', 'updated_at': '2024-01-04'},
        ]

    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch_one: bool = False, fetch_all: bool = True):
        q = " ".join(query.split())
        if q.startswith('SELECT s.*, GROUP_CONCAT(st.name) as tag_names FROM strategies s') and 'GROUP BY s.id ORDER BY s.name' in q and 'WHERE s.is_active = 1' in q:
            # get_all_strategies active only
            rows = []
            for s in self._strategies:
                if s['is_active']:
                    row = dict(s)
                    row['tag_names'] = None
                    rows.append(row)
            return rows
        if q.startswith('SELECT s.*, GROUP_CONCAT(st.name) as tag_names FROM strategies s') and 'WHERE s.id = ?' in q:
            # get_strategy_by_id
            sid = params[0] if params else None
            for s in self._strategies:
                if s['id'] == sid:
                    row = dict(s)
                    row['tag_names'] = None
                    return row if fetch_one else [row]
            return None
        # default
        return None if fetch_one else []


class TestStrategyServiceDtoReturns(unittest.TestCase):
    def test_get_all_strategies_return_dto(self):
        svc = StrategyService(_FakeDb())
        dtos = svc.get_all_strategies(return_dto=True)
        self.assertTrue(len(dtos) >= 1)
        self.assertTrue(hasattr(dtos[0], 'name'))
        self.assertTrue(hasattr(dtos[0], 'created_at'))

    def test_get_strategy_by_id_return_dto(self):
        svc = StrategyService(_FakeDb())
        dto = svc.get_strategy_by_id(1, return_dto=True)
        self.assertTrue(hasattr(dto, 'name'))
        self.assertEqual(dto.name, 'Alpha')


if __name__ == '__main__':
    unittest.main()


