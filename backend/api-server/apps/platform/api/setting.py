import json
import os
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from apps.common.depends import get_active_user
from db.database import get_db
from libs.responses.response import response_200
from ..models import PlatformModelApiSetting, PlatformSiteSetting
from ..schemas import (
    FrpConfigUpdateRequest,
    PlatformModelApiCreateRequest,
    PlatformModelApiDeleteRequest,
    PlatformModelApiListRequest,
    PlatformModelApiSetPrimaryRequest,
    PlatformModelApiUpdateRequest,
    PlatformSiteSettingInfoRequest,
    PlatformSiteSettingUpdateRequest,
)
from apps.platform.frp_service import start_frpc, stop_frpc, get_frpc_status

setting_router = APIRouter(tags=["app:platform:平台设置"])


def _require_platform_admin(user):
    if getattr(user, "is_superman", False) or int(getattr(user, "user_type", 0) or 0) == 1:
        return
    raise HTTPException(status_code=4030, detail="没有权限")


def _normalize_json_text(text_value: str | None) -> str:
    raw = (text_value or "").strip()
    if not raw:
        return "{}"
    try:
        return json.dumps(json.loads(raw), ensure_ascii=False)
    except Exception:
        return raw


def _serialize_site_setting(setting_obj: PlatformSiteSetting):
    data = setting_obj.to_dict()
    return data


def _serialize_model_api(setting_obj: PlatformModelApiSetting):
    data = setting_obj.to_dict()
    api_key = data.get("api_key") or ""
    if api_key:
        if len(api_key) <= 8:
            data["api_key_masked"] = "*" * len(api_key)
        else:
            data["api_key_masked"] = f"{api_key[:4]}...{api_key[-4:]}"
    else:
        data["api_key_masked"] = ""
    return data


