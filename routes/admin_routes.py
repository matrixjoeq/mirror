#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, jsonify, current_app

from services.admin_service import DatabaseMaintenanceService


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _svc():
    return DatabaseMaintenanceService(current_app.db_service, current_app.trading_service)


@admin_bp.route('/db/diagnose')
def db_diagnose_page():
    trade_id = request.args.get('trade_id', type=int)
    result = _svc().validate_database(trade_id)
    return render_template('admin_db.html', result=result, trade_id=trade_id)


@admin_bp.route('/db/diagnose.json')
def db_diagnose_json():
    trade_id = request.args.get('trade_id', type=int)
    return jsonify(_svc().validate_database(trade_id))


@admin_bp.route('/db/auto_fix', methods=['POST'])
def db_auto_fix():
    data = request.get_json(silent=True) or {}
    trade_ids = data.get('trade_ids')
    return jsonify(_svc().auto_fix(trade_ids))


@admin_bp.route('/db/update_row', methods=['POST'])
def db_update_row():
    data = request.get_json(force=True)
    table = data.get('table')
    pk_id = int(data.get('id'))
    updates = data.get('updates') or {}
    ok, msg = _svc().update_raw_row(table, pk_id, updates)
    return jsonify({'ok': ok, 'message': msg})


