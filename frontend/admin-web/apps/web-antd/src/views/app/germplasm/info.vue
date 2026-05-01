<script setup lang="ts">
import type {
  BreedingMaterialItem,
  BreedingProgramItem,
} from '#/api/breeding/program';
import type {
  GermplasmDetail,
  GermplasmFieldSchemaItem,
} from '#/views/apps/germplasm/types';

import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { Button, Card, Descriptions, Empty, Spin, Tag } from 'ant-design-vue';

import { $t } from '@vben/locales';
import {
  getBreedingMaterialListApi,
  getBreedingProgramListApi,
} from '#/api/breeding/program';
import {
  getGermplasmDetailApi,
  getGermplasmListApi,
  getGermplasmTaxonomyOptionsApi,
} from '#/views/apps/germplasm/api';
import GermplasmGraphModal from '#/views/apps/germplasm/components/GraphModal.vue';
import RelationshipModal from '#/views/apps/germplasm/components/RelationshipModal.vue';

defineOptions({ name: 'GermplasmInfoPage' });

const route = useRoute();
const router = useRouter();

const germplasmId = computed(() =>
  String(route.query.id || route.query.germplasm_id || ''),
);
const routeTaxonomyTaxId = computed(() => {
  const rawValue = Number(route.query.taxonomy_tax_id || 0);
  return Number.isFinite(rawValue) && rawValue > 0 ? rawValue : undefined;
});

const loading = ref(false);
const detailData = ref<GermplasmDetail | null>(null);
const breedingMaterials = ref<BreedingMaterialItem[]>([]);
const breedingPrograms = ref<BreedingProgramItem[]>([]);
const resolvedTaxonomyTaxId = ref<number | undefined>(undefined);
const relationshipVisible = ref(false);
const graphVisible = ref(false);
const relationshipNode2 = ref<string>('');

function backToList() {
  router.push('/germplasm/list');
}

const displayedAttributes = computed<Record<string, any>>(() => {
  const attrs = (detailData.value?.attributes || {}) as Record<string, any>;
  const exclude = new Set<string>([]);
  const result: Record<string, any> = {};
  Object.keys(attrs).forEach((key) => {
    if (!exclude.has(key)) {
      result[key] = attrs[key];
    }
  });
  return result;
});

const fixedFieldItems = computed(() => [
  { label: $t('germplasm.detail.germplasmId'), value: detailData.value?.id || germplasmId.value || '-' },
  { label: $t('germplasm.detail.displayName'), value: detailData.value?.display_name || '-' },
  { label: $t('germplasm.detail.englishName'), value: detailData.value?.english_name || '-' },
  { label: $t('germplasm.detail.species'), value: detailData.value?.taxonomy?.scientific_name || '-' },
  {
    label: $t('germplasm.detail.taxonomyId'),
    value:
      resolvedTaxonomyTaxId.value || detailData.value?.taxonomy?.tax_id || '-',
  },
  { label: $t('germplasm.detail.fatherAccession'), value: detailData.value?.father_accession || '-' },
  { label: $t('germplasm.detail.motherAccession'), value: detailData.value?.mother_accession || '-' },
  { label: $t('germplasm.detail.fatherName'), value: detailData.value?.father_name_snapshot || '-' },
  { label: $t('germplasm.detail.motherName'), value: detailData.value?.mother_name_snapshot || '-' },
  { label: $t('germplasm.detail.importBatch'), value: detailData.value?.audit?.batch_code || '-' },
  {
    label: $t('germplasm.detail.sourceFile'),
    value: detailData.value?.audit?.source_filename || '-',
  },
  {
    label: $t('germplasm.detail.excelRow'),
    value: detailData.value?.audit?.source_row_no || '-',
  },
  {
    label: $t('germplasm.detail.createdAt'),
    value: detailData.value?.audit?.created_at || '-',
  },
]);

const dynamicFieldSchema = computed(() =>
  [...(detailData.value?.field_schema || [])]
    .filter((item) => item.is_dynamic)
    .sort((left, right) => left.display_order - right.display_order),
);

const dynamicAttributeItems = computed(() => {
  const attrs = displayedAttributes.value;
  const schemaItems = dynamicFieldSchema.value;
  const mapped = schemaItems
    .map((field) => ({
      field,
      key: field.field_label || field.source_header || field.field_key,
      value: attrs[field.field_label || field.source_header || field.field_key],
    }))
    .filter((item) => item.value !== undefined);

  const usedKeys = new Set(mapped.map((item) => item.key));
  const extraItems = Object.entries(attrs)
    .filter(([key]) => !usedKeys.has(key))
    .map(([key, value]) => ({
      field: null,
      key,
      value,
    }));

  return [...mapped, ...extraItems];
});

