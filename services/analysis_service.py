#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析服务层
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from .database_service import DatabaseService
from .strategy_service import StrategyService


class AnalysisService:
    """分析服务"""
    
    def __init__(self, db_service: Optional[DatabaseService] = None):
        self.db = db_service or DatabaseService()
        self.strategy_service = StrategyService(self.db)
    
    def calculate_strategy_score(self, strategy_id: Optional[int] = None, strategy: Optional[str] = None,
                               symbol_code: Optional[str] = None, start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> Dict[str, Any]:
        """计算策略评分"""
        query = '''
            SELECT t.*, s.name as strategy_name
            FROM trades t
            LEFT JOIN strategies s ON t.strategy_id = s.id
            WHERE t.is_deleted = 0
        '''
        
        params = []
        
        # 策略筛选
        if strategy_id:
            query += " AND t.strategy_id = ?"
            params.append(strategy_id)
        elif strategy:
            strategy_obj = self._get_strategy_by_name(strategy)
            if strategy_obj:
                query += " AND t.strategy_id = ?"
                params.append(strategy_obj['id'])
        
        # 股票筛选
        if symbol_code:
            query += " AND t.symbol_code = ?"
            params.append(symbol_code)
        
        # 时间筛选
        if start_date:
            query += " AND t.open_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND t.open_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY t.open_date"
        
        trades = self.db.execute_query(query, tuple(params))
        
        return self._calculate_performance_metrics(trades)
    
    def get_strategy_scores(self) -> List[Dict[str, Any]]:
        """获取所有策略的评分"""
        strategies = self.strategy_service.get_all_strategies()
        scores = []
        
        for strategy in strategies:
            score = self.calculate_strategy_score(strategy_id=strategy['id'])
            score['strategy_id'] = strategy['id']
            score['strategy_name'] = strategy['name']
            scores.append(score)
        
        # 按总收益率排序
        scores.sort(key=lambda x: x['stats']['total_return_rate'], reverse=True)
        return scores
    
    def get_symbol_scores_by_strategy(self, strategy_id: Optional[int] = None, 
                                    strategy: Optional[str] = None) -> List[Dict[str, Any]]:
        """按策略获取股票评分"""
        # 获取该策略下的所有股票
        query = '''
            SELECT DISTINCT symbol_code, symbol_name
            FROM trades
            WHERE is_deleted = 0
        '''
        
        params = []
        
        if strategy_id:
            query += " AND strategy_id = ?"
            params.append(strategy_id)
        elif strategy:
            strategy_obj = self._get_strategy_by_name(strategy)
            if strategy_obj:
                query += " AND strategy_id = ?"
                params.append(strategy_obj['id'])
        
        query += " ORDER BY symbol_code"
        
        symbols = self.db.execute_query(query, tuple(params))
        
        scores = []
        for symbol in symbols:
            score = self.calculate_strategy_score(
                strategy_id=strategy_id,
                strategy=strategy,
                symbol_code=symbol['symbol_code']
            )
            score['symbol_code'] = symbol['symbol_code']
            score['symbol_name'] = symbol['symbol_name']
            scores.append(score)
        
        # 按总收益率排序
        scores.sort(key=lambda x: x['stats']['total_return_rate'], reverse=True)
        return scores
    
    def get_all_symbols(self) -> List[Dict[str, Any]]:
        """获取所有股票代码"""
        query = '''
            SELECT symbol_code, symbol_name, COUNT(*) as trade_count
            FROM trades
            WHERE is_deleted = 0
            GROUP BY symbol_code, symbol_name
            ORDER BY symbol_code
        '''
        
        symbols = self.db.execute_query(query)
        return [dict(symbol) for symbol in symbols]
    
    def get_strategies_scores_by_symbol(self, symbol_code: str) -> List[Dict[str, Any]]:
        """按股票获取策略评分"""
        strategies = self.strategy_service.get_all_strategies()
        scores = []
        
        for strategy in strategies:
            score = self.calculate_strategy_score(
                strategy_id=strategy['id'],
                symbol_code=symbol_code
            )
            
            # 只有该策略有该股票的交易时才添加
            if score['stats']['total_trades'] > 0:
                score['strategy_id'] = strategy['id']
                score['strategy_name'] = strategy['name']
                scores.append(score)
        
        # 按总收益率排序
        scores.sort(key=lambda x: x['stats']['total_return_rate'], reverse=True)
        return scores
    
    def get_time_periods(self, period_type: str = 'year') -> List[str]:
        """获取时间周期列表"""
        if period_type == 'year':
            query = '''
                SELECT DISTINCT strftime('%Y', open_date) as period
                FROM trades
                WHERE is_deleted = 0
                ORDER BY period DESC
            '''
        elif period_type == 'quarter':
            query = '''
                SELECT DISTINCT 
                    strftime('%Y', open_date) || '-Q' || 
                    CASE 
                        WHEN CAST(strftime('%m', open_date) AS INTEGER) <= 3 THEN '1'
                        WHEN CAST(strftime('%m', open_date) AS INTEGER) <= 6 THEN '2'
                        WHEN CAST(strftime('%m', open_date) AS INTEGER) <= 9 THEN '3'
                        ELSE '4'
                    END as period
                FROM trades
                WHERE is_deleted = 0
                ORDER BY period DESC
            '''
        elif period_type == 'month':
            query = '''
                SELECT DISTINCT strftime('%Y-%m', open_date) as period
                FROM trades
                WHERE is_deleted = 0
                ORDER BY period DESC
            '''
        else:
            return []
        
        periods = self.db.execute_query(query)
        return [period['period'] for period in periods]
    
    def get_strategies_scores_by_time_period(self, period: str, period_type: str = 'year') -> List[Dict[str, Any]]:
        """按时间周期获取策略评分"""
        start_date, end_date = self._get_period_date_range(period, period_type)
        
        strategies = self.strategy_service.get_all_strategies()
        scores = []
        
        for strategy in strategies:
            score = self.calculate_strategy_score(
                strategy_id=strategy['id'],
                start_date=start_date,
                end_date=end_date
            )
            
            # 只有该策略在该时期有交易时才添加
            if score['stats']['total_trades'] > 0:
                score['strategy_id'] = strategy['id']
                score['strategy_name'] = strategy['name']
                scores.append(score)
        
        # 按总收益率排序
        scores.sort(key=lambda x: x['stats']['total_return_rate'], reverse=True)
        return scores
    
    def get_period_summary(self, period: str, period_type: str = 'year') -> Dict[str, Any]:
        """获取时间周期汇总"""
        start_date, end_date = self._get_period_date_range(period, period_type)
        
        return self.calculate_strategy_score(
            start_date=start_date,
            end_date=end_date
        )
    
    def _calculate_performance_metrics(self, trades) -> Dict[str, Any]:
        """计算性能指标"""
        if not trades:
            return {
                'stats': {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_investment': 0,
                    'total_return': 0,
                    'total_return_rate': 0,
                    'avg_return_per_trade': 0,
                    'avg_holding_days': 0,
                    'total_fees': 0
                },
                'details': []
            }
        
        # 统计变量
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        total_investment = Decimal('0')
        total_return = Decimal('0')
        total_holding_days = 0
        total_fees = Decimal('0')
        
        details = []
        
        for trade in trades:
            trade_dict = dict(trade)
            
            # 计算交易手续费
            fees_query = '''
                SELECT COALESCE(SUM(transaction_fee), 0) as total_fees
                FROM trade_details
                WHERE trade_id = ? AND is_deleted = 0
            '''
            fees_result = self.db.execute_query(fees_query, (trade['id'],), fetch_one=True)
            trade_fees = fees_result['total_fees'] if fees_result else 0
            total_fees += Decimal(str(trade_fees))
            
            # 只统计已平仓的交易
            if trade['status'] == 'closed':
                total_trades += 1
                total_investment += Decimal(str(trade['total_buy_amount']))
                total_return += Decimal(str(trade['total_profit_loss']))
                total_holding_days += trade['holding_days']
                
                if trade['total_profit_loss'] > 0:
                    winning_trades += 1
                elif trade['total_profit_loss'] < 0:
                    losing_trades += 1
            
            details.append(trade_dict)
        
        # 计算比率
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        total_return_rate = (total_return / total_investment * 100) if total_investment > 0 else 0
        avg_return_per_trade = total_return / total_trades if total_trades > 0 else 0
        avg_holding_days = total_holding_days / total_trades if total_trades > 0 else 0
        
        return {
            'stats': {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': float(win_rate),
                'total_investment': float(total_investment),
                'total_return': float(total_return),
                'total_return_rate': float(total_return_rate),
                'avg_return_per_trade': float(avg_return_per_trade),
                'avg_holding_days': float(avg_holding_days),
                'total_fees': float(total_fees)
            },
            'details': details
        }
    
    def _get_strategy_by_name(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取策略"""
        strategies = self.strategy_service.get_all_strategies()
        for strategy in strategies:
            if strategy['name'] == strategy_name:
                return strategy
        return None
    
    def _get_period_date_range(self, period: str, period_type: str = 'year') -> tuple:
        """获取时间周期的日期范围"""
        if period_type == 'year':
            start_date = f"{period}-01-01"
            end_date = f"{period}-12-31"
        elif period_type == 'quarter':
            # 格式: 2024-Q1
            year, quarter = period.split('-Q')
            quarter = int(quarter)
            
            if quarter == 1:
                start_date = f"{year}-01-01"
                end_date = f"{year}-03-31"
            elif quarter == 2:
                start_date = f"{year}-04-01"
                end_date = f"{year}-06-30"
            elif quarter == 3:
                start_date = f"{year}-07-01"
                end_date = f"{year}-09-30"
            else:  # quarter == 4
                start_date = f"{year}-10-01"
                end_date = f"{year}-12-31"
        elif period_type == 'month':
            # 格式: 2024-01
            year, month = period.split('-')
            start_date = f"{year}-{month}-01"
            
            # 计算月末日期
            if month in ['01', '03', '05', '07', '08', '10', '12']:
                end_date = f"{year}-{month}-31"
            elif month in ['04', '06', '09', '11']:
                end_date = f"{year}-{month}-30"
            else:  # 2月
                # 简单处理，不考虑闰年
                end_date = f"{year}-{month}-28"
        else:
            start_date = '1900-01-01'
            end_date = '2099-12-31'
        
        return start_date, end_date
