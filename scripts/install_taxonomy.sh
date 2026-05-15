#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_FILE="$PROJECT_ROOT/backend/api-server/data/taxonomy-plants.tar.gz"

if [ ! -f "$DATA_FILE" ]; then
    echo "Error: taxonomy data file not found: $DATA_FILE"
    echo "Run 'python scripts/build/filter_plants.py <ncbi_dump> backend/api-server/data/' first."
    exit 1
fi

echo "Importing plant taxonomy data..."

cd "$PROJECT_ROOT"
python -c "
from db.database import MyDBManager
from apps.breeding.taxonomy_loader import load_taxonomy_dump

with MyDBManager() as db:
    result = load_taxonomy_dump(
        db=db,
        dump_path='$DATA_FILE',
        source_name='ncbi_plant_taxdump',
        reset_existing=False,
    )
    print(f'Imported {result[\"node_count\"]} nodes, {result[\"name_count\"]} names')
"

echo "Taxonomy import complete."
