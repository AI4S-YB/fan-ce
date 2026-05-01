"""
@File    :   routes.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
from typing import Any, List

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from apps.common.depends import get_active_user, check_permission
from apps.services.user import user_service
from apps.services.auth_key_service import auth_key_service
from apps.auth.schemas import (
    AuthKeyInfo, AuthKeyCreateResponse, AuthKeyUpdateRequest, AuthKeyUpdateResponse,
    AuthKeyDeleteResponse, AuthKeyBatchQueryRequest, AuthKeyBatchQueryResponse, AuthKeyBatchItem
)
from db.database import get_db
from libs.exceptions.exception import exceptions
from libs.responses.response import response_2000, response_200
from libs.responses.result import ResultModel, ResultPlusModel
from ..user.crud import users_db
from ..user.models import User
from ..user.schemas import PageList, UserList, UserCreate, DataId, UserOut, UserPwdRest, UserPwdUpdate, UserDelete, UserUpdate, \
    UserActiveUpdate

user_router = APIRouter()


@user_router.get("/field", summary="用户字段")
async def user_list():
    data = User.get_field()
    return response_2000(data=data)


@user_router.post("/list", dependencies=[Depends(check_permission(["sys:user:list"]))], response_model=ResultPlusModel[List[UserOut]],
                  summary="用户列表")
async def user_list(request_data: UserList, db=Depends(get_db), _user=Depends(get_active_user)):
    filters_exp = []
    if request_data.user_name:
        filters_exp.append({'name':'user_name','exp':'like','value':request_data.user_name})
    if request_data.user_email:
        filters_exp.append({'name':'user_email','exp':'like','value':request_data.user_email})
    user_data = users_db.get_list(db=db, page=request_data.page, size=request_data.size,filters_exp=filters_exp)
    return response_200(data=user_data)


@user_router.post("/options", dependencies=[Depends(check_permission(["sys:user:list"]))], response_model=ResultPlusModel[List[UserOut]],
                  summary="用户列表")
async def user_list(request_data: UserList, db=Depends(get_db), _user=Depends(get_active_user)):
    user_data = users_db.get_list(db=db, page=0, size=request_data.size)
    new_data = []
    for user in user_data['dataList']:
        new_data.append({'label': user.user_name, 'value': user.id})
    return response_2000(data=new_data)


@user_router.post("/add", dependencies=[Depends(check_permission(["sys:user:add"]))], summary="用户添加")
async def user_add(request_data: UserCreate, db=Depends(get_db)):
    if users_db.get_user_by_username(db=db, user_name=request_data.user_name):
        return response_2000(data={}, msg=f"{request_data.user_name}{exceptions.CODE_4009['msg']}", code=exceptions.CODE_4009['code'])
    user_data = users_db.create(db=db, user_data=request_data)
    #
    user_service.add_user_role(db=db, user_id=user_data.id, request_data=request_data)
    return response_2000(data=jsonable_encoder(user_data))


@user_router.post("/delete", dependencies=[Depends(check_permission(["sys:user:delete"]))], summary="用户删除")
async def user_info(request_data: UserDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    #17【系统管理】-【用户管理】- 用户列表-用户信息无法删除
    Clark 2025-07-30
    """
    user_data = users_db.remove(db=db, id=request_data.id, ids=request_data.ids)
    return response_200(data={})


@user_router.post("/info", dependencies=[Depends(check_permission(["sys:user:info"]))], response_model=ResultModel[UserOut],
                  summary="用户详情")
async def user_info(request_data: DataId, db=Depends(get_db), _user=Depends(get_active_user)):
    user_data = users_db.get(db=db, id=request_data.id)
    user_data.user_roles = user_service.get_user_role(db=db, user_id=user_data.id)
    return response_200(data=user_data)


@user_router.post("/update", dependencies=[Depends(check_permission(["sys:user:update"]))], summary="用户更新")
async def user_info(request_data: UserUpdate, db=Depends(get_db), _user=Depends(get_active_user)):
    user_obj = users_db.get(db=db, id=request_data.id)
    obj = users_db.update_one(db=db, db_obj=user_obj, obj_in=request_data)
    user_service.update_user_role(db=db, user_id=user_obj.id, request_data=request_data)
    return response_200(data=obj)


