#!/usr/bin/env bash
# ── Manual Taxonomy Import ──
# Re-import plant taxonomy data. Use this for manual updates.
# For fresh install, use install.sh instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_FILE="$PROJECT_ROOT/backend/api-server/data/taxonomy-plants.tar.gz"

if [ ! -f "$DATA_FILE" ] || [ ! -f "$PROJECT_ROOT/scripts/init_taxonomy.py" ]; then
    echo "Error: taxonomy data file not found: $DATA_FILE"
    echo "Run 'python scripts/build/filter_plants.py <ncbi_dump> backend/api-server/data/' first."
    exit 1
fi

echo "Importing plant taxonomy data..."

cd "$PROJECT_ROOT"
pixi run uv run --directory backend/api-server python ../../scripts/init_taxonomy.py data/taxonomy-plants.tar.gz

echo "Taxonomy import complete."
