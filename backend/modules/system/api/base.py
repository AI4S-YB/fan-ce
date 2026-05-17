# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/9/23 10:20
@Function:
@version :  1.0
@Desc    :  None
"""
import os
from fastapi import APIRouter, Depends, Request
from starlette.responses import FileResponse
from fastapi import APIRouter, Depends, UploadFile, File, Query
from shared.responses import response_200, response_200
from starlette.background import BackgroundTask
from fastapi.encoders import jsonable_encoder
from modules.common.security import check_token
from shared.database import get_db
from shared.responses import response_200

base_router = APIRouter()


@base_router.get("/down/{token}", summary='批量文件打包下载')
async def charts_list(token: str = None):
    """批量文件打包下载"""
    payload = check_token(token=token)
    file_path = payload.get('url')
    return FileResponse(file_path, filename=os.path.split(file_path)[-1], background=BackgroundTask(lambda: os.remove(file_path)))


@base_router.get("/down/file/{token}", summary='文件下载')
async def charts_list(token: str = None):
    """文件下载"""

    payload = check_token(token=token)
    file_path = payload.get('url')
    is_rm = payload.get('is_rm')
    if is_rm:
        return FileResponse(file_path, filename=os.path.split(file_path)[-1], background=BackgroundTask(lambda: os.remove(file_path)))
    else:
        return FileResponse(file_path, filename=os.path.split(file_path)[-1])


@base_router.get("/task/template", summary='文件模板下载')
async def template_list():
    """文件模板下载"""
    file_path = 'template.xlsx'
    return FileResponse(file_path, filename='template.xlsx')


@base_router.get("/file/info")
async def get_pdf1():
    """文件下载或预览"""
    print('cccc=======')
    is_down = False
    file_path = "/tmp/example.docx"
    # if is_down:
    headers = {
        "Content-Disposition": "inline; filename=3.docx"
    }
    return FileResponse(file_path, media_type='application/msword', headers=headers)

    # return FileResponse(file_path, media_type='application/msword', filename="3.docx")


@base_router.post("/file/callback")
async def get_pdf(request: Request):
    """文件下载或预览"""
    print('callback')
    print(await request.body())
    is_down = False

    file_path = "/tmp/example.docx"
    # if is_down:
    #     headers = {
    #         "Content-Disposition": "inline; filename=3.docx"
    #     }
    #     return FileResponse(file_path, media_type='application/msword', headers=headers)
    # else:
    #     return FileResponse(file_path, media_type='application/msword', filename="3.docx")
    return response_200(data={})

@base_router.post("/file/")
async def get_pdf():
    """文件下载或预览"""
    is_down = False
    file_path = "/tmp/example.docx"
    if is_down:
        headers = {
            "Content-Disposition": "inline; filename=12.pdf"
        }
        return FileResponse(file_path, media_type='application/pdf', headers=headers)
    else:
        return FileResponse(file_path, media_type='application/pdf', filename="file.pdf")


# @base_router.post('/file/upload', summary="文件上传")
# async def file_upload_info(id: int = Form(None), type: str = Form(None), file: UploadFile = Form(...), db=Depends(get_db)):
#     """文件上传"""
#     journal_obj = journal_db.get_one(db=db, id=int(id))
#     file_dir = settings.IMAGE_PATH
#     file_name = f'{journal_obj.code}.' + file.filename.split('.')[-1]
#     file_path = os.path.join(file_dir, file_name)
#     cont = await file.read()
#     with open(file_path, 'wb') as f:
#         f.write(cont)
#     journal_db.update(db=db, db_obj=journal_obj, obj_in={'image_path': file_name})
#     return respon_200(data='')
#
#
# @base_router.post("/template/down", summary='report下载')
# async def report_down(request_data: DownExpFile):
#     """模板下载"""
#     file_path = settings.TEMPLATE_PATH
#     file = os.path.join(file_path, 'literature.xls')
#     if request_data.type == "literature":
#         file = os.path.join(file_path, 'literature.xls')
#     if request_data.type == "authors":
#         file = os.path.join(file_path, 'authors.xlsx')
#     token = create_token(subject={'url': file, 'is_rm': False})
#     data = {"url": f"/api/v1/down/file/{token}"}
#     return respon_200(data=data)


@base_router.get("/version", summary='版本')
async def version_get(db=Depends(get_db)):
    """版本显示"""
    return response_200(data="versions")
