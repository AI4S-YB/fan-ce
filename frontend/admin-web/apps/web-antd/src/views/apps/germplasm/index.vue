<script setup lang="ts">
import type { GermplasmItem } from './types';

import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { Button, Switch, message } from 'ant-design-vue';

import { $t } from '@vben/locales';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { TableAction } from '#/components/Table';

import GermplasmGraphModal from './components/GraphModal.vue';
import StatisticsModal from './components/StatisticsModal.vue';
import { formOptions, gridOptions } from './data';
import { setGermplasmPublicApi } from './api';

const route = useRoute();
const router = useRouter();
const initialTaxonomyTaxId =
  Number(route.query.taxonomy_tax_id || 0) || undefined;
const initialBatchId = Number(route.query.batch_id || 0) || undefined;
const currentTaxonomyTaxId = ref<number | undefined>(initialTaxonomyTaxId);
const currentBatchId = ref<number | undefined>(initialBatchId);
const statisticsVisible = ref(false);
const graphVisible = ref(false);
const graphSelectedNodes = ref<string[]>([]);

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: gridOptions(null), // 先传null，组件挂载后会更新
  formOptions: formOptions(
    initialTaxonomyTaxId,
    initialBatchId,
    (taxonomyTaxId) => {
      currentTaxonomyTaxId.value = taxonomyTaxId;
    },
    (batchId) => {
      currentBatchId.value = batchId;
    },
    (batchId) => {
      currentBatchId.value = batchId;
    },
  ),
});

// 组件挂载后，更新gridOptions以传递gridApi
onMounted(() => {
  // 重新设置gridOptions，这次传入gridApi，以便在查询完成后自动更新动态列
  gridApi.setGridOptions(gridOptions(gridApi));
  if (currentBatchId.value !== undefined) {
    void gridApi.formApi?.setFieldValue?.('batch_id', currentBatchId.value);
  }
});

watch(
  () => currentBatchId.value,
  async (batchId) => {
    const formApi = gridApi.formApi;
    if (!formApi?.isMounted) {
      return;
    }
    const currentFormBatchId = await formApi.getFieldValue?.('batch_id');
    if ((currentFormBatchId ?? undefined) === (batchId ?? undefined)) {
      return;
    }
    await formApi.setFieldValue?.('batch_id', batchId);
  },
);

function openDetail(row: GermplasmItem) {
  router.push({
    path: '/germplasm/info',
    query: {
      id: row.accession_id || row.id,
      taxonomy_tax_id: String(
        row.taxonomy_tax_id || row.taxonomy?.tax_id || '',
      ),
    },
  });
}

function openImportPage() {
  router.push('/germplasm/import');
}

function openImportBatchPage() {
  router.push('/germplasm/import-batches');
}

function openStatisticsModal() {
  if (!currentTaxonomyTaxId.value) {
    return;
  }
  statisticsVisible.value = true;
}

function openFullGraphModal() {
  if (!currentTaxonomyTaxId.value) {
    return;
  }
  graphSelectedNodes.value = [];
  graphVisible.value = true;
}

async function togglePublic(row: GermplasmItem, checked: boolean) {
  try {
    await setGermplasmPublicApi({
      accession_id: row.accession_id || row.id,
      taxonomy_tax_id: row.taxonomy_tax_id!,
      is_public: checked,
    });
    row.is_public = checked;
    message.success(checked ? $t('germplasm.list.publicOn') : $t('germplasm.list.publicOff'));
  } catch (e: any) {
    message.error(e?.message || 'Failed');
  }
}

function openRowGraph(row: GermplasmItem) {
  currentTaxonomyTaxId.value = row.taxonomy_tax_id || row.taxonomy?.tax_id;
  graphSelectedNodes.value = [row.accession_id || row.id];
  graphVisible.value = true;
}
</script>

<template>
  <Page auto-content-height>
    <Grid
      :table-title="$t('germplasm.list.title')"
      :table-title-help="$t('germplasm.list.titleHelp')"
    >
      <template #toolbar-tools>
        <Button :disabled="!currentTaxonomyTaxId" @click="openStatisticsModal">
          {{ $t('germplasm.list.viewStats') }}
        </Button>
        <Button :disabled="!currentTaxonomyTaxId" @click="openFullGraphModal">
          {{ $t('germplasm.list.lineage') }}
        </Button>
        <Button @click="openImportBatchPage">{{ $t('germplasm.list.importBatch') }}</Button>
        <Button type="primary" @click="openImportPage">{{ $t('germplasm.list.import') }}</Button>
      </template>
      <template #is_public="{ row }">
        <Switch :checked="row.is_public" size="small" @update:checked="(v: boolean) => togglePublic(row, v)" />
      </template>
      <template #action="{ row }">
        <TableAction
          type="color:red"
          :outside="true"
          :actions="[
            {
              icon: 'proicons:info-square',
              danger: false,
              label: $t('germplasm.list.detail'),
              auth: 'app:germplasm:info',
              size: 'small',
              onClick: openDetail.bind(null, row),
            },
            {
              icon: 'carbon:chart-relationship',
              danger: false,
              label: $t('germplasm.list.lineage'),
              size: 'small',
              onClick: openRowGraph.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
    <StatisticsModal
      v-model:open="statisticsVisible"
      :taxonomy-tax-id="currentTaxonomyTaxId"
      :batch-id="currentBatchId"
    />
    <GermplasmGraphModal
      v-model:open="graphVisible"
      :taxonomy-tax-id="currentTaxonomyTaxId"
      :batch-id="currentBatchId"
      :selected-nodes="graphSelectedNodes"
    />
  </Page>
</template>

<style scoped>
/* 移除行点击相关样式 */
</style>
