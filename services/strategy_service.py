#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略服务层
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .database_service import DatabaseService
from models.strategy import Strategy, Tag


class StrategyService:
    """策略管理服务"""
    
    def __init__(self, db_service: Optional[DatabaseService] = None):
        self.db = db_service or DatabaseService()
    
    def get_all_strategies(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """获取所有策略"""
        query = '''
            SELECT s.*, GROUP_CONCAT(st.name) as tag_names
            FROM strategies s
            LEFT JOIN strategy_tag_relations str ON s.id = str.strategy_id
            LEFT JOIN strategy_tags st ON str.tag_id = st.id
        '''
        
        if not include_inactive:
            query += ' WHERE s.is_active = 1'
        
        query += ' GROUP BY s.id ORDER BY s.name'
        
        strategies = self.db.execute_query(query)
        
        result = []
        for strategy in strategies:
            strategy_dict = dict(strategy)
            strategy_dict['tags'] = strategy_dict['tag_names'].split(',') if strategy_dict['tag_names'] else []
            del strategy_dict['tag_names']
            result.append(strategy_dict)
        
        return result
    
    def get_strategy_by_id(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取策略"""
        query = '''
            SELECT s.*, GROUP_CONCAT(st.name) as tag_names
            FROM strategies s
            LEFT JOIN strategy_tag_relations str ON s.id = str.strategy_id
            LEFT JOIN strategy_tags st ON str.tag_id = st.id
            WHERE s.id = ?
            GROUP BY s.id
        '''
        
        strategy = self.db.execute_query(query, (strategy_id,), fetch_one=True)
        
        if strategy:
            strategy_dict = dict(strategy)
            strategy_dict['tags'] = strategy_dict['tag_names'].split(',') if strategy_dict['tag_names'] else []
            del strategy_dict['tag_names']
            return strategy_dict
        
        return None
    
    def create_strategy(self, name: str, description: str = '', tag_names: List[str] = None) -> Tuple[bool, str]:
        """创建策略"""
        if not name or not name.strip():
            return False, "策略名称不能为空"
        
        name = name.strip()
        tag_names = tag_names or []
        
        # 检查策略名称是否已存在
        existing = self.db.execute_query(
            "SELECT id FROM strategies WHERE name = ?", (name,), fetch_one=True
        )
        if existing:
            return False, f"策略名称 '{name}' 已存在"
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建策略
                cursor.execute('''
                    INSERT INTO strategies (name, description, created_at, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (name, description))
                
                strategy_id = cursor.lastrowid
                
                # 处理标签
                for tag_name in tag_names:
                    if tag_name.strip():
                        tag_id = self._get_or_create_tag(cursor, tag_name.strip())
                        cursor.execute('''
                            INSERT OR IGNORE INTO strategy_tag_relations (strategy_id, tag_id)
                            VALUES (?, ?)
                        ''', (strategy_id, tag_id))
                
                conn.commit()
                return True, f"策略 '{name}' 创建成功"
                
        except Exception as e:
            return False, f"创建策略失败: {str(e)}"
    
    def update_strategy(self, strategy_id: int, name: str, description: str = '', tag_names: List[str] = None) -> Tuple[bool, str]:
        """更新策略"""
        if not name or not name.strip():
            return False, "策略名称不能为空"
        
        name = name.strip()
        tag_names = tag_names or []
        
        # 检查策略是否存在
        existing = self.get_strategy_by_id(strategy_id)
        if not existing:
            return False, f"策略ID {strategy_id} 不存在"
        
        # 检查名称冲突（排除当前策略）
        name_conflict = self.db.execute_query(
            "SELECT id FROM strategies WHERE name = ? AND id != ?", (name, strategy_id), fetch_one=True
        )
        if name_conflict:
            return False, f"策略名称 '{name}' 已被其他策略使用"
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 更新策略信息
                cursor.execute('''
                    UPDATE strategies 
                    SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (name, description, strategy_id))
                
                # 删除旧的标签关联
                cursor.execute('DELETE FROM strategy_tag_relations WHERE strategy_id = ?', (strategy_id,))
                
                # 添加新的标签关联
                for tag_name in tag_names:
                    if tag_name.strip():
                        tag_id = self._get_or_create_tag(cursor, tag_name.strip())
                        cursor.execute('''
                            INSERT INTO strategy_tag_relations (strategy_id, tag_id)
                            VALUES (?, ?)
                        ''', (strategy_id, tag_id))
                
                conn.commit()
                return True, f"策略 '{name}' 更新成功"
                
        except Exception as e:
            return False, f"更新策略失败: {str(e)}"
    
    def delete_strategy(self, strategy_id: int) -> Tuple[bool, str]:
        """删除策略（软删除 - 设为非活跃状态）"""
        strategy = self.get_strategy_by_id(strategy_id)
        if not strategy:
            return False, f"策略ID {strategy_id} 不存在"
        
        # 检查是否有关联的交易
        trades_count = self.db.execute_query(
            "SELECT COUNT(*) as count FROM trades WHERE strategy_id = ?", 
            (strategy_id,), fetch_one=True
        )
        
        if trades_count and trades_count['count'] > 0:
            return False, f"策略 '{strategy['name']}' 有关联的交易记录，无法删除"
        
        try:
            self.db.execute_query(
                "UPDATE strategies SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (strategy_id,), fetch_all=False
            )
            return True, f"策略 '{strategy['name']}' 已禁用"
            
        except Exception as e:
            return False, f"删除策略失败: {str(e)}"
    
    def get_all_tags(self) -> List[Dict[str, Any]]:
        """获取所有标签"""
        query = "SELECT * FROM strategy_tags ORDER BY name"
        return [dict(tag) for tag in self.db.execute_query(query)]
    
    def create_tag(self, name: str) -> Tuple[bool, str]:
        """创建标签"""
        if not name or not name.strip():
            return False, "标签名称不能为空"
        
        name = name.strip()
        
        # 检查标签是否已存在
        existing = self.db.execute_query(
            "SELECT id FROM strategy_tags WHERE name = ?", (name,), fetch_one=True
        )
        if existing:
            return False, f"标签 '{name}' 已存在"
        
        try:
            self.db.execute_query(
                "INSERT INTO strategy_tags (name, created_at) VALUES (?, CURRENT_TIMESTAMP)",
                (name,), fetch_all=False
            )
            return True, f"标签 '{name}' 创建成功"
            
        except Exception as e:
            return False, f"创建标签失败: {str(e)}"
    
    def update_tag(self, tag_id: int, new_name: str) -> Tuple[bool, str]:
        """更新标签"""
        if not new_name or not new_name.strip():
            return False, "标签名称不能为空"
        
        new_name = new_name.strip()
        
        # 检查标签是否存在
        existing = self.db.execute_query(
            "SELECT name FROM strategy_tags WHERE id = ?", (tag_id,), fetch_one=True
        )
        if not existing:
            return False, f"标签ID {tag_id} 不存在"
        
        # 检查是否为预定义标签（基于名称）
        predefined_tags = ['轮动', '择时', '趋势', '套利']
        if existing['name'] in predefined_tags:
            return False, f"预定义标签不能修改"
        
        old_name = existing['name']
        
        # 检查新名称是否冲突
        name_conflict = self.db.execute_query(
            "SELECT id FROM strategy_tags WHERE name = ? AND id != ?", (new_name, tag_id), fetch_one=True
        )
        if name_conflict:
            return False, f"标签名称 '{new_name}' 已存在"
        
        try:
            self.db.execute_query(
                "UPDATE strategy_tags SET name = ? WHERE id = ?",
                (new_name, tag_id), fetch_all=False
            )
            return True, f"标签已从 '{old_name}' 更新为 '{new_name}'"
            
        except Exception as e:
            return False, f"更新标签失败: {str(e)}"
    
    def delete_tag(self, tag_id: int) -> Tuple[bool, str]:
        """删除标签"""
        # 检查标签是否存在
        existing = self.db.execute_query(
            "SELECT name FROM strategy_tags WHERE id = ?", (tag_id,), fetch_one=True
        )
        if not existing:
            return False, f"标签ID {tag_id} 不存在"
        
        # 检查是否为预定义标签（基于名称）
        predefined_tags = ['轮动', '择时', '趋势', '套利']
        if existing['name'] in predefined_tags:
            return False, f"预定义标签不能删除"
        
        tag_name = existing['name']
        
        # 检查是否有策略使用此标签
        usage_count = self.db.execute_query(
            "SELECT COUNT(*) as count FROM strategy_tag_relations WHERE tag_id = ?",
            (tag_id,), fetch_one=True
        )
        
        if usage_count and usage_count['count'] > 0:
            return False, f"标签 '{tag_name}' 正在被策略使用，无法删除"
        
        try:
            self.db.execute_query("DELETE FROM strategy_tags WHERE id = ?", (tag_id,), fetch_all=False)
            return True, f"标签 '{tag_name}' 已删除"
            
        except Exception as e:
            return False, f"删除标签失败: {str(e)}"
    
    def _get_or_create_tag(self, cursor, tag_name: str) -> int:
        """获取或创建标签，返回标签ID"""
        cursor.execute("SELECT id FROM strategy_tags WHERE name = ?", (tag_name,))
        tag = cursor.fetchone()
        
        if tag:
            return tag['id']
        else:
            cursor.execute(
                "INSERT INTO strategy_tags (name, created_at) VALUES (?, CURRENT_TIMESTAMP)",
                (tag_name,)
            )
            return cursor.lastrowid