@setting_router.post("/setting/site/info", summary="平台网站配置详情")
async def site_info(
    request_data: PlatformSiteSettingInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    site_obj = db.query(PlatformSiteSetting).order_by(PlatformSiteSetting.id.asc()).first()
    if not site_obj:
        site_obj = PlatformSiteSetting(
            site_name="",
            site_title="",
            filing_no="",
            domain="",
            ip_address="",
            port=0,
            extra_json="{}",
            user_id=_user.id,
        )
        db.add(site_obj)
        db.commit()
        db.refresh(site_obj)
    return response_200(data=_serialize_site_setting(site_obj))


@setting_router.post("/setting/site/update", summary="更新平台网站配置")
async def site_update(
    request_data: PlatformSiteSettingUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    now = int(time.time())
    site_obj = db.query(PlatformSiteSetting).order_by(PlatformSiteSetting.id.asc()).first()
    if not site_obj:
        site_obj = PlatformSiteSetting(create_time=now)
        db.add(site_obj)
    site_obj.site_name = request_data.site_name or ""
    site_obj.site_title = request_data.site_title or ""
    site_obj.filing_no = request_data.filing_no or ""
    site_obj.domain = request_data.domain or ""
    site_obj.ip_address = request_data.ip_address or ""
    site_obj.port = int(request_data.port or 0)
    site_obj.extra_json = _normalize_json_text(request_data.extra_json)
    site_obj.user_id = _user.id
    site_obj.update_time = now
    db.add(site_obj)
    db.commit()
    db.refresh(site_obj)
    return response_200(data=_serialize_site_setting(site_obj))


@setting_router.post("/setting/model/list", summary="模型API配置列表")
async def model_list(
    request_data: PlatformModelApiListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    query = db.query(PlatformModelApiSetting)
    if request_data.active_only:
        query = query.filter(PlatformModelApiSetting.is_active == True)  # noqa: E712
    rows = (
        query.order_by(
            PlatformModelApiSetting.is_primary.desc(),
            PlatformModelApiSetting.sort_order.asc(),
            PlatformModelApiSetting.id.asc(),
        ).all()
    )
    return response_200(data={"items": [_serialize_model_api(item) for item in rows]})


@setting_router.post("/setting/model/create", summary="新增模型API配置")
async def model_create(
    request_data: PlatformModelApiCreateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    now = int(time.time())
    if request_data.is_primary:
        db.query(PlatformModelApiSetting).update({"is_primary": False})
    setting_obj = PlatformModelApiSetting(
        provider_code=request_data.provider_code.strip(),
        provider_name=request_data.provider_name.strip(),
        model_name=request_data.model_name.strip(),
        api_base_url=request_data.api_base_url.strip(),
        api_key=request_data.api_key.strip(),
        is_primary=bool(request_data.is_primary),
        is_active=bool(request_data.is_active),
        sort_order=int(request_data.sort_order or 0),
        remark=(request_data.remark or "").strip(),
        extra_json=_normalize_json_text(request_data.extra_json),
        create_time=now,
        update_time=now,
        user_id=_user.id,
    )
    db.add(setting_obj)
    db.commit()
    db.refresh(setting_obj)
    return response_200(data=_serialize_model_api(setting_obj))


@setting_router.post("/setting/model/update", summary="更新模型API配置")
async def model_update(
    request_data: PlatformModelApiUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    setting_obj = db.query(PlatformModelApiSetting).filter(PlatformModelApiSetting.id == request_data.id).first()
    if not setting_obj:
        raise HTTPException(status_code=4004, detail="模型API配置不存在")
    if request_data.is_primary:
        db.query(PlatformModelApiSetting).filter(PlatformModelApiSetting.id != request_data.id).update({"is_primary": False})
    setting_obj.provider_code = request_data.provider_code.strip()
    setting_obj.provider_name = request_data.provider_name.strip()
    setting_obj.model_name = request_data.model_name.strip()
    setting_obj.api_base_url = request_data.api_base_url.strip()
    setting_obj.api_key = request_data.api_key.strip()
    setting_obj.is_primary = bool(request_data.is_primary)
    setting_obj.is_active = bool(request_data.is_active)
    setting_obj.sort_order = int(request_data.sort_order or 0)
    setting_obj.remark = (request_data.remark or "").strip()
    setting_obj.extra_json = _normalize_json_text(request_data.extra_json)
    setting_obj.update_time = int(time.time())
    setting_obj.user_id = _user.id
    db.add(setting_obj)
    db.commit()
    db.refresh(setting_obj)
    return response_200(data=_serialize_model_api(setting_obj))


@setting_router.post("/setting/model/delete", summary="删除模型API配置")
async def model_delete(
    request_data: PlatformModelApiDeleteRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    setting_obj = db.query(PlatformModelApiSetting).filter(PlatformModelApiSetting.id == request_data.id).first()
    if not setting_obj:
        return response_200(data={})
    db.delete(setting_obj)
    db.commit()
    remaining = (
        db.query(PlatformModelApiSetting)
        .order_by(PlatformModelApiSetting.sort_order.asc(), PlatformModelApiSetting.id.asc())
        .all()
    )
    if remaining and not any(item.is_primary for item in remaining):
        remaining[0].is_primary = True
        remaining[0].update_time = int(time.time())
        db.add(remaining[0])
        db.commit()
    return response_200(data={})


@setting_router.post("/setting/model/set-primary", summary="设置主模型API配置")
async def model_set_primary(
    request_data: PlatformModelApiSetPrimaryRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    setting_obj = db.query(PlatformModelApiSetting).filter(PlatformModelApiSetting.id == request_data.id).first()
    if not setting_obj:
        raise HTTPException(status_code=4004, detail="模型API配置不存在")
    db.query(PlatformModelApiSetting).update({"is_primary": False})
    setting_obj.is_primary = True
    setting_obj.update_time = int(time.time())
    setting_obj.user_id = _user.id
    db.add(setting_obj)
    db.commit()
    db.refresh(setting_obj)
    return response_200(data=_serialize_model_api(setting_obj))


# ---------------------------------------------------------------------------
# FRP Tunnel Management
# ---------------------------------------------------------------------------


@setting_router.post("/frp/config/update", summary="更新FRP隧道配置")
async def frp_config_update(
    request_data: FrpConfigUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    site = db.query(PlatformSiteSetting).order_by(PlatformSiteSetting.id.asc()).first()
    if not site:
        now = int(time.time())
        site = PlatformSiteSetting(create_time=now, user_id=_user.id)
        db.add(site)
    update_data = request_data.model_dump(exclude_unset=True)
    for field_name, field_value in update_data.items():
        setattr(site, field_name, field_value)
    site.update_time = int(time.time())
    site.user_id = _user.id
    db.add(site)
    db.commit()
    db.refresh(site)
    return response_200(data=_serialize_site_setting(site))


@setting_router.post("/frp/start", summary="启动FRP隧道")
async def frp_start(
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    site = db.query(PlatformSiteSetting).order_by(PlatformSiteSetting.id.asc()).first()
    if not site:
        return response_200(code=4000, msg="请先配置FRP隧道参数", data={})
    result = start_frpc(site)
    if result.get("frp_status") == "error":
        site.frp_status = "error"
        db.add(site)
        db.commit()
        return response_200(code=4000, msg=result.get("error", "启动失败"), data=result)
    site.frp_status = result.get("frp_status", "running")
    site.update_time = int(time.time())
    db.add(site)
    db.commit()
    return response_200(data=result)


@setting_router.post("/frp/stop", summary="停止FRP隧道")
async def frp_stop(
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    _require_platform_admin(_user)
    result = stop_frpc()
    site = db.query(PlatformSiteSetting).order_by(PlatformSiteSetting.id.asc()).first()
    if site:
        site.frp_status = "stopped"
        site.update_time = int(time.time())
        db.add(site)
        db.commit()
    return response_200(data=result)


@setting_router.post("/frp/status", summary="查询FRP隧道状态")
async def frp_status(
    db=Depends(get_db),
):
    site = db.query(PlatformSiteSetting).order_by(PlatformSiteSetting.id.asc()).first()
    if not site:
        return response_200(data={"frp_status": "stopped", "pid": None, "public_url": None, "api_url": None, "last_error": None, "uptime_seconds": None})
    result = get_frpc_status(site)
    site.frp_status = result.get("frp_status", "stopped")
    db.add(site)
    db.commit()
    return response_200(data=result)


@setting_router.get("/frp/install-script", summary="下载frps安装脚本")
async def frp_install_script():
    script_path = os.path.realpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "static", "install-frps.sh")
    )
    if not os.path.isfile(script_path):
        raise HTTPException(status_code=404, detail="安装脚本不存在")
    return FileResponse(script_path, media_type="text/plain", filename="install-frps.sh")
