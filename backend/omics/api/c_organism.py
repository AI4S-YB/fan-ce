from fastapi import APIRouter, HTTPException

from omics.schemas.organism import (
    OrganismCreateModel, OrganismResponseModel,
    OrganismUpdateModel, OrganismDeleteModel,
    TaxonomyResponseModel, TaxonomySearchModel
)

# 创建 APIRouter 实例
router = APIRouter(
    prefix="/metadata",
    tags=["FAN-CE API / Metadata"]
)

# In-memory storage for demonstration purposes
organism_storage = {}
taxonomy_storage = {
    9606: {
        "tax_id": 9606,
        "scientific_name": "Homo sapiens",
        "common_name": "Human",
        "rank": "species",
        "parent_tax_id": 9605,
        "lineage": "Eukaryota; Metazoa; Chordata; Mammalia; Primates; Hominidae; Homo"
    },
    9605: {
        "tax_id": 9605,
        "scientific_name": "Homo",
        "common_name": None,
        "rank": "genus",
        "parent_tax_id": 9604,
        "lineage": "Eukaryota; Metazoa; Chordata; Mammalia; Primates; Hominidae"
    }
}


# Create Organism
@router.post("/organism", response_model=OrganismResponseModel, summary="Create a new Organism")
async def create_organism(data: OrganismCreateModel):
    if data.tax_id in organism_storage:
        raise HTTPException(status_code=400, detail=f"Organism with Taxonomy ID {data.tax_id} already exists.")

    organism_storage[data.tax_id] = {**data.dict(), "created_at": "2024-09-28T10:30:00Z"}
    return {"message": "Organism created successfully", "data": organism_storage[data.tax_id]}


# Get Organism by Taxonomy ID
@router.get("/organism/{organism_id}", response_model=OrganismResponseModel, summary="Retrieve Organism by Taxonomy ID")
async def get_organism(tax_id: int):
    if tax_id not in organism_storage:
        raise HTTPException(status_code=404, detail=f"Organism with Taxonomy ID {tax_id} not found.")

    return {"message": "Organism found", "data": organism_storage[tax_id]}


# Update Organism by Taxonomy ID
@router.put("/organism/{organism_id}", response_model=OrganismResponseModel, summary="Update Organism by Taxonomy ID")
async def update_organism(tax_id: int, data: OrganismUpdateModel):
    if tax_id not in organism_storage:
        raise HTTPException(status_code=404, detail=f"Organism with Taxonomy ID {tax_id} not found.")

    stored_organism = organism_storage[tax_id]
    update_data = data.dict(exclude_unset=True)

    for key, value in update_data.items():
        stored_organism[key] = value

    organism_storage[tax_id] = stored_organism
    return {"message": "Organism updated successfully", "data": stored_organism}


# Delete Organism by Taxonomy ID
@router.delete("/organism/{organism_id}", response_model=OrganismDeleteModel, summary="Delete Organism by Taxonomy ID")
async def delete_organism(tax_id: int):
    if tax_id not in organism_storage:
        raise HTTPException(status_code=404, detail=f"Organism with Taxonomy ID {tax_id} not found.")

    del organism_storage[tax_id]
    return {"message": f"Organism with Taxonomy ID {tax_id} deleted successfully."}


# GET method to retrieve taxonomy by tax_id
@router.get("/taxonomy/{tax_id}", response_model=TaxonomyResponseModel, summary="Retrieve Taxonomy by Taxonomy ID")
async def get_taxonomy(tax_id: int):
    if tax_id not in taxonomy_storage:
        raise HTTPException(status_code=404, detail=f"Taxonomy ID {tax_id} not found.")

    return {"message": "Taxonomy entry found", "data": taxonomy_storage[tax_id]}


# POST method to search for organisms by keyword
@router.post("/taxonomy/search", response_model=TaxonomyResponseModel, summary="Search Taxonomy by Keyword")
async def search_taxonomy(search_data: TaxonomySearchModel):
    keyword = search_data.keyword.lower()
    results = []

    # Search through taxonomy_storage for matching scientific_name or common_name
    for entry in taxonomy_storage.values():
        if keyword in entry['scientific_name'].lower() or (entry['common_name'] and keyword in entry['common_name'].lower()):
            results.append(entry)

    if not results:
        raise HTTPException(status_code=404, detail=f"No taxonomy entries found for keyword: {keyword}")

    return {"message": f"{len(results)} taxonomy entries found", "data": results}
