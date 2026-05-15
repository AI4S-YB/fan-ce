#!/usr/bin/env bash
set -euo pipefail

echo "Bioinformatics tools check:"
echo ""

for tool in samtools bcftools blastn blastp makeblastdb primer3_core mafft FastTree muscle bedtools tabix bgzip; do
    if command -v "$tool" &>/dev/null; then
        ver=$("$tool" --version 2>&1 | head -1 || echo "version check failed")
        echo "  $tool  ✓  $ver"
    else
        echo "  $tool  ✗  not found"
    fi
done
