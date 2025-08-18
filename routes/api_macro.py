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
    view = request.args.get('view', 'value')
    date = request.args.get('date')
    window = request.args.get('window')
    svc = MacroService(current_app.db_service)
    return jsonify(svc.get_snapshot(view=view, date=date, window=window))


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