const breedingProgramMap = computed(() =>
  Object.fromEntries(breedingPrograms.value.map((item) => [item.id, item])),
);

const breedingReferenceGroups = computed(() => {
  const grouped = new Map<
    number,
    { materials: BreedingMaterialItem[]; program: BreedingProgramItem | null }
  >();
  breedingMaterials.value.forEach((item) => {
    const programId = item.program_id;
    if (!grouped.has(programId)) {
      grouped.set(programId, {
        program: breedingProgramMap.value[programId] || null,
        materials: [],
      });
    }
    grouped.get(programId)!.materials.push(item);
  });
  return [...grouped.entries()]
    .map(([programId, value]) => ({
      programId,
      program: value.program,
      materials: value.materials,
    }))
    .sort((a, b) => b.materials.length - a.materials.length);
});

function formatValue(value: any) {
  if (value === null || value === undefined) {
    return '-';
  }
  if (typeof value === 'boolean') {
    return value ? $t('germplasm.detail.yes') : $t('germplasm.detail.no');
  }
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

function isLongText(value: any) {
  return (
    typeof value === 'string' && (value.length > 100 || value.includes('\n'))
  );
}

function fieldSchemaTagColor(field: GermplasmFieldSchemaItem) {
  if (field.data_type === 'number') {
    return 'purple';
  }
  if (field.data_type === 'date') {
    return 'geekblue';
  }
  return 'gold';
}

function openBreedingProgram(programId: number) {
  router.push(`/breeding/program/detail/${programId}`);
}

function openRelationshipWith(accessionId: string) {
  relationshipNode2.value = accessionId;
  relationshipVisible.value = true;
}

function openLineageGraph() {
  graphVisible.value = true;
}

async function loadPageData() {
  if (!germplasmId.value) {
    detailData.value = null;
    breedingMaterials.value = [];
    return;
  }
  loading.value = true;
  try {
    let taxonomyTaxId = routeTaxonomyTaxId.value;
    if (!taxonomyTaxId) {
      const [listResult, taxonomyResult] = await Promise.all([
        getGermplasmListApi({
          page: 1,
          size: 2,
          keyword: germplasmId.value,
        }),
        getGermplasmTaxonomyOptionsApi({
          limit: 5,
          active_only: 1,
        }),
      ]);
      const matchedItems =
        (listResult as any)?.items ?? (listResult as any)?.data?.items ?? [];
      const taxonomyItems =
        (taxonomyResult as any)?.items ??
        (taxonomyResult as any)?.data?.items ??
        [];
      if (matchedItems.length === 1) {
        taxonomyTaxId =
          matchedItems[0]?.taxonomy_tax_id || matchedItems[0]?.taxonomy?.tax_id;
      } else if (taxonomyItems.length === 1) {
        taxonomyTaxId = taxonomyItems[0]?.tax_id;
      }
    }

    resolvedTaxonomyTaxId.value = taxonomyTaxId;
    if (!taxonomyTaxId) {
      detailData.value = null;
      breedingMaterials.value = [];
      breedingPrograms.value = [];
      return;
    }

    const [detailResponse, materialResult, programResult] = await Promise.all([
      getGermplasmDetailApi(germplasmId.value, taxonomyTaxId),
      getBreedingMaterialListApi({
        page: 1,
        size: 100,
        keyword: germplasmId.value,
      }),
      getBreedingProgramListApi({
        page: 1,
        size: 100,
      }),
    ]);
    detailData.value = (detailResponse as any)?.data ?? (detailResponse as any);
    breedingMaterials.value = (materialResult.items || []).filter(
      (item) => item.germplasm_accession === germplasmId.value,
    );
    breedingPrograms.value = programResult.items || [];
  } finally {
    loading.value = false;
  }
}

watch(
  () => [germplasmId.value, routeTaxonomyTaxId.value],
  () => {
    void loadPageData();
  },
  { immediate: true },
);

onMounted(() => {
  void loadPageData();
});
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <div class="germplasm-info-page">
      <Card :bordered="false" class="hero-card">
        <template #extra>
          <Button type="primary" @click="backToList">{{ $t('germplasm.detail.backToList') }}</Button>
        </template>
        <div class="hero-eyebrow">{{ $t('germplasm.detail.heroEyebrow') }}</div>
        <h2 class="hero-title">{{ $t('germplasm.detail.title') }}</h2>
        <p class="hero-description">
          {{ $t('germplasm.detail.detailPageDescription') }}
        </p>
      </Card>

      <Spin :spinning="loading">
        <template v-if="germplasmId">
          <div class="summary-grid">
            <Card :bordered="false">
              <div class="summary-label">{{ $t('germplasm.detail.germplasmId') }}</div>
              <div class="summary-value">{{ germplasmId }}</div>
            </Card>
            <Card :bordered="false">
              <div class="summary-label">{{ $t('germplasm.detail.parentCount') }}</div>
              <div class="summary-value">
                {{ detailData?.lineage_summary?.parent_count || 0 }}
              </div>
            </Card>
            <Card :bordered="false">
              <div class="summary-label">{{ $t('germplasm.detail.breedingMaterials') }}</div>
              <div class="summary-value">
                {{ breedingMaterials.length }}
              </div>
            </Card>
            <Card :bordered="false">
              <div class="summary-label">{{ $t('germplasm.detail.childCount') }}</div>
              <div class="summary-value">
                {{ detailData?.lineage_summary?.child_count || 0 }}
              </div>
            </Card>
          </div>

          <div class="content-grid">
            <Card :bordered="false" :title="$t('germplasm.detail.overview')">
              <Descriptions bordered :column="1">
                <Descriptions.Item
                  v-for="item in fixedFieldItems"
                  :key="item.label"
                  :label="item.label"
                >
                  {{ item.value }}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card :bordered="false" :title="$t('germplasm.detail.breedingReference')">
              <div
                v-if="breedingReferenceGroups.length > 0"
                class="reference-list"
              >
                <div
                  v-for="group in breedingReferenceGroups"
                  :key="group.programId"
                  class="reference-item"
                >
                  <div class="reference-header">
                    <div>
                      <div class="reference-title">
                        {{
                          group.program?.name || $t('germplasm.detail.unnamedProgram', { id: group.programId })
                        }}
                      </div>
                      <div class="reference-subtitle">
                        {{ group.program?.code || '-' }}
                      </div>
                    </div>
                    <Button
                      size="small"
                      @click="openBreedingProgram(group.programId)"
                    >
                      {{ $t('germplasm.detail.openProgram') }}
                    </Button>
                  </div>
                  <div class="reference-tags">
                    <Tag
                      v-for="item in group.materials"
                      :key="item.id"
                      color="blue"
                    >
                      {{ item.material_code }} / {{ item.material_name }}
                    </Tag>
                  </div>
                </div>
              </div>
              <Empty v-else :description="$t('germplasm.detail.notReferenced')" />
            </Card>
          </div>

          <div class="content-grid">
            <Card :bordered="false" :title="$t('germplasm.detail.lineageRelationship')">
              <template #extra>
                <Button size="small" @click="openLineageGraph">{{ $t('germplasm.list.viewLineage') }}</Button>
              </template>
              <div class="reference-list">
                <div class="reference-item">
                  <div class="reference-title">{{ $t('germplasm.detail.parents') }}</div>
                  <div
                    v-if="detailData?.lineage_summary?.parents?.length"
                    class="reference-tags"
                  >
                    <Tag
                      v-for="parent in detailData.lineage_summary.parents"
                      :key="`${parent.parent_role}-${parent.parent_accession}`"
                      color="cyan"
                      class="clickable-tag"
                      @click="openRelationshipWith(parent.parent_accession)"
                    >
                      {{ parent.parent_role === 'father' ? $t('germplasm.detail.father') : $t('germplasm.detail.mother') }} /
                      {{ parent.parent_accession }}
                    </Tag>
                  </div>
                  <Empty v-else :description="$t('germplasm.detail.noParents')" />
                </div>
                <div class="reference-item">
                  <div class="reference-title">{{ $t('germplasm.detail.children') }}</div>
                  <div
                    v-if="detailData?.lineage_summary?.children?.length"
                    class="reference-tags"
                  >
                    <Tag
                      v-for="child in detailData.lineage_summary.children"
                      :key="`${child.parent_role}-${child.child_accession}`"
                      color="gold"
                      class="clickable-tag"
                      @click="openRelationshipWith(child.child_accession)"
                    >
                      {{ child.child_accession }}
                    </Tag>
                  </div>
                  <Empty v-else :description="$t('germplasm.detail.noChildren')" />
                </div>
              </div>
            </Card>

            <Card :bordered="false" :title="$t('germplasm.detail.dynamicFields')">
              <Descriptions
                v-if="dynamicAttributeItems.length > 0"
                bordered
                :column="1"
              >
                <Descriptions.Item
                  v-for="item in dynamicAttributeItems"
                  :key="item.key"
                  :label="item.key"
                >
                  <div v-if="isLongText(item.value)" class="long-text">
                    <pre>{{ formatValue(item.value) }}</pre>
                  </div>
                  <span v-else>{{ formatValue(item.value) }}</span>
                </Descriptions.Item>
              </Descriptions>
              <Empty v-else :description="$t('germplasm.detail.noDynamicFields')" />
            </Card>
          </div>

          <div class="content-grid">
            <Card :bordered="false" :title="$t('germplasm.detail.fieldSchemaSnapshot')">
              <div v-if="dynamicFieldSchema.length > 0" class="schema-grid">
                <div
                  v-for="field in dynamicFieldSchema"
                  :key="`${field.field_key}-${field.source_header}`"
                  class="schema-item"
                >
                  <div class="schema-title-row">
                    <div class="schema-title">{{ field.field_label }}</div>
                    <Tag :color="fieldSchemaTagColor(field)">
                      {{ field.data_type }}
                    </Tag>
                  </div>
                  <div class="schema-meta">
                    {{ $t('germplasm.detail.sourceColumnName') }} {{ field.source_header }}
                  </div>
                  <div class="schema-meta">{{ $t('germplasm.detail.systemKey') }} {{ field.field_key }}</div>
                </div>
              </div>
              <Empty v-else :description="$t('germplasm.detail.noFieldSchema')" />
            </Card>

            <Card :bordered="false" :title="$t('germplasm.detail.importAudit')">
              <Descriptions bordered :column="1">
                <Descriptions.Item :label="$t('germplasm.detail.batchCode')">
                  {{ detailData?.audit?.batch_code || '-' }}
                </Descriptions.Item>
                <Descriptions.Item :label="$t('germplasm.detail.sourceFile')">
                  {{ detailData?.audit?.source_filename || '-' }}
                </Descriptions.Item>
                <Descriptions.Item :label="$t('germplasm.detail.originalPath')">
                  {{ detailData?.audit?.source_file_path || '-' }}
                </Descriptions.Item>
                <Descriptions.Item :label="$t('germplasm.detail.excelRow')">
                  {{ detailData?.audit?.source_row_no || '-' }}
                </Descriptions.Item>
                <Descriptions.Item :label="$t('germplasm.detail.createdAt')">
                  {{ detailData?.audit?.created_at || '-' }}
                </Descriptions.Item>
                <Descriptions.Item :label="$t('germplasm.detail.updatedAt')">
                  {{ detailData?.audit?.updated_at || '-' }}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </div>
        </template>

        <Empty
          v-else
          :description="$t('germplasm.detail.noParam')"
        />
      </Spin>
    </div>
    <RelationshipModal
      v-model:open="relationshipVisible"
      :taxonomy-tax-id="resolvedTaxonomyTaxId"
      :accession-id1="germplasmId"
      :accession-id2="relationshipNode2"
      :batch-id="detailData?.audit?.batch_id"
    />
    <GermplasmGraphModal
      v-model:open="graphVisible"
      :taxonomy-tax-id="resolvedTaxonomyTaxId"
      :batch-id="detailData?.audit?.batch_id"
      :selected-nodes="[germplasmId]"
    />
  </Page>
</template>

<style scoped lang="less">
.germplasm-info-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card {
  background:
    radial-gradient(
      circle at top right,
      rgba(22, 119, 255, 0.12),
      transparent 36%
    ),
    linear-gradient(135deg, #f8fbff 0%, #f6f8fc 100%);
}

.hero-eyebrow {
  color: #1677ff;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-title {
  margin: 8px 0;
  color: #13213a;
  font-size: 28px;
  font-weight: 700;
}

.hero-description {
  max-width: 860px;
  margin: 0;
  color: #516074;
  line-height: 1.7;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-label {
  color: #6a778b;
  font-size: 13px;
}

.summary-value {
  margin-top: 8px;
  color: #13213a;
  font-size: 28px;
  font-weight: 700;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.reference-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reference-item {
  padding: 14px;
  border-radius: 12px;
  background: #f8fbff;
}

.reference-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.reference-title {
  color: #13213a;
  font-weight: 700;
}

.reference-subtitle {
  margin-top: 4px;
  color: #6a778b;
  font-size: 12px;
}

.reference-tags,
.neighbor-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.clickable-tag {
  cursor: pointer;
}

.long-text {
  max-height: 240px;
  overflow-y: auto;
}

.long-text pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.schema-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.schema-item {
  padding: 14px;
  border-radius: 12px;
  background: #f8fbff;
}

.schema-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.schema-title {
  color: #13213a;
  font-weight: 700;
}

.schema-meta {
  margin-top: 8px;
  color: #6a778b;
  font-size: 12px;
}

@media (max-width: 960px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid {
    grid-template-columns: 1fr;
  }

  .schema-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .reference-header {
    flex-direction: column;
  }
}
</style>
