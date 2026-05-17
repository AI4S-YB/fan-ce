from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from omics.db import SessionLocal
from models.meta_file import FileMetadata, FileMetadataEnhancement
from schemas.meta_file import FilePathInput, EnhancementCreate, FileMetadataOut, EnhancementOut
from core.meta_utils import extract_basic_metadata

# 创建 APIRouter 实例
router = APIRouter(
    prefix="/metadata",
    tags=["FAN-CE API / Metadata"]
)

# 获取数据库 Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/file/", response_model=FileMetadataOut)
def add_file_metadata(file: FilePathInput, db: Session = Depends(get_db)):
    if db.query(FileMetadata).filter_by(path=file.path).first():
        raise HTTPException(status_code=400, detail="该路径已存在")

    try:
        meta = extract_basic_metadata(file.path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    new_meta = FileMetadata(**meta)
    db.add(new_meta)
    db.commit()
    db.refresh(new_meta)
    return new_meta

@router.post("/file/{file_id}/enhancement/", response_model=EnhancementOut)
def add_enhancement(file_id: int, enh: EnhancementCreate, db: Session = Depends(get_db)):
    # Check if file exists
    file = db.query(FileMetadata).filter_by(id=file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")

    # Create enhancement items
    enhancement_objects = []
    for enhancement_item in enh.enhancements:
        enh_obj = FileMetadataEnhancement(
            file_id=file_id,
            term_id=enhancement_item.term_id,
            term_name=enhancement_item.term_name,
            term_description=enhancement_item.term_description,
            value=enhancement_item.value
        )
        enhancement_objects.append(enh_obj)

    # Add all enhancement objects to database
    db.add_all(enhancement_objects)
    db.commit()
    
    # Refresh all objects to get their IDs
    for obj in enhancement_objects:
        db.refresh(obj)

    # Return in expected format
    return EnhancementOut(enhancements=enhancement_objects)
    

@router.get("/files/", response_model=list[FileMetadataOut])
def list_metadata(db: Session = Depends(get_db)):
    return db.query(FileMetadata).all()

@router.get("/file/{file_id}", response_model=FileMetadataOut)
def get_file_metadata(file_id: int, db: Session = Depends(get_db)):
    file = db.query(FileMetadata).filter_by(id=file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file