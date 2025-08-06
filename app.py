#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势交易跟踪系统 - 主应用文件
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
import sqlite3
import json
from decimal import Decimal
import os
import random
import string

app = Flask(__name__)
app.secret_key = 'trend_trading_tracker_2024'

# 数据库文件路径
DB_PATH = 'database/trading_tracker.db'

class TradingTracker:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 创建交易主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL DEFAULT 'trend',  -- trend: 趋势跟踪, rotation: 轮动策略, grid: 网格策略
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        # 为现有数据添加策略字段（兼容性处理）
        try:
            cursor.execute("SELECT strategy FROM trades LIMIT 1")
        except sqlite3.OperationalError:
            # 如果strategy字段不存在，添加它并设置默认值
            cursor.execute('ALTER TABLE trades ADD COLUMN strategy TEXT DEFAULT "trend"')
            cursor.execute('UPDATE trades SET strategy = "trend" WHERE strategy IS NULL')

        # 为现有数据添加交易日志字段（兼容性处理）
        try:
            cursor.execute("SELECT trade_log FROM trades LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE trades ADD COLUMN trade_log TEXT')

        # 为现有trade_details表添加新字段（兼容性处理）
        try:
            cursor.execute("SELECT transaction_fee FROM trade_details LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE trade_details ADD COLUMN transaction_fee DECIMAL(10,3) DEFAULT 0')

        try:
            cursor.execute("SELECT buy_reason FROM trade_details LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE trade_details ADD COLUMN buy_reason TEXT')

        try:
            cursor.execute("SELECT sell_reason FROM trade_details LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE trade_details ADD COLUMN sell_reason TEXT')

        # 为trades表添加软删除字段（兼容性处理）
        try:
            cursor.execute("SELECT deleted_at FROM trades LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE trades ADD COLUMN deleted_at TIMESTAMP')
            cursor.execute('ALTER TABLE trades ADD COLUMN deleted_reason TEXT')

        # 为trade_details表添加软删除字段（兼容性处理）
        try:
            cursor.execute("SELECT deleted_at FROM trade_details LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute('ALTER TABLE trade_details ADD COLUMN deleted_at TIMESTAMP')

        # 创建删除记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deleted_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER NOT NULL,
                operation_type TEXT NOT NULL, -- 'delete' or 'restore'
                affected_details TEXT, -- JSON array of detail IDs that were affected
                confirmation_code TEXT NOT NULL, -- 操作时使用的确认码
                delete_reason TEXT, -- 删除原因
                operator_note TEXT, -- 操作备注
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_id) REFERENCES trades (id)
            )
        ''')

        # 创建策略管理相关表

        # 创建策略表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建策略标签表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_predefined BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建策略标签关系表
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

        # 初始化预定义标签
        predefined_tags = ['轮动', '择时', '趋势', '套利']
        for tag_name in predefined_tags:
            cursor.execute('''
                INSERT OR IGNORE INTO strategy_tags (name, is_predefined)
                VALUES (?, 1)
            ''', (tag_name,))

        # 初始化默认策略（从原有固定策略迁移）
        default_strategies = [
            ('趋势跟踪策略', '基于趋势分析的交易策略', ['趋势']),
            ('轮动策略', '基于行业或板块轮动的交易策略', ['轮动']),
            ('网格策略', '基于价格网格的程序化交易策略', ['择时']),
            ('套利策略', '基于价差套利的交易策略', ['套利'])
        ]

        for strategy_name, strategy_desc, tag_names in default_strategies:
            # 插入策略
            cursor.execute('''
                INSERT OR IGNORE INTO strategies (name, description)
                VALUES (?, ?)
            ''', (strategy_name, strategy_desc))

            # 获取策略ID
            cursor.execute('SELECT id FROM strategies WHERE name = ?', (strategy_name,))
            strategy_row = cursor.fetchone()
            if strategy_row:
                strategy_id = strategy_row['id']

                # 添加标签关系
                for tag_name in tag_names:
                    cursor.execute('SELECT id FROM strategy_tags WHERE name = ?', (tag_name,))
                    tag_row = cursor.fetchone()
                    if tag_row:
                        tag_id = tag_row['id']
                        cursor.execute('''
                            INSERT OR IGNORE INTO strategy_tag_relations (strategy_id, tag_id)
                            VALUES (?, ?)
                        ''', (strategy_id, tag_id))

        # 检查是否需要迁移现有数据（从strategy字段到strategy_id字段）
        try:
            cursor.execute("SELECT strategy_id FROM trades LIMIT 1")
        except sqlite3.OperationalError:
            # strategy_id字段不存在，需要迁移
            cursor.execute('ALTER TABLE trades ADD COLUMN strategy_id INTEGER')

            # 迁移现有数据
            old_strategy_mapping = {
                'trend': '趋势跟踪策略',
                'rotation': '轮动策略',
                'grid': '网格策略',
                'arbitrage': '套利策略'
            }

            for old_strategy, new_strategy_name in old_strategy_mapping.items():
                cursor.execute('SELECT id FROM strategies WHERE name = ?', (new_strategy_name,))
                strategy_row = cursor.fetchone()
                if strategy_row:
                    strategy_id = strategy_row['id']
                    cursor.execute('''
                        UPDATE trades SET strategy_id = ?
                        WHERE strategy = ? AND strategy_id IS NULL
                    ''', (strategy_id, old_strategy))

            # 处理没有匹配到的记录，设置为趋势跟踪策略
            cursor.execute('SELECT id FROM strategies WHERE name = ?', ('趋势跟踪策略',))
            default_strategy_row = cursor.fetchone()
            if default_strategy_row:
                default_strategy_id = default_strategy_row['id']
                cursor.execute('''
                    UPDATE trades SET strategy_id = ?
                    WHERE strategy_id IS NULL
                ''', (default_strategy_id,))

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy_id ON trades(strategy_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(open_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_details_trade ON trade_details(trade_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy_tags_strategy ON strategy_tag_relations(strategy_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy_tags_tag ON strategy_tag_relations(tag_id)')

        conn.commit()
        conn.close()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ==================== 策略管理方法 ====================

    def get_all_strategies(self, include_inactive=False):
        """获取所有策略"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if include_inactive:
                cursor.execute('''
                    SELECT s.*,
                           GROUP_CONCAT(DISTINCT st.name) as tag_names,
                           COUNT(DISTINCT t.id) as trade_count
                    FROM strategies s
                    LEFT JOIN strategy_tag_relations str ON s.id = str.strategy_id
                    LEFT JOIN strategy_tags st ON str.tag_id = st.id
                    LEFT JOIN trades t ON s.id = t.strategy_id AND t.deleted_at IS NULL
                    GROUP BY s.id
                    ORDER BY s.created_at DESC
                ''')
            else:
                cursor.execute('''
                    SELECT s.*,
                           GROUP_CONCAT(DISTINCT st.name) as tag_names,
                           COUNT(DISTINCT t.id) as trade_count
                    FROM strategies s
                    LEFT JOIN strategy_tag_relations str ON s.id = str.strategy_id
                    LEFT JOIN strategy_tags st ON str.tag_id = st.id
                    LEFT JOIN trades t ON s.id = t.strategy_id AND t.deleted_at IS NULL
                    WHERE s.is_active = 1
                    GROUP BY s.id
                    ORDER BY s.created_at DESC
                ''')

            strategies = []
            for row in cursor.fetchall():
                strategy = dict(row)
                strategy['tags'] = row['tag_names'].split(',') if row['tag_names'] else []
                strategies.append(strategy)

            return strategies

        except Exception as e:
            print(f"获取策略列表失败: {str(e)}")
            return []
        finally:
            conn.close()

    def get_strategy_by_id(self, strategy_id):
        """根据ID获取策略"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT s.*,
                       GROUP_CONCAT(DISTINCT st.name) as tag_names
                FROM strategies s
                LEFT JOIN strategy_tag_relations str ON s.id = str.strategy_id
                LEFT JOIN strategy_tags st ON str.tag_id = st.id
                WHERE s.id = ?
                GROUP BY s.id
            ''', (strategy_id,))

            row = cursor.fetchone()
            if row:
                strategy = dict(row)
                strategy['tags'] = row['tag_names'].split(',') if row['tag_names'] else []
                return strategy
            return None

        except Exception as e:
            print(f"获取策略失败: {str(e)}")
            return None
        finally:
            conn.close()

    def create_strategy(self, name, description='', tag_names=[]):
        """创建新策略"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 检查名称是否重复
            cursor.execute('SELECT id FROM strategies WHERE name = ?', (name,))
            if cursor.fetchone():
                return False, "策略名称已存在"

            # 插入策略
            cursor.execute('''
                INSERT INTO strategies (name, description)
                VALUES (?, ?)
            ''', (name, description))

            strategy_id = cursor.lastrowid

            # 处理标签
            for tag_name in tag_names:
                tag_name = tag_name.strip()
                if not tag_name:
                    continue

                # 确保标签存在
                cursor.execute('''
                    INSERT OR IGNORE INTO strategy_tags (name, is_predefined)
                    VALUES (?, 0)
                ''', (tag_name,))

                # 获取标签ID
                cursor.execute('SELECT id FROM strategy_tags WHERE name = ?', (tag_name,))
                tag_row = cursor.fetchone()
                if tag_row:
                    tag_id = tag_row['id']
                    # 添加策略标签关系
                    cursor.execute('''
                        INSERT OR IGNORE INTO strategy_tag_relations (strategy_id, tag_id)
                        VALUES (?, ?)
                    ''', (strategy_id, tag_id))

            conn.commit()
            return True, f"策略 '{name}' 创建成功"

        except Exception as e:
            conn.rollback()
            return False, f"创建策略失败: {str(e)}"
        finally:
            conn.close()

    def update_strategy(self, strategy_id, name, description='', tag_names=[]):
        """更新策略"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 检查策略是否存在
            cursor.execute('SELECT * FROM strategies WHERE id = ?', (strategy_id,))
            if not cursor.fetchone():
                return False, "策略不存在"

            # 检查名称是否与其他策略重复
            cursor.execute('SELECT id FROM strategies WHERE name = ? AND id != ?', (name, strategy_id))
            if cursor.fetchone():
                return False, "策略名称已存在"

            # 更新策略基本信息
            cursor.execute('''
                UPDATE strategies
                SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, description, strategy_id))

            # 删除原有标签关系
            cursor.execute('DELETE FROM strategy_tag_relations WHERE strategy_id = ?', (strategy_id,))

            # 添加新的标签关系
            for tag_name in tag_names:
                tag_name = tag_name.strip()
                if not tag_name:
                    continue

                # 确保标签存在
                cursor.execute('''
                    INSERT OR IGNORE INTO strategy_tags (name, is_predefined)
                    VALUES (?, 0)
                ''', (tag_name,))

                # 获取标签ID
                cursor.execute('SELECT id FROM strategy_tags WHERE name = ?', (tag_name,))
                tag_row = cursor.fetchone()
                if tag_row:
                    tag_id = tag_row['id']
                    # 添加策略标签关系
                    cursor.execute('''
                        INSERT OR IGNORE INTO strategy_tag_relations (strategy_id, tag_id)
                        VALUES (?, ?)
                    ''', (strategy_id, tag_id))

            conn.commit()
            return True, f"策略 '{name}' 更新成功"

        except Exception as e:
            conn.rollback()
            return False, f"更新策略失败: {str(e)}"
        finally:
            conn.close()

    def delete_strategy(self, strategy_id):
        """删除策略（软删除）"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 检查策略是否存在
            cursor.execute('SELECT name FROM strategies WHERE id = ?', (strategy_id,))
            strategy_row = cursor.fetchone()
            if not strategy_row:
                return False, "策略不存在"

            # 检查是否有关联的交易记录
            cursor.execute('''
                SELECT COUNT(*) as count FROM trades
                WHERE strategy_id = ? AND deleted_at IS NULL
            ''', (strategy_id,))
            trade_count = cursor.fetchone()['count']

            if trade_count > 0:
                return False, f"无法删除策略，还有 {trade_count} 笔关联的交易记录"

            # 软删除策略
            cursor.execute('''
                UPDATE strategies
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (strategy_id,))

            conn.commit()
            return True, f"策略 '{strategy_row['name']}' 已删除"

        except Exception as e:
            conn.rollback()
            return False, f"删除策略失败: {str(e)}"
        finally:
            conn.close()

    def get_all_tags(self):
        """获取所有可用标签"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT st.*, COUNT(str.strategy_id) as usage_count
                FROM strategy_tags st
                LEFT JOIN strategy_tag_relations str ON st.id = str.tag_id
                GROUP BY st.id
                ORDER BY st.is_predefined DESC, st.name ASC
            ''')

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            print(f"获取标签列表失败: {str(e)}")
            return []
        finally:
            conn.close()

    def create_tag(self, name):
        """创建新标签"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR IGNORE INTO strategy_tags (name, is_predefined)
                VALUES (?, 0)
            ''', (name,))

            if cursor.rowcount > 0:
                conn.commit()
                return True, f"标签 '{name}' 创建成功"
            else:
                return False, "标签已存在"

        except Exception as e:
            conn.rollback()
            return False, f"创建标签失败: {str(e)}"
        finally:
            conn.close()

    def update_tag(self, tag_id, new_name):
        """更新标签名称"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 检查标签是否存在
            cursor.execute('SELECT * FROM strategy_tags WHERE id = ?', (tag_id,))
            tag = cursor.fetchone()
            if not tag:
                return False, "标签不存在"

            # 检查是否为预定义标签
            if tag['is_predefined']:
                return False, "预定义标签不能修改"

            # 检查新名称是否已存在
            cursor.execute('SELECT id FROM strategy_tags WHERE name = ? AND id != ?', (new_name, tag_id))
            if cursor.fetchone():
                return False, "标签名称已存在"

            # 更新标签名称
            cursor.execute('''
                UPDATE strategy_tags
                SET name = ?
                WHERE id = ?
            ''', (new_name, tag_id))

            conn.commit()
            return True, f"标签已更新为 '{new_name}'"

        except Exception as e:
            conn.rollback()
            return False, f"更新标签失败: {str(e)}"
        finally:
            conn.close()

    def delete_tag(self, tag_id):
        """删除标签"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 检查标签是否存在
            cursor.execute('SELECT * FROM strategy_tags WHERE id = ?', (tag_id,))
            tag = cursor.fetchone()
            if not tag:
                return False, "标签不存在"

            # 检查是否为预定义标签
            if tag['is_predefined']:
                return False, "预定义标签不能删除"

            # 检查是否有策略正在使用此标签
            cursor.execute('''
                SELECT COUNT(*) as count FROM strategy_tag_relations
                WHERE tag_id = ?
            ''', (tag_id,))
            usage_count = cursor.fetchone()['count']

            if usage_count > 0:
                return False, f"无法删除标签，还有 {usage_count} 个策略正在使用"

            # 删除标签
            cursor.execute('DELETE FROM strategy_tags WHERE id = ?', (tag_id,))

            conn.commit()
            return True, f"标签 '{tag['name']}' 已删除"

        except Exception as e:
            conn.rollback()
            return False, f"删除标签失败: {str(e)}"
        finally:
            conn.close()

    def add_buy_transaction(self, strategy, symbol_code, symbol_name, price, quantity, transaction_date, transaction_fee=0, buy_reason=''):
        """添加买入交易"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            amount = Decimal(str(price)) * quantity
            transaction_fee = Decimal(str(transaction_fee)) if transaction_fee else Decimal('0')

            # 处理策略参数：支持策略ID（数字）或策略名称（字符串）或旧的策略代码
            strategy_id = None
            if isinstance(strategy, (int, str)) and str(strategy).isdigit():
                # 如果是数字，直接作为策略ID
                strategy_id = int(strategy)
                # 验证策略ID是否存在
                cursor.execute('SELECT id FROM strategies WHERE id = ? AND is_active = 1', (strategy_id,))
                if not cursor.fetchone():
                    return False, f"策略ID {strategy_id} 不存在或已被禁用"
            else:
                # 如果是字符串，先尝试作为策略名称查找
                cursor.execute('SELECT id FROM strategies WHERE name = ? AND is_active = 1', (strategy,))
                strategy_row = cursor.fetchone()
                if strategy_row:
                    strategy_id = strategy_row['id']
                else:
                    # 如果找不到，尝试从旧的策略代码映射
                    old_strategy_mapping = {
                        'trend': '趋势跟踪策略',
                        'rotation': '轮动策略',
                        'grid': '网格策略',
                        'arbitrage': '套利策略'
                    }
                    strategy_name = old_strategy_mapping.get(strategy)
                    if strategy_name:
                        cursor.execute('SELECT id FROM strategies WHERE name = ? AND is_active = 1', (strategy_name,))
                        strategy_row = cursor.fetchone()
                        if strategy_row:
                            strategy_id = strategy_row['id']

                    if not strategy_id:
                        return False, f"未找到策略 '{strategy}'"

            # 查找是否已有该标的的同策略未完成交易
            cursor.execute('''
                SELECT id FROM trades
                WHERE strategy_id = ? AND symbol_code = ? AND status = 'open' AND deleted_at IS NULL
                ORDER BY open_date DESC LIMIT 1
            ''', (strategy_id, symbol_code))

            trade_row = cursor.fetchone()

            if trade_row:
                # 更新现有交易
                trade_id = trade_row['id']
                cursor.execute('''
                    UPDATE trades SET
                        total_buy_amount = total_buy_amount + ?,
                        total_buy_quantity = total_buy_quantity + ?,
                        remaining_quantity = remaining_quantity + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (float(amount + transaction_fee), quantity, quantity, trade_id))
            else:
                # 创建新交易
                cursor.execute('''
                    INSERT INTO trades (strategy_id, symbol_code, symbol_name, open_date, total_buy_amount,
                                      total_buy_quantity, remaining_quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (strategy_id, symbol_code, symbol_name, transaction_date, float(amount + transaction_fee), quantity, quantity))
                trade_id = cursor.lastrowid

            # 添加交易明细
            cursor.execute('''
                INSERT INTO trade_details (trade_id, transaction_type, price, quantity,
                                         amount, transaction_date, transaction_fee, buy_reason)
                VALUES (?, 'buy', ?, ?, ?, ?, ?, ?)
            ''', (trade_id, float(price), quantity, float(amount), transaction_date, float(transaction_fee), buy_reason))

            conn.commit()
            return True, trade_id

        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def add_sell_transaction(self, trade_id, price, quantity, transaction_date, transaction_fee=0, sell_reason='', trade_log=''):
        """添加卖出交易"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            transaction_fee = Decimal(str(transaction_fee)) if transaction_fee else Decimal('0')
            # 获取交易信息
            cursor.execute('''
                SELECT * FROM trades WHERE id = ? AND status = 'open'
            ''', (trade_id,))
            trade = cursor.fetchone()

            if not trade:
                return False, "交易不存在或已平仓"

            if quantity > trade['remaining_quantity']:
                return False, "卖出数量超过剩余持仓"

            # 计算卖出金额
            sell_amount = Decimal(str(price)) * quantity

            # 计算加权平均买入价（包含买入手续费）
            avg_buy_price = Decimal(str(trade['total_buy_amount'])) / trade['total_buy_quantity']

            # 计算这笔卖出的盈亏（扣除手续费）
            buy_cost = avg_buy_price * quantity
            net_sell_amount = sell_amount - transaction_fee
            profit_loss = net_sell_amount - buy_cost
            profit_loss_pct = (profit_loss / buy_cost) * 100 if buy_cost > 0 else 0

            # 更新剩余数量
            new_remaining_quantity = trade['remaining_quantity'] - quantity

            # 更新交易主表（卖出金额不包含手续费，先不更新total_profit_loss）
            cursor.execute('''
                UPDATE trades SET
                    total_sell_amount = total_sell_amount + ?,
                    total_sell_quantity = total_sell_quantity + ?,
                    remaining_quantity = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (float(sell_amount), quantity, new_remaining_quantity, trade_id))

            # 如果完全平仓，更新状态和计算持仓天数
            if new_remaining_quantity == 0:
                holding_days = (datetime.strptime(transaction_date, '%Y-%m-%d').date() -
                              datetime.strptime(trade['open_date'], '%Y-%m-%d').date()).days

                # 计算总的交易费用（买入+卖出所有费用）
                cursor.execute('''
                    SELECT SUM(transaction_fee) as total_fees FROM trade_details WHERE trade_id = ?
                ''', (trade_id,))
                total_fees_result = cursor.fetchone()
                total_fees = Decimal(str(total_fees_result['total_fees'])) if total_fees_result['total_fees'] else Decimal('0')

                # 重新计算总盈亏：卖出总额 - 买入总额 - 所有交易费用
                # 注意：total_buy_amount已包含买入费用，total_sell_amount不包含卖出费用
                cursor.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
                current_trade = cursor.fetchone()

                # 计算净卖出总额（扣除卖出费用）
                cursor.execute('''
                    SELECT SUM(transaction_fee) as sell_fees FROM trade_details
                    WHERE trade_id = ? AND transaction_type = 'sell'
                ''', (trade_id,))
                sell_fees_result = cursor.fetchone()
                sell_fees = Decimal(str(sell_fees_result['sell_fees'])) if sell_fees_result['sell_fees'] else Decimal('0')

                net_sell_amount = Decimal(str(current_trade['total_sell_amount'])) - sell_fees
                final_profit_loss = net_sell_amount - Decimal(str(current_trade['total_buy_amount']))

                total_profit_loss_pct = (final_profit_loss / Decimal(str(current_trade['total_buy_amount']))) * 100

                cursor.execute('''
                    UPDATE trades SET
                        status = 'closed',
                        close_date = ?,
                        holding_days = ?,
                        total_profit_loss = ?,
                        total_profit_loss_pct = ?,
                        trade_log = ?
                    WHERE id = ?
                ''', (transaction_date, holding_days, float(final_profit_loss), float(total_profit_loss_pct), trade_log, trade_id))
            else:
                # 部分卖出时不累加盈亏，保持为null，因为最终会在完全平仓时统一计算
                # 这样避免重复计算和错误累加
                pass

            # 添加卖出明细
            cursor.execute('''
                INSERT INTO trade_details (trade_id, transaction_type, price, quantity,
                                         amount, transaction_date, transaction_fee, sell_reason,
                                         profit_loss, profit_loss_pct)
                VALUES (?, 'sell', ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (trade_id, float(price), quantity, float(sell_amount),
                  transaction_date, float(transaction_fee), sell_reason, float(profit_loss), float(profit_loss_pct)))

            conn.commit()
            return True, "卖出成功"

        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def get_all_trades(self, status=None, strategy=None, include_deleted=False):
        """获取所有交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        where_conditions = []
        params = []

        # 默认排除已删除的记录
        if not include_deleted:
            where_conditions.append("deleted_at IS NULL")

        if status:
            where_conditions.append("status = ?")
            params.append(status)

        if strategy:
            where_conditions.append("strategy = ?")
            params.append(strategy)

        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        cursor.execute('''
            SELECT * FROM trades
            {}
            ORDER BY open_date DESC, id DESC
        '''.format(where_clause), params)

        trades = cursor.fetchall()
        conn.close()

        return [dict(trade) for trade in trades]

    def get_trade_details(self, trade_id, include_deleted=False):
        """获取交易明细"""
        conn = self.get_connection()
        cursor = conn.cursor()

        where_clause = "WHERE trade_id = ?"
        if not include_deleted:
            where_clause += " AND deleted_at IS NULL"

        cursor.execute(f'''
            SELECT * FROM trade_details
            {where_clause}
            ORDER BY transaction_date ASC, id ASC
        ''', (trade_id,))

        details = cursor.fetchall()
        conn.close()

        return [dict(detail) for detail in details]

    def record_modification(self, cursor, trade_id, detail_id, modification_type, field_name, old_value, new_value, reason=''):
        """记录修改历史"""
        cursor.execute('''
            INSERT INTO trade_modifications
            (trade_id, detail_id, modification_type, field_name, old_value, new_value, modification_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (trade_id, detail_id, modification_type, field_name, str(old_value), str(new_value), reason))

    def update_trade_record(self, trade_id, trade_log='', detail_updates=None, modification_reason='', new_strategy_id=None):
        """修改已平仓交易记录，支持修改所有字段并记录修改历史"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 检查交易是否存在且已平仓
            cursor.execute('SELECT * FROM trades WHERE id = ? AND status = "closed"', (trade_id,))
            trade = cursor.fetchone()

            if not trade:
                return False, "交易不存在或未平仓，无法修改"

            # 更新交易日志并记录历史
            if trade_log and trade_log != (trade['trade_log'] or ''):
                old_log = trade['trade_log'] or ''
                cursor.execute('''
                    UPDATE trades SET
                        trade_log = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (trade_log, trade_id))

                # 记录修改历史
                self.record_modification(cursor, trade_id, None, 'trade', 'trade_log', old_log, trade_log, modification_reason)

            # 更新策略并记录历史
            if new_strategy_id and str(new_strategy_id) != str(trade['strategy_id']):
                # 验证新策略是否存在
                cursor.execute('SELECT name FROM strategies WHERE id = ? AND is_active = 1', (new_strategy_id,))
                strategy_result = cursor.fetchone()
                if not strategy_result:
                    return False, "指定的策略不存在或已停用"

                old_strategy_id = trade['strategy_id']
                cursor.execute('''
                    UPDATE trades SET
                        strategy_id = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_strategy_id, trade_id))

                # 记录修改历史
                self.record_modification(cursor, trade_id, None, 'trade', 'strategy_id',
                                       old_strategy_id, new_strategy_id, modification_reason)

            # 更新交易明细
            if detail_updates:
                for detail_update in detail_updates:
                    detail_id = detail_update['id']

                    # 获取原交易明细
                    cursor.execute('SELECT * FROM trade_details WHERE id = ?', (detail_id,))
                    original_detail = cursor.fetchone()

                    if not original_detail:
                        continue

                    # 支持修改的字段
                    modifiable_fields = {
                        'price': float,
                        'quantity': int,
                        'transaction_fee': float,
                        'buy_reason': str,
                        'sell_reason': str
                    }

                    update_fields = []
                    update_values = []

                    # 检查每个字段是否有变化，记录修改历史
                    for field_name, field_type in modifiable_fields.items():
                        if field_name in detail_update:
                            new_value = detail_update[field_name]
                            old_value = original_detail[field_name]

                            # 类型转换
                            if field_type != str:
                                new_value = field_type(new_value) if new_value else 0
                                old_value = field_type(old_value) if old_value else 0
                            else:
                                new_value = str(new_value) if new_value else ''
                                old_value = str(old_value) if old_value else ''

                            # 如果值有变化，记录修改历史并准备更新
                            if new_value != old_value:
                                self.record_modification(cursor, trade_id, detail_id, 'detail', field_name, old_value, new_value, modification_reason)
                                update_fields.append(f"{field_name} = ?")
                                update_values.append(new_value)

                    # 如果有字段需要更新
                    if update_fields:
                        # 如果修改了价格或数量，需要重新计算金额
                        if 'price' in detail_update or 'quantity' in detail_update:
                            price = detail_update.get('price', original_detail['price'])
                            quantity = detail_update.get('quantity', original_detail['quantity'])
                            new_amount = float(price) * int(quantity)

                            # 记录金额变化
                            if new_amount != original_detail['amount']:
                                self.record_modification(cursor, trade_id, detail_id, 'detail', 'amount', original_detail['amount'], new_amount, modification_reason)
                                update_fields.append("amount = ?")
                                update_values.append(new_amount)

                        # 执行更新
                        update_sql = f"UPDATE trade_details SET {', '.join(update_fields)} WHERE id = ?"
                        update_values.append(detail_id)
                        cursor.execute(update_sql, update_values)

                # 重新计算所有汇总数据
                self._recalculate_trade_totals(cursor, trade_id)

            conn.commit()
            return True, "交易记录修改成功"

        except Exception as e:
            conn.rollback()
            return False, f"修改失败: {str(e)}"
        finally:
            conn.close()

    def _recalculate_trade_totals(self, cursor, trade_id):
        """重新计算交易汇总数据"""
        # 获取所有交易明细
        cursor.execute('''
            SELECT transaction_type, amount, quantity, transaction_fee
            FROM trade_details
            WHERE trade_id = ?
        ''', (trade_id,))
        details = cursor.fetchall()

        total_buy_amount = 0
        total_buy_quantity = 0
        total_sell_amount = 0
        total_sell_quantity = 0

        # 计算汇总数据
        for detail in details:
            amount = float(detail['amount'])
            quantity = int(detail['quantity'])
            fee = float(detail['transaction_fee'] or 0)

            if detail['transaction_type'] == 'buy':
                total_buy_amount += amount + fee  # 买入成本包含费用
                total_buy_quantity += quantity
            else:
                total_sell_amount += amount  # 卖出金额不包含费用
                total_sell_quantity += quantity

        # 计算净盈亏
        cursor.execute('''
            SELECT SUM(transaction_fee) as sell_fees FROM trade_details
            WHERE trade_id = ? AND transaction_type = 'sell'
        ''', (trade_id,))
        sell_fees_result = cursor.fetchone()
        sell_fees = float(sell_fees_result['sell_fees']) if sell_fees_result['sell_fees'] else 0

        net_sell_amount = total_sell_amount - sell_fees
        final_profit_loss = net_sell_amount - total_buy_amount
        final_profit_loss_pct = (final_profit_loss / total_buy_amount * 100) if total_buy_amount > 0 else 0

        # 更新主交易记录
        cursor.execute('''
            UPDATE trades SET
                total_buy_amount = ?,
                total_buy_quantity = ?,
                total_sell_amount = ?,
                total_sell_quantity = ?,
                total_profit_loss = ?,
                total_profit_loss_pct = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (total_buy_amount, total_buy_quantity, total_sell_amount, total_sell_quantity,
              final_profit_loss, final_profit_loss_pct, trade_id))

        # 重新计算每笔卖出的盈亏
        if total_buy_quantity > 0:
            avg_buy_price = total_buy_amount / total_buy_quantity

            cursor.execute('''
                SELECT * FROM trade_details
                WHERE trade_id = ? AND transaction_type = 'sell'
            ''', (trade_id,))
            sell_details = cursor.fetchall()

            for sell_detail in sell_details:
                sell_fee = float(sell_detail['transaction_fee'] or 0)
                sell_amount = float(sell_detail['amount'])
                quantity = int(sell_detail['quantity'])

                buy_cost = avg_buy_price * quantity
                net_sell_amount = sell_amount - sell_fee
                profit_loss = net_sell_amount - buy_cost
                profit_loss_pct = (profit_loss / buy_cost * 100) if buy_cost > 0 else 0

                cursor.execute('''
                    UPDATE trade_details SET
                        profit_loss = ?,
                        profit_loss_pct = ?
                    WHERE id = ?
                ''', (profit_loss, profit_loss_pct, sell_detail['id']))

    def get_trade_modifications(self, trade_id):
        """获取交易修改历史"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT tm.*, td.transaction_type, td.transaction_date
            FROM trade_modifications tm
            LEFT JOIN trade_details td ON tm.detail_id = td.id
            WHERE tm.trade_id = ?
            ORDER BY tm.created_at DESC
        ''', (trade_id,))

        modifications = cursor.fetchall()
        conn.close()

        return [dict(mod) for mod in modifications]

    def calculate_strategy_score(self, strategy_id=None, strategy=None, symbol_code=None, start_date=None, end_date=None):
        """计算策略打分"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 构建查询条件
            where_conditions = ["status = 'closed'", "deleted_at IS NULL"]
            params = []

            # 支持新的strategy_id参数，同时保持向后兼容
            if strategy_id:
                where_conditions.append("strategy_id = ?")
                params.append(strategy_id)
            elif strategy:
                # 兼容旧的strategy参数，尝试转换为strategy_id
                if isinstance(strategy, str):
                    # 旧策略代码映射
                    old_strategy_mapping = {
                        'trend': 1, 'rotation': 2, 'grid': 3, 'arbitrage': 4
                    }
                    strategy_id = old_strategy_mapping.get(strategy)
                    if strategy_id:
                        where_conditions.append("strategy_id = ?")
                        params.append(strategy_id)
                    else:
                        where_conditions.append("strategy = ?")
                        params.append(strategy)
                else:
                    where_conditions.append("strategy_id = ?")
                    params.append(strategy)

            if symbol_code:
                where_conditions.append("symbol_code = ?")
                params.append(symbol_code)

            if start_date:
                where_conditions.append("open_date >= ?")
                params.append(start_date)

            if end_date:
                where_conditions.append("close_date <= ?")
                params.append(end_date)

            where_clause = " AND ".join(where_conditions)

            # 获取已平仓交易
            cursor.execute(f'''
                SELECT * FROM trades
                WHERE {where_clause}
                ORDER BY close_date DESC
            ''', params)

            trades = cursor.fetchall()

            if not trades:
                return {
                    'win_rate_score': 0.0,
                    'profit_loss_ratio_score': 0.0,
                    'frequency_score': 0.0,
                    'total_score': 0.0,
                    'rating': '无数据',
                    'stats': {
                        'total_trades': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'win_rate': 0.0,
                        'avg_profit_loss_ratio': 0.0,
                        'avg_holding_days': 0.0,
                        'total_transaction_fees': 0.0,
                        'avg_fee_ratio': 0.0,
                        'total_fee_ratio': 0.0
                    }
                }

            # 计算基础统计
            total_trades = len(trades)
            winning_trades = sum(1 for trade in trades if trade['total_profit_loss'] > 0)
            losing_trades = sum(1 for trade in trades if trade['total_profit_loss'] < 0)

            # 计算胜率
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

            # 计算平均盈亏比
            winning_profits = [trade['total_profit_loss'] for trade in trades if trade['total_profit_loss'] > 0]
            losing_losses = [abs(trade['total_profit_loss']) for trade in trades if trade['total_profit_loss'] < 0]

            avg_profit = sum(winning_profits) / len(winning_profits) if winning_profits else 0
            avg_loss = sum(losing_losses) / len(losing_losses) if losing_losses else 1

            avg_profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0

            # 计算平均持仓天数
            holding_days = [trade['holding_days'] for trade in trades if trade['holding_days'] is not None]
            avg_holding_days = sum(holding_days) / len(holding_days) if holding_days else 0

            # 计算交易费用统计
            total_transaction_fees = 0
            total_transaction_volume = 0
            fee_ratios = []

            for trade in trades:
                # 获取每笔交易的总费用
                cursor.execute('''
                    SELECT SUM(transaction_fee) as total_fees,
                           SUM(CASE WHEN transaction_type = 'buy' THEN amount ELSE 0 END) as buy_volume,
                           SUM(CASE WHEN transaction_type = 'sell' THEN amount ELSE 0 END) as sell_volume
                    FROM trade_details WHERE trade_id = ?
                ''', (trade['id'],))
                fee_data = cursor.fetchone()

                if fee_data and fee_data['total_fees']:
                    trade_fees = float(fee_data['total_fees'])
                    trade_volume = float(fee_data['buy_volume'] or 0) + float(fee_data['sell_volume'] or 0)

                    total_transaction_fees += trade_fees
                    total_transaction_volume += trade_volume

                    if trade_volume > 0:
                        fee_ratio = (trade_fees / trade_volume) * 100
                        fee_ratios.append(fee_ratio)

            avg_fee_ratio = sum(fee_ratios) / len(fee_ratios) if fee_ratios else 0
            total_fee_ratio = (total_transaction_fees / total_transaction_volume) * 100 if total_transaction_volume > 0 else 0

            # 计算各项得分
            win_rate_score = round(min(win_rate / 10, 10.0), 2)

            # 盈亏比得分
            if avg_profit_loss_ratio < 1:
                profit_loss_ratio_score = 0.0
            elif avg_profit_loss_ratio > 10:
                profit_loss_ratio_score = 10.0
            else:
                profit_loss_ratio_score = round(avg_profit_loss_ratio, 2)

            # 频率得分（基于平均持仓天数）
            if avg_holding_days <= 1:
                frequency_score = 8.0
            elif avg_holding_days <= 7:
                frequency_score = 7.0
            elif avg_holding_days <= 30:
                frequency_score = 6.0
            elif avg_holding_days <= 180:
                frequency_score = 5.0
            elif avg_holding_days <= 360:
                frequency_score = 4.0
            elif avg_holding_days <= 720:
                frequency_score = 3.0
            elif avg_holding_days <= 1800:
                frequency_score = 2.0
            elif avg_holding_days <= 2880:
                frequency_score = 1.0
            else:
                frequency_score = 0.0

            # 总分
            total_score = round(win_rate_score + profit_loss_ratio_score + frequency_score, 2)

            # 评级
            if total_score >= 26:
                rating = '完美'
            elif total_score >= 23:
                rating = '优秀'
            elif total_score >= 20:
                rating = '良好'
            elif total_score >= 18:
                rating = '合格'
            else:
                rating = '不合格'

            return {
                'win_rate_score': win_rate_score,
                'profit_loss_ratio_score': profit_loss_ratio_score,
                'frequency_score': frequency_score,
                'total_score': total_score,
                'rating': rating,
                'stats': {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': round(win_rate, 2),
                    'avg_profit_loss_ratio': round(avg_profit_loss_ratio, 2),
                    'avg_holding_days': round(avg_holding_days, 2),
                    'total_transaction_fees': round(total_transaction_fees, 2),
                    'avg_fee_ratio': round(avg_fee_ratio, 4),
                    'total_fee_ratio': round(total_fee_ratio, 4)
                }
            }

        except Exception as e:
            return {
                'win_rate_score': 0.0,
                'profit_loss_ratio_score': 0.0,
                'frequency_score': 0.0,
                'total_score': 0.0,
                'rating': '计算错误',
                'stats': {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0.0,
                    'avg_profit_loss_ratio': 0.0,
                    'avg_holding_days': 0.0,
                    'total_transaction_fees': 0.0,
                    'avg_fee_ratio': 0.0,
                    'total_fee_ratio': 0.0
                },
                'error': str(e)
            }
        finally:
            conn.close()

    def get_strategy_scores(self):
        """获取所有策略的打分"""
        scores = {}
        strategies = self.get_all_strategies()
        for strategy in strategies:
            strategy_key = str(strategy['id'])  # 使用策略ID作为key
            scores[strategy_key] = self.calculate_strategy_score(strategy_id=strategy['id'])
            scores[strategy_key]['strategy_name'] = strategy['name']
            scores[strategy_key]['strategy_tags'] = strategy['tags']
        return scores

    def get_symbol_scores_by_strategy(self, strategy_id=None, strategy=None):
        """获取某策略下所有标的的打分"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 构建查询条件
            if strategy_id:
                query_condition = "strategy_id = ?"
                query_param = strategy_id
            elif strategy:
                # 兼容旧的strategy参数
                if isinstance(strategy, str):
                    old_strategy_mapping = {
                        'trend': 1, 'rotation': 2, 'grid': 3, 'arbitrage': 4
                    }
                    mapped_id = old_strategy_mapping.get(strategy)
                    if mapped_id:
                        query_condition = "strategy_id = ?"
                        query_param = mapped_id
                    else:
                        query_condition = "strategy = ?"
                        query_param = strategy
                else:
                    query_condition = "strategy_id = ?"
                    query_param = strategy
            else:
                return []

            # 获取该策略下所有已平仓的标的
            cursor.execute(f'''
                SELECT DISTINCT symbol_code, symbol_name
                FROM trades
                WHERE {query_condition} AND status = 'closed' AND deleted_at IS NULL
                ORDER BY symbol_code
            ''', (query_param,))

            symbols = cursor.fetchall()
            scores = []

            for symbol in symbols:
                symbol_code = symbol['symbol_code']
                symbol_name = symbol['symbol_name']
                score = self.calculate_strategy_score(strategy_id=strategy_id, strategy=strategy, symbol_code=symbol_code)
                score['symbol_code'] = symbol_code
                score['symbol_name'] = symbol_name
                scores.append(score)

            return scores

        except Exception as e:
            return []
        finally:
            conn.close()

    def get_all_symbols(self):
        """获取所有标的列表"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT DISTINCT symbol_code, symbol_name
                FROM trades
                WHERE status = 'closed' AND deleted_at IS NULL
                ORDER BY symbol_code
            ''')

            return cursor.fetchall()

        except Exception as e:
            return []
        finally:
            conn.close()

    def get_strategies_scores_by_symbol(self, symbol_code):
        """获取某标的下所有策略的打分"""
        scores = []
        strategies = self.get_all_strategies()

        for strategy in strategies:
            score = self.calculate_strategy_score(strategy_id=strategy['id'], symbol_code=symbol_code)
            score['strategy_id'] = strategy['id']
            score['strategy_code'] = str(strategy['id'])  # 为了兼容性
            score['strategy_name'] = strategy['name']
            score['strategy_tags'] = strategy['tags']
            scores.append(score)

        return scores

    def get_time_periods(self, period_type='year'):
        """获取时间段列表"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if period_type == 'year':
                cursor.execute('''
                    SELECT DISTINCT strftime('%Y', close_date) as period
                    FROM trades
                    WHERE status = 'closed' AND close_date IS NOT NULL AND deleted_at IS NULL
                    ORDER BY period DESC
                ''')
            elif period_type == 'quarter':
                cursor.execute('''
                    SELECT DISTINCT
                        strftime('%Y', close_date) || '-Q' ||
                        CASE
                            WHEN CAST(strftime('%m', close_date) AS INTEGER) <= 3 THEN '1'
                            WHEN CAST(strftime('%m', close_date) AS INTEGER) <= 6 THEN '2'
                            WHEN CAST(strftime('%m', close_date) AS INTEGER) <= 9 THEN '3'
                            ELSE '4'
                        END as period,
                        strftime('%Y', close_date) as year,
                        CASE
                            WHEN CAST(strftime('%m', close_date) AS INTEGER) <= 3 THEN '1'
                            WHEN CAST(strftime('%m', close_date) AS INTEGER) <= 6 THEN '2'
                            WHEN CAST(strftime('%m', close_date) AS INTEGER) <= 9 THEN '3'
                            ELSE '4'
                        END as quarter
                    FROM trades
                    WHERE status = 'closed' AND close_date IS NOT NULL AND deleted_at IS NULL
                    ORDER BY year DESC, quarter DESC
                ''')
            elif period_type == 'month':
                cursor.execute('''
                    SELECT DISTINCT strftime('%Y-%m', close_date) as period
                    FROM trades
                    WHERE status = 'closed' AND close_date IS NOT NULL AND deleted_at IS NULL
                    ORDER BY period DESC
                ''')

            return [row['period'] for row in cursor.fetchall()]

        except Exception as e:
            return []
        finally:
            conn.close()

    def get_period_date_range(self, period, period_type='year'):
        """根据时间段获取开始和结束日期"""
        start_date = None
        end_date = None

        if period_type == 'year':
            start_date = f"{period}-01-01"
            end_date = f"{period}-12-31"
        elif period_type == 'quarter':
            year, quarter = period.split('-Q')
            if quarter == '1':
                start_date = f"{year}-01-01"
                end_date = f"{year}-03-31"
            elif quarter == '2':
                start_date = f"{year}-04-01"
                end_date = f"{year}-06-30"
            elif quarter == '3':
                start_date = f"{year}-07-01"
                end_date = f"{year}-09-30"
            else:
                start_date = f"{year}-10-01"
                end_date = f"{year}-12-31"
        elif period_type == 'month':
            year, month = period.split('-')
            start_date = f"{year}-{month}-01"
            # 计算月末日期
            if month in ['01', '03', '05', '07', '08', '10', '12']:
                end_date = f"{year}-{month}-31"
            elif month in ['04', '06', '09', '11']:
                end_date = f"{year}-{month}-30"
            else:  # 二月
                # 简单处理，不考虑闰年
                end_date = f"{year}-{month}-28"
        else:
            # 默认按年处理
            start_date = f"{period}-01-01"
            end_date = f"{period}-12-31"

        return start_date, end_date

    def get_strategies_scores_by_time_period(self, period, period_type='year'):
        """获取某时间段下所有策略的打分"""
        start_date, end_date = self.get_period_date_range(period, period_type)
        scores = []
        strategies = self.get_all_strategies()

        for strategy in strategies:
            score = self.calculate_strategy_score(strategy_id=strategy['id'], start_date=start_date, end_date=end_date)
            score['strategy_id'] = strategy['id']
            score['strategy_code'] = str(strategy['id'])  # 为了兼容性
            score['strategy_name'] = strategy['name']
            score['strategy_tags'] = strategy['tags']
            score['period'] = period
            score['start_date'] = start_date
            score['end_date'] = end_date
            scores.append(score)

        return scores

    def get_period_summary(self, period, period_type='year'):
        """获取某时间段的总体统计摘要"""
        start_date, end_date = self.get_period_date_range(period, period_type)

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 获取时间段内的基本统计
            cursor.execute('''
                SELECT
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN total_profit_loss > 0 THEN 1 END) as winning_trades,
                    COUNT(CASE WHEN total_profit_loss < 0 THEN 1 END) as losing_trades,
                    COALESCE(SUM(total_profit_loss), 0) as total_profit,
                    COALESCE(AVG(JULIANDAY(close_date) - JULIANDAY(open_date)), 0) as avg_holding_days,
                    COUNT(DISTINCT symbol_code) as total_symbols,
                    COUNT(DISTINCT strategy_id) as active_strategies
                FROM trades
                WHERE status = 'closed'
                  AND close_date >= ?
                  AND close_date <= ?
                  AND deleted_at IS NULL
            ''', (start_date, end_date))

            summary = dict(cursor.fetchone())

            # 单独计算总交易费用
            cursor.execute('''
                SELECT COALESCE(SUM(td.transaction_fee), 0) as total_fees
                FROM trades t
                JOIN trade_details td ON t.id = td.trade_id
                WHERE t.status = 'closed'
                  AND t.close_date >= ?
                  AND t.close_date <= ?
                  AND t.deleted_at IS NULL
                  AND td.deleted_at IS NULL
            ''', (start_date, end_date))

            fee_result = cursor.fetchone()
            summary['total_fees'] = fee_result[0] if fee_result else 0.0

            # 计算胜率
            if summary['total_trades'] > 0:
                summary['win_rate'] = round((summary['winning_trades'] / summary['total_trades']) * 100, 2)
            else:
                summary['win_rate'] = 0.0

            # 获取最佳和最差表现的策略
            strategies = self.get_all_strategies()
            best_strategy = None
            worst_strategy = None
            best_score = -1
            worst_score = 31  # 最大分数是30

            for strategy in strategies:
                score = self.calculate_strategy_score(
                    strategy_id=strategy['id'],
                    start_date=start_date,
                    end_date=end_date
                )

                if score['stats']['total_trades'] > 0:
                    if score['total_score'] > best_score:
                        best_score = score['total_score']
                        best_strategy = {
                            'id': strategy['id'],
                            'name': strategy['name'],
                            'score': score['total_score'],
                            'trades': score['stats']['total_trades'],
                            'win_rate': score['stats']['win_rate']
                        }

                    if score['total_score'] < worst_score:
                        worst_score = score['total_score']
                        worst_strategy = {
                            'id': strategy['id'],
                            'name': strategy['name'],
                            'score': score['total_score'],
                            'trades': score['stats']['total_trades'],
                            'win_rate': score['stats']['win_rate']
                        }

            summary['best_strategy'] = best_strategy
            summary['worst_strategy'] = worst_strategy
            summary['period'] = period
            summary['period_type'] = period_type
            summary['start_date'] = start_date
            summary['end_date'] = end_date

            return summary

        except Exception as e:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_profit': 0.0,
                'total_fees': 0.0,
                'avg_holding_days': 0.0,
                'total_symbols': 0,
                'active_strategies': 0,
                'win_rate': 0.0,
                'best_strategy': None,
                'worst_strategy': None,
                'period': period,
                'period_type': period_type,
                'start_date': start_date,
                'end_date': end_date,
                'error': str(e)
            }
        finally:
            conn.close()

    def generate_confirmation_code(self, length=6):
        """生成随机确认码"""
        characters = string.ascii_uppercase + string.digits
        # 排除容易混淆的字符
        characters = characters.replace('0', '').replace('O', '').replace('1', '').replace('I', '').replace('L', '')
        return ''.join(random.choice(characters) for _ in range(length))

    def soft_delete_trade(self, trade_id, confirmation_code, delete_reason, operator_note=''):
        """软删除交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 检查交易是否存在且未被删除
            cursor.execute('SELECT * FROM trades WHERE id = ? AND deleted_at IS NULL', (trade_id,))
            trade = cursor.fetchone()

            if not trade:
                return False, "交易不存在或已被删除"

            # 获取交易明细
            cursor.execute('SELECT id FROM trade_details WHERE trade_id = ? AND deleted_at IS NULL', (trade_id,))
            detail_ids = [row['id'] for row in cursor.fetchall()]

            # 标记交易为已删除
            delete_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                UPDATE trades SET
                    deleted_at = ?,
                    deleted_reason = ?
                WHERE id = ?
            ''', (delete_time, delete_reason, trade_id))

            # 标记所有相关明细为已删除
            cursor.execute('''
                UPDATE trade_details SET deleted_at = ? WHERE trade_id = ?
            ''', (delete_time, trade_id))

            # 记录删除操作
            cursor.execute('''
                INSERT INTO deleted_records
                (trade_id, operation_type, affected_details, confirmation_code, delete_reason, operator_note)
                VALUES (?, 'delete', ?, ?, ?, ?)
            ''', (trade_id, json.dumps(detail_ids), confirmation_code, delete_reason, operator_note))

            conn.commit()
            return True, "交易记录已成功删除"

        except Exception as e:
            conn.rollback()
            return False, f"删除失败: {str(e)}"
        finally:
            conn.close()

    def batch_delete_trades(self, trade_ids, confirmation_code, delete_reason, operator_note=''):
        """批量软删除交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            success_count = 0
            failed_trades = []

            for trade_id in trade_ids:
                # 检查交易是否存在且未被删除
                cursor.execute('SELECT * FROM trades WHERE id = ? AND deleted_at IS NULL', (trade_id,))
                trade = cursor.fetchone()

                if not trade:
                    failed_trades.append(f"交易ID {trade_id}: 不存在或已被删除")
                    continue

                # 获取交易明细
                cursor.execute('SELECT id FROM trade_details WHERE trade_id = ? AND deleted_at IS NULL', (trade_id,))
                detail_ids = [row['id'] for row in cursor.fetchall()]

                # 标记交易为已删除
                delete_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    UPDATE trades SET
                        deleted_at = ?,
                        deleted_reason = ?
                    WHERE id = ?
                ''', (delete_time, delete_reason, trade_id))

                # 标记所有相关明细为已删除
                cursor.execute('''
                    UPDATE trade_details SET deleted_at = ? WHERE trade_id = ?
                ''', (delete_time, trade_id))

                # 记录删除操作
                cursor.execute('''
                    INSERT INTO deleted_records
                    (trade_id, operation_type, affected_details, confirmation_code, delete_reason, operator_note)
                    VALUES (?, 'delete', ?, ?, ?, ?)
                ''', (trade_id, json.dumps(detail_ids), confirmation_code, delete_reason, operator_note))

                success_count += 1

            conn.commit()

            if failed_trades:
                message = f"成功删除 {success_count} 笔交易，{len(failed_trades)} 笔失败：" + "; ".join(failed_trades)
                return success_count > 0, message
            else:
                return True, f"成功删除 {success_count} 笔交易记录"

        except Exception as e:
            conn.rollback()
            return False, f"批量删除失败: {str(e)}"
        finally:
            conn.close()

    def get_deleted_trades(self):
        """获取已删除的交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT t.*,
                   dr.delete_reason, dr.operator_note, dr.created_at as deleted_time,
                   dr.confirmation_code
            FROM trades t
            LEFT JOIN deleted_records dr ON t.id = dr.trade_id AND dr.operation_type = 'delete'
            WHERE t.deleted_at IS NOT NULL
            ORDER BY t.deleted_at DESC
        ''')

        trades = cursor.fetchall()
        conn.close()

        return [dict(trade) for trade in trades]

    def restore_trade(self, trade_id, confirmation_code, operator_note=''):
        """恢复已删除的交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 检查交易是否存在且已被删除
            cursor.execute('SELECT * FROM trades WHERE id = ? AND deleted_at IS NOT NULL', (trade_id,))
            trade = cursor.fetchone()

            if not trade:
                return False, "交易不存在或未被删除"

            # 获取被删除的交易明细
            cursor.execute('SELECT id FROM trade_details WHERE trade_id = ? AND deleted_at IS NOT NULL', (trade_id,))
            detail_ids = [row['id'] for row in cursor.fetchall()]

            # 恢复交易记录
            cursor.execute('''
                UPDATE trades SET
                    deleted_at = NULL,
                    deleted_reason = NULL
                WHERE id = ?
            ''', (trade_id,))

            # 恢复所有相关明细
            cursor.execute('''
                UPDATE trade_details SET deleted_at = NULL WHERE trade_id = ?
            ''', (trade_id,))

            # 记录恢复操作
            cursor.execute('''
                INSERT INTO deleted_records
                (trade_id, operation_type, affected_details, confirmation_code, operator_note)
                VALUES (?, 'restore', ?, ?, ?)
            ''', (trade_id, json.dumps(detail_ids), confirmation_code, operator_note))

            conn.commit()
            return True, "交易记录已成功恢复"

        except Exception as e:
            conn.rollback()
            return False, f"恢复失败: {str(e)}"
        finally:
            conn.close()

    def batch_restore_trades(self, trade_ids, confirmation_code, operator_note=''):
        """批量恢复已删除的交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            success_count = 0
            failed_trades = []

            for trade_id in trade_ids:
                # 检查交易是否存在且已被删除
                cursor.execute('SELECT * FROM trades WHERE id = ? AND deleted_at IS NOT NULL', (trade_id,))
                trade = cursor.fetchone()

                if not trade:
                    failed_trades.append(f"交易ID {trade_id}: 不存在或未被删除")
                    continue

                # 获取被删除的交易明细
                cursor.execute('SELECT id FROM trade_details WHERE trade_id = ? AND deleted_at IS NOT NULL', (trade_id,))
                detail_ids = [row['id'] for row in cursor.fetchall()]

                # 恢复交易记录
                cursor.execute('''
                    UPDATE trades SET
                        deleted_at = NULL,
                        deleted_reason = NULL
                    WHERE id = ?
                ''', (trade_id,))

                # 恢复所有相关明细
                cursor.execute('''
                    UPDATE trade_details SET deleted_at = NULL WHERE trade_id = ?
                ''', (trade_id,))

                # 记录恢复操作
                cursor.execute('''
                    INSERT INTO deleted_records
                    (trade_id, operation_type, affected_details, confirmation_code, operator_note)
                    VALUES (?, 'restore', ?, ?, ?)
                ''', (trade_id, json.dumps(detail_ids), confirmation_code, operator_note))

                success_count += 1

            conn.commit()

            if failed_trades:
                message = f"成功恢复 {success_count} 笔交易，{len(failed_trades)} 笔失败：" + "; ".join(failed_trades)
                return success_count > 0, message
            else:
                return True, f"成功恢复 {success_count} 笔交易记录"

        except Exception as e:
            conn.rollback()
            return False, f"批量恢复失败: {str(e)}"
        finally:
            conn.close()

    def permanently_delete_trade(self, trade_id, confirmation_code, confirmation_text, delete_reason, operator_note=''):
        """彻底删除交易记录（不可恢复）"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 验证确认文字
            if confirmation_text.upper() != 'PERMANENTLY DELETE':
                return False, "确认文字不正确，请输入 'PERMANENTLY DELETE'"

            # 检查交易是否存在且已被软删除
            cursor.execute('SELECT * FROM trades WHERE id = ? AND deleted_at IS NOT NULL', (trade_id,))
            trade = cursor.fetchone()

            if not trade:
                return False, "交易不存在或未被删除"

            # 获取要删除的交易明细ID
            cursor.execute('SELECT id FROM trade_details WHERE trade_id = ?', (trade_id,))
            detail_ids = [row['id'] for row in cursor.fetchall()]

            # 记录彻底删除操作（在删除前记录）
            cursor.execute('''
                INSERT INTO deleted_records
                (trade_id, operation_type, affected_details, confirmation_code, delete_reason, operator_note)
                VALUES (?, 'permanent_delete', ?, ?, ?, ?)
            ''', (trade_id, json.dumps(detail_ids), confirmation_code, delete_reason, operator_note))

            # 物理删除交易明细
            cursor.execute('DELETE FROM trade_details WHERE trade_id = ?', (trade_id,))

            # 物理删除交易记录
            cursor.execute('DELETE FROM trades WHERE id = ?', (trade_id,))

            conn.commit()
            return True, "交易记录已彻底删除，无法恢复"

        except Exception as e:
            conn.rollback()
            return False, f"彻底删除失败: {str(e)}"
        finally:
            conn.close()

    def batch_permanently_delete_trades(self, trade_ids, confirmation_code, confirmation_text, delete_reason, operator_note=''):
        """批量彻底删除交易记录（不可恢复）"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 验证确认文字
            if confirmation_text.upper() != 'PERMANENTLY DELETE':
                return False, "确认文字不正确，请输入 'PERMANENTLY DELETE'"

            success_count = 0
            failed_trades = []

            for trade_id in trade_ids:
                # 检查交易是否存在且已被软删除
                cursor.execute('SELECT * FROM trades WHERE id = ? AND deleted_at IS NOT NULL', (trade_id,))
                trade = cursor.fetchone()

                if not trade:
                    failed_trades.append(f"交易ID {trade_id}: 不存在或未被删除")
                    continue

                # 获取要删除的交易明细ID
                cursor.execute('SELECT id FROM trade_details WHERE trade_id = ?', (trade_id,))
                detail_ids = [row['id'] for row in cursor.fetchall()]

                # 记录彻底删除操作（在删除前记录）
                cursor.execute('''
                    INSERT INTO deleted_records
                    (trade_id, operation_type, affected_details, confirmation_code, delete_reason, operator_note)
                    VALUES (?, 'permanent_delete', ?, ?, ?, ?)
                ''', (trade_id, json.dumps(detail_ids), confirmation_code, delete_reason, operator_note))

                # 物理删除交易明细
                cursor.execute('DELETE FROM trade_details WHERE trade_id = ?', (trade_id,))

                # 物理删除交易记录
                cursor.execute('DELETE FROM trades WHERE id = ?', (trade_id,))

                success_count += 1

            conn.commit()

            if failed_trades:
                message = f"成功彻底删除 {success_count} 笔交易，{len(failed_trades)} 笔失败：" + "; ".join(failed_trades)
                return success_count > 0, message
            else:
                return True, f"成功彻底删除 {success_count} 笔交易记录，无法恢复"

        except Exception as e:
            conn.rollback()
            return False, f"批量彻底删除失败: {str(e)}"
        finally:
            conn.close()

# 策略定义
STRATEGIES = {
    'trend': '趋势跟踪',
    'rotation': '轮动策略',
    'grid': '网格策略',
    'arbitrage': '套利策略'
}

# 全局实例
tracker = TradingTracker(DB_PATH)

@app.route('/')
def index():
    """首页"""
    # 获取所有活跃策略
    strategies_data = tracker.get_all_strategies()
    strategies_dict = {str(s['id']): s['name'] for s in strategies_data}

    # 获取策略筛选参数
    selected_strategy = request.args.get('strategy', 'all')
    strategy_filter = None if selected_strategy == 'all' else selected_strategy

    # 获取交易数据用于统计
    all_trades = tracker.get_all_trades()
    if strategy_filter and strategy_filter != 'all':
        # 如果有策略筛选，过滤交易
        strategy_id = int(strategy_filter) if strategy_filter.isdigit() else None
        if strategy_id:
            all_trades = [t for t in all_trades if t.get('strategy_id') == strategy_id]

    open_trades = [t for t in all_trades if t['status'] == 'open']
    closed_trades = [t for t in all_trades if t['status'] == 'closed']

    # 计算统计数据
    total_trades = len(all_trades)
    total_open = len(open_trades)
    total_closed = len(closed_trades)

    # 计算总盈亏
    total_profit_loss = sum(trade['total_profit_loss'] for trade in all_trades)

    # 获取最近5笔交易
    recent_trades = sorted(all_trades, key=lambda x: x['created_at'], reverse=True)[:5]

    # 为recent_trades添加策略名称
    for trade in recent_trades:
        strategy_id = trade.get('strategy_id')
        if strategy_id:
            strategy = next((s for s in strategies_data if s['id'] == strategy_id), None)
            trade['strategy_name'] = strategy['name'] if strategy else '未知策略'
        else:
            # 兼容旧数据
            old_strategy_mapping = {
                'trend': '趋势跟踪策略',
                'rotation': '轮动策略',
                'grid': '网格策略',
                'arbitrage': '套利策略'
            }
            trade['strategy_name'] = old_strategy_mapping.get(trade.get('strategy', ''), '未知策略')

    # 按策略统计
    strategy_stats = {}
    for strategy in strategies_data:
        strategy_trades = [t for t in all_trades if t.get('strategy_id') == strategy['id']]
        strategy_stats[str(strategy['id'])] = {
            'name': strategy['name'],
            'total_trades': len(strategy_trades),
            'total_profit_loss': sum(trade['total_profit_loss'] for trade in strategy_trades)
        }

    stats = {
        'total_trades': total_trades,
        'open_trades': total_open,
        'closed_trades': total_closed,
        'total_profit_loss': total_profit_loss,
        'recent_trades': recent_trades,
        'strategy_stats': strategy_stats,
        'selected_strategy': selected_strategy
    }

    return render_template('index.html', stats=stats, strategies=strategies_dict)

@app.route('/trades')
def trades():
    """交易列表页面"""
    status = request.args.get('status', 'all')
    strategy = request.args.get('strategy', 'all')

    # 构建筛选条件
    status_filter = None if status == 'all' else status
    strategy_filter = None if strategy == 'all' else strategy

    trades_data = tracker.get_all_trades(status=status_filter, strategy=strategy_filter)

    return render_template('trades.html',
                         trades=trades_data,
                         current_status=status,
                         current_strategy=strategy,
                         strategies=STRATEGIES)

@app.route('/add_buy', methods=['GET', 'POST'])
def add_buy():
    """添加买入交易"""
    # 获取所有活跃策略
    strategies_data = tracker.get_all_strategies()
    strategies_dict = {str(s['id']): s['name'] for s in strategies_data}

    if request.method == 'POST':
        try:
            strategy = request.form['strategy']  # 这里将是策略ID
            symbol_code = request.form['symbol_code'].strip().upper()
            symbol_name = request.form['symbol_name'].strip()
            price = float(request.form['price'])
            quantity = int(request.form['quantity'])
            transaction_date = request.form['transaction_date']
            transaction_fee = float(request.form.get('transaction_fee', 0))
            buy_reason = request.form.get('buy_reason', '').strip()

            success, result = tracker.add_buy_transaction(
                strategy, symbol_code, symbol_name, price, quantity, transaction_date, transaction_fee, buy_reason
            )

            if success:
                return redirect(url_for('trades'))
            else:
                return render_template('add_buy.html',
                                     strategies=strategies_dict,
                                     strategies_data=strategies_data,
                                     error=result)

        except Exception as e:
            return render_template('add_buy.html',
                                 strategies=strategies_dict,
                                 strategies_data=strategies_data,
                                 error=f"输入错误: {str(e)}")

    # GET请求，获取默认策略
    default_strategy = request.args.get('strategy')
    # 如果传入的是旧的策略代码，转换为策略ID
    if default_strategy:
        old_strategy_mapping = {
            'trend': '趋势跟踪策略',
            'rotation': '轮动策略',
            'grid': '网格策略',
            'arbitrage': '套利策略'
        }
        strategy_name = old_strategy_mapping.get(default_strategy, default_strategy)

        # 查找对应的策略ID
        for strategy in strategies_data:
            if strategy['name'] == strategy_name or str(strategy['id']) == default_strategy:
                default_strategy = str(strategy['id'])
                break
        else:
            default_strategy = str(strategies_data[0]['id']) if strategies_data else None
    else:
        default_strategy = str(strategies_data[0]['id']) if strategies_data else None

    return render_template('add_buy.html',
                         strategies=strategies_dict,
                         strategies_data=strategies_data,
                         default_strategy=default_strategy)

@app.route('/add_sell/<int:trade_id>', methods=['GET', 'POST'])
def add_sell(trade_id):
    """添加卖出交易"""
    if request.method == 'POST':
        try:
            price = float(request.form['price'])
            quantity = int(request.form['quantity'])
            transaction_date = request.form['transaction_date']
            transaction_fee = float(request.form.get('transaction_fee', 0))
            sell_reason = request.form.get('sell_reason', '').strip()
            trade_log = request.form.get('trade_log', '').strip()

            success, result = tracker.add_sell_transaction(
                trade_id, price, quantity, transaction_date, transaction_fee, sell_reason, trade_log
            )

            if success:
                return redirect(url_for('trades'))
            else:
                return render_template('add_sell.html', trade_id=trade_id, error=result)

        except Exception as e:
            return render_template('add_sell.html', trade_id=trade_id, error=f"输入错误: {str(e)}")

    # 获取交易信息
    trades_data = tracker.get_all_trades()
    trade = next((t for t in trades_data if t['id'] == trade_id), None)

    if not trade:
        return redirect(url_for('trades'))

    return render_template('add_sell.html', trade=trade)

@app.route('/trade_details/<int:trade_id>')
def trade_details(trade_id):
    """交易明细页面"""
    trades_data = tracker.get_all_trades()
    trade = next((t for t in trades_data if t['id'] == trade_id), None)

    if not trade:
        return redirect(url_for('trades'))

    details = tracker.get_trade_details(trade_id)

    return render_template('trade_details.html', trade=trade, details=details)

@app.route('/edit_trade/<int:trade_id>', methods=['GET', 'POST'])
def edit_trade(trade_id):
    """修改已平仓交易记录"""
    if request.method == 'POST':
        try:
            trade_log = request.form.get('trade_log', '').strip()
            modification_reason = request.form.get('modification_reason', '').strip()
            new_strategy_id = request.form.get('strategy_id')

            # 检查修改原因是否为空
            if not modification_reason:
                raise ValueError("修改原因不能为空")

            # 处理交易明细更新
            detail_updates = []
            for key, value in request.form.items():
                if key.startswith('detail_'):
                    parts = key.split('_')
                    if len(parts) >= 3:
                        detail_id = parts[1]
                        field_name = '_'.join(parts[2:])

                        # 确保detail_updates中有对应的记录
                        detail_record = next((d for d in detail_updates if d['id'] == detail_id), None)
                        if not detail_record:
                            detail_record = {'id': detail_id}
                            detail_updates.append(detail_record)

                        detail_record[field_name] = value.strip() if isinstance(value, str) else value

            success, result = tracker.update_trade_record(trade_id, trade_log, detail_updates, modification_reason, new_strategy_id)

            if success:
                return redirect(url_for('trade_details', trade_id=trade_id))
            else:
                # 重新获取数据以显示错误
                trades_data = tracker.get_all_trades()
                trade = next((t for t in trades_data if t['id'] == trade_id), None)
                details = tracker.get_trade_details(trade_id)
                strategies_data = tracker.get_all_strategies()
                strategies_dict = {str(s['id']): s['name'] for s in strategies_data}
                return render_template('edit_trade.html', trade=trade, details=details,
                                     strategies_data=strategies_data, strategies_dict=strategies_dict, error=result)

        except Exception as e:
            # 重新获取数据以显示错误
            trades_data = tracker.get_all_trades()
            trade = next((t for t in trades_data if t['id'] == trade_id), None)
            details = tracker.get_trade_details(trade_id)
            strategies_data = tracker.get_all_strategies()
            strategies_dict = {str(s['id']): s['name'] for s in strategies_data}
            return render_template('edit_trade.html', trade=trade, details=details,
                                 strategies_data=strategies_data, strategies_dict=strategies_dict, error=f"输入错误: {str(e)}")

    # GET请求，显示修改页面
    trades_data = tracker.get_all_trades()
    trade = next((t for t in trades_data if t['id'] == trade_id), None)

    if not trade:
        return redirect(url_for('trades'))

    # 只允许修改已平仓的交易
    if trade['status'] != 'closed':
        return redirect(url_for('trade_details', trade_id=trade_id))

    details = tracker.get_trade_details(trade_id)
    strategies_data = tracker.get_all_strategies()
    strategies_dict = {str(s['id']): s['name'] for s in strategies_data}

    return render_template('edit_trade.html', trade=trade, details=details,
                         strategies_data=strategies_data, strategies_dict=strategies_dict)

@app.route('/trade_modifications/<int:trade_id>')
def trade_modifications(trade_id):
    """获取交易修改历史"""
    modifications = tracker.get_trade_modifications(trade_id)
    return jsonify({'modifications': modifications})

@app.route('/generate_confirmation_code')
def generate_confirmation_code():
    """生成确认码API"""
    code = tracker.generate_confirmation_code()
    return jsonify({'confirmation_code': code})

@app.route('/delete_trade/<int:trade_id>', methods=['POST'])
def delete_trade(trade_id):
    """删除单笔交易记录"""
    try:
        confirmation_code = request.form.get('confirmation_code', '').strip()
        delete_reason = request.form.get('delete_reason', '').strip()
        operator_note = request.form.get('operator_note', '').strip()

        if not confirmation_code:
            return jsonify({'success': False, 'message': '确认码不能为空'})

        if not delete_reason:
            return jsonify({'success': False, 'message': '删除原因不能为空'})

        success, message = tracker.soft_delete_trade(trade_id, confirmation_code, delete_reason, operator_note)
        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@app.route('/batch_delete_trades', methods=['POST'])
def batch_delete_trades():
    """批量删除交易记录"""
    try:
        trade_ids = request.form.getlist('trade_ids[]')
        confirmation_code = request.form.get('confirmation_code', '').strip()
        delete_reason = request.form.get('delete_reason', '').strip()
        operator_note = request.form.get('operator_note', '').strip()

        if not trade_ids:
            return jsonify({'success': False, 'message': '请选择要删除的交易记录'})

        if not confirmation_code:
            return jsonify({'success': False, 'message': '确认码不能为空'})

        if not delete_reason:
            return jsonify({'success': False, 'message': '删除原因不能为空'})

        # 转换为整数
        trade_ids = [int(id) for id in trade_ids]

        success, message = tracker.batch_delete_trades(trade_ids, confirmation_code, delete_reason, operator_note)
        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'批量删除失败: {str(e)}'})

# ==================== 策略管理路由 ====================

@app.route('/strategies')
def strategies():
    """策略管理页面"""
    strategies_data = tracker.get_all_strategies()
    tags_data = tracker.get_all_tags()
    return render_template('strategies.html', strategies=strategies_data, tags=tags_data)

@app.route('/strategy/create', methods=['GET', 'POST'])
def create_strategy():
    """创建策略"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            tag_names = request.form.getlist('tags')

            if not name:
                return jsonify({'success': False, 'message': '策略名称不能为空'})

            success, message = tracker.create_strategy(name, description, tag_names)
            return jsonify({'success': success, 'message': message})

        except Exception as e:
            return jsonify({'success': False, 'message': f'创建策略失败: {str(e)}'})

    # GET请求，显示创建表单
    tags_data = tracker.get_all_tags()
    return render_template('create_strategy.html', tags=tags_data)

@app.route('/strategy/<int:strategy_id>/edit', methods=['GET', 'POST'])
def edit_strategy(strategy_id):
    """编辑策略"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            tag_names = request.form.getlist('tags')

            if not name:
                return jsonify({'success': False, 'message': '策略名称不能为空'})

            success, message = tracker.update_strategy(strategy_id, name, description, tag_names)
            return jsonify({'success': success, 'message': message})

        except Exception as e:
            return jsonify({'success': False, 'message': f'更新策略失败: {str(e)}'})

    # GET请求，显示编辑表单
    strategy = tracker.get_strategy_by_id(strategy_id)
    if not strategy:
        return redirect(url_for('strategies'))

    tags_data = tracker.get_all_tags()
    return render_template('edit_strategy.html', strategy=strategy, tags=tags_data)

@app.route('/strategy/<int:strategy_id>/delete', methods=['POST'])
def delete_strategy(strategy_id):
    """删除策略"""
    try:
        success, message = tracker.delete_strategy(strategy_id)
        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'删除策略失败: {str(e)}'})

@app.route('/api/strategies')
def api_strategies():
    """获取策略列表API"""
    strategies_data = tracker.get_all_strategies()
    return jsonify(strategies_data)

@app.route('/api/tags')
def api_tags():
    """获取标签列表API"""
    tags_data = tracker.get_all_tags()
    return jsonify(tags_data)

@app.route('/api/tag/create', methods=['POST'])
def create_tag():
    """创建标签API"""
    try:
        name = request.form.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'message': '标签名称不能为空'})

        success, message = tracker.create_tag(name)
        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'创建标签失败: {str(e)}'})

@app.route('/api/tag/<int:tag_id>/update', methods=['POST'])
def update_tag(tag_id):
    """更新标签API"""
    try:
        new_name = request.form.get('name', '').strip()
        if not new_name:
            return jsonify({'success': False, 'message': '标签名称不能为空'})

        success, message = tracker.update_tag(tag_id, new_name)
        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'更新标签失败: {str(e)}'})

@app.route('/api/tag/<int:tag_id>/delete', methods=['POST'])
def delete_tag(tag_id):
    """删除标签API"""
    try:
        success, message = tracker.delete_tag(tag_id)
        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'删除标签失败: {str(e)}'})

@app.route('/deleted_trades')
def deleted_trades():
    """查看已删除的交易记录"""
    deleted_trades_data = tracker.get_deleted_trades()
    return render_template('deleted_trades.html', trades=deleted_trades_data, strategies=STRATEGIES)

@app.route('/restore_trade/<int:trade_id>', methods=['POST'])
def restore_trade(trade_id):
    """恢复单笔已删除的交易记录"""
    try:
        confirmation_code = request.form.get('confirmation_code', '').strip()
        operator_note = request.form.get('operator_note', '').strip()

        if not confirmation_code:
            return jsonify({'success': False, 'message': '确认码不能为空'})

        success, message = tracker.restore_trade(trade_id, confirmation_code, operator_note)
        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'恢复失败: {str(e)}'})

@app.route('/batch_restore_trades', methods=['POST'])
def batch_restore_trades():
    """批量恢复已删除的交易记录"""
    try:
        trade_ids = request.form.getlist('trade_ids[]')
        confirmation_code = request.form.get('confirmation_code', '').strip()
        operator_note = request.form.get('operator_note', '').strip()

        if not trade_ids:
            return jsonify({'success': False, 'message': '请选择要恢复的交易记录'})

        if not confirmation_code:
            return jsonify({'success': False, 'message': '确认码不能为空'})

        # 转换为整数
        trade_ids = [int(id) for id in trade_ids]

        success, message = tracker.batch_restore_trades(trade_ids, confirmation_code, operator_note)
        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'批量恢复失败: {str(e)}'})

@app.route('/permanently_delete_trade/<int:trade_id>', methods=['POST'])
def permanently_delete_trade(trade_id):
    """彻底删除单笔交易记录（不可恢复）"""
    try:
        confirmation_code = request.form.get('confirmation_code', '').strip()
        confirmation_text = request.form.get('confirmation_text', '').strip()
        delete_reason = request.form.get('delete_reason', '').strip()
        operator_note = request.form.get('operator_note', '').strip()

        if not confirmation_code:
            return jsonify({'success': False, 'message': '确认码不能为空'})

        if not confirmation_text:
            return jsonify({'success': False, 'message': '确认文字不能为空'})

        if not delete_reason:
            return jsonify({'success': False, 'message': '删除原因不能为空'})

        success, message = tracker.permanently_delete_trade(trade_id, confirmation_code, confirmation_text, delete_reason, operator_note)
        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'彻底删除失败: {str(e)}'})

@app.route('/batch_permanently_delete_trades', methods=['POST'])
def batch_permanently_delete_trades():
    """批量彻底删除交易记录（不可恢复）"""
    try:
        trade_ids = request.form.getlist('trade_ids[]')
        confirmation_code = request.form.get('confirmation_code', '').strip()
        confirmation_text = request.form.get('confirmation_text', '').strip()
        delete_reason = request.form.get('delete_reason', '').strip()
        operator_note = request.form.get('operator_note', '').strip()

        if not trade_ids:
            return jsonify({'success': False, 'message': '请选择要彻底删除的交易记录'})

        if not confirmation_code:
            return jsonify({'success': False, 'message': '确认码不能为空'})

        if not confirmation_text:
            return jsonify({'success': False, 'message': '确认文字不能为空'})

        if not delete_reason:
            return jsonify({'success': False, 'message': '删除原因不能为空'})

        # 转换为整数
        trade_ids = [int(id) for id in trade_ids]

        success, message = tracker.batch_permanently_delete_trades(trade_ids, confirmation_code, confirmation_text, delete_reason, operator_note)
        return jsonify({'success': success, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'批量彻底删除失败: {str(e)}'})

@app.route('/strategy_scores')
def strategy_scores():
    """策略评分概览页面"""
    scores = tracker.get_strategy_scores()
    strategies_data = tracker.get_all_strategies()
    strategies_dict = {str(s['id']): s['name'] for s in strategies_data}
    return render_template('strategy_scores.html', scores=scores, strategies=strategies_dict, strategies_data=strategies_data)

@app.route('/strategy_detail/<int:strategy_id>')
def strategy_detail(strategy_id):
    """策略详情页面"""
    # 验证策略是否存在
    strategy = tracker.get_strategy_by_id(strategy_id)
    if not strategy:
        return redirect(url_for('strategy_scores'))

    # 获取排序参数
    sort_by = request.args.get('sort', 'total_score')
    sort_order = request.args.get('order', 'desc')

    # 获取该策略的总体评分
    strategy_score = tracker.calculate_strategy_score(strategy_id=strategy_id)

    # 获取该策略下各标的的评分
    symbol_scores = tracker.get_symbol_scores_by_strategy(strategy_id=strategy_id)

    # 排序
    reverse = sort_order == 'desc'
    if sort_by in ['total_score', 'win_rate_score', 'profit_loss_ratio_score', 'frequency_score']:
        symbol_scores.sort(key=lambda x: x[sort_by], reverse=reverse)
    elif sort_by == 'symbol_code':
        symbol_scores.sort(key=lambda x: x['symbol_code'], reverse=reverse)
    elif sort_by == 'win_rate':
        symbol_scores.sort(key=lambda x: x['stats']['win_rate'], reverse=reverse)
    elif sort_by == 'avg_profit_loss_ratio':
        symbol_scores.sort(key=lambda x: x['stats']['avg_profit_loss_ratio'], reverse=reverse)
    elif sort_by == 'avg_holding_days':
        symbol_scores.sort(key=lambda x: x['stats']['avg_holding_days'], reverse=reverse)

    strategies_data = tracker.get_all_strategies()
    strategies_dict = {str(s['id']): s['name'] for s in strategies_data}

    return render_template('strategy_detail.html',
                         strategy_id=strategy_id,
                         strategy=strategy,
                         strategy_score=strategy_score,
                         symbol_scores=symbol_scores,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         strategies=strategies_dict)

@app.route('/api/strategy_score')
def api_strategy_score():
    """策略评分API"""
    strategy_id = request.args.get('strategy_id')
    strategy = request.args.get('strategy')  # 保持向后兼容
    symbol_code = request.args.get('symbol')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # 优先使用strategy_id，如果没有则使用strategy（向后兼容）
    if strategy_id:
        score = tracker.calculate_strategy_score(strategy_id=int(strategy_id), symbol_code=symbol_code, start_date=start_date, end_date=end_date)
    else:
        score = tracker.calculate_strategy_score(strategy=strategy, symbol_code=symbol_code, start_date=start_date, end_date=end_date)

    return jsonify(score)

@app.route('/symbol_comparison')
def symbol_comparison():
    """标的策略比较页面"""
    symbols = tracker.get_all_symbols()
    strategies_data = tracker.get_all_strategies()
    strategies_dict = {str(s['id']): s['name'] for s in strategies_data}
    return render_template('symbol_comparison.html', symbols=symbols, strategies=strategies_dict, strategies_data=strategies_data)

@app.route('/symbol_detail/<symbol_code>')
def symbol_detail(symbol_code):
    """标的详情页面 - 比较不同策略"""
    # 获取排序参数
    sort_by = request.args.get('sort', 'total_score')
    sort_order = request.args.get('order', 'desc')

    # 获取标的信息
    symbols = tracker.get_all_symbols()
    symbol_info = next((s for s in symbols if s['symbol_code'] == symbol_code), None)
    if not symbol_info:
        return redirect(url_for('symbol_comparison'))

    # 获取该标的下各策略的评分
    strategy_scores = tracker.get_strategies_scores_by_symbol(symbol_code)

    # 排序
    reverse = sort_order == 'desc'
    if sort_by in ['total_score', 'win_rate_score', 'profit_loss_ratio_score', 'frequency_score']:
        strategy_scores.sort(key=lambda x: x[sort_by], reverse=reverse)
    elif sort_by == 'strategy_code':
        strategy_scores.sort(key=lambda x: x['strategy_code'], reverse=reverse)
    elif sort_by == 'win_rate':
        strategy_scores.sort(key=lambda x: x['stats']['win_rate'], reverse=reverse)
    elif sort_by == 'avg_profit_loss_ratio':
        strategy_scores.sort(key=lambda x: x['stats']['avg_profit_loss_ratio'], reverse=reverse)
    elif sort_by == 'avg_holding_days':
        strategy_scores.sort(key=lambda x: x['stats']['avg_holding_days'], reverse=reverse)

    strategies_data = tracker.get_all_strategies()
    strategies_dict = {str(s['id']): s['name'] for s in strategies_data}

    return render_template('symbol_detail.html',
                         symbol_code=symbol_code,
                         symbol_name=symbol_info['symbol_name'],
                         strategy_scores=strategy_scores,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         strategies=strategies_dict,
                         strategies_data=strategies_data)

@app.route('/time_comparison')
def time_comparison():
    """时间段策略比较页面"""
    period_type = request.args.get('period_type', 'year')
    periods = tracker.get_time_periods(period_type)
    strategies_data = tracker.get_all_strategies()
    strategies_dict = {str(s['id']): s['name'] for s in strategies_data}
    return render_template('time_comparison.html',
                         periods=periods,
                         period_type=period_type,
                         strategies=strategies_dict,
                         strategies_data=strategies_data)

@app.route('/time_detail/<period>')
def time_detail(period):
    """时间段详情页面 - 比较不同策略"""
    period_type = request.args.get('period_type', 'year')
    sort_by = request.args.get('sort', 'total_score')
    sort_order = request.args.get('order', 'desc')

    # 获取该时间段下各策略的评分
    strategy_scores = tracker.get_strategies_scores_by_time_period(period, period_type)

    # 获取时间段总结
    period_summary = tracker.get_period_summary(period, period_type)

    if not strategy_scores:
        return redirect(url_for('time_comparison', period_type=period_type))

    # 排序
    reverse = sort_order == 'desc'
    if sort_by in ['total_score', 'win_rate_score', 'profit_loss_ratio_score', 'frequency_score']:
        strategy_scores.sort(key=lambda x: x[sort_by], reverse=reverse)
    elif sort_by == 'strategy_code':
        strategy_scores.sort(key=lambda x: x['strategy_code'], reverse=reverse)
    elif sort_by == 'win_rate':
        strategy_scores.sort(key=lambda x: x['stats']['win_rate'], reverse=reverse)
    elif sort_by == 'avg_profit_loss_ratio':
        strategy_scores.sort(key=lambda x: x['stats']['avg_profit_loss_ratio'], reverse=reverse)
    elif sort_by == 'avg_holding_days':
        strategy_scores.sort(key=lambda x: x['stats']['avg_holding_days'], reverse=reverse)

    strategies_data = tracker.get_all_strategies()
    strategies_dict = {str(s['id']): s['name'] for s in strategies_data}

    return render_template('time_detail.html',
                         period=period,
                         period_type=period_type,
                         strategy_scores=strategy_scores,
                         period_summary=period_summary,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         strategies=strategies_dict,
                         strategies_data=strategies_data)

@app.route('/api/strategy_trend')
def api_strategy_trend():
    """获取策略表现趋势数据"""
    period_type = request.args.get('period_type', 'year')

    # 获取所有时间段
    periods = tracker.get_time_periods(period_type)
    strategies = tracker.get_all_strategies()

    trend_data = {
        'periods': periods,
        'strategies': [],
        'period_type': period_type
    }

    # 为每个策略收集趋势数据
    for strategy in strategies:
        strategy_trend = {
            'id': strategy['id'],
            'name': strategy['name'],
            'tags': strategy['tags'],
            'scores': []
        }

        for period in periods:
            score_data = tracker.calculate_strategy_score(
                strategy_id=strategy['id'],
                start_date=tracker.get_period_date_range(period, period_type)[0],
                end_date=tracker.get_period_date_range(period, period_type)[1]
            )
            strategy_trend['scores'].append({
                'period': period,
                'total_score': score_data['total_score'],
                'win_rate_score': score_data['win_rate_score'],
                'profit_loss_ratio_score': score_data['profit_loss_ratio_score'],
                'frequency_score': score_data['frequency_score'],
                'total_trades': score_data['stats']['total_trades']
            })

        trend_data['strategies'].append(strategy_trend)

    return jsonify(trend_data)

if __name__ == '__main__':
    print("趋势交易跟踪系统启动中...")
    print(f"数据库文件: {os.path.abspath(DB_PATH)}")
    print("访问地址: http://127.0.0.1:8383")
    app.run(debug=True, host='127.0.0.1', port=8383)