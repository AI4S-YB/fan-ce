#!/usr/bin/env bash

set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8002/api/v1}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin123456}"

VARIANT_TITLE="${VARIANT_TITLE:-demo_variants}"
EXPRESSION_TITLE="${EXPRESSION_TITLE:-demo_expression}"
ANNOTATION_TITLE="${ANNOTATION_TITLE:-demo_annotation}"
ANNOTATION_GFF_TITLE="${ANNOTATION_GFF_TITLE:-demo_annotation_gff}"
SIGNAL_TITLE="${SIGNAL_TITLE:-demo_signal}"
INTERACTION_TITLE="${INTERACTION_TITLE:-demo_interaction}"

VARIANT_FILE="${VARIANT_FILE:-/tmp/fan_ce_demo_variants.vcf}"
EXPRESSION_FILE="${EXPRESSION_FILE:-/tmp/fan_ce_demo_expression.tsv}"
ANNOTATION_FILE="${ANNOTATION_FILE:-/tmp/fan_ce_demo_annotation.sqlite}"
ANNOTATION_GFF_FILE="${ANNOTATION_GFF_FILE:-/tmp/fan_ce_demo_annotation.gff3}"
SIGNAL_FILE="${SIGNAL_FILE:-/tmp/fan_ce_demo_signal.bed}"
INTERACTION_FILE="${INTERACTION_FILE:-/tmp/fan_ce_demo_interaction.bedpe}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

need_cmd curl
need_cmd jq
need_cmd python3

login() {
  curl -s -X POST "${API_BASE_URL}/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${ADMIN_USERNAME}\",\"password\":\"${ADMIN_PASSWORD}\"}" |
    jq -r '.data.access_token'
}

TOKEN="$(login)"
if [[ -z "${TOKEN}" || "${TOKEN}" == "null" ]]; then
  echo "failed to login to backend" >&2
  exit 1
fi

api_post() {
  local path="$1"
  local payload="$2"
  curl -s -X POST "${API_BASE_URL}${path}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H 'Content-Type: application/json' \
    -d "${payload}"
}

write_variant_demo_file() {
  cat >"${VARIANT_FILE}" <<'EOF'
##fileformat=VCFv4.2
##contig=<ID=Chr1,length=100000>
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SampleA	SampleB
Chr1	1000	.	A	G	60	PASS	.	GT	0/1	1/1
Chr1	1500	.	C	T	60	PASS	.	GT	0/0	0/1
Chr1	2200	.	G	A	60	PASS	.	GT	1/1	0/1
EOF
}

write_expression_demo_file() {
  cat >"${EXPRESSION_FILE}" <<'EOF'
gene	SampleA	SampleB	SampleC
Gene001	10	5	0
Gene002	3	8	2
Gene003	0	12	7
Gene004	15	1	9
EOF
}

