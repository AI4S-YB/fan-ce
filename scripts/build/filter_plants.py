#!/usr/bin/env python3
"""Filter NCBI taxonomy dump to Viridiplantae (tax_id: 33090) subtree only.

Usage:
    python filter_plants.py <path_to_new_taxdump.tar.gz> <output_dir>
    python filter_plants.py <path_to_extracted_dump_dir> <output_dir>

Output: <output_dir>/nodes.dmp + <output_dir>/names.dmp (plant-only)
"""

import argparse
import os
import sys
import tarfile
import tempfile
from pathlib import Path


PLANT_ROOT_TAX_ID = 33090  # Viridiplantae


def parse_nodes(nodes_path: Path) -> dict[int, int]:
    """Parse nodes.dmp, return {tax_id: parent_tax_id}."""
    nodes: dict[int, int] = {}
    with open(nodes_path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t|\t")
            if len(parts) < 2:
                continue
            tax_id = int(parts[0].strip())
            parent_tax_id = int(parts[1].strip())
            nodes[tax_id] = parent_tax_id
    return nodes


def collect_subtree(nodes: dict[int, int], root_tax_id: int) -> set[int]:
    """BFS from root_tax_id, return set of all descendant tax_ids (including root)."""
    children: dict[int, list[int]] = {}
    for tax_id, parent_id in nodes.items():
        children.setdefault(parent_id, []).append(tax_id)

    result: set[int] = set()
    queue = [root_tax_id]
    while queue:
        tax_id = queue.pop(0)
        if tax_id in result:
            continue
        result.add(tax_id)
        queue.extend(children.get(tax_id, []))
    return result


def filter_dmp(input_path: Path, output_path: Path, keep_ids: set[int]):
    """Write lines from input dmp whose first column is in keep_ids."""
    written = 0
    with open(input_path, encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            parts = line.strip().split("\t|\t")
            if not parts:
                continue
            try:
                tax_id = int(parts[0].strip())
            except ValueError:
                continue
            if tax_id in keep_ids:
                fout.write(line)
                written += 1
    return written


def is_dump_dir(path: Path) -> bool:
    return (path / "nodes.dmp").exists() and (path / "names.dmp").exists()


def main():
    parser = argparse.ArgumentParser(description="Filter NCBI taxonomy to Viridiplantae only")
    parser.add_argument("input", help="Path to new_taxdump.tar.gz or extracted dump directory")
    parser.add_argument("output_dir", help="Output directory for filtered nodes.dmp + names.dmp")
    parser.add_argument("--tax-id", type=int, default=PLANT_ROOT_TAX_ID,
                        help=f"Root tax_id for filtering (default: {PLANT_ROOT_TAX_ID})")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cleanup_dir = None
    work_dir = input_path

    if not input_path.exists():
        print(f"Error: input path does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    if input_path.suffix in (".gz", ".tgz") or ".tar" in input_path.suffixes:
        print(f"Extracting {input_path} ...")
        cleanup_dir = tempfile.mkdtemp(prefix="taxonomy_filter_")
        with tarfile.open(input_path, "r:gz") as tar:
            tar.extractall(cleanup_dir)
        work_dir = Path(cleanup_dir)
        # sometimes the archive has a top-level directory
        for child in work_dir.iterdir():
            if child.is_dir() and is_dump_dir(child):
                work_dir = child
                break

    if not is_dump_dir(work_dir):
        print(f"Error: nodes.dmp and names.dmp not found under {work_dir}", file=sys.stderr)
        sys.exit(1)

    nodes_path = work_dir / "nodes.dmp"
    names_path = work_dir / "names.dmp"

    print(f"Parsing nodes from {nodes_path} ...")
    nodes = parse_nodes(nodes_path)
    print(f"  Total nodes: {len(nodes):,}")

    print(f"Collecting subtree for tax_id={args.tax_id} ...")
    keep_ids = collect_subtree(nodes, args.tax_id)
    print(f"  Plant nodes: {len(keep_ids):,} ({len(keep_ids) / len(nodes) * 100:.1f}%)")

    out_nodes = output_dir / "nodes.dmp"
    out_names = output_dir / "names.dmp"

    print(f"Writing {out_nodes} ...")
    n = filter_dmp(nodes_path, out_nodes, keep_ids)
    print(f"  Written: {n:,} lines")

    print(f"Writing {out_names} ...")
    n = filter_dmp(names_path, out_names, keep_ids)
    print(f"  Written: {n:,} lines")

    if cleanup_dir:
        import shutil
        shutil.rmtree(cleanup_dir)

    print("Done.")


if __name__ == "__main__":
    main()
