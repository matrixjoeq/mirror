#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观观察 - API 路由（MVP）
"""

from flask import Blueprint, request, jsonify, current_app

from services.macro_service import MacroService
from utils.decorators import handle_errors


api_macro_bp = Blueprint('api_macro', __name__, url_prefix='/api/macro')


@api_macro_bp.route('/snapshot')
@handle_errors
def snapshot():
    """返回宏观快照
    Query:
      - view: value|zscore|percentile|trend（默认 value）
      - date: 截止日期
      - window: 分析窗口：6m/1y/3y/5y/10y
      - economies: 逗号分隔经济体过滤
      - indicators: 逗号分隔指标过滤
    """
    view = request.args.get('view', 'value')
    date = request.args.get('date')
    window = request.args.get('window')
    nocache = request.args.get('nocache', 'false').lower() in ('1','true','yes')
    svc = MacroService(current_app.db_service)
    snap = svc.get_snapshot(view=view, date=date, window=window, nocache=nocache)
    economies = request.args.get('economies')
    indicators = request.args.get('indicators')
    if economies:
        ecos = [e.strip().upper() for e in economies.split(',') if e.strip()]
        snap['economies'] = [e for e in snap['economies'] if e in ecos]
        snap['ranking'] = [r for r in snap['ranking'] if r['economy'] in snap['economies']]
        snap['matrix'] = {e: snap['matrix'][e] for e in snap['economies'] if e in snap['matrix']}
    if indicators:
        inds = [i.strip() for i in indicators.split(',') if i.strip()]
        for e, row in snap['matrix'].items():
            row['by_indicator'] = {k: v for k, v in row.get('by_indicator', {}).items() if k in inds}
    return jsonify(snap)


@api_macro_bp.route('/country')
@handle_errors
def country():
    economy = request.args.get('economy', 'US')
    window = request.args.get('window', '3y')
    svc = MacroService(current_app.db_service)
    return jsonify(svc.get_country(economy=economy, window=window))


@api_macro_bp.route('/score')
@handle_errors
def score():
    entity_type = request.args.get('entity_type', 'commodity')
    entity_id = request.args.get('entity_id', 'gold')
    view = request.args.get('view', 'trend')
    svc = MacroService(current_app.db_service)
    return jsonify(svc.get_score(entity_type=entity_type, entity_id=entity_id, view=view))


@api_macro_bp.route('/refresh', methods=['POST'])
@handle_errors
def refresh():
    svc = MacroService(current_app.db_service)
    return jsonify(svc.refresh_all())


@api_macro_bp.route('/status')
@handle_errors
def status():
    svc = MacroService(current_app.db_service)
    return jsonify(svc.repo.get_refresh_status())


