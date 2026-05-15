from __future__ import annotations

import shutil
import tarfile
import tempfile
from pathlib import Path
from io import StringIO

from .models import (
    BreedingTaxonomyName,
    BreedingTaxonomyNode,
)


SEARCH_NAME_CLASSES = {
    "scientific name",
    "common name",
    "synonym",
    "equivalent name",
    "genbank common name",
    "genbank synonym",
    "blast name",
}


def _split_dmp_line(raw_line: str) -> list[str]:
    return [item.strip() for item in raw_line.rstrip("\n").split("\t|\t")]


def _resolve_taxdump_dir(dump_path: str):
    path = Path(dump_path)
    if path.is_dir():
        return path, None
    if path.is_file() and path.name.endswith((".tar.gz", ".tgz")):
        temp_dir = Path(tempfile.mkdtemp(prefix="fan_taxdump_"))
        with tarfile.open(path, "r:gz") as archive:
            archive.extractall(temp_dir)
        return temp_dir, temp_dir
    raise ValueError(f"unsupported taxonomy dump path: {dump_path}")


def parse_taxonomy_nodes(nodes_path: str | Path):
    nodes = {}
    with open(nodes_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            parts = _split_dmp_line(raw_line)
            if len(parts) < 3:
                continue
            tax_id = int(parts[0])
            parent_tax_id = int(parts[1])
            rank = parts[2]
            nodes[tax_id] = {
                "tax_id": tax_id,
                "parent_tax_id": parent_tax_id,
                "rank": rank,
            }
    return nodes


def parse_taxonomy_names(names_path: str | Path, *, allowed_name_classes: set[str] | None = None):
    names = []
    scientific_names = {}
    common_names = {}
    with open(names_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            parts = _split_dmp_line(raw_line)
            if len(parts) < 4:
                continue
            tax_id = int(parts[0])
            name_txt = parts[1]
            unique_name = parts[2] or None
            name_class = parts[3].replace("\t|", "").strip()
            if name_class == "scientific name":
                scientific_names[tax_id] = name_txt
            elif name_class == "common name" and tax_id not in common_names:
                common_names[tax_id] = name_txt
            if allowed_name_classes is not None and name_class not in allowed_name_classes:
                continue
            names.append(
                {
                    "tax_id": tax_id,
                    "name_txt": name_txt,
                    "unique_name": unique_name,
                    "name_class": name_class,
                }
            )
    return names, scientific_names, common_names


def build_taxonomy_lineages(nodes: dict[int, dict], scientific_names: dict[int, str]):
    """Build lineage text and lineage_ids array for each node.

    Returns: {tax_id: (lineage_text: str | None, lineage_ids: list[int], lineage_names: list[str])}
    """
    lineage_cache: dict[int, tuple[str | None, list[int], list[str]]] = {}

    def resolve_lineage(tax_id: int):
        if tax_id in lineage_cache:
            return lineage_cache[tax_id]
        node = nodes.get(tax_id)
        if node is None:
            lineage_cache[tax_id] = (None, [], [])
            return lineage_cache[tax_id]

        parent_tax_id = node.get("parent_tax_id")
        if not parent_tax_id or parent_tax_id == tax_id or parent_tax_id not in nodes:
            lineage_cache[tax_id] = (None, [], [])
            return lineage_cache[tax_id]

        parent_lineage, parent_ids, parent_names = resolve_lineage(parent_tax_id)
        parent_name = scientific_names.get(parent_tax_id)
        lineage_ids = list(parent_ids) + [parent_tax_id]
        lineage_names = list(parent_names)
        if parent_name:
            lineage_names.append(parent_name)
        lineage_text = "; ".join(lineage_names) if lineage_names else None
        lineage_cache[tax_id] = (lineage_text, lineage_ids, lineage_names)
        return lineage_cache[tax_id]

    for tax_id in nodes:
        resolve_lineage(tax_id)
    return lineage_cache


def _copy_rows_to_postgres(raw_conn, *, table_name: str, columns: list[str], rows: list[tuple]):
    if not rows:
        return
    buffer = StringIO()
    for row in rows:
        serialized = []
        for value in row:
            if value is None:
                serialized.append("\\N")
            elif isinstance(value, list):
                # PostgreSQL array literal: {item1,item2,...}
                array_str = "{" + ",".join(str(v) for v in value) + "}"
                serialized.append(array_str)
            else:
                text = str(value)
                text = text.replace("\\", "\\\\").replace("\t", " ").replace("\n", " ").replace("\r", " ")
                serialized.append(text)
        buffer.write("\t".join(serialized))
        buffer.write("\n")
    buffer.seek(0)
    with raw_conn.cursor() as cur:
        copy_sql = (
            f"COPY {table_name} ({', '.join(columns)}) "
            "FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '\\N')"
        )
        with cur.copy(copy_sql) as copy:
            copy.write(buffer.read())


def _load_taxonomy_dump_postgres(
    db,
    *,
    dump_path: str,
    dump_dir: Path,
    source_name: str,
    source_version: str | None,
    reset_existing: bool,
):
    nodes_path = dump_dir / "nodes.dmp"
    names_path = dump_dir / "names.dmp"
    if not nodes_path.exists() or not names_path.exists():
        raise ValueError(f"nodes.dmp or names.dmp not found under {dump_dir}")

    nodes = parse_taxonomy_nodes(nodes_path)
    names, scientific_names, common_names = parse_taxonomy_names(
        names_path,
        allowed_name_classes=SEARCH_NAME_CLASSES,
    )
    lineages = build_taxonomy_lineages(nodes=nodes, scientific_names=scientific_names)

    engine = db.get_bind()
    raw_conn = engine.raw_connection()
    try:
        if reset_existing:
            with raw_conn.cursor() as cur:
                cur.execute("DELETE FROM brd_taxonomy_name")
                cur.execute("DELETE FROM brd_taxonomy_node")

        node_rows = []
        for tax_id, node in nodes.items():
            lineage_text, lineage_ids, _lineage_names = lineages.get(tax_id, (None, [], []))
            node_rows.append(
                (
                    tax_id,
                    node.get("parent_tax_id"),
                    node.get("rank"),
                    scientific_names.get(tax_id) or str(tax_id),
                    common_names.get(tax_id),
                    lineage_ids,
                    lineage_text,
                    "plant_dump",
                    1,
                )
            )

        _copy_rows_to_postgres(
            raw_conn,
            table_name="brd_taxonomy_node",
            columns=[
                "tax_id",
                "parent_tax_id",
                "rank",
                "scientific_name",
                "common_name",
                "lineage_ids",
                "lineage",
                "source",
                "is_active",
            ],
            rows=node_rows,
        )

        name_rows = [
            (name["tax_id"], name["name_txt"], name["unique_name"], name["name_class"])
            for name in names
        ]
        _copy_rows_to_postgres(
            raw_conn,
            table_name="brd_taxonomy_name",
            columns=["tax_id", "name_txt", "unique_name", "name_class"],
            rows=name_rows,
        )

        raw_conn.commit()
        return {
            "source_name": source_name,
            "source_version": source_version,
            "node_count": len(nodes),
            "name_count": len(name_rows),
            "dump_dir": str(dump_dir),
        }
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


def load_taxonomy_dump(
    db,
    *,
    dump_path: str,
    source_name: str = "ncbi_taxdump",
    source_version: str | None = None,
    reset_existing: bool = False,
):
    dump_dir, cleanup_dir = _resolve_taxdump_dir(dump_path)
    try:
        dialect_name = db.get_bind().dialect.name
        if dialect_name == "postgresql":
            return _load_taxonomy_dump_postgres(
                db=db,
                dump_path=dump_path,
                dump_dir=dump_dir,
                source_name=source_name,
                source_version=source_version,
                reset_existing=reset_existing,
            )

        nodes_path = dump_dir / "nodes.dmp"
        names_path = dump_dir / "names.dmp"
        if not nodes_path.exists() or not names_path.exists():
            raise ValueError(f"nodes.dmp or names.dmp not found under {dump_dir}")

        nodes = parse_taxonomy_nodes(nodes_path)
        names, scientific_names, common_names = parse_taxonomy_names(
            names_path,
            allowed_name_classes=SEARCH_NAME_CLASSES,
        )
        lineages = build_taxonomy_lineages(nodes=nodes, scientific_names=scientific_names)

        if reset_existing:
            db.query(BreedingTaxonomyName).delete()
            db.query(BreedingTaxonomyNode).delete()
            db.flush()

        for tax_id, node in nodes.items():
            lineage_text, lineage_ids, _lineage_names = lineages.get(tax_id, (None, [], []))
            payload = {
                "parent_tax_id": node.get("parent_tax_id"),
                "rank": node.get("rank"),
                "scientific_name": scientific_names.get(tax_id) or str(tax_id),
                "common_name": common_names.get(tax_id),
                "lineage_ids": lineage_ids,
                "lineage": lineage_text,
                "source": "plant_dump",
                "is_active": 1,
            }
            row = db.query(BreedingTaxonomyNode).filter(BreedingTaxonomyNode.tax_id == tax_id).first()
            if row is None:
                db.add(BreedingTaxonomyNode(tax_id=tax_id, **payload))
            else:
                for field, value in payload.items():
                    setattr(row, field, value)
                db.add(row)

        seen_name_keys = set()
        for name in names:
            key = (name["tax_id"], name["name_txt"], name["name_class"])
            if key in seen_name_keys:
                continue
            seen_name_keys.add(key)
            db.add(BreedingTaxonomyName(**name))

        db.commit()
        return {
            "source_name": source_name,
            "source_version": source_version,
            "node_count": len(nodes),
            "name_count": len(seen_name_keys),
            "dump_dir": str(dump_dir),
        }
    finally:
        if cleanup_dir is not None and cleanup_dir.exists():
            shutil.rmtree(cleanup_dir, ignore_errors=True)
