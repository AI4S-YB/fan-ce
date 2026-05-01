from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from enum import Enum

#class MultiOmicsData(BaseModel):
#    omics_type: str = Field(..., example="genomics")
#    sample_id: str = Field(..., example="S12345")
#    data: List[float] = Field(..., example=[0.1, 0.2, 0.3])
#    description: Optional[str] = Field(None, example="This is a test description")


# https://docs.gdc.cancer.gov/API/Users_Guide/Data_Analysis/

# 权限级别的枚举类
class AccessLevel(str, Enum):
    public = "public"  # 公开
    private = "private"  # 私有
    restricted = "restricted"  # 仅限特定用户组

# 基因组基础模型
class GenomeBaseModel(BaseModel):
    id: str = Field(default='370101', title="Genome ID")


# 基因组创建模型
class GenomeCreateModel(BaseModel):
    organism_id: str
    taxid: str = Field(..., title="Taxonomy ID", description="分类学ID，例如NCBI物种编号")  # 必填项
    genome_sequences: str = Field(..., title="FASTA File Path", description="基因组的FASTA序列文件路径")  # 必填项
    gene_annotation: str = Field(..., title="GFF File Path", description="基因组注释的GFF文件路径")  # 必填项 
    version: str = Field(..., title="Genome Version", description="基因组的版本号，例如v1.0")  # 必填项
    article_ids: List[str] = Field(..., title="Associated Article IDs", description="与基因组数据相关的文章ID列表")  # 可关联的文章
    created_by: str = Field(..., title="User ID", description="创建人用户ID")  # 创建人
    access_level: AccessLevel = Field(..., title="Access Level", description="数据使用权限，公开或仅限自己可见")  # 数据使用权限

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "genome_sequences": "/path/to/genome.fasta",
                "gene_annotation": "/path/to/gene_models.gff",
                "taxid": "3702",
                "version": "v1.0",
                "article_ids": ["P12345", "P67890"],
                "created_by": "user_001",
                "access_level": "public"
            }
        }
    )
# 基因组响应模型
class GenomeResponseModel(BaseModel):
    genome_id: str = Field(
        ..., 
        title="Genome ID", 
        description="基因组的唯一标识符"
    )
    taxid: str = Field(
        ..., 
        title="Taxonomy ID", 
        description="物种的分类学ID，例如NCBI物种编号"
    )
    order: str = Field(
        ..., 
        title="Plant order name", 
        description="植物的目名称"
    )
    family: str = Field(
        ..., 
        title="Plant family name", 
        description="植物的科名称"
    )
    genus: str = Field(
        ..., 
        title="Plant genus name", 
        description="植物的属名称"
    )
    species: str = Field(
        ..., 
        title="Plant species", 
        description="植物的种名称"
    )
    subspecies: str = Field(
        ..., 
        title="Plant subspecies", 
        description="植物的亚种名称"
    )
    cultivar: str = Field(
        ..., 
        title="Plant cultivar", 
        description="植物的栽培品种名称"
    )
    variety: str = Field(
        ..., 
        title="Plant variety", 
        description="植物的变种名称"
    )
    ecotype: str = Field(
        ..., 
        title="Plant ecotype", 
        description="植物的生态型"
    )
    scientific_name: str = Field(
        ..., 
        title="Scientific name", 
        description="植物的科学名称"
    )
    common_name: str = Field(
        ..., 
        title="Plant common name", 
        description="植物的俗称"
    )
    genome_seq_num: int = Field(
        ..., 
        title="Number of chromosome/scaffolds", 
        description="基因组中染色体或支架的数量"
    )
    genome_size: float = Field(
        ..., 
        title="Genome size (Mb)", 
        description="基因组的大小，以百万碱基对（Mb）为单位"
    )
    gene_num: int = Field(
        ..., 
        title="Number of genes", 
        description="基因的数量"
    )
    mrna_num: int = Field(
        ..., 
        title="Number of mRNAs", 
        description="mRNA的数量"
    )
    cds_num: int = Field(
        ..., 
        title="Number of coding sequences", 
        description="编码序列（CDS）的数量"
    )
    pep_num: int = Field(
        ..., 
        title="Number of proteins", 
        description="蛋白质的数量"
    )
    version: str = Field(
        ..., 
        title="Genome/Annotation version", 
        description="基因组或功能注释的版本号"
    )
    haplotype_resolved: str = Field(
        ..., 
        title="Is the genome Haplotype resolved?", 
        description="基因组是否为单倍型解析"
    )
    ploidy: str = Field(
        ..., 
        title="Genome ploidy", 
        description="基因组的倍性，例如二倍体或三倍体"
    )
    publication: str = Field(
        ..., 
        title="PubMed ID", 
        description="与基因组相关的文献的PubMed ID"
    )
    doi: str = Field(
        ..., 
        title="DOI: digital object identifier", 
        description="文献的数字对象标识符 (DOI)"
    )
    pub_title: str = Field(
        ..., 
        title="Title (Publication)", 
        description="与基因组相关的文献标题"
    )
    pub_abstract: str = Field(
        ..., 
        title="Abstract (Publication)", 
        description="与基因组相关的文献摘要"
    )
    pub_authors: str = Field(
        ..., 
        title="Authors (Publication)", 
        description="与基因组相关的文献作者列表"
    )
    pub_journal: str = Field(
        ..., 
        title="Journal (Publication)", 
        description="发表文献的期刊名称"
    )
    pub_date: str = Field(
        ..., 
        title="Date (Publication)", 
        description="文献的发表日期"
    )
    download: str = Field(
        ..., 
        title="Download code/address", 
        description="基因组数据的下载代码或地址"
    )
    image: str = Field(
        ..., 
        title="Path to plant image", 
        description="植物图像的文件路径"
    )

    # 配置 json_schema_extra 以提供示例数据
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "370101",
                "taxid": "3702",
                "order": "Brassicales",
                "family": "Brassicaceae",
                "genus": "Arabidopsis",
                "species": "thaliana",
                "subspecies": "unknown",
                "cultivar": "unknown",
                "variety": "unknown",
                "ecotype": "Columbia-0 (Col-0)",
                "scientific_name": "Arabidopsis thaliana",
                "common_name": "Arabidopsis",
                "genome_seq_num": 7,
                "genome_size": 119.67,
                "gene_num": 27654,
                "mrna_num": 48455,
                "cds_num": 48455,
                "pep_num": 48455,
                "ver": "P_Araport11",
                "haplotype_resolved": "No",
                "ploidy": "diploid",
                "publication": "27862469",
                "doi": "https://doi.org/10.1111/tpj.13415",
                "pub_title": "Araport11: a complete reannotation of the Arabidopsis thaliana reference genome.",
                "pub_abstract": "The flowering plant Arabidopsis thaliana is a dicot model organism ......",
                "pub_authors": "Cheng CY; Krishnakumar V; Chan AP; Thibaud-Nissen F; Schobel S; Town CD",
                "pub_journal": "Plant J",
                "pub_date": "2017 Feb",
                "download": "d10f885644082aac",
                "image": "/path/to/image.jpg"
            }
        }
        
    )
# 基因组更新模型
class GenomeUpdateModel(BaseModel):
    id: str = Field(default='370101', title="Genome ID")


# 基因组删除模型
class GenomeDeleteModel(BaseModel):
    id: str = Field(default='370101', title="Genome ID")