#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库服务层
"""

import sqlite3
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from config import Config


class DatabaseService:
    """数据库操作服务"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DB_PATH
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建交易主表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER,  -- 策略ID（外键）
                    strategy TEXT NOT NULL DEFAULT 'trend',  -- 兼容旧版本
                    symbol_code TEXT NOT NULL,
                    symbol_name TEXT NOT NULL,
                    open_date DATE NOT NULL,
                    close_date DATE,
                    status TEXT DEFAULT 'open',  -- open: 持仓中, closed: 已平仓
                    total_buy_amount DECIMAL(15,3) DEFAULT 0,
                    total_buy_quantity INTEGER DEFAULT 0,
                    total_sell_amount DECIMAL(15,3) DEFAULT 0,
                    total_sell_quantity INTEGER DEFAULT 0,
                    remaining_quantity INTEGER DEFAULT 0,
                    total_profit_loss DECIMAL(15,3) DEFAULT 0,
                    total_profit_loss_pct DECIMAL(8,4) DEFAULT 0,
                    holding_days INTEGER DEFAULT 0,
                    trade_log TEXT,  -- 交易日志（平仓时填写）
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_deleted INTEGER DEFAULT 0,
                    delete_date TIMESTAMP,
                    delete_reason TEXT,
                    operator_note TEXT,
                    FOREIGN KEY (strategy_id) REFERENCES strategies (id)
                )
            ''')

            # 创建交易明细表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,  -- buy: 买入, sell: 卖出
                    price DECIMAL(10,3) NOT NULL,
                    quantity INTEGER NOT NULL,
                    amount DECIMAL(15,3) NOT NULL,
                    transaction_date DATE NOT NULL,
                    transaction_fee DECIMAL(10,3) DEFAULT 0,  -- 交易手续费
                    buy_reason TEXT,  -- 买入理由
                    sell_reason TEXT,  -- 卖出理由
                    profit_loss DECIMAL(15,3) DEFAULT 0,
                    profit_loss_pct DECIMAL(8,4) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_deleted INTEGER DEFAULT 0,
                    delete_date TIMESTAMP,
                    delete_reason TEXT,
                    operator_note TEXT,
                    FOREIGN KEY (trade_id) REFERENCES trades (id)
                )
            ''')

            # 创建修改历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_modifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER NOT NULL,
                    detail_id INTEGER,  -- 如果修改的是明细，记录明细ID
                    modification_type TEXT NOT NULL,  -- 'trade' or 'detail'
                    field_name TEXT NOT NULL,  -- 被修改的字段名
                    old_value TEXT,  -- 原值
                    new_value TEXT,  -- 新值
                    modification_reason TEXT,  -- 修改原因
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trade_id) REFERENCES trades (id),
                    FOREIGN KEY (detail_id) REFERENCES trade_details (id)
                )
            ''')

            # 创建策略表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建标签表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建策略标签关联表 
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_tag_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_id) REFERENCES strategies (id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES strategy_tags (id) ON DELETE CASCADE,
                    UNIQUE(strategy_id, tag_id)
                )
            ''')
            
            # 创建标签表 (重命名为strategy_tags以匹配现有数据)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    is_predefined BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 数据库升级处理
            self._handle_database_migrations(cursor)
            
            conn.commit()

    def _handle_database_migrations(self, cursor):
        """处理数据库迁移和兼容性"""
        try:
            # 检查并添加缺失的字段
            self._add_column_if_not_exists(cursor, 'trades', 'strategy_id', 'INTEGER')
            self._add_column_if_not_exists(cursor, 'trades', 'is_deleted', 'INTEGER DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'trades', 'delete_date', 'TIMESTAMP')
            self._add_column_if_not_exists(cursor, 'trades', 'delete_reason', 'TEXT')
            self._add_column_if_not_exists(cursor, 'trades', 'operator_note', 'TEXT')
            
            self._add_column_if_not_exists(cursor, 'trade_details', 'is_deleted', 'INTEGER DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'trade_details', 'delete_date', 'TIMESTAMP')
            self._add_column_if_not_exists(cursor, 'trade_details', 'delete_reason', 'TEXT')
            self._add_column_if_not_exists(cursor, 'trade_details', 'operator_note', 'TEXT')
            
        except sqlite3.OperationalError as e:
            print(f"数据库迁移警告: {e}")

    def _add_column_if_not_exists(self, cursor, table_name, column_name, column_definition):
        """如果列不存在则添加"""
        try:
            cursor.execute(f"SELECT {column_name} FROM {table_name} LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}')

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = True) -> Any:
        """执行查询并返回结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            # 如果是插入、更新、删除操作，需要提交事务
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                conn.commit()
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return cursor.lastrowid

    def execute_transaction(self, operations: List[Dict[str, Any]]) -> bool:
        """执行事务操作"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for op in operations:
                    cursor.execute(op['query'], op.get('params', ()))
                conn.commit()
                return True
        except Exception as e:
            print(f"事务执行失败: {e}")
            return False
