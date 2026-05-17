from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from omics.db import Base

class FileMetadata(Base):
    __tablename__ = "file_metadata"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    name = Column(String)
    size = Column(Integer)
    modified_time = Column(DateTime)

    enhancements = relationship("FileMetadataEnhancement", back_populates="file", cascade="all, delete")

class FileMetadataEnhancement(Base):
    __tablename__ = "file_metadata_enhancement"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("file_metadata.id"))
    term_id = Column(String)
    term_name = Column(String)
    term_description = Column(Text)
    value = Column(String)

    file = relationship("FileMetadata", back_populates="enhancements")
