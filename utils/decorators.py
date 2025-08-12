#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
装饰器模块
"""

from functools import wraps
from flask import request, jsonify
from .exceptions import DomainError, ValidationError, NotFoundError, ConflictError, UnauthorizedError, ForbiddenError


def require_confirmation_code(f):
    """要求确认码的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        confirmation_code = request.form.get('confirmation_code') or request.json.get('confirmation_code')
        
        if not confirmation_code:
            return jsonify({
                'success': False,
                'message': '请提供确认码'
            }), 400
        
        return f(*args, **kwargs)
    
    return decorated_function


def handle_errors(f):
    """错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            return jsonify({'success': False, 'code': e.code, 'message': str(e)}), 400
        except NotFoundError as e:
            return jsonify({'success': False, 'code': e.code, 'message': str(e)}), 404
        except ConflictError as e:
            return jsonify({'success': False, 'code': e.code, 'message': str(e)}), 409
        except UnauthorizedError as e:
            return jsonify({'success': False, 'code': e.code, 'message': str(e)}), 401
        except ForbiddenError as e:
            return jsonify({'success': False, 'code': e.code, 'message': str(e)}), 403
        except DomainError as e:
            return jsonify({'success': False, 'code': e.code, 'message': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'code': 'internal_error', 'message': f'操作失败: {str(e)}'}), 500
    
    return decorated_function


def require_json(f):
    """要求JSON请求的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': '请求必须是JSON格式'
            }), 400
        
        return f(*args, **kwargs)
    
    return decorated_function
