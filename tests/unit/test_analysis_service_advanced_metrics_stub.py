#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.analysis_service import AnalysisService


class TestAnalysisServiceAdvancedMetricsStub(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_analysis_adv_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = AnalysisService(self.db)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_compute_advanced_metrics_handles_no_trades(self):
        # Private method call via name-mangled access; expect zeros when no trade ids
        ann_vol, ann_ret, mdd, sharpe, calmar = self.svc._compute_advanced_metrics([], None, None)  # type: ignore[attr-defined]
        self.assertEqual((ann_vol, ann_ret, mdd, sharpe, calmar), (0.0, 0.0, 0.0, 0.0, 0.0))


if __name__ == '__main__':
    unittest.main()


