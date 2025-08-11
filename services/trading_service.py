#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易服务层
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal

from .database_service import DatabaseService
from .strategy_service import StrategyService
from models.trading import Trade, TradeDetail, TradeModification
from utils.helpers import generate_confirmation_code


class TradingService:
    """交易管理服务"""
    
    def __init__(self, db_service: Optional[DatabaseService] = None):
        self.db = db_service or DatabaseService()
        self.strategy_service = StrategyService(self.db)
    
    def add_buy_transaction(self, strategy, symbol_code: str, symbol_name: str, 
                          price: Decimal, quantity: int, transaction_date: str,
                          transaction_fee: Decimal = Decimal('0'), buy_reason: str = '') -> Tuple[bool, Any]:
        """添加买入交易"""
        try:
            # 输入验证
            if not symbol_code or not symbol_name:
                return False, "股票代码和名称不能为空"
            
            if price <= 0 or quantity <= 0:
                return False, "价格和数量必须大于0"
            
            # 解析和验证策略
            strategy_id = self._resolve_strategy(strategy)
            if not strategy_id:
                return False, f"策略ID {strategy} 不存在或已被禁用"
            
            # 确保类型一致并计算交易金额
            price = Decimal(str(price))
            quantity = int(quantity)
            transaction_fee = Decimal(str(transaction_fee))
            amount = price * quantity + transaction_fee
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查是否已有该股票的开放交易
                cursor.execute('''
                    SELECT id FROM trades 
                    WHERE strategy_id = ? AND symbol_code = ? AND status = 'open' AND is_deleted = 0
                ''', (strategy_id, symbol_code))
                
                existing_trade = cursor.fetchone()
                
                if existing_trade:
                    # 更新现有交易
                    trade_id = existing_trade['id']
                    self._update_existing_trade_for_buy(cursor, trade_id, price, quantity, transaction_date, transaction_fee, amount)
                else:
                    # 创建新交易
                    trade_id = self._create_new_trade(cursor, strategy_id, symbol_code, symbol_name, transaction_date)
                    # 更新新交易的金额
                    self._update_existing_trade_for_buy(cursor, trade_id, price, quantity, transaction_date, transaction_fee, amount)
                
                # 添加交易明细
                cursor.execute('''
                    INSERT INTO trade_details (
                        trade_id, transaction_type, price, quantity, amount,
                        transaction_date, transaction_fee, buy_reason, created_at
                    ) VALUES (?, 'buy', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (trade_id, float(price), quantity, float(amount), transaction_date, float(transaction_fee), buy_reason))
                
                conn.commit()
                return True, trade_id
                
        except Exception as e:
            return False, f"添加买入交易失败: {str(e)}"
    
    def add_sell_transaction(self, trade_id: int, price: Decimal, quantity: int,
                           transaction_date: str, transaction_fee: Decimal = Decimal('0'),
                           sell_reason: str = '', trade_log: str = '') -> Tuple[bool, str]:
        """添加卖出交易"""
        try:
            # 确保类型一致
            price = Decimal(str(price))
            quantity = int(quantity)
            transaction_fee = Decimal(str(transaction_fee))
            
            # 输入验证
            if price <= 0 or quantity <= 0:
                return False, "价格和数量必须大于0"
            
            # 获取交易信息
            trade = self.get_trade_by_id(trade_id)
            if not trade:
                return False, f"交易ID {trade_id} 不存在"
            
            if trade['status'] == 'closed':
                return False, "该交易已平仓"
            
            if trade['remaining_quantity'] < quantity:
                return False, f"卖出数量({quantity})超过剩余持仓({trade['remaining_quantity']})"
            
            # 计算交易金额（amount 仍记录净额：卖出收入扣除卖出费用）
            sell_amount = price * quantity - transaction_fee

            # 计算不含费用的加权买入均价与盈亏
            # 按买入明细聚合，得到总买入金额（不含费用）与数量，以及买入手续费总额
            buy_agg = self.db.execute_query(
                """
                SELECT COALESCE(SUM(price * quantity), 0) AS gross_buy,
                       COALESCE(SUM(quantity), 0) AS qty,
                       COALESCE(SUM(transaction_fee), 0) AS buy_fees
                FROM trade_details
                WHERE trade_id = ? AND transaction_type = 'buy' AND is_deleted = 0
                """,
                (trade_id,),
                fetch_one=True,
            )
            gross_buy = Decimal(str(buy_agg['gross_buy'])) if buy_agg else Decimal('0')
            total_buy_quantity = Decimal(str(buy_agg['qty'])) if buy_agg else Decimal('0')
            total_buy_fees = Decimal(str(buy_agg['buy_fees'])) if buy_agg else Decimal('0')

            avg_buy_price_ex_fee = (gross_buy / total_buy_quantity) if total_buy_quantity > 0 else Decimal('0')
            buy_cost_ex_fee = avg_buy_price_ex_fee * Decimal(str(quantity))
            gross_sell_amount = price * quantity
            # 毛利（不含任何费用）
            profit_loss = gross_sell_amount - buy_cost_ex_fee
            # 分摊到本次卖出的买入手续费
            buy_fee_alloc_for_this_sell = (total_buy_fees * (Decimal(str(quantity)) / total_buy_quantity)) if total_buy_quantity > 0 else Decimal('0')
            # 净利 = 净卖出(扣本次卖出费) - 不含费买入成本 - 分摊买入手续费
            net_profit_this_sell = (gross_sell_amount - transaction_fee) - buy_cost_ex_fee - buy_fee_alloc_for_this_sell
            profit_loss_pct = ((gross_sell_amount - buy_cost_ex_fee) / buy_cost_ex_fee * 100) if buy_cost_ex_fee > 0 else Decimal('0')
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 添加卖出明细（不存储单笔盈亏，仅存金额与费用）
                cursor.execute('''
                    INSERT INTO trade_details (
                        trade_id, transaction_type, price, quantity, amount,
                        transaction_date, transaction_fee, sell_reason,
                        created_at
                    ) VALUES (?, 'sell', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (trade_id, float(price), quantity, float(sell_amount), transaction_date,
                      float(transaction_fee), sell_reason))
                
                # 更新交易主记录
                new_remaining = trade['remaining_quantity'] - quantity
                new_sell_amount = Decimal(str(trade['total_sell_amount'])) + sell_amount
                new_sell_quantity = trade['total_sell_quantity'] + quantity
                new_profit_loss = Decimal(str(trade['total_profit_loss'])) + profit_loss
                # 使用不含费用的总买入额作为分母计算汇总盈亏比例
                # 以买入明细实时聚合为准，避免费用干扰
                total_buy_gross_row = self.db.execute_query(
                    """
                    SELECT COALESCE(SUM(price * quantity), 0) AS gross_buy
                    FROM trade_details
                    WHERE trade_id = ? AND transaction_type = 'buy' AND is_deleted = 0
                    """,
                    (trade_id,),
                    fetch_one=True,
                )
                total_buy_gross = Decimal(str(total_buy_gross_row['gross_buy'])) if total_buy_gross_row else Decimal('0')
                new_profit_loss_pct = (new_profit_loss / total_buy_gross * 100) if total_buy_gross > 0 else Decimal('0')

                # 计算累计手续费（卖出+分摊买入），用于得到总净利润与净利率
                sell_fees_row = self.db.execute_query(
                    """
                    SELECT COALESCE(SUM(transaction_fee),0) AS sell_fees
                    FROM trade_details
                    WHERE trade_id = ? AND transaction_type = 'sell' AND is_deleted = 0
                    """,
                    (trade_id,),
                    fetch_one=True,
                )
                sell_fees_total = Decimal(str(sell_fees_row['sell_fees'])) if sell_fees_row else Decimal('0')
                buy_fees_row = self.db.execute_query(
                    """
                    SELECT COALESCE(SUM(transaction_fee),0) AS buy_fees
                    FROM trade_details
                    WHERE trade_id = ? AND transaction_type = 'buy' AND is_deleted = 0
                    """,
                    (trade_id,),
                    fetch_one=True,
                )
                buy_fees_total = Decimal(str(buy_fees_row['buy_fees'])) if buy_fees_row else Decimal('0')
                # 已卖出部分的买入成本与分摊买入手续费
                buy_cost_for_sold = avg_buy_price_ex_fee * Decimal(str(new_sell_quantity))
                allocated_buy_fees_for_sold = (buy_fees_total * (Decimal(str(new_sell_quantity)) / total_buy_quantity)) if total_buy_quantity > 0 else Decimal('0')
                new_gross_profit_total = new_profit_loss
                new_net_profit_total = new_gross_profit_total - sell_fees_total - allocated_buy_fees_for_sold
                denom_buy_cost_for_sold = buy_cost_for_sold
                new_net_profit_pct = (new_net_profit_total / denom_buy_cost_for_sold * 100) if denom_buy_cost_for_sold > 0 else Decimal('0')
                
                status = 'closed' if new_remaining == 0 else 'open'
                close_date = transaction_date if status == 'closed' else None
                
                # 计算持仓天数
                if status == 'closed':
                    open_date = datetime.strptime(trade['open_date'], '%Y-%m-%d').date()
                    close_date_obj = datetime.strptime(transaction_date, '%Y-%m-%d').date()
                    holding_days = (close_date_obj - open_date).days
                else:
                    holding_days = trade['holding_days']
                
                cursor.execute('''
                    UPDATE trades SET
                        total_sell_amount = ?, total_sell_quantity = ?, remaining_quantity = ?,
                        total_profit_loss = ?, total_profit_loss_pct = ?,
                        total_gross_profit = ?, total_net_profit = ?, total_net_profit_pct = ?,
                        status = ?, close_date = ?, holding_days = ?, trade_log = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                        float(new_sell_amount), new_sell_quantity, new_remaining,
                        float(new_gross_profit_total), float(new_profit_loss_pct),
                        float(new_gross_profit_total), float(new_net_profit_total), float(new_net_profit_pct),
                        status, close_date, holding_days, trade_log, trade_id
                ))
                
                conn.commit()
                return True, "卖出交易添加成功"
                
        except Exception as e:
            return False, f"添加卖出交易失败: {str(e)}"
    
    def get_all_trades(self, status: Optional[str] = None, strategy: Optional[str] = None,
                       include_deleted: bool = False,
                       order_by: str = 't.created_at DESC',
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取交易列表（统一查询与计算接口）

        - 统一补全指标：总毛利润、总净利润、总净利率、总买入成交（不含费用）等
        - 支持按状态/策略筛选，按任意列排序，并可限制返回条数
        """
        query = '''
            SELECT t.*, s.name as strategy_name
            FROM trades t
            LEFT JOIN strategies s ON t.strategy_id = s.id
        '''
        
        conditions = []
        params = []
        
        if not include_deleted:
            conditions.append("t.is_deleted = 0")
        
        if status:
            conditions.append("t.status = ?")
            params.append(status)
        
        if strategy:
            strategy_id = self._resolve_strategy(strategy)
            if strategy_id:
                conditions.append("t.strategy_id = ?")
                params.append(strategy_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # 排序（白名单保护，避免SQL注入，这里仅允许以 t. 或 s. 开头的列/表达式）
        safe_order_by = order_by if order_by and (order_by.strip().startswith('t.') or order_by.strip().startswith('s.')) else 't.created_at DESC'
        query += f" ORDER BY {safe_order_by}"
        if limit is not None and isinstance(limit, int) and limit > 0:
            query += f" LIMIT {limit}"
        
        trades = self.db.execute_query(query, tuple(params))
        trade_dicts: List[Dict[str, Any]] = [dict(trade) for trade in trades]

        # 统一计算指标（仅按开仓级别聚合，不保留每笔卖出盈亏）
        for t in trade_dicts:
            try:
                sums = self.db.execute_query(
                    """
                    SELECT 
                      COALESCE(SUM(CASE WHEN transaction_type='buy' THEN price*quantity END),0) AS gross_buy,
                      COALESCE(SUM(CASE WHEN transaction_type='buy' THEN transaction_fee END),0) AS buy_fees,
                      COALESCE(SUM(CASE WHEN transaction_type='sell' THEN price*quantity END),0) AS gross_sell,
                      COALESCE(SUM(CASE WHEN transaction_type='sell' THEN transaction_fee END),0) AS sell_fees,
                      COALESCE(SUM(CASE WHEN transaction_type='sell' THEN quantity END),0) AS sold_qty,
                      COALESCE(SUM(CASE WHEN transaction_type='buy' THEN quantity END),0) AS buy_qty
                    FROM trade_details WHERE trade_id = ? AND is_deleted = 0
                    """,
                    (t['id'],),
                    fetch_one=True,
                )
                gross_buy_total = Decimal(str(sums['gross_buy'])) if sums else Decimal('0')
                buy_fees_total = Decimal(str(sums['buy_fees'])) if sums else Decimal('0')
                gross_sell_total = Decimal(str(sums['gross_sell'])) if sums else Decimal('0')
                sell_fees_total = Decimal(str(sums['sell_fees'])) if sums else Decimal('0')
                sold_qty = Decimal(str(sums['sold_qty'])) if sums else Decimal('0')
                buy_qty = Decimal(str(sums['buy_qty'])) if sums else Decimal('0')

                avg_buy_price_ex_fee = (gross_buy_total / buy_qty) if buy_qty > 0 else Decimal('0')
                buy_cost_for_sold = avg_buy_price_ex_fee * sold_qty
                allocated_buy_fees_for_sold = (buy_fees_total * (sold_qty / buy_qty)) if buy_qty > 0 else Decimal('0')
                gross_profit_for_sold = gross_sell_total - buy_cost_for_sold
                net_profit = gross_profit_for_sold - sell_fees_total - allocated_buy_fees_for_sold
                denom = buy_cost_for_sold
                net_profit_pct = (net_profit / denom * 100) if denom > 0 else Decimal('0')

                # 写回统一字段
                t['total_gross_buy'] = float(gross_buy_total)
                t['total_buy_fees'] = float(buy_fees_total)
                t['total_sell_fees'] = float(sell_fees_total)
                t['total_gross_profit'] = float(gross_profit_for_sold)
                t['total_net_profit'] = float(net_profit)
                t['total_net_profit_pct'] = float(net_profit_pct)
                # 兼容旧字段：total_profit_loss 表示毛利润
                t['total_profit_loss'] = float(gross_profit_for_sold)
                t['total_profit_loss_pct'] = float((gross_profit_for_sold / denom * 100) if denom > 0 else Decimal('0'))
                # 额外派生：总买入金额（不含费用）、总卖出金额（不含费用）、总交易费用、总费用占比
                total_buy_amount_ex_fee = gross_buy_total
                total_sell_amount_ex_fee = gross_sell_total
                total_fees = buy_fees_total + sell_fees_total
                total_fee_ratio = (total_fees / gross_buy_total * 100) if gross_buy_total > 0 else Decimal('0')
                t['total_buy_amount'] = float(total_buy_amount_ex_fee)
                t['total_sell_amount'] = float(total_sell_amount_ex_fee)
                t['total_fees'] = float(total_fees)
                t['total_fee_ratio_pct'] = float(total_fee_ratio)
            except Exception:
                continue

        return trade_dicts
    
    def get_trade_by_id(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取交易"""
        query = '''
            SELECT t.*, s.name as strategy_name
            FROM trades t
            LEFT JOIN strategies s ON t.strategy_id = s.id
            WHERE t.id = ?
        '''
        
        trade = self.db.execute_query(query, (trade_id,), fetch_one=True)
        return dict(trade) if trade else None

    def get_trade_overview_metrics(self, trade_id: int) -> Dict[str, Any]:
        """返回单笔交易的统一口径汇总指标（买入/卖出/盈亏）。

        所有金额均为不含费用的成交额，费用单列；净利润=毛利−卖出费−按卖出份额分摊的买入费；
        净利率分母=已卖出部分的不含费买入成本。与 get_all_trades 的聚合口径一致。
        """
        sums = self.db.execute_query(
            """
            SELECT 
              COALESCE(SUM(CASE WHEN transaction_type='buy' THEN price*quantity END),0) AS gross_buy,
              COALESCE(SUM(CASE WHEN transaction_type='buy' THEN transaction_fee END),0) AS buy_fees,
              COALESCE(SUM(CASE WHEN transaction_type='sell' THEN price*quantity END),0) AS gross_sell,
              COALESCE(SUM(CASE WHEN transaction_type='sell' THEN transaction_fee END),0) AS sell_fees,
              COALESCE(SUM(CASE WHEN transaction_type='sell' THEN quantity END),0) AS sold_qty,
              COALESCE(SUM(CASE WHEN transaction_type='buy' THEN quantity END),0) AS buy_qty
            FROM trade_details WHERE trade_id = ? AND is_deleted = 0
            """,
            (trade_id,),
            fetch_one=True,
        )

        gross_buy_total = Decimal(str(sums['gross_buy'])) if sums else Decimal('0')
        buy_fees_total = Decimal(str(sums['buy_fees'])) if sums else Decimal('0')
        gross_sell_total = Decimal(str(sums['gross_sell'])) if sums else Decimal('0')
        sell_fees_total = Decimal(str(sums['sell_fees'])) if sums else Decimal('0')
        sold_qty = Decimal(str(sums['sold_qty'])) if sums else Decimal('0')
        buy_qty = Decimal(str(sums['buy_qty'])) if sums else Decimal('0')

        avg_buy_price_ex_fee = (gross_buy_total / buy_qty) if buy_qty > 0 else Decimal('0')
        avg_sell_price_ex_fee = (gross_sell_total / sold_qty) if sold_qty > 0 else Decimal('0')
        buy_cost_for_sold = avg_buy_price_ex_fee * sold_qty
        allocated_buy_fees_for_sold = (buy_fees_total * (sold_qty / buy_qty)) if buy_qty > 0 else Decimal('0')
        gross_profit_for_sold = gross_sell_total - buy_cost_for_sold
        net_profit = gross_profit_for_sold - sell_fees_total - allocated_buy_fees_for_sold
        denom = buy_cost_for_sold

        overview: Dict[str, Any] = {
            'buy_gross': float(gross_buy_total),
            'buy_qty': int(buy_qty),
            'buy_fees': float(buy_fees_total),
            'avg_buy_ex': float(avg_buy_price_ex_fee) if buy_qty > 0 else 0.0,
            'sell_gross': float(gross_sell_total),
            'sell_qty': int(sold_qty),
            'sell_fees': float(sell_fees_total),
            'avg_sell_ex': float(avg_sell_price_ex_fee) if sold_qty > 0 else 0.0,
            'gross_profit': float(gross_profit_for_sold),
            'gross_profit_rate': float((gross_profit_for_sold / gross_buy_total * 100) if gross_buy_total > 0 else Decimal('0')),
            'net_profit': float(net_profit),
            'net_profit_rate': float((net_profit / denom * 100) if denom > 0 else Decimal('0')),
            # 与列表统一的派生字段
            'total_buy_amount': float(gross_buy_total),
            'total_sell_amount': float(gross_sell_total),
            'total_buy_fees': float(buy_fees_total),
            'total_sell_fees': float(sell_fees_total),
            'total_profit_loss': float(gross_profit_for_sold),
            'total_profit_loss_pct': float((gross_profit_for_sold / denom * 100) if denom > 0 else Decimal('0')),
            'total_net_profit': float(net_profit),
            'total_net_profit_pct': float((net_profit / denom * 100) if denom > 0 else Decimal('0')),
            'total_fees': float(buy_fees_total + sell_fees_total),
            'total_fee_ratio_pct': float(((buy_fees_total + sell_fees_total) / gross_buy_total * 100) if gross_buy_total > 0 else Decimal('0')),
        }
        return overview
    
    def get_trade_details(self, trade_id: int, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """获取交易明细"""
        query = "SELECT * FROM trade_details WHERE trade_id = ?"
        
        if not include_deleted:
            query += " AND is_deleted = 0"
        
        query += " ORDER BY transaction_date, created_at"
        
        details = self.db.execute_query(query, (trade_id,))
        return [dict(detail) for detail in details]

    def compute_buy_detail_remaining_map(self, trade_id: int) -> Dict[int, int]:
        """基于FIFO计算每个买入明细剩余可卖份额。

        返回: {buy_detail_id: remaining_quantity}
        """
        # 读取该交易所有明细，按日期+创建顺序
        query = "SELECT * FROM trade_details WHERE trade_id = ? AND is_deleted = 0 ORDER BY transaction_date, created_at, id"
        rows = self.db.execute_query(query, (trade_id,))
        details = [dict(r) for r in rows]

        # 仅买入明细列表（FIFO队列）
        buy_queue: List[Dict[str, Any]] = []
        for d in details:
            if d['transaction_type'] == 'buy':
                buy_queue.append({'id': d['id'], 'remaining': int(d['quantity'])})

        # 消耗卖出数量（FIFO）
        for d in details:
            if d['transaction_type'] == 'sell':
                sell_qty = int(d['quantity'])
                i = 0
                while sell_qty > 0 and i < len(buy_queue):
                    take = min(buy_queue[i]['remaining'], sell_qty)
                    buy_queue[i]['remaining'] -= take
                    sell_qty -= take
                    if buy_queue[i]['remaining'] == 0:
                        i += 1
                    else:
                        i += 1  # move forward to avoid infinite loop in unexpected data

        # 生成映射
        remaining_map: Dict[int, int] = {}
        for b in buy_queue:
            remaining_map[b['id']] = max(0, int(b['remaining']))
        return remaining_map
    
    def soft_delete_trade(self, trade_id: int, confirmation_code: str, 
                         delete_reason: str, operator_note: str = '') -> bool:
        """软删除交易"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 软删除交易主记录
                cursor.execute('''
                    UPDATE trades SET 
                        is_deleted = 1, delete_date = CURRENT_TIMESTAMP,
                        delete_reason = ?, operator_note = ?
                    WHERE id = ?
                ''', (delete_reason, operator_note, trade_id))
                
                # 软删除相关交易明细
                cursor.execute('''
                    UPDATE trade_details SET 
                        is_deleted = 1, delete_date = CURRENT_TIMESTAMP,
                        delete_reason = ?, operator_note = ?
                    WHERE trade_id = ?
                ''', (delete_reason, operator_note, trade_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"软删除交易失败: {str(e)}")
            return False
    
    def restore_trade(self, trade_id: int, confirmation_code: str, operator_note: str = '') -> bool:
        """恢复已删除的交易"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 恢复交易主记录
                cursor.execute('''
                    UPDATE trades SET 
                        is_deleted = 0, delete_date = NULL,
                        delete_reason = '', operator_note = ?
                    WHERE id = ?
                ''', (operator_note, trade_id))
                
                # 恢复相关交易明细
                cursor.execute('''
                    UPDATE trade_details SET 
                        is_deleted = 0, delete_date = NULL,
                        delete_reason = '', operator_note = ?
                    WHERE trade_id = ?
                ''', (operator_note, trade_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"恢复交易失败: {str(e)}")
            return False
    
    def permanently_delete_trade(self, trade_id: int, confirmation_code: str,
                               confirmation_text: str, delete_reason: str, operator_note: str = '') -> bool:
        """永久删除交易"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 删除交易明细
                cursor.execute("DELETE FROM trade_details WHERE trade_id = ?", (trade_id,))
                
                # 删除修改历史
                cursor.execute("DELETE FROM trade_modifications WHERE trade_id = ?", (trade_id,))
                
                # 删除交易主记录
                cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"永久删除交易失败: {str(e)}")
            return False
    
    def get_deleted_trades(self) -> List[Dict[str, Any]]:
        """获取已删除的交易"""
        query = '''
            SELECT t.*, s.name as strategy_name
            FROM trades t
            LEFT JOIN strategies s ON t.strategy_id = s.id
            WHERE t.is_deleted = 1
            ORDER BY t.delete_date DESC
        '''
        
        trades = self.db.execute_query(query)
        return [dict(trade) for trade in trades]
    
    def record_modification(self, trade_id: int, detail_id: Optional[int], 
                          modification_type: str, field_name: str, 
                          old_value: str, new_value: str, reason: str = '') -> bool:
        """记录修改历史"""
        try:
            self.db.execute_query('''
                INSERT INTO trade_modifications (
                    trade_id, detail_id, modification_type, field_name,
                    old_value, new_value, modification_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (trade_id, detail_id, modification_type, field_name, 
                  old_value, new_value, reason), fetch_all=False)
            return True
            
        except Exception as e:
            print(f"记录修改历史失败: {str(e)}")
            return False
    
    def get_trade_modifications(self, trade_id: int) -> List[Dict[str, Any]]:
        """获取交易修改历史"""
        query = '''
            SELECT * FROM trade_modifications 
            WHERE trade_id = ? 
            ORDER BY created_at DESC
        '''
        
        modifications = self.db.execute_query(query, (trade_id,))
        return [dict(mod) for mod in modifications]

    def update_trade_record(self, trade_id: int, detail_updates: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """根据提供的明细更新列表，更新交易明细并重算汇总与盈亏。

        detail_updates: 每项包含字段：
          - detail_id: 明细ID（必填）
          - price, quantity, transaction_fee, buy_reason, sell_reason: 任意可选更新字段
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # 校验交易存在
                cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
                trade_row = cursor.fetchone()
                if not trade_row:
                    return False, f"交易ID {trade_id} 不存在"

                # 逐条更新明细
                for upd in detail_updates:
                    detail_id = upd.get('detail_id')
                    if not detail_id:
                        return False, "detail_id 缺失"

                    cursor.execute("SELECT * FROM trade_details WHERE id = ? AND trade_id = ?", (detail_id, trade_id))
                    detail = cursor.fetchone()
                    if not detail:
                        return False, f"明细ID {detail_id} 不存在于交易 {trade_id}"

                    # 计算新的字段值（若未给出则使用原值）
                    price = Decimal(str(upd.get('price', detail['price'])))
                    quantity = int(upd.get('quantity', detail['quantity']))
                    transaction_fee = Decimal(str(upd.get('transaction_fee', detail['transaction_fee'])))
                    buy_reason = upd.get('buy_reason', detail['buy_reason'])
                    sell_reason = upd.get('sell_reason', detail['sell_reason'])

                    if price <= 0 or quantity <= 0:
                        return False, "价格和数量必须大于0"

                    # 重新计算 amount 与（若为卖出）临时 profit_loss，最终会统一重算
                    if detail['transaction_type'] == 'buy':
                        amount = price * quantity + transaction_fee
                        cursor.execute(
                            '''UPDATE trade_details SET price = ?, quantity = ?, amount = ?, transaction_date = transaction_date,
                               transaction_fee = ?, buy_reason = ? WHERE id = ?''',
                            (float(price), quantity, float(amount), float(transaction_fee), buy_reason, detail_id)
                        )
                    else:
                        amount = price * quantity - transaction_fee
                        cursor.execute(
                            '''UPDATE trade_details SET price = ?, quantity = ?, amount = ?, transaction_date = transaction_date,
                               transaction_fee = ?, sell_reason = ? WHERE id = ?''',
                            (float(price), quantity, float(amount), float(transaction_fee), sell_reason, detail_id)
                        )

                # 读取该交易的全部明细以便重算
                cursor.execute("SELECT * FROM trade_details WHERE trade_id = ? AND is_deleted = 0 ORDER BY transaction_date, created_at, id", (trade_id,))
                all_details = cursor.fetchall()

                # 汇总买入与卖出
                total_buy_amount = Decimal('0')  # 买入总额（含手续费）
                total_buy_quantity = 0
                total_sell_amount = Decimal('0')  # 卖出净收入（扣除手续费）
                total_sell_quantity = 0

                for d in all_details:
                    if d['transaction_type'] == 'buy':
                        total_buy_amount += Decimal(str(d['amount']))
                        total_buy_quantity += int(d['quantity'])
                    else:
                        total_sell_amount += Decimal(str(d['amount']))
                        total_sell_quantity += int(d['quantity'])

                remaining_quantity = total_buy_quantity - total_sell_quantity

                # 以加权平均成本法重算每笔卖出明细盈亏（不计入任何费用）
                # 使用不含费用的买入均价：sum(price*qty)/sum(qty)
                # 使用当前事务内的明细数据计算不含费用的买入总额与数量
                gross_buy_total = Decimal('0')
                gross_buy_qty = Decimal('0')
                for d in all_details:
                    if d['transaction_type'] == 'buy':
                        gross_buy_total += Decimal(str(d['price'])) * Decimal(str(d['quantity']))
                        gross_buy_qty += Decimal(str(d['quantity']))
                avg_buy_price_ex_fee = (gross_buy_total / gross_buy_qty) if gross_buy_qty > 0 else Decimal('0')
                total_profit_loss = Decimal('0')
                for d in all_details:
                    if d['transaction_type'] == 'sell':
                        # 毛卖出额（不含费用）
                        gross_sell_amount = Decimal(str(d['price'])) * Decimal(str(d['quantity']))
                        buy_cost = avg_buy_price_ex_fee * Decimal(str(d['quantity']))
                        gross_profit = gross_sell_amount - buy_cost
                        net_profit = (gross_sell_amount - Decimal(str(d['transaction_fee']))) - buy_cost
                        profit_loss = gross_profit  # 兼容旧字段：total_profit_loss 代表毛利
                        profit_loss_pct = (gross_profit / buy_cost * 100) if buy_cost > 0 else Decimal('0')
                        gross_profit_pct = profit_loss_pct
                        net_profit_pct = (net_profit / buy_cost * 100) if buy_cost > 0 else Decimal('0')
                        total_profit_loss += gross_profit
                        cursor.execute(
                            '''UPDATE trade_details SET profit_loss = ?, profit_loss_pct = ?,
                               gross_profit = ?, gross_profit_pct = ?, net_profit = ?, net_profit_pct = ?
                               WHERE id = ?''',
                            (float(profit_loss), float(profit_loss_pct),
                             float(gross_profit), float(gross_profit_pct), float(net_profit), float(net_profit_pct), d['id'])
                        )

                # 汇总毛利/净利
                cursor.execute("""
                    SELECT COALESCE(SUM(CASE WHEN transaction_type='sell' THEN price*quantity END),0) AS gross_sell,
                           COALESCE(SUM(CASE WHEN transaction_type='sell' THEN transaction_fee END),0) AS sell_fees
                    FROM trade_details WHERE trade_id = ? AND is_deleted = 0
                """, (trade_id,))
                sums = cursor.fetchone()
                gross_sell_total = Decimal(str(sums['gross_sell'])) if sums else Decimal('0')
                sell_fees_total = Decimal(str(sums['sell_fees'])) if sums else Decimal('0')
                total_gross_profit = total_profit_loss  # 兼容：旧字段等于毛利
                total_net_profit = total_gross_profit - sell_fees_total
                total_profit_loss_pct = (total_gross_profit / gross_buy_total * 100) if gross_buy_total > 0 else Decimal('0')
                total_net_profit_pct = (total_net_profit / gross_buy_total * 100) if gross_buy_total > 0 else Decimal('0')

                # 关闭状态与日期/持仓天数
                status = 'closed' if remaining_quantity == 0 and total_sell_quantity > 0 else 'open'
                close_date = None
                holding_days = trade_row['holding_days']
                if status == 'closed':
                    # 取最后一笔卖出的日期作为 close_date
                    cursor.execute("SELECT MAX(transaction_date) AS cd FROM trade_details WHERE trade_id = ? AND transaction_type = 'sell' AND is_deleted = 0", (trade_id,))
                    row = cursor.fetchone()
                    close_date = row['cd'] if row and row['cd'] else None
                    if close_date:
                        open_date = datetime.strptime(trade_row['open_date'], '%Y-%m-%d').date()
                        close_date_obj = datetime.strptime(close_date, '%Y-%m-%d').date()
                        holding_days = (close_date_obj - open_date).days

                # 更新主交易表
                cursor.execute(
                    '''UPDATE trades SET total_buy_amount = ?, total_buy_quantity = ?,
                       total_sell_amount = ?, total_sell_quantity = ?, remaining_quantity = ?,
                       total_profit_loss = ?, total_profit_loss_pct = ?,
                       total_gross_profit = ?, total_net_profit = ?, total_net_profit_pct = ?,
                       status = ?, close_date = ?, holding_days = ?,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?''',
                    (
                        float(total_buy_amount), total_buy_quantity,
                        float(total_sell_amount), total_sell_quantity, remaining_quantity,
                        float(total_gross_profit), float(total_profit_loss_pct),
                        float(total_gross_profit), float(total_net_profit), float(total_net_profit_pct),
                        status, close_date, holding_days, trade_id
                    )
                )

                conn.commit()
                return True, "交易明细更新成功"

        except Exception as e:
            return False, f"更新交易记录失败: {str(e)}"
    
    def _resolve_strategy(self, strategy) -> Optional[int]:
        """解析策略参数，返回策略ID"""
        if isinstance(strategy, int):
            # 验证策略ID是否存在且活跃
            strategy_obj = self.strategy_service.get_strategy_by_id(strategy)
            return strategy if strategy_obj and strategy_obj['is_active'] else None
        elif isinstance(strategy, str):
            # 根据策略名称查找
            strategies = self.strategy_service.get_all_strategies()
            for s in strategies:
                if s['name'] == strategy:
                    return s['id']
            return None
        else:
            return None
    
    def _update_existing_trade_for_buy(self, cursor, trade_id: int, price: Decimal, 
                                     quantity: int, transaction_date: str, 
                                     transaction_fee: Decimal, amount: Decimal):
        """更新现有交易的买入信息"""
        # 获取当前交易信息
        cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        trade = cursor.fetchone()
        
        new_buy_amount = trade['total_buy_amount'] + float(amount)
        new_buy_quantity = trade['total_buy_quantity'] + quantity
        new_remaining = trade['remaining_quantity'] + quantity
        
        cursor.execute('''
            UPDATE trades SET
                total_buy_amount = ?, total_buy_quantity = ?, remaining_quantity = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_buy_amount, new_buy_quantity, new_remaining, trade_id))
    
    def _create_new_trade(self, cursor, strategy_id: int, symbol_code: str, 
                        symbol_name: str, transaction_date: str) -> int:
        """创建新的交易记录"""
        cursor.execute('''
            INSERT INTO trades (
                strategy_id, symbol_code, symbol_name, open_date, status,
                total_buy_amount, total_buy_quantity, remaining_quantity,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'open', 0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (strategy_id, symbol_code, symbol_name, transaction_date))
        
        return cursor.lastrowid
