#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from flask import Blueprint, jsonify, request
from services.meso_service import MesoService


api_meso_bp = Blueprint('api_meso', __name__)


@api_meso_bp.route('/api/meso/instruments', methods=['GET', 'POST'])
def meso_instruments():
    svc = MesoService()
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        rows = data.get('instruments') or []
        res = svc.upsert_tracked_instruments(rows)
        return jsonify(res)
    only_active = request.args.get('active', '1') == '1'
    res = svc.list_tracked_instruments(only_active=only_active)
    return jsonify({"items": res})


@api_meso_bp.route('/api/meso/settings/start_date', methods=['GET', 'POST'])
def meso_global_start_date():
    svc = MesoService()
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        date_str = data.get('start_date')
        if not date_str:
            return jsonify({"error": "start_date required"}), 400
        res = svc.set_global_start_date(date_str)
        return jsonify(res)
    # GET
    from services.meso_repository import MesoRepository
    repo = MesoRepository()
    cur = repo.get_global_start_date()
    return jsonify({"start_date": cur})


@api_meso_bp.route('/api/meso/refresh', methods=['POST'])
def meso_refresh():
    svc = MesoService()
    data = request.get_json(silent=True) or {}
    symbols = data.get('symbols')
    since = data.get('since')
    period = data.get('period', '5y')
    return_mode = data.get('return_mode', 'price')  # price | total
    res = svc.refresh_prices_and_scores(symbols=symbols, period=period, since=since, return_mode=return_mode)
    return jsonify(res)


@api_meso_bp.route('/api/meso/rankings/asset_class', methods=['GET'])
def meso_rankings_asset_class():
    svc = MesoService()
    asof = request.args.get('asof')
    top = int(request.args.get('top', '10'))
    return_mode = request.args.get('return_mode', 'price')
    res = svc.get_asset_class_rankings(asof=asof, top=top, return_mode=return_mode)
    return jsonify(res)

@api_meso_bp.route('/api/meso/rankings/equity_market', methods=['GET'])
def meso_rankings_equity_market():
    svc = MesoService()
    asof = request.args.get('asof')
    top = int(request.args.get('top', '10'))
    return_mode = request.args.get('return_mode', 'price')
    res = svc.get_equity_market_rankings(asof=asof, top=top, return_mode=return_mode)
    return jsonify(res)

@api_meso_bp.route('/api/meso/rankings/equity_category', methods=['GET'])
def meso_rankings_equity_category():
    svc = MesoService()
    market = request.args.get('market')
    if not market:
        return jsonify({"error": "market required"}), 400
    asof = request.args.get('asof')
    top = int(request.args.get('top', '10'))
    return_mode = request.args.get('return_mode', 'price')
    res = svc.get_equity_category_rankings(market=market, asof=asof, top=top, return_mode=return_mode)
    return jsonify(res)


