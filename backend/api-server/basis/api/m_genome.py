from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import logging
import uuid
from typing import Dict, Any

from basis.core.meta_utils import extract_genome_metadata
from basis.core.genome_utils import process_genome_files
from basis.db.db import SessionLocal
from basis.models.meta_genome import GenomeMetadata, GenomeMetadataEnhancement
from basis.schemas.meta_genome import *

# 配置logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 简单的内存缓存实现
class SimpleCache:
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def get(self, key: str) -> Any:
        return self._cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value
    
    def delete(self, key: str) -> None:
        self._cache.pop(key, None)

# 创建缓存实例
cache = SimpleCache()

# 创建 APIRouter 实例
genome_router = APIRouter(
    prefix="/omics/genome",
    tags=["omics:genome"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@genome_router.post("/process", response_model=dict, 
    summary="Process genome data asynchronously")
async def process_genome(request: GenomeProcessRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    
    # Check if genome path already exists
    '''
    try:
        existing_genome = db.query(GenomeMetadata).filter_by(path=request.path).first()
        if existing_genome:
            raise HTTPException(status_code=400, detail="Path already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")
    '''

    # Create a task status entry
    task_id = str(uuid.uuid4())
    status = {
        "task_id": task_id,
        "status": "processing",
        "message": "Genome processing started"
    }
    
    #  With error handling
    try:
        background_tasks.add_task(process_genome_files, task_id, request.genome_path, request.operation)
        logger.info(f"Background task {task_id} started successfully")
    except Exception as e:
        logger.error(f"Failed to start background task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start processing")

    return status


@genome_router.get("/status/{task_id}", response_model=dict)
async def get_processing_status(task_id: str):
    status = cache.get(f"genome_task_{task_id}")
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status


@genome_router.get("/list", response_model=list)
def get_genome_list(db: Session = Depends(get_db)):
    """获取所有基因组列表，用于下拉选择器"""
    try:
        genomes = db.query(GenomeMetadata).all()
        genome_list = []
        for genome in genomes:
            # 从enhancements中提取物种名称作为显示名称
            species_name = next((e.value for e in genome.enhancements if e.term_id == "meta:species"), f"基因组{genome.id}")
            genome_list.append({
                "value": str(genome.id),
                "label": f"{species_name} ({genome.name})" if genome.name else species_name,
                "id": genome.id,
                "name": genome.name,
                "path": genome.path
            })
        return genome_list
    except Exception as e:
        logger.error(f"Failed to get genome list: {str(e)}")
        return []


@genome_router.get("/{genome_id}", response_model=GenomeMetadataOut)
def get_genome_metadata(genome_id: int, db: Session = Depends(get_db)):
    genome = db.query(GenomeMetadata).filter_by(id=genome_id).first()
    if not genome:
        raise HTTPException(status_code=404, detail="Genome not found")
    return genome
