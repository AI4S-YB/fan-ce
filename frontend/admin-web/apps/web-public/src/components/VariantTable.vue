<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  result: Record<string, any> | null;
  loading?: boolean;
}>();

interface VariantRow {
  id: string;
  chrom: string;
  pos: number;
  ref: string;
  alt: string;
  qual: string;
  genotypes: { sample: string; gt: string }[];
}

const variants = computed<VariantRow[]>(() => {
  const preview = props.result?.data?.preview || props.result?.preview || '';
  if (!preview) return [];
  const lines = preview.split('\n').filter((l: string) => l && !l.startsWith('#'));
  if (lines.length === 0) return [];

  const headerLine = preview.split('\n').find((l: string) => l.startsWith('#CHROM'));
  const sampleNames = headerLine ? headerLine.split('\t').slice(9) : [];

  return lines.map((line: string) => {
    const fields = line.split('\t');
    const genotypes = sampleNames.map((name: string, i: number) => ({
      sample: name,
      gt: fields[9 + i] ? fields[9 + i].split(':')[0] : './.',
    }));
    return {
      id: `${fields[0]}:${fields[1]}`,
      chrom: fields[0],
      pos: Number(fields[1]),
      ref: fields[3],
      alt: fields[4],
      qual: fields[5],
      genotypes,
    };
  });
});

function alleleDisplay(gt: string, ref: string, alt: string): string {
  return gt.replace(/0/g, ref).replace(/1/g, alt).replace(/\|/g, '/');
}
</script>

<template>
  <div>
    <el-table :data="variants" border size="small" v-loading="loading" max-height="600" stripe>
      <el-table-column type="expand">
        <template #default="scope">
          <el-table :data="scope.row.genotypes" border size="small" max-height="300">
            <el-table-column prop="sample" label="Sample" min-width="140" />
            <el-table-column label="Allele" min-width="120">
              <template #default="{ row: gr }">
                {{ alleleDisplay(gr.gt, scope.row.ref, scope.row.alt) }}
              </template>
            </el-table-column>
          </el-table>
        </template>
      </el-table-column>
      <el-table-column prop="chrom" label="Chrom" width="120" />
      <el-table-column prop="pos" label="Position" width="120" sortable />
      <el-table-column prop="ref" label="Ref" width="80" />
      <el-table-column prop="alt" label="Alt" width="80" />
      <el-table-column prop="qual" label="Qual" width="80" />
    </el-table>
    <el-empty v-if="!loading && variants.length === 0" description="No variants found" />
  </div>
</template>
