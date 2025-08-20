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
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS index_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    close REAL,
                    currency TEXT,
                    close_usd REAL,
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
                INSERT OR REPLACE INTO index_prices (symbol, date, close, currency, close_usd)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.get("symbol"),
                        r.get("date"),
                        float(r.get("close")) if r.get("close") is not None else None,
                        r.get("currency"),
                        float(r.get("close_usd")) if r.get("close_usd") is not None else None,
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
                    "SELECT date, close, currency, close_usd FROM index_prices WHERE symbol=? AND date>=? ORDER BY date",
                    (symbol, start),
                )
            else:
                cur.execute(
                    "SELECT date, close, currency, close_usd FROM index_prices WHERE symbol=? ORDER BY date",
                    (symbol,),
                )
            rows = cur.fetchall()
        return [
            {"date": r[0], "close": r[1], "currency": r[2], "close_usd": r[3]} for r in rows
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

    def record_refresh(self, source: str, refreshed_at: str, rows: int) -> None:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO refresh_meta (source, refreshed_at, rows) VALUES (?, ?, ?)",
                (source, refreshed_at, int(rows)),
            )
            conn.commit()


