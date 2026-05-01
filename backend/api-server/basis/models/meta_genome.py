from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from basis.db.db import Base

class GenomeMetadata(Base):
    __tablename__ = "genome_metadata"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    name = Column(String)
    file_count = Column(Integer)
    total_size = Column(Integer)
    modified_time = Column(DateTime)

    enhancements = relationship("GenomeMetadataEnhancement", back_populates="genome", cascade="all, delete")

class GenomeMetadataEnhancement(Base):
    __tablename__ = "genome_metadata_enhancement"

    id = Column(Integer, primary_key=True, index=True)
    genome_id = Column(Integer, ForeignKey("genome_metadata.id"))
    term_id = Column(String)
    term_name = Column(String)
    term_description = Column(Text)
    value = Column(String)

    genome = relationship("GenomeMetadata", back_populates="enhancements")