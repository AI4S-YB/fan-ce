# apps/breeding/tools.py
"""Breeding program tools for LLM function calling."""
from apps.breeding.models import (
    BreedingBioSample,
    BreedingMaterial,
    BreedingProgram,
    BreedingTrial,
)
from apps.datasets.services import dataset_domain_service
from libs.tool_registry import ToolDefinition, tool_registry


async def _link_dataset_to_program(db, arguments: dict, user) -> dict:
    """Preview: link a dataset to a breeding program.

    Loads dataset and program context. Returns them as a preview for
    the LLM to process with user instructions. No DB writes.
    """
    dataset_id = arguments.get("dataset_id")
    program_id = arguments.get("program_id")

    if not dataset_id or not program_id:
        return {"error": "dataset_id and program_id are required"}

    try:
        dataset_id = int(dataset_id)
        program_id = int(program_id)
    except (TypeError, ValueError):
        return {"error": "dataset_id and program_id must be valid integers"}

    # Load dataset context
    try:
        ds = dataset_domain_service.get_dataset(db=db, dataset_id=dataset_id, user=user)
    except Exception:
        return {"error": f"Dataset {dataset_id} not found or access denied"}

    # Load program context
    program = db.query(BreedingProgram).filter(BreedingProgram.id == program_id).first()
    if not program:
        return {"error": f"Breeding program {program_id} not found"}

    materials = (
        db.query(BreedingMaterial)
        .filter(
            BreedingMaterial.program_id == program_id,
            BreedingMaterial.status == "active",
        )
        .all()
    )

    trials = (
        db.query(BreedingTrial)
        .filter(
            BreedingTrial.program_id == program_id,
            BreedingTrial.status == "active",
        )
        .all()
    )

    biosamples = (
        db.query(BreedingBioSample)
        .join(BreedingMaterial, BreedingBioSample.material_id == BreedingMaterial.id)
        .filter(BreedingMaterial.program_id == program_id)
        .all()
    )

    # Build context for LLM
    context = {
        "dataset": {
            "id": ds.get("id"),
            "type": ds.get("dataset_type"),
            "organism": ds.get("organism"),
            "assembly": ds.get("assembly"),
            "query_adapter": ds.get("query_adapter", {}),
        },
        "program": {
            "id": program.id,
            "name": program.name,
            "code": program.code,
            "species_name": program.species_name,
        },
        "materials": [
            {
                "id": m.id,
                "material_code": m.material_code,
                "material_name": m.material_name,
                "material_type": m.material_type,
                "germplasm_accession": m.germplasm_accession,
                "germplasm_name": m.germplasm_name,
            }
            for m in materials
        ],
        "trials": [
            {
                "id": t.id,
                "trial_code": t.trial_code,
                "trial_name": t.trial_name,
            }
            for t in trials
        ],
        "biosamples": [
            {
                "id": b.id,
                "material_id": b.material_id,
                "sample_code": b.sample_code,
            }
            for b in biosamples
        ],
    }

    return {
        "status": "preview",
        "message": "Context loaded. Awaiting LLM processing with user instructions.",
        "context": context,
        "note": (
            "The LLM will generate proposed subject_links and variant_maps "
            "based on the context above. Review before committing."
        ),
    }


TOOL_LINK_DATASET = ToolDefinition(
    name="link_dataset_to_program",
    description=(
        "将一个 dataset 关联到育种项目 (brd_program)。加载项目和数据集上下文，"
        "结合用户的自然语言指令，由 LLM 生成样本级别的关联映射建议。"
        "返回 preview 供用户审核，审核通过后才写入数据库。"
        "适用于 VCF、RNA-seq 表达矩阵、表型数据等所有数据类型。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "integer",
                "description": "要关联的 dataset ID",
            },
            "program_id": {
                "type": "integer",
                "description": "目标育种项目 (brd_program) ID",
            },
        },
        "required": ["dataset_id", "program_id"],
    },
    execute=_link_dataset_to_program,
    require_admin=True,
)

BREEDING_TOOLS = [TOOL_LINK_DATASET]


def register_breeding_tools():
    """Register breeding-related tools. Called during app startup."""
    tool_registry.register_many(BREEDING_TOOLS)
