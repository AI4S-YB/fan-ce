<script setup lang="ts">
import type { BreedingProgramItem } from '#/api/breeding/program';

import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { $t } from '@vben/locales';

import { Button, Card, Input, Select, Space, Table, Tag } from 'ant-design-vue';

import { getBreedingProgramListApi } from '#/api/breeding/program';

defineOptions({ name: 'BreedingProgramListPage' });

const router = useRouter();

const loading = ref(false);
const rows = ref<BreedingProgramItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);

const filters = reactive({
  keyword: '',
  species_name: undefined as string | undefined,
  status: undefined as string | undefined,
});

const resultSummary = computed(() => {
  return rows.value.reduce(
    (acc, item) => {
      const counts = item.summary_counts || {
        materials: 0,
        trials: 0,
        plots: 0,
        observations: 0,
        biosamples: 0,
        assays: 0,
        data_files: 0,
      };
      acc.materials += counts.materials;
      acc.observations += counts.observations;
      acc.biosamples += counts.biosamples;
      acc.assays += counts.assays;
      acc.dataFiles += counts.data_files;
      return acc;
    },
    {
      materials: 0,
      observations: 0,
      biosamples: 0,
      assays: 0,
      dataFiles: 0,
    },
  );
});

const activeCount = computed(
  () => rows.value.filter(item => item.status === 'active').length,
);

const statusOptions = [
  { label: $t('breeding.list.active'), value: 'active' },
  { label: $t('breeding.list.archived'), value: 'archived' },
  { label: $t('breeding.list.draft'), value: 'draft' },
];

const columns = [
  { title: $t('breeding.list.programCode'), dataIndex: 'code', key: 'code', width: 140 },
  { title: $t('breeding.list.programInfo'), dataIndex: 'name', key: 'project', minWidth: 320 },
  { title: $t('breeding.list.species'), dataIndex: 'species_name', key: 'species_name', width: 140 },
  { title: $t('breeding.list.startYear'), dataIndex: 'start_year', key: 'start_year', width: 100 },
  { title: $t('breeding.list.scale'), key: 'scale', minWidth: 280 },
  { title: $t('breeding.list.status'), dataIndex: 'status', key: 'status', width: 100 },
  { title: $t('breeding.list.owner'), dataIndex: 'owner_name', key: 'owner_name', width: 140 },
  { title: $t('breeding.list.updatedAt'), dataIndex: 'updated_at', key: 'updated_at', width: 200 },
  { title: $t('breeding.list.action'), key: 'action', width: 120 },
];

const paginationConfig = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: total.value,
  showSizeChanger: true,
  showTotal: (value: number) => $t('component.table.total', { total: value }),
}));

function statusColor(status?: string | null) {
  if (status === 'active') {
    return 'green';
  }
  if (status === 'archived') {
    return 'orange';
  }
  if (status === 'draft') {
    return 'blue';
  }
  return 'default';
}

