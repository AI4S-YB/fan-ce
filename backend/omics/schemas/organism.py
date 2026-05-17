from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class OrganismCreateModel(BaseModel):
    tax_id: int = Field(..., title="Taxonomy ID", description="The unique NCBI taxonomy identifier")
    scientific_name: str = Field(..., title="Scientific Name", description="The official scientific name of the organism")
    common_name: Optional[str] = Field(None, title="Common Name", description="The common name of the organism")
    rank: str = Field(..., title="Taxonomic Rank", description="The taxonomic rank of the organism (e.g., species, genus)")
    parent_tax_id: Optional[int] = Field(None, title="Parent Taxonomy ID", description="The Taxonomy ID of the parent organism")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tax_id": 9606,
                "scientific_name": "Homo sapiens",
                "common_name": "Human",
                "rank": "species",
                "parent_tax_id": 9605
            }
        }
    )
class OrganismResponseModel(BaseModel):
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
    tax_id: int = Field(..., title="Taxonomy ID", description="The unique NCBI taxonomy identifier")
    scientific_name: str = Field(..., title="Scientific Name", description="The official scientific name of the organism")
    common_name: Optional[str] = Field(None, title="Common Name", description="The common name of the organism")
    rank: str = Field(..., title="Taxonomic Rank", description="The taxonomic rank of the organism (e.g., species, genus)")
    parent_tax_id: Optional[int] = Field(None, title="Parent Taxonomy ID", description="The Taxonomy ID of the parent organism")
    created_at: str = Field(..., title="Date Created", description="The date when the organism was added to the system")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tax_id": 9606,
                "scientific_name": "Homo sapiens",
                "common_name": "Human",
                "rank": "species",
                "parent_tax_id": 9605,
                "created_at": "2024-09-28T10:30:00Z"
            }
        }
        
    )
class OrganismUpdateModel(BaseModel):
    scientific_name: Optional[str] = Field(None, title="Scientific Name", description="The official scientific name of the organism")
    common_name: Optional[str] = Field(None, title="Common Name", description="The common name of the organism")
    rank: Optional[str] = Field(None, title="Taxonomic Rank", description="The taxonomic rank of the organism (e.g., species, genus)")
    parent_tax_id: Optional[int] = Field(None, title="Parent Taxonomy ID", description="The Taxonomy ID of the parent organism")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scientific_name": "Homo sapiens sapiens",
                "common_name": "Modern Human",
                "rank": "subspecies"
            }
        }
    )
class OrganismDeleteModel(BaseModel):
    message: str = Field(..., title="Delete Confirmation Message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Organism with Taxonomy ID 9606 deleted successfully."
            }
        }
    )
###################### 
# Model for taxonomy #
######################

class TaxonomyResponseModel(BaseModel):
    tax_id: int = Field(..., title="Taxonomy ID", description="The unique identifier for the organism in the taxonomy database")
    scientific_name: str = Field(..., title="Scientific Name", description="The official scientific name of the organism")
    common_name: Optional[str] = Field(None, title="Common Name", description="The common name of the organism, if available")
    rank: str = Field(..., title="Taxonomic Rank", description="The taxonomic rank of the organism (e.g., species, genus)")
    parent_tax_id: Optional[int] = Field(None, title="Parent Taxonomy ID", description="The taxonomy ID of the parent organism")
    lineage: str = Field(..., title="Taxonomic Lineage", description="The full taxonomic lineage of the organism")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tax_id": 9606,
                "scientific_name": "Homo sapiens",
                "common_name": "Human",
                "rank": "species",
                "parent_tax_id": 9605,
                "lineage": "Eukaryota; Metazoa; Chordata; Mammalia; Primates; Hominidae; Homo"
            }
        }
    )
class TaxonomySearchModel(BaseModel):
    keyword: str = Field(..., title="Search Keyword", description="The keyword used to search for organisms in the taxonomy database")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "keyword": "homo"
            }
        }
    )
