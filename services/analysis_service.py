#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析服务层
"""

from typing import List, Dict, Any, Optional, cast, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal

from .database_service import DatabaseService
from .strategy_service import StrategyService
from utils.helpers import get_period_date_range
from .mappers import dict_to_trade_dto, TradeDTO, ScoreDTO, to_dict_dataclass


class AnalysisService:
    """分析服务"""

    def __init__(self, db_service: Optional[DatabaseService] = None):
        self.db = db_service or DatabaseService()
        self.strategy_service = StrategyService(self.db)

    def calculate_strategy_score(self, strategy_id: Optional[int] = None, strategy: Optional[str] = None,
                               symbol_code: Optional[str] = None, start_date: Optional[str] = None,
                               end_date: Optional[str] = None, return_dto: bool = False) -> Dict[str, Any] | ScoreDTO:
        """计算策略评分"""
        query = '''
            SELECT t.*, s.name as strategy_name
            FROM trades t
            LEFT JOIN strategies s ON t.strategy_id = s.id
            WHERE t.is_deleted = 0
        '''

        params: List[Any] = []

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
        result = self._calculate_performance_metrics(trades)

        # 附加高级风险/收益指标（使用专业库计算）
        try:
            trade_ids = [int(t['id']) for t in trades]
            ann_vol, ann_ret, mdd, sharpe, calmar = self._compute_advanced_metrics(trade_ids, start_date, end_date)
            result['stats']['annual_volatility'] = float(ann_vol)
            result['stats']['annual_return'] = float(ann_ret)
            result['stats']['max_drawdown'] = float(mdd)
            result['stats']['sharpe_ratio'] = float(sharpe)
            result['stats']['calmar_ratio'] = float(calmar)
        except Exception:
            # 出错时保持兼容（不阻塞主流程）
            result['stats'].setdefault('annual_volatility', 0.0)
            result['stats'].setdefault('annual_return', 0.0)
            result['stats'].setdefault('max_drawdown', 0.0)
            result['stats'].setdefault('sharpe_ratio', 0.0)
            result['stats'].setdefault('calmar_ratio', 0.0)
        if return_dto:
            return ScoreDTO(
                strategy_id=strategy_id,
                strategy_name=strategy if strategy and not strategy_id else None,
                stats=result['stats']
            )
        return result

    def attach_legacy_score_fields(self, score: Dict[str, Any]) -> Dict[str, Any]:
        """为评分结果附加旧字段（向后兼容）。

        规则与路由层保持一致，但集中在服务层，避免重复（DRY）。
        """
        if not score or 'stats' not in score:
            return score
        stats = score['stats']
        score['win_rate_score'] = min(stats.get('win_rate', 0) / 10, 10)
        plr = stats.get('avg_profit_loss_ratio', 0) or 0
        if plr == 0:
            score['profit_loss_ratio_score'] = 0
        elif plr == 9999.0:
            score['profit_loss_ratio_score'] = 10
        else:
            score['profit_loss_ratio_score'] = min(plr, 10)
        if stats.get('total_trades', 0) == 0:
            score['frequency_score'] = 0
        elif stats.get('avg_holding_days', 0) <= 1:
            score['frequency_score'] = 8
        elif stats.get('avg_holding_days', 0) <= 7:
            score['frequency_score'] = 7
        elif stats.get('avg_holding_days', 0) <= 30:
            score['frequency_score'] = 6
        else:
            score['frequency_score'] = max(0, 6 - (stats.get('avg_holding_days', 0) - 30) / 30)
        score['total_score'] = score['win_rate_score'] + score['profit_loss_ratio_score'] + score['frequency_score']
        return score

    def _compute_legacy_fields(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """基于统计数据计算旧版评分字段与评级，供 DTO 填充使用。"""
        if not stats:
            return {'win_rate_score': 0.0, 'profit_loss_ratio_score': 0.0, 'frequency_score': 0.0, 'total_score': 0.0, 'rating': 'D'}
        win_rate_score = min((stats.get('win_rate', 0) or 0) / 10, 10)
        plr = stats.get('avg_profit_loss_ratio', 0) or 0
        if plr == 0:
            profit_loss_ratio_score = 0.0
        elif plr == 9999.0:
            profit_loss_ratio_score = 10.0
        else:
            profit_loss_ratio_score = float(min(plr, 10))
        # 频率分数
        total_trades = stats.get('total_trades', 0) or 0
        avg_days = stats.get('avg_holding_days', 0) or 0
        if total_trades == 0:
            frequency_score = 0.0
        elif avg_days <= 1:
            frequency_score = 8.0
        elif avg_days <= 7:
            frequency_score = 7.0
        elif avg_days <= 30:
            frequency_score = 6.0
        else:
            frequency_score = max(0.0, 6.0 - (avg_days - 30) / 30)
        total_score = float(win_rate_score) + float(profit_loss_ratio_score) + float(frequency_score)
        if total_score >= 26:
            rating = 'A+'
        elif total_score >= 23:
            rating = 'A'
        elif total_score >= 20:
            rating = 'B'
        elif total_score >= 18:
            rating = 'C'
        else:
            rating = 'D'
        return {
            'win_rate_score': float(win_rate_score),
            'profit_loss_ratio_score': float(profit_loss_ratio_score),
            'frequency_score': float(frequency_score),
            'total_score': float(total_score),
            'rating': rating,
        }

    # 中期优化：提供公开的评分计算工具，供路由与 API 统一使用
    def compute_score_fields(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """基于统计数据计算评分三项与总分及评级。

        输出字段：win_rate_score, profit_loss_ratio_score, frequency_score, total_score, rating
        """
        return self._compute_legacy_fields(stats or {})

    def attach_score_fields(self, score: Dict[str, Any]) -> Dict[str, Any]:
        """在评分字典上附加统一评分字段并返回（原地更新）。"""
        if not score or 'stats' not in score:
            return score
        score.update(self.compute_score_fields(score['stats']))
        return score

    def get_strategy_scores(self, return_dto: bool = False) -> List[Dict[str, Any]] | List[ScoreDTO]:
        """获取所有策略的评分"""
        strategies = self.strategy_service.get_all_strategies()
        scores: List[Dict[str, Any]] = []

        for strategy in strategies:
            score = self.calculate_strategy_score(strategy_id=strategy['id'])
            if isinstance(score, dict):
                score['strategy_id'] = strategy['id']
                score['strategy_name'] = strategy['name']
                scores.append(score)

        # 按总收益率排序
        scores.sort(key=lambda x: x['stats']['total_return_rate'], reverse=True)
        if return_dto:
            return [ScoreDTO(strategy_id=s['strategy_id'], strategy_name=s['strategy_name'], stats=s['stats']) for s in scores]
        return scores

    def get_symbol_scores_by_strategy(self, strategy_id: Optional[int] = None,
                                    strategy: Optional[str] = None, return_dto: bool = False) -> List[Dict[str, Any]] | List[ScoreDTO]:
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

        scores: List[Dict[str, Any]] = []
        for symbol in symbols:
            score = self.calculate_strategy_score(
                strategy_id=strategy_id,
                strategy=strategy,
                symbol_code=symbol['symbol_code']
            )
            if isinstance(score, dict):
                score['symbol_code'] = symbol['symbol_code']
                score['symbol_name'] = symbol['symbol_name']
                scores.append(score)

        # 按总收益率排序
        scores.sort(key=lambda x: x['stats']['total_return_rate'], reverse=True)
        if return_dto:
            sid = strategy_id or (self._get_strategy_by_name(strategy) or {}).get('id')
            return [ScoreDTO(strategy_id=sid,
                             strategy_name=strategy,
                             stats=s['stats'],
                             symbol_code=s.get('symbol_code'),
                             symbol_name=s.get('symbol_name')) for s in scores]
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

    def get_strategies_scores_by_symbol(self, symbol_code: str, return_dto: bool = False) -> List[Dict[str, Any]] | List[ScoreDTO]:
        """按股票获取策略评分"""
        strategies = self.strategy_service.get_all_strategies()
        scores: List[Dict[str, Any]] = []

        for strategy in strategies:
            score = self.calculate_strategy_score(
                strategy_id=strategy['id'],
                symbol_code=symbol_code
            )

            # 只有该策略有该股票的交易时才添加
            from typing import cast as _cast
            score_d = _cast(Dict[str, Any], score)
            if score_d['stats']['total_trades'] > 0:
                score_d['strategy_id'] = strategy['id']
                score_d['strategy_name'] = strategy['name']
                scores.append(score_d)

        # 按总收益率排序
        scores.sort(key=lambda x: x['stats']['total_return_rate'], reverse=True)
        if return_dto:
            return [ScoreDTO(strategy_id=s['strategy_id'], strategy_name=s['strategy_name'], stats=s['stats']) for s in scores]
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

    def get_strategies_scores_by_time_period(self, period: str, period_type: str = 'year', return_dto: bool = False) -> List[Dict[str, Any]] | List[ScoreDTO]:
        """按时间周期获取策略评分"""
        start_date, end_date = self._get_period_date_range(period, period_type)

        strategies = self.strategy_service.get_all_strategies()
        scores: List[Dict[str, Any]] = []

        for strategy in strategies:
            score = self.calculate_strategy_score(
                strategy_id=strategy['id'],
                start_date=start_date,
                end_date=end_date
            )

            # 只有该策略在该时期有交易时才添加
            if isinstance(score, dict) and score['stats']['total_trades'] > 0:
                score['strategy_id'] = strategy['id']
                score['strategy_name'] = strategy['name']
                scores.append(score)

        # 按总收益率排序
        scores.sort(key=lambda x: x['stats']['total_return_rate'], reverse=True)
        if return_dto:
            return [ScoreDTO(strategy_id=s['strategy_id'], strategy_name=s['strategy_name'], stats=s['stats']) for s in scores]
        return scores

    def get_period_summary(self, period: str, period_type: str = 'year', return_dto: bool = False) -> Dict[str, Any] | ScoreDTO:
        """获取时间周期汇总"""
        start_date, end_date = self._get_period_date_range(period, period_type)

        result = self.calculate_strategy_score(
            start_date=start_date,
            end_date=end_date
        )
        if return_dto:
            from typing import cast as _cast
            res_d = _cast(Dict[str, Any], result)
            return ScoreDTO(strategy_id=None, strategy_name=None, stats=res_d['stats'])
        return result

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
                    'total_fees': 0,
                    'avg_profit_loss_ratio': 0.0
                },
                'details': []
            }

        # 统计变量（新增毛利/净利统计）
        total_trades = 0  # 仅统计已平仓交易数
        winning_trades = 0
        losing_trades = 0
        total_investment = Decimal('0')
        total_return = Decimal('0')  # 兼容：代表总毛利
        total_net_return = Decimal('0')
        total_holding_days = 0
        total_fees = Decimal('0')
        sum_profit = Decimal('0')
        sum_loss_abs = Decimal('0')
        # 累计成交额（不含费），用于换手率计算
        total_buy_gross_amount = Decimal('0')
        total_sell_gross_amount = Decimal('0')

        details = []

        for trade in trades:
            trade_dict = dict(trade)

            # 只统计已平仓的交易（同时仅对已平仓交易进行聚合查询，避免大量无效查询）
            if trade_dict['status'] == 'closed':
                # 计算交易手续费（仅针对已平仓交易）
                fees_query = '''
                    SELECT COALESCE(SUM(transaction_fee), 0) as total_fees
                    FROM trade_details
                    WHERE trade_id = ? AND is_deleted = 0
                '''
                fees_result = self.db.execute_query(fees_query, (trade_dict['id'],), fetch_one=True)
                trade_fees = fees_result['total_fees'] if fees_result else 0
                total_fees += Decimal(str(trade_fees))

                total_trades += 1
                total_investment += Decimal(str(trade_dict['total_buy_amount']))
                # 计算该交易的毛利/净利（基于明细，避免依赖主表聚合列）
                buys = self.db.execute_query(
                    '''SELECT COALESCE(SUM(price*quantity),0) AS buy_gross, COALESCE(SUM(quantity),0) AS buy_qty
                       FROM trade_details WHERE trade_id=? AND transaction_type='buy' AND is_deleted=0''',
                    (trade_dict['id'],), fetch_one=True
                )
                sells = self.db.execute_query(
                    '''SELECT COALESCE(SUM(price*quantity),0) AS sell_gross, COALESCE(SUM(quantity),0) AS sell_qty,
                              COALESCE(SUM(transaction_fee),0) AS sell_fees
                       FROM trade_details WHERE trade_id=? AND transaction_type='sell' AND is_deleted=0''',
                    (trade_dict['id'],), fetch_one=True
                )
                def _get_dec(row, key):
                    try:
                        return Decimal(str(row[key]))
                    except Exception:
                        return Decimal('0')
                buy_gross = _get_dec(buys, 'buy_gross') if buys else Decimal('0')
                buy_qty = _get_dec(buys, 'buy_qty') if buys else Decimal('0')
                sell_gross = _get_dec(sells, 'sell_gross') if sells else Decimal('0')
                sell_qty = _get_dec(sells, 'sell_qty') if sells else Decimal('0')
                sell_fees = _get_dec(sells, 'sell_fees') if sells else Decimal('0')
                # 累加买卖成交额（不含费）
                total_buy_gross_amount += buy_gross
                total_sell_gross_amount += sell_gross
                avg_buy_ex = (buy_gross / buy_qty) if buy_qty > 0 else Decimal('0')
                trade_gross_profit = sell_gross - avg_buy_ex * sell_qty
                trade_net_profit = trade_gross_profit - sell_fees
                # 兼容：当无法从明细获得有效数据（如单元测试使用Mock DB），回退使用主表字段 total_profit_loss
                if (buy_qty == 0 and sell_qty == 0) and 'total_profit_loss' in trade_dict:
                    try:
                        trade_gross_profit = Decimal(str(trade_dict['total_profit_loss']))
                        trade_net_profit = trade_gross_profit  # 无法区分费用时回退为相同
                    except Exception:
                        pass

                total_return += trade_gross_profit
                total_net_return += trade_net_profit
                total_holding_days += trade_dict['holding_days']

                if trade_gross_profit > 0:
                    winning_trades += 1
                    sum_profit += trade_gross_profit
                elif trade_gross_profit < 0:
                    losing_trades += 1
                    sum_loss_abs += abs(trade_gross_profit)

            details.append(trade_dict)

        # 计算比率（显式转换为 float 以满足类型检查）
        win_rate: float = (float(winning_trades) / float(total_trades) * 100.0) if total_trades > 0 else 0.0
        total_return_rate: float = (
            float(total_return / total_investment * 100) if total_investment > 0 else 0.0
        )
        avg_return_per_trade: float = (
            float(total_return / total_trades) if total_trades > 0 else 0.0
        )
        total_net_return_rate: float = (
            float(total_net_return / total_investment * 100) if total_investment > 0 else 0.0
        )
        avg_net_return_per_trade: float = (
            float(total_net_return / total_trades) if total_trades > 0 else 0.0
        )
        avg_holding_days: float = (
            float(total_holding_days / total_trades) if total_trades > 0 else 0.0
        )
        # 盈亏比（Profit Factor）：总盈利/总亏损绝对值
        if total_trades > 0:
            if sum_loss_abs > 0:
                profit_loss_ratio = float((sum_profit / sum_loss_abs).quantize(Decimal('0.01')))
            else:
                # 没有亏损但有盈利时，设置为一个较大值用于展示，同时在打分处会被截断
                profit_loss_ratio = float('inf') if sum_profit > 0 else 0.0
        else:
            profit_loss_ratio = 0.0

        # 换手率：区间内买卖成交额之和相对总投入（不含费）。
        # 结果以百分比形式返回（如 250.00 表示 2.5 倍）。
        try:
            turnover_ratio = float(((total_buy_gross_amount + total_sell_gross_amount) / total_investment)) if total_investment > 0 else 0.0
        except Exception:
            turnover_ratio = 0.0
        turnover_rate_pct = float(turnover_ratio * 100.0)

        return {
            'stats': {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_investment': float(total_investment),
                'total_return': float(total_return),
                'total_return_rate': total_return_rate,
                'avg_return_per_trade': avg_return_per_trade,
                'avg_holding_days': avg_holding_days,
                'total_fees': float(total_fees),
                'avg_profit_loss_ratio': (profit_loss_ratio if profit_loss_ratio != float('inf') else 9999.0),
                # 新增毛利/净利统计
                'total_gross_return': float(total_return),
                'total_net_return': float(total_net_return),
                'total_net_return_rate': total_net_return_rate,
                'avg_net_return_per_trade': avg_net_return_per_trade,
                # 新增：换手率
                'turnover_rate': turnover_rate_pct,
            },
            'details': details
        }

    # -------------------------------------------
    # 高级指标（年化波动率、年化收益率、最大回撤）
    # 使用 numpy/pandas/empyrical 计算
    # -------------------------------------------
    def _compute_advanced_metrics(
        self,
        trade_ids: List[int],
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> Tuple[float, float, float, float, float]:
        """基于卖出事件构建日收益序列，并计算年化波动率/年化收益率/最大回撤/夏普/卡玛。

        说明：
        - 日收益构造：以每个卖出明细相对于该交易加权买入均价的不含费毛收益率为当日收益，
          按卖出份额加权聚合到交易日。
        - 指标计算：严格委托于 empyrical 库，不自行编码公式。
        """
        if not trade_ids:
            return 0.0, 0.0, 0.0, 0.0, 0.0

        try:
            import numpy as np  # noqa: F401
            import pandas as pd
            try:
                import empyrical as ep
            except Exception:
                import empyrical_reloaded as ep
        except Exception:
            return 0.0, 0.0, 0.0, 0.0, 0.0

        # 读取每个 trade 的买入聚合（用于计算加权买入均价）
        in_clause = ','.join(['?'] * len(trade_ids))
        buys_sql = f"""
            SELECT trade_id,
                   SUM(CASE WHEN transaction_type='buy' THEN price*quantity END) AS gross_buy,
                   SUM(CASE WHEN transaction_type='buy' THEN quantity END) AS buy_qty
            FROM trade_details
            WHERE trade_id IN ({in_clause}) AND is_deleted = 0
            GROUP BY trade_id
        """
        buy_rows = self.db.execute_query(buys_sql, tuple(trade_ids))
        trade_to_avg_buy: Dict[int, float] = {}
        for r in buy_rows:
            try:
                gid = int(r['trade_id'])
                gross_buy = float(r['gross_buy'] or 0.0)
                buy_qty = float(r['buy_qty'] or 0.0)
                trade_to_avg_buy[gid] = (gross_buy / buy_qty) if buy_qty > 0 else 0.0
            except Exception:
                continue

        # 卖出明细（限定日期范围）
        where_dates = []
        params: List[Any] = list(trade_ids)
        if start_date:
            where_dates.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            where_dates.append("transaction_date <= ?")
            params.append(end_date)
        where_clause = (" AND " + " AND ".join(where_dates)) if where_dates else ""

        sells_sql = f"""
            SELECT trade_id, transaction_date, price, quantity
            FROM trade_details
            WHERE trade_id IN ({in_clause})
              AND transaction_type='sell' AND is_deleted = 0
              {where_clause}
            ORDER BY transaction_date
        """
        sell_rows = self.db.execute_query(sells_sql, tuple(params))
        if not sell_rows:
            return 0.0, 0.0, 0.0, 0.0, 0.0

        # 聚合到日期：按卖出份额对每笔 (price - avg_buy)/avg_buy 加权
        by_date: Dict[str, Dict[str, float]] = {}
        for r in sell_rows:
            tid = int(r['trade_id'])
            dt = str(r['transaction_date'])
            price = float(r['price'])
            qty = float(r['quantity'])
            avg_buy = float(trade_to_avg_buy.get(tid, 0.0))
            if avg_buy <= 0 or qty <= 0:
                continue
            ret = (price - avg_buy) / avg_buy
            bucket = by_date.setdefault(dt, {'wret': 0.0, 'w': 0.0})
            bucket['wret'] += ret * qty
            bucket['w'] += qty

        if not by_date:
            return 0.0, 0.0, 0.0, 0.0, 0.0

        # 构造 pandas Series（日频，缺失天填充 0）
        data = []
        for d, agg in by_date.items():
            w = agg['w'] or 1.0
            data.append((pd.to_datetime(d), agg['wret'] / w))
        df = pd.DataFrame(data, columns=['date', 'ret']).sort_values('date')
        df = df.set_index('date')
        # 日频重采样，空天补 0 收益（无交易日视作0）
        full = df.resample('D').sum().fillna(0.0)
        ret_series = full['ret']

        try:
            ann_vol = float(ep.annual_volatility(ret_series))
            ann_ret = float(ep.annual_return(ret_series))
            mdd = float(ep.max_drawdown(ret_series))
            try:
                # 兼容 empyrical 与 empyrical_reloaded 两种包的 API
                sharpe = float(getattr(ep, 'sharpe_ratio', ep.stats.sharpe_ratio)(ret_series))
            except Exception:
                sharpe = 0.0
            try:
                calmar = float(getattr(ep, 'calmar_ratio', ep.stats.calmar_ratio)(ret_series))
            except Exception:
                calmar = 0.0
            return ann_vol, ann_ret, mdd, sharpe, calmar
        except Exception:
            return 0.0, 0.0, 0.0, 0.0, 0.0

    def _get_strategy_by_name(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取策略"""
        strategies = self.strategy_service.get_all_strategies()
        for strategy in strategies:
            if strategy['name'] == strategy_name:
                return strategy
        return None

    def _get_period_date_range(self, period: str, period_type: str = 'year') -> tuple:
        """获取时间周期的日期范围"""
        return get_period_date_range(period, period_type)
