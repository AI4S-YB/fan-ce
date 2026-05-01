"""
@File    :   auth_key_service.py
@Time    :   2025/09/22 12:00:00
@Author  :   Claude
@Version :   1.0
@Desc    :   认证密钥服务 - 处理密钥生成、验证、管理等功能
"""

import secrets
import string
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from apps.system.user.models import User
from apps.system.user.crud import users_db
from apps.system.team.models import TeamUserLink


class AuthKeyService:
    """认证密钥服务类"""
    
    @staticmethod
    def generate_auth_key(team_id: int) -> str:
        """
        生成认证密钥
        
        Args:
            team_id: 团队ID
            
        Returns:
            str: 格式为 fandb_team{team_id}_{random_16_chars} 的认证密钥
        """
        # 生成16位随机字符串（小写字母+数字）
        random_chars = ''.join(
            secrets.choice(string.ascii_lowercase + string.digits) 
            for _ in range(16)
        )
        return f"fandb_team{team_id}_{random_chars}"
    
    @staticmethod
    def extract_team_id_from_auth_key(auth_key: str) -> Optional[int]:
        """
        从认证密钥中提取team_id
        
        Args:
            auth_key: 认证密钥
            
        Returns:
            Optional[int]: 提取的team_id，如果格式不正确返回None
        """
        try:
            if auth_key and auth_key.startswith('fandb_team'):
                parts = auth_key.split('_')
                if len(parts) >= 2:
                    team_part = parts[1]  # team24
                    if team_part.startswith('team'):
                        return int(team_part.replace('team', ''))
        except (IndexError, ValueError):
            pass
        return None
    
    @staticmethod
    def validate_auth_key_format(auth_key: str) -> bool:
        """
        验证认证密钥格式是否正确
        
        Args:
            auth_key: 认证密钥
            
        Returns:
            bool: 格式是否正确
        """
        if not auth_key:
            return False
        
        # 检查基本格式：fandb_team{数字}_{16位字符}
        parts = auth_key.split('_')
        if len(parts) != 3:
            return False
        
        prefix, team_part, random_part = parts
        
        # 检查前缀
        if prefix != 'fandb':
            return False
        
        # 检查团队部分
        if not team_part.startswith('team') or not team_part[4:].isdigit():
            return False
        
        # 检查随机部分长度
        if len(random_part) != 16:
            return False
        
        # 检查随机部分只包含小写字母和数字
        if not all(c in string.ascii_lowercase + string.digits for c in random_part):
            return False
        
        return True
    
    @staticmethod
    def get_user_by_auth_key(db: Session, auth_key: str) -> Optional[User]:
        """
        根据认证密钥获取用户
        
        Args:
            db: 数据库会话
            auth_key: 认证密钥
            
        Returns:
            Optional[User]: 用户对象，如果未找到返回None
        """
        return users_db.get_filter(db=db, filters={'auth_key': auth_key})
    
    @staticmethod
    def get_user_primary_team_id(db: Session, user: User) -> Optional[int]:
        """
        获取用户的主要团队ID（第一个团队）
        
        Args:
            db: 数据库会话
            user: 用户对象
            
        Returns:
            Optional[int]: 团队ID，如果用户没有团队返回None
        """
        team_link = db.query(TeamUserLink).filter(
            TeamUserLink.user_id == user.id
        ).first()
        
        return team_link.team_id if team_link else None
    
    @staticmethod
    def validate_auth_key(db: Session, auth_key: str) -> Dict[str, Any]:
        """
        全面验证认证密钥
        
        Args:
            db: 数据库会话
            auth_key: 认证密钥
            
        Returns:
            Dict[str, Any]: 验证结果
            {
                'valid': bool,           # 是否有效
                'user': User,           # 用户对象（如果有效）
                'team_id': int,         # 团队ID（如果有效）
                'error': str            # 错误信息（如果无效）
            }
        """
        result = {
            'valid': False,
            'user': None,
            'team_id': None,
            'error': None
        }
        
        # 1. 验证密钥格式
        if not AuthKeyService.validate_auth_key_format(auth_key):
            result['error'] = 'AUTH_KEY_FORMAT_INVALID'
            return result
        
        # 2. 查找用户
        user = AuthKeyService.get_user_by_auth_key(db, auth_key)
        if not user:
            result['error'] = 'AUTH_KEY_NOT_FOUND'
            return result
        
        # 3. 检查用户状态
        if not user.is_active or user.is_deleted:
            result['error'] = 'USER_INACTIVE_OR_DELETED'
            return result
        
        # 4. 检查密钥状态
        if user.key_status != 'active':
            result['error'] = 'AUTH_KEY_DISABLED'
            return result
        
        # 5. 验证密钥中的team_id与用户实际团队的一致性
        key_team_id = AuthKeyService.extract_team_id_from_auth_key(auth_key)
        user_team_id = AuthKeyService.get_user_primary_team_id(db, user)
        
        if key_team_id != user_team_id:
            result['error'] = 'AUTH_KEY_TEAM_MISMATCH'
            return result
        
        # 验证通过
        result.update({
            'valid': True,
            'user': user,
            'team_id': user_team_id,
            'error': None
        })
        
        return result
    
    @staticmethod
    def generate_auth_key_for_user(db: Session, user_id: int) -> Dict[str, Any]:
        """
        为用户生成认证密钥
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 生成结果
            {
                'success': bool,
                'auth_key': str,        # 生成的密钥（如果成功）
                'error': str            # 错误信息（如果失败）
            }
        """
        result = {
            'success': False,
            'auth_key': None,
            'error': None
        }
        
        # 1. 获取用户
        user = users_db.get_one(db=db, id=user_id)
        if not user:
            result['error'] = 'USER_NOT_FOUND'
            return result
        
        # 2. 检查用户是否已有密钥
        if user.auth_key:
            result['error'] = 'AUTH_KEY_ALREADY_EXISTS'
            return result
        
        # 3. 获取用户的团队ID
        team_id = AuthKeyService.get_user_primary_team_id(db, user)
        if not team_id:
            result['error'] = 'USER_NO_TEAM'
            return result
        
        # 4. 生成新密钥
        auth_key = AuthKeyService.generate_auth_key(team_id)
        
        # 5. 检查密钥唯一性（理论上不会重复，但为安全起见检查）
        existing_user = AuthKeyService.get_user_by_auth_key(db, auth_key)
        if existing_user:
            # 重新生成一次
            auth_key = AuthKeyService.generate_auth_key(team_id)
            existing_user = AuthKeyService.get_user_by_auth_key(db, auth_key)
            if existing_user:
                result['error'] = 'AUTH_KEY_COLLISION'
                return result
        
        # 6. 更新用户记录
        try:
            users_db.update_one(db=db, db_obj=user, obj_in={
                'auth_key': auth_key,
                'key_status': 'active'
            })
            db.commit()
            
            result.update({
                'success': True,
                'auth_key': auth_key,
                'error': None
            })
        except Exception as e:
            db.rollback()
            result['error'] = f'DATABASE_ERROR: {str(e)}'
        
        return result
    
    @staticmethod
    def regenerate_auth_key_for_user(db: Session, user_id: int) -> Dict[str, Any]:
        """
        为用户重新生成认证密钥
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 重新生成结果
        """
        result = {
            'success': False,
            'auth_key': None,
            'error': None
        }
        
        # 1. 获取用户
        user = users_db.get_one(db=db, id=user_id)
        if not user:
            result['error'] = 'USER_NOT_FOUND'
            return result
        
        # 2. 获取用户的团队ID
        team_id = AuthKeyService.get_user_primary_team_id(db, user)
        if not team_id:
            result['error'] = 'USER_NO_TEAM'
            return result
        
        # 3. 生成新密钥
        auth_key = AuthKeyService.generate_auth_key(team_id)
        
        # 4. 更新用户记录
        try:
            users_db.update_one(db=db, db_obj=user, obj_in={
                'auth_key': auth_key,
                'key_status': 'active'
            })
            db.commit()
            
            result.update({
                'success': True,
                'auth_key': auth_key,
                'error': None
            })
        except Exception as e:
            db.rollback()
            result['error'] = f'DATABASE_ERROR: {str(e)}'
        
        return result
    
    @staticmethod
    def update_auth_key_status(db: Session, user_id: int, status: str) -> Dict[str, Any]:
        """
        更新用户认证密钥状态
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            status: 新状态 ('active' 或 'disabled')
            
        Returns:
            Dict[str, Any]: 更新结果
        """
        result = {
            'success': False,
            'error': None
        }
        
        if status not in ['active', 'disabled']:
            result['error'] = 'INVALID_STATUS'
            return result
        
        # 1. 获取用户
        user = users_db.get_one(db=db, id=user_id)
        if not user:
            result['error'] = 'USER_NOT_FOUND'
            return result
        
        # 2. 检查用户是否有密钥
        if not user.auth_key:
            result['error'] = 'AUTH_KEY_NOT_EXISTS'
            return result
        
        # 3. 更新状态
        try:
            users_db.update_one(db=db, db_obj=user, obj_in={
                'key_status': status
            })
            db.commit()
            
            result['success'] = True
        except Exception as e:
            db.rollback()
            result['error'] = f'DATABASE_ERROR: {str(e)}'
        
        return result
    
    @staticmethod
    def delete_auth_key(db: Session, user_id: int) -> Dict[str, Any]:
        """
        删除用户认证密钥
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 删除结果
        """
        result = {
            'success': False,
            'error': None
        }
        
        # 1. 获取用户
        user = users_db.get_one(db=db, id=user_id)
        if not user:
            result['error'] = 'USER_NOT_FOUND'
            return result
        
        # 2. 删除密钥
        try:
            users_db.update_one(db=db, db_obj=user, obj_in={
                'auth_key': None,
                'key_status': None
            })
            db.commit()
            
            result['success'] = True
        except Exception as e:
            db.rollback()
            result['error'] = f'DATABASE_ERROR: {str(e)}'
        
        return result


# 创建服务实例
auth_key_service = AuthKeyService()