async function loadPrograms() {
  loading.value = true;
  try {
    const result = await getBreedingProgramListApi({
      page: page.value,
      size: pageSize.value,
      keyword: filters.keyword || undefined,
      species_name: filters.species_name,
      status: filters.status,
    });
    rows.value = result.items || [];
    total.value = result.total || 0;
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  page.value = 1;
  void loadPrograms();
}

function handleReset() {
  filters.keyword = '';
  filters.species_name = undefined;
  filters.status = undefined;
  page.value = 1;
  void loadPrograms();
}

function handleTableChange(pagination: { current?: number; pageSize?: number }) {
  page.value = pagination.current || 1;
  pageSize.value = pagination.pageSize || 10;
  void loadPrograms();
}

function openDetail(row: Record<string, any>) {
  router.push(`/breeding/program/detail/${row.id}`).catch((error) => {
    console.error('Navigation failed:', error);
  });
}

onMounted(() => {
  void loadPrograms();
});
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <div class="program-list-page">
      <Card :bordered="false" class="hero-card">
        <div class="hero-eyebrow">{{ $t('breeding.list.heroEyebrow') }}</div>
        <div class="hero-title-row">
          <div>
            <h2 class="hero-title">{{ $t('breeding.list.title') }}</h2>
          </div>
          <Button @click="loadPrograms">{{ $t('breeding.list.refresh') }}</Button>
        </div>
      </Card>

      <Card :bordered="false">
        <div class="result-summary-grid">
          <Card :bordered="false" class="summary-card">
            <div class="summary-label">{{ $t('breeding.list.programsInResult') }}</div>
            <div class="summary-value">{{ rows.length }}</div>
            <div class="summary-meta">{{ $t('breeding.list.totalHits', { count: total }) }}</div>
          </Card>
          <Card :bordered="false" class="summary-card">
            <div class="summary-label">{{ $t('breeding.list.activeProjects') }}</div>
            <div class="summary-value">{{ activeCount }}</div>
            <div class="summary-meta">{{ $t('breeding.list.activeProjectsHint') }}</div>
          </Card>
          <Card :bordered="false" class="summary-card">
            <div class="summary-label">{{ $t('breeding.list.totalMaterials') }}</div>
            <div class="summary-value">{{ resultSummary.materials }}</div>
            <div class="summary-meta">{{ $t('breeding.list.totalMaterialsHint') }}</div>
          </Card>
          <Card :bordered="false" class="summary-card">
            <div class="summary-label">{{ $t('breeding.list.totalObservations') }}</div>
            <div class="summary-value">{{ resultSummary.observations }}</div>
            <div class="summary-meta">{{ $t('breeding.list.totalObservationsHint') }}</div>
          </Card>
          <Card :bordered="false" class="summary-card">
            <div class="summary-label">{{ $t('breeding.list.omicsAssays') }}</div>
            <div class="summary-value">{{ resultSummary.assays }}</div>
            <div class="summary-meta">{{ $t('breeding.list.omicsAssaysHint') }}</div>
          </Card>
        </div>

        <div class="filter-bar">
          <Input
            v-model:value="filters.keyword"
            allow-clear
            :placeholder="$t('breeding.list.searchPlaceholder')"
            @press-enter="handleSearch"
          />
          <Input
            v-model:value="filters.species_name"
            allow-clear
            :placeholder="$t('breeding.list.speciesPlaceholder')"
            @press-enter="handleSearch"
          />
          <Select
            v-model:value="filters.status"
            allow-clear
            :options="statusOptions"
            :placeholder="$t('breeding.list.statusPlaceholder')"
          />
          <Space>
            <Button type="primary" @click="handleSearch">{{ $t('breeding.list.query') }}</Button>
            <Button @click="handleReset">{{ $t('breeding.list.reset') }}</Button>
          </Space>
        </div>

        <Table
          :columns="columns"
          :data-source="rows"
          :loading="loading"
          :pagination="paginationConfig"
          :scroll="{ x: 1200 }"
          row-key="id"
          @change="handleTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'project'">
              <div class="project-cell">
                <div class="project-name-row">
                  <span class="project-name">{{ record.name }}</span>
                  <Tag color="blue">{{ record.code }}</Tag>
                </div>
                <div class="project-goal">
                  {{ record.breeding_goal || $t('breeding.list.noBreedingGoal') }}
                </div>
                <div class="project-preview">
                  <div class="project-preview-group" v-if="record.preview_summary?.materials?.length">
                    <span class="project-preview-label">{{ $t('breeding.list.representativeMaterial') }}</span>
                    <div class="project-tag-list">
                      <Tag
                        v-for="item in record.preview_summary.materials"
                        :key="`${record.id}-material-${item.material_code}`"
                        :color="item.is_check ? 'gold' : 'blue'"
                      >
                        {{ item.material_code }}{{ item.is_check ? $t('breeding.list.checkAbbr') : '' }}
                      </Tag>
                    </div>
                  </div>
                  <div class="project-preview-group" v-if="record.preview_summary?.traits?.length">
                    <span class="project-preview-label">{{ $t('breeding.list.mainTraits') }}</span>
                    <div class="project-tag-list">
                      <Tag
                        v-for="item in record.preview_summary.traits"
                        :key="`${record.id}-trait-${item.trait_code}`"
                        color="green"
                      >
                        {{ item.trait_name }}
                      </Tag>
                    </div>
                  </div>
                  <div class="project-preview-group" v-if="record.preview_summary?.assay_types?.length">
                    <span class="project-preview-label">{{ $t('breeding.list.assayType') }}</span>
                    <div class="project-tag-list">
                      <Tag
                        v-for="item in record.preview_summary.assay_types"
                        :key="`${record.id}-assay-${item.assay_type}`"
                        color="cyan"
                      >
                        {{ item.assay_type }}
                      </Tag>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <template v-else-if="column.key === 'scale'">
              <div class="scale-grid">
                <div class="scale-item">
                  <span class="scale-label">{{ $t('breeding.list.material') }}</span>
                  <span class="scale-value">{{ record.summary_counts?.materials || 0 }}</span>
                </div>
                <div class="scale-item">
                  <span class="scale-label">{{ $t('breeding.list.observation') }}</span>
                  <span class="scale-value">{{ record.summary_counts?.observations || 0 }}</span>
                </div>
                <div class="scale-item">
                  <span class="scale-label">{{ $t('breeding.list.sample') }}</span>
                  <span class="scale-value">{{ record.summary_counts?.biosamples || 0 }}</span>
                </div>
                <div class="scale-item">
                  <span class="scale-label">{{ $t('breeding.list.experiment') }}</span>
                  <span class="scale-value">{{ record.summary_counts?.assays || 0 }}</span>
                </div>
                <div class="scale-item">
                  <span class="scale-label">{{ $t('breeding.list.file') }}</span>
                  <span class="scale-value">{{ record.summary_counts?.data_files || 0 }}</span>
                </div>
              </div>
            </template>
            <template v-else-if="column.key === 'status'">
              <Tag :color="statusColor(record.status)">
                {{ record.status || $t('breeding.list.unknown') }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <Button size="small" type="link" @click="openDetail(record)">
                {{ $t('breeding.list.viewDetail') }}
              </Button>
            </template>
          </template>
        </Table>
      </Card>
    </div>
  </Page>
</template>

<style scoped lang="less">
.program-list-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card {
  background:
    radial-gradient(circle at top right, rgba(22, 119, 255, 0.12), transparent 36%),
    linear-gradient(135deg, #f8fbff 0%, #f6f8fc 100%);
}

.hero-eyebrow {
  color: #1677ff;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-title-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
}

.hero-title {
  margin: 8px 0;
  color: #13213a;
  font-size: 26px;
  font-weight: 700;
}

.hero-description {
  max-width: 780px;
  margin: 0;
  color: #516074;
  line-height: 1.7;
}

.filter-bar {
  display: grid;
  grid-template-columns: minmax(220px, 1.5fr) minmax(160px, 1fr) 140px auto;
  gap: 12px;
  margin-bottom: 16px;
}

.result-summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-card {
  background:
    radial-gradient(circle at top right, rgba(22, 119, 255, 0.08), transparent 42%),
    linear-gradient(135deg, #fbfdff 0%, #f6f8fc 100%);
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

.summary-meta {
  margin-top: 6px;
  color: #6a778b;
  font-size: 12px;
}

.project-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.project-name-row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.project-name {
  color: #13213a;
  font-size: 15px;
  font-weight: 700;
}

.project-goal {
  display: -webkit-box;
  overflow: hidden;
  color: #516074;
  line-height: 1.7;
  text-overflow: ellipsis;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.project-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 2px;
}

.project-preview-group {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.project-preview-label {
  flex: 0 0 auto;
  min-width: 64px;
  color: #6a778b;
  font-size: 12px;
  line-height: 24px;
}

.project-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.scale-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.scale-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f8fbff;
}

.scale-label {
  color: #6a778b;
  font-size: 12px;
}

.scale-value {
  color: #13213a;
  font-size: 18px;
  font-weight: 700;
}

@media (max-width: 960px) {
  .hero-title-row {
    flex-direction: column;
  }

  .result-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-bar {
    grid-template-columns: 1fr;
  }

  .scale-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .project-preview-group {
    flex-direction: column;
    gap: 4px;
  }
}

@media (max-width: 640px) {
  .result-summary-grid {
    grid-template-columns: 1fr;
  }

  .scale-grid {
    grid-template-columns: 1fr;
  }
}
</style>
