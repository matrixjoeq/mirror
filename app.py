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

app = Flask(__name__)
app.secret_key = 'trend_trading_tracker_2024'

# 数据库文件路径
DB_PATH = 'trading_tracker.db'

class TradingTracker:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
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
                profit_loss DECIMAL(15,3) DEFAULT 0,
                profit_loss_pct DECIMAL(8,4) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_id) REFERENCES trades (id)
            )
        ''')
        
        # 为现有数据添加策略字段（兼容性处理）
        try:
            cursor.execute("SELECT strategy FROM trades LIMIT 1")
        except sqlite3.OperationalError:
            # 如果strategy字段不存在，添加它并设置默认值
            cursor.execute('ALTER TABLE trades ADD COLUMN strategy TEXT DEFAULT "trend"')
            cursor.execute('UPDATE trades SET strategy = "trend" WHERE strategy IS NULL')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(open_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_details_trade ON trade_details(trade_id)')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def add_buy_transaction(self, strategy, symbol_code, symbol_name, price, quantity, transaction_date):
        """添加买入交易"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            amount = Decimal(str(price)) * quantity
            
            # 查找是否已有该标的的同策略未完成交易
            cursor.execute('''
                SELECT id FROM trades 
                WHERE strategy = ? AND symbol_code = ? AND status = 'open'
                ORDER BY open_date DESC LIMIT 1
            ''', (strategy, symbol_code))
            
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
                ''', (float(amount), quantity, quantity, trade_id))
            else:
                # 创建新交易
                cursor.execute('''
                    INSERT INTO trades (strategy, symbol_code, symbol_name, open_date, total_buy_amount, 
                                      total_buy_quantity, remaining_quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (strategy, symbol_code, symbol_name, transaction_date, float(amount), quantity, quantity))
                trade_id = cursor.lastrowid
            
            # 添加交易明细
            cursor.execute('''
                INSERT INTO trade_details (trade_id, transaction_type, price, quantity, 
                                         amount, transaction_date)
                VALUES (?, 'buy', ?, ?, ?, ?)
            ''', (trade_id, float(price), quantity, float(amount), transaction_date))
            
            conn.commit()
            return True, trade_id
            
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
    
    def add_sell_transaction(self, trade_id, price, quantity, transaction_date):
        """添加卖出交易"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
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
            
            # 计算加权平均买入价
            avg_buy_price = Decimal(str(trade['total_buy_amount'])) / trade['total_buy_quantity']
            
            # 计算这笔卖出的盈亏
            buy_cost = avg_buy_price * quantity
            profit_loss = sell_amount - buy_cost
            profit_loss_pct = (profit_loss / buy_cost) * 100 if buy_cost > 0 else 0
            
            # 更新剩余数量
            new_remaining_quantity = trade['remaining_quantity'] - quantity
            
            # 更新交易主表
            cursor.execute('''
                UPDATE trades SET
                    total_sell_amount = total_sell_amount + ?,
                    total_sell_quantity = total_sell_quantity + ?,
                    remaining_quantity = ?,
                    total_profit_loss = total_profit_loss + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (float(sell_amount), quantity, new_remaining_quantity, float(profit_loss), trade_id))
            
            # 如果完全平仓，更新状态和计算持仓天数
            if new_remaining_quantity == 0:
                holding_days = (datetime.strptime(transaction_date, '%Y-%m-%d').date() - 
                              datetime.strptime(trade['open_date'], '%Y-%m-%d').date()).days
                
                total_profit_loss_pct = ((Decimal(str(trade['total_profit_loss'])) + profit_loss) / 
                                       Decimal(str(trade['total_buy_amount']))) * 100
                
                cursor.execute('''
                    UPDATE trades SET
                        status = 'closed',
                        close_date = ?,
                        holding_days = ?,
                        total_profit_loss_pct = ?
                    WHERE id = ?
                ''', (transaction_date, holding_days, float(total_profit_loss_pct), trade_id))
            
            # 添加卖出明细
            cursor.execute('''
                INSERT INTO trade_details (trade_id, transaction_type, price, quantity, 
                                         amount, transaction_date, profit_loss, profit_loss_pct)
                VALUES (?, 'sell', ?, ?, ?, ?, ?, ?)
            ''', (trade_id, float(price), quantity, float(sell_amount), 
                  transaction_date, float(profit_loss), float(profit_loss_pct)))
            
            conn.commit()
            return True, "卖出成功"
            
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
    
    def get_all_trades(self, status=None, strategy=None):
        """获取所有交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        where_conditions = []
        params = []
        
        if status:
            where_conditions.append("status = ?")
            params.append(status)
            
        if strategy:
            where_conditions.append("strategy = ?")
            params.append(strategy)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        cursor.execute(f'''
            SELECT * FROM trades 
            {where_clause}
            ORDER BY open_date DESC, id DESC
        ''', params)
        
        trades = cursor.fetchall()
        conn.close()
        
        return [dict(trade) for trade in trades]
    
    def get_trade_details(self, trade_id):
        """获取交易明细"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM trade_details 
            WHERE trade_id = ?
            ORDER BY transaction_date ASC, id ASC
        ''', (trade_id,))
        
        details = cursor.fetchall()
        conn.close()
        
        return [dict(detail) for detail in details]

# 策略定义
STRATEGIES = {
    'trend': '趋势跟踪',
    'rotation': '轮动策略', 
    'grid': '网格策略'
}

# 全局实例
tracker = TradingTracker(DB_PATH)

@app.route('/')
def index():
    """首页"""
    # 获取策略筛选参数
    selected_strategy = request.args.get('strategy', 'all')
    strategy_filter = None if selected_strategy == 'all' else selected_strategy
    
    # 获取交易数据用于统计
    all_trades = tracker.get_all_trades(strategy=strategy_filter)
    open_trades = tracker.get_all_trades('open', strategy=strategy_filter)
    closed_trades = tracker.get_all_trades('closed', strategy=strategy_filter)
    
    # 计算统计数据
    total_trades = len(all_trades)
    total_open = len(open_trades)
    total_closed = len(closed_trades)
    
    # 计算总盈亏
    total_profit_loss = sum(trade['total_profit_loss'] for trade in all_trades)
    
    # 获取最近5笔交易
    recent_trades = all_trades[:5]
    
    # 按策略统计
    strategy_stats = {}
    for strategy_code, strategy_name in STRATEGIES.items():
        strategy_trades = tracker.get_all_trades(strategy=strategy_code)
        strategy_stats[strategy_code] = {
            'name': strategy_name,
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
    
    return render_template('index.html', stats=stats, strategies=STRATEGIES)

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
    if request.method == 'POST':
        try:
            strategy = request.form['strategy']
            symbol_code = request.form['symbol_code'].strip().upper()
            symbol_name = request.form['symbol_name'].strip()
            price = float(request.form['price'])
            quantity = int(request.form['quantity'])
            transaction_date = request.form['transaction_date']
            
            success, result = tracker.add_buy_transaction(
                strategy, symbol_code, symbol_name, price, quantity, transaction_date
            )
            
            if success:
                return redirect(url_for('trades', strategy=strategy))
            else:
                return render_template('add_buy.html', strategies=STRATEGIES, error=result)
                
        except Exception as e:
            return render_template('add_buy.html', strategies=STRATEGIES, error=f"输入错误: {str(e)}")
    
    # GET请求，获取默认策略
    default_strategy = request.args.get('strategy', 'trend')
    return render_template('add_buy.html', strategies=STRATEGIES, default_strategy=default_strategy)

@app.route('/add_sell/<int:trade_id>', methods=['GET', 'POST'])
def add_sell(trade_id):
    """添加卖出交易"""
    if request.method == 'POST':
        try:
            price = float(request.form['price'])
            quantity = int(request.form['quantity'])
            transaction_date = request.form['transaction_date']
            
            success, result = tracker.add_sell_transaction(
                trade_id, price, quantity, transaction_date
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

if __name__ == '__main__':
    print("趋势交易跟踪系统启动中...")
    print(f"数据库文件: {os.path.abspath(DB_PATH)}")
    print("访问地址: http://127.0.0.1:8383")
    app.run(debug=True, host='127.0.0.1', port=8383)