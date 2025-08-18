#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile

from services.database_service import DatabaseService
from services.analysis_service import AnalysisService


def _tmp_db() -> str:
    fd, path = tempfile.mkstemp(prefix='analysis_flow_', suffix='.db')
    os.close(fd)
    return path


def test_calculate_strategy_score_with_sample_trades():
    db_path = _tmp_db()
    try:
        db = DatabaseService(db_path)
        with db.get_connection() as conn:
            cur = conn.cursor()
            # 策略
            cur.execute("INSERT INTO strategies(name, description) VALUES(?, ?)", ("trend", ""))
            # 交易（已平仓）
            cur.execute(
                """
                INSERT INTO trades(strategy_id, strategy, symbol_code, symbol_name, open_date, close_date, status,
                                   total_buy_amount, total_buy_quantity, total_sell_amount, total_sell_quantity,
                                   remaining_quantity, total_profit_loss, total_profit_loss_pct, holding_days,
                                   is_deleted)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
                """,
                (
                    1, 'trend', 'TEST', 'Test Inc', '2024-01-01', '2024-01-10', 'closed',
                    1000.0, 10, 1200.0, 10,
                    0, 200.0, 0.2, 9,
                ),
            )
            trade_id = cur.lastrowid
            # 明细：两笔买入，一笔卖出
            cur.execute(
                "INSERT INTO trade_details(trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee) VALUES(?,?,?,?,?,?,?)",
                (trade_id, 'buy', 100.0, 5, 500.0, '2024-01-02', 0.5),
            )
            cur.execute(
                "INSERT INTO trade_details(trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee) VALUES(?,?,?,?,?,?,?)",
                (trade_id, 'buy', 100.0, 5, 500.0, '2024-01-03', 0.5),
            )
            cur.execute(
                "INSERT INTO trade_details(trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee) VALUES(?,?,?,?,?,?,?)",
                (trade_id, 'sell', 120.0, 10, 1200.0, '2024-01-10', 1.0),
            )
            conn.commit()

        svc = AnalysisService(db)
        res = svc.calculate_strategy_score(strategy_id=1)
        assert 'stats' in res
        stats = res['stats']
        # 覆盖关键字段存在性与类型
        for k in (
            'total_trades', 'winning_trades', 'losing_trades', 'win_rate',
            'total_investment', 'total_return', 'total_return_rate',
            'avg_return_per_trade', 'avg_holding_days', 'total_fees',
            'avg_profit_loss_ratio', 'turnover_rate'
        ):
            assert k in stats
        # 基本正确性：盈利为正，交易数为1
        assert stats['total_trades'] == 1
        assert stats['total_return'] >= 0
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


