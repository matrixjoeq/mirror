#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库服务层
"""

import sqlite3
import re
from typing import Optional, List, Dict, Any, Iterable
from contextlib import contextmanager

from config import Config


class DatabaseService:
    """数据库操作服务"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            # 若在 Flask 上下文中，优先使用 current_app.config['DB_PATH']，以便测试环境共用同一数据库
            try:
                from flask import current_app  # 延迟导入以避免循环依赖
                if current_app and current_app.config.get('DB_PATH'):
                    self.db_path = current_app.config.get('DB_PATH')
                else:
                    self.db_path = Config.DB_PATH
            except Exception:
                self.db_path = Config.DB_PATH
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

            # 统一使用 strategy_tags 表作为标签表（移除未被业务使用的 tags 表）

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
            
            # 常用索引（幂等创建）
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_strategy_id ON trades(strategy_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol_code ON trades(symbol_code)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_is_deleted ON trades(is_deleted)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_details_trade ON trade_details(trade_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_details_type_deleted ON trade_details(transaction_type, is_deleted)")
            except sqlite3.OperationalError as e:
                try:
                    from flask import current_app
                    current_app.logger.warning(f"索引创建警告: {e}")
                except Exception:
                    import logging
                    logging.getLogger(__name__).warning(f"索引创建警告: {e}")

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
            # 盈利细分统计（毛利/净利）
            self._add_column_if_not_exists(cursor, 'trades', 'total_gross_profit', 'DECIMAL(15,3) DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'trades', 'total_net_profit', 'DECIMAL(15,3) DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'trades', 'total_net_profit_pct', 'DECIMAL(8,4) DEFAULT 0')
            # 费用统计字段（买入费/卖出费/总费用/费用占比）
            self._add_column_if_not_exists(cursor, 'trades', 'total_buy_fees', 'DECIMAL(15,3) DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'trades', 'total_sell_fees', 'DECIMAL(15,3) DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'trades', 'total_fees', 'DECIMAL(15,3) DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'trades', 'total_fee_ratio_pct', 'DECIMAL(8,4) DEFAULT 0')
            
            self._add_column_if_not_exists(cursor, 'trade_details', 'is_deleted', 'INTEGER DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'trade_details', 'delete_date', 'TIMESTAMP')
            self._add_column_if_not_exists(cursor, 'trade_details', 'delete_reason', 'TEXT')
            self._add_column_if_not_exists(cursor, 'trade_details', 'operator_note', 'TEXT')
            # 明细级毛利/净利
            self._add_column_if_not_exists(cursor, 'trade_details', 'gross_profit', 'DECIMAL(15,3) DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'trade_details', 'gross_profit_pct', 'DECIMAL(8,4) DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'trade_details', 'net_profit', 'DECIMAL(15,3) DEFAULT 0')
            self._add_column_if_not_exists(cursor, 'trade_details', 'net_profit_pct', 'DECIMAL(8,4) DEFAULT 0')
            
        except sqlite3.OperationalError as e:
            try:
                from flask import current_app
                current_app.logger.warning(f"数据库迁移警告: {e}")
            except Exception:
                import logging
                logging.getLogger(__name__).warning(f"数据库迁移警告: {e}")

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
        # 启用外键约束，保证参照完整性
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass

        # 安全包装：为 cursor() 提供带预执行校验的代理
        class _SafeCursor:
            def __init__(self, real_cursor, validator):
                self._cur = real_cursor
                self._validator = validator

            def execute(self, query, params: Iterable = ()): 
                self._validator(query, params)
                return self._cur.execute(query, params)

            def executemany(self, query, seq_of_params): 
                # 对批量执行也进行语句级校验
                self._validator(query, None, is_many=True)
                return self._cur.executemany(query, seq_of_params)

            def executescript(self, script):  # 禁止使用 executescript 以防多语句注入
                raise RuntimeError("executescript is disabled for security reasons")

            def __getattr__(self, item):
                return getattr(self._cur, item)

        class _SafeConnection:
            def __init__(self, real_conn, validator):
                self._conn = real_conn
                self._validator = validator

            def cursor(self):
                return _SafeCursor(self._conn.cursor(), self._validator)

            # 透传其他属性/方法（commit、rollback、close等）
            def __getattr__(self, item):
                return getattr(self._conn, item)

            def close(self):
                return self._conn.close()

        safe_conn = _SafeConnection(conn, self._pre_execute_check)
        try:
            yield safe_conn
        finally:
            safe_conn.close()

    # -------------------------
    # SQL 安全预执行检查
    # -------------------------
    def _pre_execute_check(self, query: str, params: Optional[Iterable] = None, is_many: bool = False) -> None:
        """在任何 SQL 执行前进行统一的安全性检查，降低注入风险。

        规则（尽量不影响正常开发）：
        - 禁止多语句与脚本执行：不允许出现分号、executescript。
        - 禁止内联注释：不允许出现 '--' 或 '/* */' 模式。
        - 强制参数化：若提供了 params，则 SQL 必须包含 '?' 或命名占位符 ':'。
        - 拦截典型注入模式：如 'UNION SELECT'、'OR 1=1' 等（大小写不敏感）。
        """

        if not isinstance(query, str):
            raise ValueError("SQL 必须为字符串类型")

        q = query.strip()

        # 去除注释后再进行风险检测（允许存在注释，但不参与判定）
        def _strip_sql_comments(sql: str) -> str:
            # 移除 -- 到行尾
            sql_no_line = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
            # 移除 /* ... */ 注释块
            sql_no_block = re.sub(r"/\*.*?\*/", "", sql_no_line, flags=re.DOTALL)
            return sql_no_block

        q_nc = _strip_sql_comments(q)

        # 多语句/脚本（简单防护）
        if ';' in q_nc:
            # 允许末尾单个分号？为降低风险，统一禁止
            raise ValueError("检测到分号，已阻止可能的多语句执行")

        # 强制参数化
        # 仅当确实传入了参数（非空）时才校验占位符
        params_len = None
        if params is not None and hasattr(params, '__len__'):
            try:
                params_len = len(params)  # type: ignore[arg-type]
            except Exception:
                params_len = None
        if params_len and params_len > 0:
            if not (('?' in q_nc) or (re.search(r"\:[A-Za-z_][A-Za-z0-9_]*", q_nc) is not None)):
                raise ValueError("提供了参数但未使用占位符，已阻止执行")

        # 典型注入模式（注意尽量少误报）
        suspicious_patterns = [
            r"(?i)\bunion\s+select\b",
            r"(?i)\bor\s+1\s*=\s*1\b",
            r"(?i)\battach\s+database\b",
        ]
        for pat in suspicious_patterns:
            if re.search(pat, q_nc):
                raise ValueError("检测到可疑SQL模式，已阻止执行")

    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = True) -> Any:
        """执行查询并返回结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 预执行安全检查在 SafeCursor 中已经进行，这里保持调用清晰
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
                    # 逐条操作前会由 SafeCursor 校验
                    cursor.execute(op['query'], op.get('params', ()))
                conn.commit()
                return True
        except Exception as e:
            try:
                from flask import current_app
                current_app.logger.warning(f"事务执行失败: {e}")
            except Exception:
                import logging
                logging.getLogger(__name__).warning(f"事务执行失败: {e}")
            return False