@user_router.post("/active", dependencies=[Depends(check_permission(["sys:user:active"]))], summary="用户激活和禁用更新")
async def user_info(request_data: UserActiveUpdate, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = users_db.get(db=db, id=request_data.id)
    obj = users_db.update_one(db=db, db_obj=db_obj, obj_in=request_data)
    return response_200(data=obj)


@user_router.post("/pwd/reset", dependencies=[Depends(check_permission(["sys:user:reset"]))], summary="重置密码")
async def user_add(request_data: UserPwdRest, db=Depends(get_db)):
    _user = users_db.get(db=db, id=request_data.id)
    data = users_db.reset_password(db=db, db_obj=_user, obj_in={'new_password': request_data.new_password})
    return response_200(data=data)


@user_router.post("/auth/info", response_model=ResultModel[UserOut], summary="个人信息")
async def login_get_user(db: Session = Depends(get_db), user=Depends(get_active_user)) -> Any:
    return response_200(data=user)


@user_router.post("/pwd/update", response_model=ResultModel[UserOut], summary="个人密码修改")
async def login_get_user(request_data: UserPwdUpdate, db: Session = Depends(get_db), user=Depends(get_active_user)) -> Any:
    # obj = users_db.update(db=db, db_obj=user, obj_in={'new_password': request_data.new_password})
    data = users_db.reset_password(db=db, db_obj=user, obj_in={'new_password': request_data.new_password})
    return response_200(data=data)


@user_router.post("/notice", summary="用户信息通知")
async def user_notice(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = users_db.get_list(db=db, page=request_data.page, size=request_data.size)
    return response_200(data=db_obj)


# === 认证密钥管理API ===

@user_router.get("/{user_id}/auth-key", 
                dependencies=[Depends(check_permission(["sys:user:update"]))],
                response_model=ResultModel[AuthKeyInfo], 
                summary="获取用户认证密钥信息")
async def get_user_auth_key(
    user_id: int, 
    db: Session = Depends(get_db), 
    _user=Depends(get_active_user)
):
    """获取指定用户的认证密钥信息"""
    try:
        # 获取用户
        user = users_db.get_one(db=db, id=user_id)
        if not user:
            return response_2000(code=404, msg="用户不存在")
        
        # 检查用户是否有密钥
        if not user.auth_key:
            return response_2000(code=404, msg="用户尚未配置认证密钥", data={
                "has_key": False,
                "user_id": user_id
            })
        
        # 获取用户团队ID
        team_id = auth_key_service.get_user_primary_team_id(db, user)
        if not team_id:
            return response_2000(code=400, msg="用户未分配团队")
        
        auth_key_info = AuthKeyInfo(
            auth_key=user.auth_key,
            status=user.key_status or 'active',
            user_id=user.id,
            team_id=team_id,
            has_key=True
        )
        
        return response_200(data=auth_key_info)
        
    except Exception as e:
        return response_2000(code=500, msg=f"获取认证密钥信息失败: {str(e)}")


@user_router.post("/{user_id}/auth-key", 
                 dependencies=[Depends(check_permission(["sys:user:update"]))],
                 response_model=ResultModel[AuthKeyCreateResponse], 
                 summary="生成用户认证密钥")
async def generate_user_auth_key(
    user_id: int, 
    db: Session = Depends(get_db), 
    _user=Depends(get_active_user)
):
    """为指定用户生成认证密钥"""
    try:
        result = auth_key_service.generate_auth_key_for_user(db, user_id)
        
        if not result['success']:
            error_messages = {
                'USER_NOT_FOUND': '用户不存在',
                'AUTH_KEY_ALREADY_EXISTS': '用户已存在认证密钥，请先删除后重新生成',
                'USER_NO_TEAM': '用户未分配团队，无法生成密钥',
                'AUTH_KEY_COLLISION': '密钥生成冲突，请重试'
            }
            
            error_msg = error_messages.get(result['error'], f"生成失败: {result['error']}")
            return response_2000(code=400, msg=error_msg)
        
        # 获取用户团队ID用于响应
        user = users_db.get_one(db=db, id=user_id)
        team_id = auth_key_service.get_user_primary_team_id(db, user)
        
        response_data = AuthKeyCreateResponse(
            auth_key=result['auth_key'],
            status='active',
            user_id=user_id,
            team_id=team_id
        )
        
        return response_200(data=response_data, msg="认证密钥生成成功")
        
    except Exception as e:
        return response_2000(code=500, msg=f"生成认证密钥失败: {str(e)}")


@user_router.post("/{user_id}/auth-key/regenerate", 
                 dependencies=[Depends(check_permission(["sys:user:update"]))],
                 response_model=ResultModel[AuthKeyCreateResponse], 
                 summary="重新生成用户认证密钥")
async def regenerate_user_auth_key(
    user_id: int, 
    db: Session = Depends(get_db), 
    _user=Depends(get_active_user)
):
    """重新生成指定用户的认证密钥"""
    try:
        result = auth_key_service.regenerate_auth_key_for_user(db, user_id)
        
        if not result['success']:
            error_messages = {
                'USER_NOT_FOUND': '用户不存在',
                'USER_NO_TEAM': '用户未分配团队，无法生成密钥'
            }
            
            error_msg = error_messages.get(result['error'], f"重新生成失败: {result['error']}")
            return response_2000(code=400, msg=error_msg)
        
        # 获取用户团队ID用于响应
        user = users_db.get_one(db=db, id=user_id)
        team_id = auth_key_service.get_user_primary_team_id(db, user)
        
        response_data = AuthKeyCreateResponse(
            auth_key=result['auth_key'],
            status='active',
            user_id=user_id,
            team_id=team_id
        )
        
        return response_200(data=response_data, msg="认证密钥重新生成成功")
        
    except Exception as e:
        return response_2000(code=500, msg=f"重新生成认证密钥失败: {str(e)}")


@user_router.post("/{user_id}/auth-key/status", 
                  dependencies=[Depends(check_permission(["sys:user:update"]))],
                  response_model=ResultModel[AuthKeyUpdateResponse], 
                  summary="更新用户认证密钥状态")
async def update_user_auth_key_status(
    user_id: int, 
    request_data: AuthKeyUpdateRequest,
    db: Session = Depends(get_db), 
    _user=Depends(get_active_user)
):
    """更新指定用户的认证密钥状态"""
    try:
        result = auth_key_service.update_auth_key_status(db, user_id, request_data.status)
        
        if not result['success']:
            error_messages = {
                'USER_NOT_FOUND': '用户不存在',
                'AUTH_KEY_NOT_EXISTS': '用户尚未配置认证密钥',
                'INVALID_STATUS': '无效的状态值，只支持 active 或 disabled'
            }
            
            error_msg = error_messages.get(result['error'], f"状态更新失败: {result['error']}")
            return response_2000(code=400, msg=error_msg)
        
        # 获取更新后的用户信息
        user = users_db.get_one(db=db, id=user_id)
        
        response_data = AuthKeyUpdateResponse(
            auth_key=user.auth_key,
            status=request_data.status,
            updated=True
        )
        
        return response_200(data=response_data, msg=f"认证密钥已{request_data.status}")
        
    except Exception as e:
        return response_2000(code=500, msg=f"更新认证密钥状态失败: {str(e)}")


@user_router.delete("/{user_id}/auth-key", 
                   dependencies=[Depends(check_permission(["sys:user:update"]))],
                   response_model=ResultModel[AuthKeyDeleteResponse], 
                   summary="删除用户认证密钥")
async def delete_user_auth_key(
    user_id: int, 
    db: Session = Depends(get_db), 
    _user=Depends(get_active_user)
):
    """删除指定用户的认证密钥"""
    try:
        result = auth_key_service.delete_auth_key(db, user_id)
        
        if not result['success']:
            error_messages = {
                'USER_NOT_FOUND': '用户不存在'
            }
            
            error_msg = error_messages.get(result['error'], f"删除失败: {result['error']}")
            return response_2000(code=400, msg=error_msg)
        
        response_data = AuthKeyDeleteResponse(
            deleted=True,
            user_id=user_id
        )
        
        return response_200(data=response_data, msg="认证密钥删除成功")
        
    except Exception as e:
        return response_2000(code=500, msg=f"删除认证密钥失败: {str(e)}")


@user_router.post("/auth-keys/batch", 
                 dependencies=[Depends(check_permission(["sys:user:list"]))],
                 response_model=ResultModel[AuthKeyBatchQueryResponse], 
                 summary="批量查询用户认证密钥")
async def batch_query_auth_keys(
    request_data: AuthKeyBatchQueryRequest,
    db: Session = Depends(get_db), 
    _user=Depends(get_active_user)
):
    """批量查询用户认证密钥信息"""
    try:
        # 构建查询过滤条件
        filters = {}
        if request_data.team_id:
            # 通过团队ID过滤用户
            from apps.system.team.models import TeamUserLink
            team_user_links = db.query(TeamUserLink).filter(
                TeamUserLink.team_id == request_data.team_id
            ).all()
            user_ids = [link.user_id for link in team_user_links]
            if not user_ids:
                # 该团队没有用户
                return response_200(data=AuthKeyBatchQueryResponse(
                    total=0,
                    page=request_data.page,
                    size=request_data.size,
                    items=[]
                ))
            filters['id'] = user_ids
        
        if request_data.status:
            filters['key_status'] = request_data.status
        
        # 只查询有认证密钥的用户
        filters['auth_key__ne'] = None
        
        # 分页查询
        user_data = users_db.get_list(
            db=db, 
            page=request_data.page, 
            size=request_data.size,
            filters=filters
        )
        
        # 构建响应数据
        items = []
        for user in user_data['data']:
            # 获取用户团队ID
            team_id = auth_key_service.get_user_primary_team_id(db, user)
            
            # 脱敏处理认证密钥
            masked_key = f"{user.auth_key[:15]}..." if user.auth_key else None
            
            items.append(AuthKeyBatchItem(
                user_id=user.id,
                username=user.user_name,
                auth_key=masked_key,
                status=user.key_status or 'active',
                team_id=team_id or 0
            ))
        
        response_data = AuthKeyBatchQueryResponse(
            total=user_data['total'],
            page=request_data.page,
            size=request_data.size,
            items=items
        )
        
        return response_200(data=response_data)
        
    except Exception as e:
        return response_2000(code=500, msg=f"批量查询认证密钥失败: {str(e)}")
