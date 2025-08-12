#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
领域异常类型：用于在服务层抛出语义化错误，并由装饰器统一映射为HTTP响应。
"""


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str = "业务错误"):
        super().__init__(message)


class ValidationError(DomainError):
    code = "validation_error"


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class UnauthorizedError(DomainError):
    code = "unauthorized"


class ForbiddenError(DomainError):
    code = "forbidden"


class InternalError(DomainError):
    code = "internal_error"


