#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略相关数据模型
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Strategy:
    """投资策略"""
    id: Optional[int] = None
    name: str = ''
    description: str = ''
    is_active: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: Optional[List['Tag']] = None


@dataclass 
class Tag:
    """标签"""
    id: Optional[int] = None
    name: str = ''
    created_at: Optional[datetime] = None


@dataclass
class StrategyTag:
    """策略标签关联"""
    strategy_id: int = 0
    tag_id: int = 0
