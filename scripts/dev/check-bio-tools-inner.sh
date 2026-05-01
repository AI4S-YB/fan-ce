#!/usr/bin/env bash
set -euo pipefail

echo "samtools: $(command -v samtools)"
samtools --version | head -n 1
echo "bcftools: $(command -v bcftools)"
bcftools --version | head -n 1
echo "tabix: $(command -v tabix)"
tabix --version
