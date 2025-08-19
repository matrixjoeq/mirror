#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观观察 - 页面路由（MVP）
"""

from flask import Blueprint, render_template, request, current_app

from services.macro_service import MacroService


macro_bp = Blueprint('macro', __name__)


@macro_bp.route('/macro')
def dashboard():
    svc = MacroService(current_app.db_service)
    snap = svc.get_snapshot(view=request.args.get('view', 'value'), window=request.args.get('window'))
    return render_template('macro_dashboard.html', snapshot=snap)


@macro_bp.route('/macro/country')
def country():
    economy = request.args.get('economy', 'US')
    window = request.args.get('window', '3y')
    svc = MacroService(current_app.db_service)
    data = svc.get_country(economy=economy, window=window)
    return render_template('macro_country.html', data=data)


@macro_bp.route('/macro/compare')
def compare():
    svc = MacroService(current_app.db_service)
    snap = svc.get_snapshot(view=request.args.get('view', 'value'), window=request.args.get('window'))
    return render_template('macro_compare.html', snapshot=snap)


