from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook


TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "static"
    / "templates"
    / "germplasm"
    / "crop_germplasm_v1.xlsx"
)
RICE_DEMO_PATH = (
    Path(__file__).resolve().parents[1]
    / "static"
    / "templates"
    / "germplasm"
    / "crop_germplasm_rice_demo.xlsx"
)


def build_template() -> Workbook:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "germplasm_import"

    sheet.append(["#title", "Crop Germplasm Import Template v1"])
    sheet.append(
        [
            "#description",
            (
                "Prepare FAN-CE germplasm import data here. "
                "Select taxonomy on the import page; do not add a species column in the workbook."
            ),
        ]
    )
    sheet.append(["#required", "Columns ID and chinese_name are required."])
    sheet.append(
        [
            "#custom_fields",
            "All columns after M_name are treated as batch-level custom fields and may vary by submission.",
        ]
    )
    sheet.append(
        [
            "#notes",
            "Rows beginning with # are treated as instructions and ignored during validation.",
        ]
    )
    sheet.append([])
    sheet.append(
        [
            "ID",
            "chinese_name",
            "english_name",
            "P",
            "M",
            "P_name",
            "M_name",
            "breeding_note",
            "trait_flower_color",
            "trait_growth_habit",
            "collector_note",
        ]
    )
    sheet.append(
        [
            "CROP0001",
            "示例材料1",
            "Example Line 1",
            "CROP0101",
            "CROP0102",
            "Parent Line A",
            "Parent Line B",
            "2024 spring crossing population",
            "purple",
            "upright",
            "Example custom field values only",
        ]
    )
    sheet.append(
        [
            "CROP0002",
            "示例材料2",
            "Example Line 2",
            "CROP0201",
            "CROP0202",
            "Parent Line C",
            "Parent Line D",
            "Breeding target: fragrance",
            "pink",
            "compact",
            "Custom columns can be renamed or replaced",
        ]
    )
    return workbook


def build_rice_demo() -> Workbook:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "rice_demo_import"

    sheet.append(["#title", "Crop Germplasm Rice Demo"])
    sheet.append(
        [
            "#description",
            (
                "Demo dataset for Oryza sativa. "
                "Choose taxonomy Oryza sativa on the import page before uploading."
            ),
        ]
    )
    sheet.append(["#required", "Columns ID and chinese_name are required."])
    sheet.append(
        [
            "#custom_fields",
            "All columns after M_name are dynamic fields in this batch. You can rename them in your own file.",
        ]
    )
    sheet.append(
        [
            "#notes",
            "This file is only for frontend testing. It contains simple rice germplasm examples with parent references.",
        ]
    )
    sheet.append([])
    sheet.append(
        [
            "ID",
            "chinese_name",
            "english_name",
            "P",
            "M",
            "P_name",
            "M_name",
            "subspecies",
            "grain_type",
            "origin_site",
            "collector_note",
        ]
    )
    sheet.append(
        [
            "RICE0001",
            "华南籼稻1号",
            "South China Indica 1",
            "RICE0101",
            "RICE0102",
            "恢复系A",
            "保持系B",
            "indica",
            "long grain",
            "Guangzhou",
            "demo line for import validation",
        ]
    )
    sheet.append(
        [
            "RICE0002",
            "东北粳稻2号",
            "Northeast Japonica 2",
            "RICE0103",
            "RICE0104",
            "父本C",
            "母本D",
            "japonica",
            "medium grain",
            "Harbin",
            "adapted to cool region",
        ]
    )
    sheet.append(
        [
            "RICE0003",
            "两系杂交稻3号",
            "Hybrid Rice 3",
            "RICE0001",
            "RICE0002",
            "华南籼稻1号",
            "东北粳稻2号",
            "hybrid",
            "long grain",
            "Wuhan",
            "uses demo parents from same workbook",
        ]
    )
    sheet.append(
        [
            "RICE0004",
            "香稻材料4号",
            "Fragrant Rice 4",
            "",
            "",
            "",
            "",
            "japonica",
            "aromatic",
            "Changsha",
            "simple accession without parent info",
        ]
    )
    return workbook


def main() -> None:
    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    outputs = [
        (TEMPLATE_PATH, build_template()),
        (RICE_DEMO_PATH, build_rice_demo()),
    ]
    for output_path, workbook in outputs:
        workbook.save(output_path)
        workbook.close()
        print(f"generated {output_path}")


if __name__ == "__main__":
    main()