write_annotation_demo_file() {
  ANNOTATION_FILE="${ANNOTATION_FILE}" python3 - <<'PY'
import os
import sqlite3

db_path = os.environ["ANNOTATION_FILE"]
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE hse_genes (
      gene_id TEXT PRIMARY KEY,
      chrom TEXT NOT NULL,
      start INTEGER NOT NULL,
      stop INTEGER NOT NULL,
      strand TEXT,
      description TEXT,
      canonical_transcript TEXT,
      family TEXT
    )
    """
)
cur.execute(
    """
    CREATE TABLE hse_transcripts (
      transcript_id TEXT PRIMARY KEY,
      gene_id TEXT NOT NULL,
      chrom TEXT NOT NULL,
      start INTEGER NOT NULL,
      stop INTEGER NOT NULL,
      strand TEXT,
      description TEXT
    )
    """
)
cur.executemany(
    "INSERT INTO hse_genes VALUES (?,?,?,?,?,?,?,?)",
    [
        ("Gene001", "chr1", 100, 400, "+", "demo annotation gene 1", "Tx001", "TF"),
        ("Gene002", "chr1", 700, 980, "-", "demo annotation gene 2", "Tx002", "Kinase"),
    ],
)
cur.executemany(
    "INSERT INTO hse_transcripts VALUES (?,?,?,?,?,?,?)",
    [
        ("Tx001", "Gene001", "chr1", 120, 360, "+", "demo transcript 1"),
        ("Tx002", "Gene002", "chr1", 730, 930, "-", "demo transcript 2"),
    ],
)
conn.commit()
conn.close()
PY
}

write_annotation_gff_demo_file() {
  cat >"${ANNOTATION_GFF_FILE}" <<'EOF'
##gff-version 3
chr1	demo	gene	100	400	.	+	.	ID=Gene001;Name=Gene001;gene_id=Gene001
chr1	demo	mRNA	120	360	.	+	.	ID=Tx001;Parent=Gene001;transcript_id=Tx001;gene_id=Gene001
chr1	demo	exon	120	200	.	+	.	ID=Tx001.exon1;Parent=Tx001;gene_id=Gene001
chr1	demo	exon	240	360	.	+	.	ID=Tx001.exon2;Parent=Tx001;gene_id=Gene001
chr1	demo	gene	700	980	.	-	.	ID=Gene002;Name=Gene002;gene_id=Gene002
chr1	demo	mRNA	730	930	.	-	.	ID=Tx002;Parent=Gene002;transcript_id=Tx002;gene_id=Gene002
chr1	demo	exon	730	810	.	-	.	ID=Tx002.exon1;Parent=Tx002;gene_id=Gene002
chr1	demo	exon	850	930	.	-	.	ID=Tx002.exon2;Parent=Tx002;gene_id=Gene002
EOF
}

write_signal_demo_file() {
  cat >"${SIGNAL_FILE}" <<'EOF'
chr1	50	180	peak_001	12	+
chr1	220	360	peak_002	25	+
chr1	500	820	peak_003	18	-
chr2	100	260	peak_004	30	+
EOF
}

write_interaction_demo_file() {
  cat >"${INTERACTION_FILE}" <<'EOF'
chr1	100	180	chr1	520	610	loop_001	42	+	-
chr1	140	220	chr1	900	980	loop_002	35	+	+
chr1	400	520	chr2	100	260	loop_003	18	-	+
chr2	200	320	chr2	700	860	loop_004	27	+	-
EOF
}

find_dataset_by_title() {
  local title="$1"
  api_post "/admin/dataset/list" "{\"page\":1,\"size\":200,\"name\":\"${title}\"}" |
    jq -c --arg title "${title}" '.data.dataList[]? | select(.title == $title or .name == $title)' |
    head -n 1
}

register_dataset() {
  local title="$1"
  local dataset_type="$2"
  local file_path="$3"
  api_post "/admin/dataset/ingest/register" \
    "{\"file_path\":\"${file_path}\",\"name\":\"${title}\",\"dataset_type\":\"${dataset_type}\",\"remark\":\"dev demo dataset\",\"is_public\":false}"
}

run_pipeline() {
  local dataset_id="$1"
  api_post "/admin/dataset/ingest/pipeline" \
    "{\"id\":${dataset_id},\"detail\":\"dev demo pipeline\"}" >/dev/null
}

publish_dataset() {
  local dataset_id="$1"
  api_post "/admin/dataset/publish" \
    "{\"id\":${dataset_id},\"note\":\"publish dev demo dataset\"}" >/dev/null
}

ensure_dataset_public() {
  local title="$1"
  local dataset_type="$2"
  local file_path="$3"

  local dataset_json
  dataset_json="$(find_dataset_by_title "${title}")"

  if [[ -z "${dataset_json}" ]]; then
    echo "creating dataset: ${title}" >&2
    dataset_json="$(register_dataset "${title}" "${dataset_type}" "${file_path}" | jq -c '.data')"
  else
    echo "reusing dataset: ${title}" >&2
  fi

  local dataset_id
  local visibility
  dataset_id="$(echo "${dataset_json}" | jq -r '.id')"
  visibility="$(echo "${dataset_json}" | jq -r '.visibility // "private"')"

  if [[ -z "${dataset_id}" || "${dataset_id}" == "null" ]]; then
    echo "failed to resolve dataset id for ${title}" >&2
    exit 1
  fi

  local detail_json
  detail_json="$(api_post "/admin/dataset/info" "{\"id\":${dataset_id}}")"
  local lifecycle
  lifecycle="$(echo "${detail_json}" | jq -r '.data.lifecycle_state // "draft"')"

  if [[ "${lifecycle}" != "ready" && "${lifecycle}" != "public" ]]; then
    echo "running pipeline for ${title}" >&2
    run_pipeline "${dataset_id}"
  fi

  if [[ "${visibility}" != "public" ]]; then
    echo "publishing ${title}" >&2
    publish_dataset "${dataset_id}"
  fi

  echo "${dataset_id}"
}

write_variant_demo_file
write_expression_demo_file
write_annotation_demo_file
write_annotation_gff_demo_file
write_signal_demo_file
write_interaction_demo_file

VARIANT_ID="$(ensure_dataset_public "${VARIANT_TITLE}" "variant" "${VARIANT_FILE}")"
EXPRESSION_ID="$(ensure_dataset_public "${EXPRESSION_TITLE}" "expression" "${EXPRESSION_FILE}")"
ANNOTATION_ID="$(ensure_dataset_public "${ANNOTATION_TITLE}" "annotation" "${ANNOTATION_FILE}")"
ANNOTATION_GFF_ID="$(ensure_dataset_public "${ANNOTATION_GFF_TITLE}" "annotation" "${ANNOTATION_GFF_FILE}")"
SIGNAL_ID="$(ensure_dataset_public "${SIGNAL_TITLE}" "signal" "${SIGNAL_FILE}")"
INTERACTION_ID="$(ensure_dataset_public "${INTERACTION_TITLE}" "interaction" "${INTERACTION_FILE}")"

echo "public demo datasets are ready"
echo "variant dataset id: ${VARIANT_ID}"
echo "expression dataset id: ${EXPRESSION_ID}"
echo "annotation dataset id: ${ANNOTATION_ID}"
echo "annotation gff dataset id: ${ANNOTATION_GFF_ID}"
echo "signal dataset id: ${SIGNAL_ID}"
echo "interaction dataset id: ${INTERACTION_ID}"
