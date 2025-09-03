#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中观观察体系 - 仓储层

存储全球股指价格、换算后的USD价格、计算得到的趋势分数，以及刷新元数据。
"""

from __future__ import annotations

from typing import Any, Iterable

from .database_service import DatabaseService
from config import Config


class MesoRepository:
    def __init__(self):
        # 强制使用独立库
        try:
            from flask import current_app
            db_path = current_app.config.get("MESO_DB_PATH", Config.MESO_DB_PATH)
        except Exception:
            db_path = Config.MESO_DB_PATH
        self.db = DatabaseService(db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            # 追踪标的元数据
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS index_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    name TEXT,
                    currency TEXT,
                    region TEXT,
                    market TEXT,
                    asset_class TEXT,
                    category TEXT,
                    subcategory TEXT,
                    provider TEXT,
                    use_adjusted INTEGER DEFAULT 1,
                    always_full_refresh INTEGER DEFAULT 0,
                    benchmark_symbol TEXT,
                    start_date_override TEXT,
                    is_active INTEGER DEFAULT 1
                )
                """
            )
            # 设置表（全局起始日期等）
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS meso_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS index_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    close REAL,
                    close_tr REAL,
                    currency TEXT,
                    close_usd REAL,
                    close_usd_tr REAL,
                    UNIQUE(symbol, date)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS trend_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    score REAL,
                    components_json TEXT,
                    UNIQUE(symbol, date)
                )
                """
            )
            # O'Neil 风格相对强弱（RS）分数与序列（独立于 trend_scores）
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rs_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    r1m REAL,
                    r3m REAL,
                    r6m REAL,
                    r12m REAL,
                    composite_score REAL,
                    rs_rank_market INTEGER,
                    rs_rank_global INTEGER,
                    rs_line REAL,
                    rs_line_ma_21 REAL,
                    rs_line_ma_50 REAL,
                    rs_line_slope REAL,
                    entry_signal INTEGER,
                    exit_signal INTEGER,
                    stop_level REAL,
                    target_level REAL,
                    UNIQUE(symbol, date)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS refresh_meta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    refreshed_at TEXT NOT NULL,
                    rows INTEGER DEFAULT 0
                )
                """
            )
            conn.commit()

    def upsert_index_prices(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT OR REPLACE INTO index_prices (symbol, date, close, close_tr, currency, close_usd, close_usd_tr)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.get("symbol"),
                        r.get("date"),
                        float(r.get("close")) if r.get("close") is not None else None,
                        float(r.get("close_tr")) if r.get("close_tr") is not None else None,
                        r.get("currency"),
                        float(r.get("close_usd")) if r.get("close_usd") is not None else None,
                        float(r.get("close_usd_tr")) if r.get("close_usd_tr") is not None else None,
                    )
                    for r in rows
                ],
            )
            conn.commit()
            return cur.rowcount or 0

    def upsert_trend_scores(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT OR REPLACE INTO trend_scores (symbol, date, score, components_json)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        r.get("symbol"),
                        r.get("date"),
                        float(r.get("score")) if r.get("score") is not None else None,
                        r.get("components_json"),
                    )
                    for r in rows
                ],
            )
            conn.commit()
            return cur.rowcount or 0

    def upsert_rs_scores(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT OR REPLACE INTO rs_scores (
                    symbol, date,
                    r1m, r3m, r6m, r12m,
                    composite_score,
                    rs_rank_market, rs_rank_global,
                    rs_line, rs_line_ma_21, rs_line_ma_50, rs_line_slope,
                    entry_signal, exit_signal,
                    stop_level, target_level
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        r.get("symbol"),
                        r.get("date"),
                        None if r.get("r1m") is None else float(r.get("r1m")),
                        None if r.get("r3m") is None else float(r.get("r3m")),
                        None if r.get("r6m") is None else float(r.get("r6m")),
                        None if r.get("r12m") is None else float(r.get("r12m")),
                        None if r.get("composite_score") is None else float(r.get("composite_score")),
                        None if r.get("rs_rank_market") is None else int(r.get("rs_rank_market")),
                        None if r.get("rs_rank_global") is None else int(r.get("rs_rank_global")),
                        None if r.get("rs_line") is None else float(r.get("rs_line")),
                        None if r.get("rs_line_ma_21") is None else float(r.get("rs_line_ma_21")),
                        None if r.get("rs_line_ma_50") is None else float(r.get("rs_line_ma_50")),
                        None if r.get("rs_line_slope") is None else float(r.get("rs_line_slope")),
                        None if r.get("entry_signal") is None else int(bool(r.get("entry_signal"))),
                        None if r.get("exit_signal") is None else int(bool(r.get("exit_signal"))),
                        None if r.get("stop_level") is None else float(r.get("stop_level")),
                        None if r.get("target_level") is None else float(r.get("target_level")),
                    )
                    for r in rows
                ],
            )
            conn.commit()
            return cur.rowcount or 0

    def get_latest_price_date(self, symbol: str) -> str | None:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(date) FROM index_prices WHERE symbol=?", (symbol,))
            row = cur.fetchone()
            return row[0] if row and row[0] else None

    def get_latest_score_date(self, symbol: str) -> str | None:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(date) FROM trend_scores WHERE symbol=?", (symbol,))
            row = cur.fetchone()
            return row[0] if row and row[0] else None

    def fetch_prices(self, symbol: str, start: str | None = None) -> list[dict[str, Any]]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            if start:
                cur.execute(
                    "SELECT date, close, close_tr, currency, close_usd, close_usd_tr FROM index_prices WHERE symbol=? AND date>=? ORDER BY date",
                    (symbol, start),
                )
            else:
                cur.execute(
                    "SELECT date, close, close_tr, currency, close_usd, close_usd_tr FROM index_prices WHERE symbol=? ORDER BY date",
                    (symbol,),
                )
            rows = cur.fetchall()
        return [
            {"date": r[0], "close": r[1], "close_tr": r[2], "currency": r[3], "close_usd": r[4], "close_usd_tr": r[5]} for r in rows
        ]

    def fetch_scores(self, symbol: str, start: str | None = None) -> list[dict[str, Any]]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            if start:
                cur.execute(
                    "SELECT date, score, components_json FROM trend_scores WHERE symbol=? AND date>=? ORDER BY date",
                    (symbol, start),
                )
            else:
                cur.execute(
                    "SELECT date, score, components_json FROM trend_scores WHERE symbol=? ORDER BY date",
                    (symbol,),
                )
            rows = cur.fetchall()
        return [
            {"date": r[0], "score": r[1], "components_json": r[2]} for r in rows
        ]

    def fetch_rs_scores(self, symbol: str, start: str | None = None) -> list[dict[str, Any]]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            if start:
                cur.execute(
                    """
                    SELECT date, r1m, r3m, r6m, r12m, composite_score,
                           rs_rank_market, rs_rank_global,
                           rs_line, rs_line_ma_21, rs_line_ma_50, rs_line_slope,
                           entry_signal, exit_signal, stop_level, target_level
                    FROM rs_scores
                    WHERE symbol=? AND date>=? ORDER BY date
                    """,
                    (symbol, start),
                )
            else:
                cur.execute(
                    """
                    SELECT date, r1m, r3m, r6m, r12m, composite_score,
                           rs_rank_market, rs_rank_global,
                           rs_line, rs_line_ma_21, rs_line_ma_50, rs_line_slope,
                           entry_signal, exit_signal, stop_level, target_level
                    FROM rs_scores
                    WHERE symbol=? ORDER BY date
                    """,
                    (symbol,),
                )
            rows = cur.fetchall()
        keys = [
            "date", "r1m", "r3m", "r6m", "r12m", "composite_score",
            "rs_rank_market", "rs_rank_global",
            "rs_line", "rs_line_ma_21", "rs_line_ma_50", "rs_line_slope",
            "entry_signal", "exit_signal", "stop_level", "target_level",
        ]
        out: list[dict[str, Any]] = []
        for r in rows:
            item = {}
            for i, k in enumerate(keys):
                item[k] = r[i]
            out.append(item)
        return out

    def get_latest_rs_date(self, symbol: str) -> str | None:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(date) FROM rs_scores WHERE symbol=?", (symbol,))
            row = cur.fetchone()
            return row[0] if row and row[0] else None

    # ------- 元数据与设置 -------
    def upsert_index_metadata(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT INTO index_metadata (
                    symbol, name, currency, region, market, asset_class, category, subcategory,
                    provider, use_adjusted, always_full_refresh, benchmark_symbol, start_date_override, is_active
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name=excluded.name,
                    currency=excluded.currency,
                    region=excluded.region,
                    market=excluded.market,
                    asset_class=excluded.asset_class,
                    category=excluded.category,
                    subcategory=excluded.subcategory,
                    provider=excluded.provider,
                    use_adjusted=excluded.use_adjusted,
                    always_full_refresh=excluded.always_full_refresh,
                    benchmark_symbol=excluded.benchmark_symbol,
                    start_date_override=excluded.start_date_override,
                    is_active=excluded.is_active
                """,
                [
                    (
                        r.get("symbol"), r.get("name"), r.get("currency"), r.get("region"), r.get("market"),
                        r.get("asset_class"), r.get("category"), r.get("subcategory"), r.get("provider"),
                        1 if r.get("use_adjusted", True) else 0,
                        1 if r.get("always_full_refresh", False) else 0,
                        r.get("benchmark_symbol"), r.get("start_date_override"),
                        1 if r.get("is_active", True) else 0,
                    )
                    for r in rows
                ],
            )
            conn.commit()
            return cur.rowcount or 0

    def list_index_metadata(self, only_active: bool = True) -> list[dict[str, Any]]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            if only_active:
                cur.execute("SELECT symbol,name,currency,region,market,asset_class,category,subcategory,provider,use_adjusted,always_full_refresh,benchmark_symbol,start_date_override,is_active FROM index_metadata WHERE is_active=1 ORDER BY asset_class, market, category, symbol")
            else:
                cur.execute("SELECT symbol,name,currency,region,market,asset_class,category,subcategory,provider,use_adjusted,always_full_refresh,benchmark_symbol,start_date_override,is_active FROM index_metadata ORDER BY asset_class, market, category, symbol")
            rows = cur.fetchall()
        keys = ["symbol","name","currency","region","market","asset_class","category","subcategory","provider","use_adjusted","always_full_refresh","benchmark_symbol","start_date_override","is_active"]
        out: list[dict[str, Any]] = []
        for r in rows:
            item = {}
            for i, k in enumerate(keys):
                item[k] = r[i]
            out.append(item)
        return out

    def set_global_start_date(self, date_str: str) -> None:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO meso_settings (key, value) VALUES ('global_start_date', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (date_str,))
            conn.commit()

    def get_global_start_date(self) -> str | None:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM meso_settings WHERE key='global_start_date'")
            row = cur.fetchone()
            return row[0] if row else None

    def record_refresh(self, source: str, refreshed_at: str, rows: int) -> None:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO refresh_meta (source, refreshed_at, rows) VALUES (?, ?, ?)",
                (source, refreshed_at, int(rows)),
            )
            conn.commit()


