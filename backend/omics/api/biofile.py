from fastapi import APIRouter, UploadFile, File, Query
from typing import Literal, List, Tuple
from pathlib import Path
import tempfile, shutil, os

from omics.schemas.biofile import PathRequest, AnalyzeResponse, BatchAnalyzeResponse
from omics.core.biofile.detector import detect_path
from omics.core.biofile.analyze import analyze_file
from shared.responses import response_200

biofile_router = APIRouter(prefix="/omics/biofile", tags=["omics:biofile"])


@biofile_router.post("/analyze-local-file")
def analyze_local_file(request: PathRequest):
    """
    分析本地文件
    
    Args:
        request: 包含本地文件路径的请求
        
    Returns:
        标准响应格式包装的文件分析结果，包含检测信息和元数据
    """
    result = analyze_file(request.path)
    return response_200(data=AnalyzeResponse(**result).dict())

@biofile_router.post("/analyze-local-directory")
def analyze_local_directory(request: PathRequest):
    """
    分析本地文件夹下的所有文件
    
    Args:
        request: 包含本地文件夹路径的请求
        
    Returns:
        标准响应格式包装的批量文件分析结果
    """
    import glob
    
    # 检查文件夹是否存在
    if not os.path.isdir(request.path):
        raise ValueError(f"Directory not found: {request.path}")
    
    # 获取文件夹下所有文件（不包括子文件夹）
    file_pattern = os.path.join(request.path, "*")
    all_paths = glob.glob(file_pattern)
    file_paths = [p for p in all_paths if os.path.isfile(p)]
    
    # 分析每个文件
    results = []
    for file_path in file_paths:
        try:
            result = analyze_file(file_path)
            results.append(AnalyzeResponse(**result))
        except Exception as e:
            # 如果某个文件分析失败，跳过该文件但记录错误
            print(f"Failed to analyze {file_path}: {str(e)}")
            continue
    
    batch_result = BatchAnalyzeResponse(
        items=results,
        total_files=len(results),
        directory_path=request.path
    )
    
    return response_200(data=batch_result.dict())

def _persist_upload_to_temp(upload: UploadFile) -> str:
    """
    将上传的文件保存到临时文件
    
    保留原始文件扩展名，便于检测规则根据扩展名进行加权评分。
    
    Args:
        upload: FastAPI UploadFile 对象
        
    Returns:
        str: 临时文件的绝对路径
        
    Note:
        - 临时文件会在处理完成后自动删除
        - 保留文件扩展名有助于提高检测准确性
    """
    suffix = Path(upload.filename).suffix if upload.filename else ""
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="upload_")
    os.close(fd)  # 仅拿路径，实际写入用普通 open
    with open(tmp_path, "wb") as out:
        # 直接从 UploadFile.file（SpooledTemporaryFile）流式拷贝到磁盘
        shutil.copyfileobj(upload.file, out)
    return tmp_path

def _persist_uploads_to_temp_dir(uploads: List[UploadFile]) -> Tuple[str, List[str]]:
    """
    将多个上传文件保存到同一个临时目录
    
    保留原始文件名，便于sidecar文件检测。
    
    Args:
        uploads: FastAPI UploadFile 对象列表
        
    Returns:
        Tuple[str, List[str]]: (临时目录路径, 文件路径列表)
        
    Note:
        - 所有文件保存在同一临时目录中
        - 保留原始文件名有助于sidecar文件检测
        - 临时目录和文件会在处理完成后自动删除
    """
    temp_dir = tempfile.mkdtemp(prefix="upload_batch_")
    file_paths = []
    
    for upload in uploads:
        # 保留原始文件名
        filename = upload.filename if upload.filename else f"unnamed_{len(file_paths)}"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, "wb") as out:
            shutil.copyfileobj(upload.file, out)
        file_paths.append(file_path)
    
    return temp_dir, file_paths

@biofile_router.post("/analyze-single-file")
def analyze_single_file(file: UploadFile = File(...),):
    """
    单文件分析（原有功能保持不变）
    
    Args:
        file: 上传的文件
        
    Returns:
        标准响应格式包装的文件分析结果，包含检测信息和元数据
    """
    tmp_path = _persist_upload_to_temp(file)
    try:
        result = analyze_file(tmp_path)
        return response_200(data=AnalyzeResponse(**result).dict())
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

@biofile_router.post("/analyze-batch-file")
def analyze_batch_file(files: List[UploadFile] = File(...),):
    """
    批量文件分析
    
    Args:
        files: 上传的多个文件列表
        
    Returns:
        标准响应格式包装的批量文件分析结果
    """
    results = []
    tmps: List[str] = []
    
    try:
        for file in files:
            tmp_path = _persist_upload_to_temp(file)
            tmps.append(tmp_path)
            
            try:
                result = analyze_file(tmp_path)
                results.append(AnalyzeResponse(**result))
            except Exception as e:
                # 如果某个文件分析失败，跳过该文件但记录错误
                print(f"Failed to analyze {file.filename}: {str(e)}")
                continue
        
        batch_result = BatchAnalyzeResponse(
            items=results,
            total_files=len(results),
            directory_path="uploaded_files"  # 对于上传文件，使用固定标识
        )
        
        return response_200(data=batch_result.dict())
    finally:
        # 清理所有临时文件
        for tmp_path in tmps:
            try:
                os.remove(tmp_path)
            except OSError:
                pass