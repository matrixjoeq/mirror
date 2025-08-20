#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template
from services.meso_service import MesoService


meso_bp = Blueprint('meso', __name__)


@meso_bp.route('/meso')
def dashboard():
    svc = MesoService()
    indexes = svc.list_indexes()
    return render_template('meso_dashboard.html', indexes=indexes)


