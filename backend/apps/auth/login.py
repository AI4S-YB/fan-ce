"""
@File    :   login.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.requests import Request

from apps.common.depends import get_db
from apps.common.depends import users_db
from apps.common.schemas import Token, TokenDoc
from apps.common.security import create_access_token
from apps.services.rbd import rbd_service
from apps.services.auth_key_service import auth_key_service
from core.config import settings
from libs.exceptions.exception import exceptions
from libs.responses.response import response_200, response_2000
from libs.responses.result import ResultModel
from .schemas import UserGetToken, AuthKeyLoginRequest, AuthKeyLoginResponse, AuthKeyVerifyRequest, AuthKeyVerifyResponse, UserInfo

login_router = APIRouter(tags=['auth:认证'])


# 文档登录
@login_router.post("/login/access-token", response_model=TokenDoc, summary="用户登录认证", include_in_schema=False)
async def login_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    user = users_db.authenticate(db, user_name=form_data.username, user_password=form_data.password)
    if not user:
        raise HTTPException(status_code=exceptions.CODE_4004['code'], detail=exceptions.CODE_4004['msg'])
    elif not users_db.is_active(user):
        raise HTTPException(status_code=exceptions.CODE_4003['code'], detail=exceptions.CODE_4003['msg'])
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(user.id, expires_delta=access_token_expires)
    return {"access_token": token, "token_type": "Bearer"}


# 前端登录
@login_router.post("/auth/login", response_model=ResultModel[Token], summary="获取token")
async def login_get_token(user_data: UserGetToken, request: Request, db: Session = Depends(get_db)) -> Any:
    """用户认证获取token值"""
    user_data.user_name = user_data.username
    user_data.user_password = user_data.password
    user = users_db.authenticate(db, user_name=user_data.user_name, user_password=user_data.user_password)
    if not user:
        raise HTTPException(status_code=exceptions.CODE_4002.get('code'), detail=exceptions.CODE_4002.get('msg'))
    elif not users_db.is_active(user):
        raise HTTPException(status_code=exceptions.CODE_4003.get('code'), detail=exceptions.CODE_4003.get("msg"))
    role_ids = rbd_service.get_user_role_all_ids(db=db, user=user)
    user_default = rbd_service.get_user_default(db=db, user=user)
    if not role_ids:
        raise HTTPException(status_code=exceptions.CODE_4011.get('code'), detail=exceptions.CODE_4011.get('msg'))
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(user.id, expires_delta=access_token_expires)
    user_avatar = f"/api/v1/avatar/{user.user_avatar}"

    project_data = user_default.get('project_info', {})

    return response_200(data={"access_token": token, "token_type": settings.TOKEN_TYPE, "user_id": user.id, 'user_avatar': user_avatar,
                              'user_name': user.user_name, 'team': {},
                              'project': project_data}
                        )


# === 认证密钥登录API ===

@login_router.post("/auth/api-key-login", 
                  response_model=ResultModel[AuthKeyLoginResponse], 
                  summary="认证密钥登录")
async def api_key_login(
    request_data: AuthKeyLoginRequest, 
    request: Request, 
    db: Session = Depends(get_db)
) -> Any:
    """基于认证密钥进行用户认证并获取token"""
    try:
        # 验证认证密钥
        validation_result = auth_key_service.validate_auth_key(db, request_data.auth_key)
        
        if not validation_result['valid']:
            # 根据错误类型返回不同的错误码
            error_codes = {
                'AUTH_KEY_FORMAT_INVALID': {'code': 40001, 'msg': '认证密钥格式错误'},
                'AUTH_KEY_NOT_FOUND': {'code': 40002, 'msg': '认证密钥无效或不存在'},
                'USER_INACTIVE_OR_DELETED': {'code': 40003, 'msg': '用户账号已禁用或删除'},
                'AUTH_KEY_DISABLED': {'code': 40004, 'msg': '认证密钥已被禁用'},
                'AUTH_KEY_TEAM_MISMATCH': {'code': 40005, 'msg': '认证密钥与用户团队不匹配'}
            }
            
            error_info = error_codes.get(validation_result['error'], {
                'code': 40006, 
                'msg': f"认证失败: {validation_result['error']}"
            })
            
            raise HTTPException(
                status_code=401, 
                detail={
                    "error": "invalid_auth_key",
                    "message": error_info['msg'],
                    "code": error_info['code']
                }
            )
        
        user = validation_result['user']
        team_id = validation_result['team_id']
        
        # 检查用户权限和角色
        role_ids = rbd_service.get_user_role_all_ids(db=db, user=user)
        if not role_ids:
            raise HTTPException(
                status_code=403, 
                detail={
                    "error": "no_permissions",
                    "message": "用户未分配任何角色权限",
                    "code": 40011
                }
            )
        
        # 获取用户默认团队和项目信息
        user_default = rbd_service.get_user_default(db=db, user=user)
        
        # 生成访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(user.id, expires_delta=access_token_expires)
        
        # 构建用户信息
        user_info = UserInfo(
            id=user.id,
            username=user.user_name,
            team_id=team_id,
            project_id=user_default.get('project_info', {}).get('id', 0)
        )
        
        # 构建响应数据
        response_data = AuthKeyLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 转换为秒
            user_info=user_info
        )
        
        return response_200(data=response_data, msg="认证成功")
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 其他异常
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"认证服务内部错误: {str(e)}",
                "code": 50001
            }
        )


@login_router.post("/auth/verify-api-key", 
                  response_model=ResultModel[AuthKeyVerifyResponse], 
                  summary="验证认证密钥")
async def verify_api_key(
    request_data: AuthKeyVerifyRequest,
    db: Session = Depends(get_db)
) -> Any:
    """验证认证密钥的有效性"""
    try:
        # 验证认证密钥
        validation_result = auth_key_service.validate_auth_key(db, request_data.auth_key)
        
        if validation_result['valid']:
            response_data = AuthKeyVerifyResponse(
                valid=True,
                user_id=validation_result['user'].id,
                team_id=validation_result['team_id'],
                status='active'
            )
        else:
            response_data = AuthKeyVerifyResponse(
                valid=False,
                user_id=None,
                team_id=None,
                status=None
            )
        
        return response_200(data=response_data)
        
    except Exception as e:
        return response_2000(
            code=500, 
            message=f"验证认证密钥失败: {str(e)}"
        )
