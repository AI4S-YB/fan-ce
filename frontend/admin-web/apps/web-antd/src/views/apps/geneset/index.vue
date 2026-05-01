<script lang="ts" setup>
import { ref, reactive } from 'vue';

import { Page } from '@vben/common-ui';
import { Select } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteGeneSetApi, getGeneSetByGenomeApi, getGeneSetDetailApi, getGenomeOptionsApi } from '#/api/apps/geneset';
import { Button } from '#/components/Button';
import { TableAction } from '#/components/Table';
import { IconEnum } from '#/enums/appEnum';
import { useMessage } from '#/hooks/web/useMessage';
import { $t as t } from '#/locales';
import { useProjectStoreWithOut } from '#/store/modules/project';

import { useSearchFormSchema } from './data';

defineOptions({ name: 'GeneSetList' });

const { createMessage } = useMessage();
const proStore = useProjectStoreWithOut();

// 当前选择的基因组文件路径
const selectedFilePath = ref<string>('');

// 基因组选项
const genomeOptions = ref<{label: string; value: string}[]>([]);

// 获取基因组选项列表
async function loadGenomeOptions() {
  try {
    const response = await getGenomeOptionsApi();
    genomeOptions.value = response || [];
  } catch (error) {
    console.error('获取基因组列表失败:', error);
    createMessage.error(t('geneset.list.fetchGenomeError'));
    // 如果接口调用失败，使用默认选项
    genomeOptions.value = [
      { label: t('geneset.list.fallbackGenomeLabel', { id: '82' }), value: '82' },
      { label: t('geneset.list.fallbackGenomeLabel', { id: '96' }), value: '96' },
    ];
  }
}

// 组件挂载时加载基因组选项
loadGenomeOptions();

// 懒加载展开行详情数据
const loadExpandMethod = async (params: any) => {
  if (!selectedFilePath.value || !params || !params.row) return;
  
  const { row } = params;
  const projectId = proStore.projectInfo?.id;
  if (!projectId) {
    createMessage.error(t('geneset.list.missingInfo'));
    return;
  }
  
  try {
    const res = await getGeneSetDetailApi({
      file_path: selectedFilePath.value,
      geneset_id: row.geneset_id,
      project_id: projectId,
      page: 1,
      size: 100,
    });
    
    // 将详情数据设置到行对象上
    row.detailList = res.dataList || [];
  } catch (error) {
    console.error('加载基因集详情失败:', error);
    createMessage.error(t('geneset.list.loadDetailError'));
    row.detailList = [];
  }
};

// 表格配置
const gridOptions = ref({
  columns: [
    { fixed: 'left', title: '', type: 'checkbox', width: 50 },
    {
      type: 'expand',
      width: 80,
      title: t('geneset.list.expand'),
      slots: { content: 'expand' },
    },
    {
      field: 'geneset_id',
      title: t('geneset.list.geneSetId'),
      width: 100,
      sortable: true,
    },
    {
      field: 'geneset_name',
      title: t('geneset.list.geneSetName'),
      width: 200,
      showOverflow: false,
    },
    {
      field: 'description',
      title: t('geneset.list.description'),
      width: 300,
      showOverflow: false,
    },
    {
      field: 'gene_count',
      title: t('geneset.list.geneCount'),
      width: 120,
      sortable: true,
    },
    {
      field: 'create_time',
      title: t('geneset.list.createTime'),
      width: 180,
      formatter: ({ cellValue }: any) => {
        return cellValue ? new Date(cellValue * 1000).toLocaleString() : '-';
      },
    },
    {
      field: 'action',
      title: t('geneset.list.action'),
      width: 120,
      fixed: 'right',
      slots: { default: 'action' },
    },
  ],
  border: true,
  minHeight: 500,
  exportConfig: {},
  keepSource: true,
  pagerConfig: {
    pageSize: 20,
  },
  expandConfig: {
    lazy: true,
    loadMethod: loadExpandMethod,
    expandAll: false,
  },
  proxyConfig: {
    autoLoad: false, // 初始不自动加载
    response: {
      result: 'dataList',
      total: 'total',
    },
    ajax: {
      query: async ({ page }: any) => {
        if (!selectedFilePath.value) {
          return { dataList: [], total: 0 };
        }
        
        const projectId = proStore.projectInfo?.id;
        const teamId = proStore.projectInfo?.id;
        
        if (!projectId || !teamId) {
          createMessage.error(t('geneset.list.missingInfo'));
          return { dataList: [], total: 0 };
        }
        
        return await getGeneSetByGenomeApi({
          file_path: selectedFilePath.value,
          team_id: teamId,
          project_id: projectId,
          page: page.currentPage,
          size: page.pageSize,
        });
      },
    },
  },
  id: 'main-geneset',
  rowConfig: {
    isHover: true,
  },
  customConfig: {
    storage: true,
  },
  toolbarConfig: {
    custom: true,
    export: true,
    import: false,
  },
});

const formOptions = {
  schemas: useSearchFormSchema(),
};

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: gridOptions.value,
  formOptions: formOptions,
});

// 处理基因组选择变化
function handleGenomeChange(filePath: string) {
  selectedFilePath.value = filePath;
  
  if (filePath) {
    // 重新查询数据
    setTimeout(() => {
      gridApi.grid.commitProxy('query');
    }, 100);
  } else {
    // 清空数据
    gridApi.grid.reloadData([]);
  }
}

// 处理操作
async function handleAction(action: string, row?: any) {
  switch (action) {
    case 'delete':
      await handleDelete(row);
      break;
    case 'batchDelete':
      await handleBatchDelete();
      break;
  }
}

// 删除单个基因集
async function handleDelete(row: any) {
  try {
    await deleteGeneSetApi({ id: row.geneset_id });
    createMessage.success(t('common.delSuccessText'));
    gridApi.grid.commitProxy('query');
  } catch (error) {
    console.error('删除基因集失败:', error);
    createMessage.error(t('geneset.list.deleteError'));
  }
}

// 批量删除基因集
async function handleBatchDelete() {
  const selectedRows = gridApi.grid.getCheckboxRecords();
  if (!selectedRows || selectedRows.length === 0) {
    createMessage.warning(t('geneset.list.selectFirst'));
    return;
  }

  try {
    const ids = selectedRows.map((row: any) => row.geneset_id);
    await deleteGeneSetApi({ ids });
    createMessage.success(t('common.delSuccessText'));
    gridApi.grid.commitProxy('query');
  } catch (error) {
    console.error('批量删除基因集失败:', error);
    createMessage.error(t('geneset.list.deleteError'));
  }
}
</script>

<template>
  <Page :height-offset="20" auto-content-height style="padding: 0">
    <!-- 基因组选择器 -->
    <div style="padding: 16px; margin-bottom: 16px; background: #f5f5f5;">
      <div style="display: flex; gap: 16px; align-items: center;">
        <span style="font-weight: 500;">{{ t('geneset.list.selectGenome') }}：</span>
        <Select
          v-model:value="selectedFilePath"
          :placeholder="t('geneset.list.placeholderGenome')"
          style="width: 200px;"
          @change="handleGenomeChange"
        >
          <Select.Option
            v-for="option in genomeOptions"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }}
          </Select.Option>
        </Select>
        <span v-if="!selectedFilePath" style=" font-size: 12px;color: #666;">
          {{ t('geneset.list.selectGenomeFirst') }}
        </span>
      </div>
    </div>

    <!-- 主表格：基因集列表（带行展开功能） -->
    <div v-if="selectedFilePath">
      <Grid>
        <template #toolbar-tools>
          <Button
            pre-icon="ant-design:delete-outlined"
            danger
            @click="handleAction('batchDelete')"
          >
          {{ t('geneset.list.batchDelete') }}
          </Button>
        </template>

        <!-- 展开行内容插槽 -->
        <template #expand="{ row }">
          <div style="padding: 16px; background: #fafafa;">
            <div style="margin-bottom: 12px; font-weight: 500; color: #666;">
              {{ t('geneset.list.detailOf') }}{{ row.geneset_id }}) - {{ t('geneset.list.totalGenes', { count: row.gene_count }) }}
            </div>
            
            <!-- 嵌套的基因详情表格 -->
            <div v-if="!row.detailList || row.detailList.length === 0" 
                 style=" padding: 20px; color: #999;text-align: center;">
              {{ t('geneset.list.noGeneData') }}
            </div>
            <div v-else style="max-height: 300px; overflow-y: auto; border: 1px solid #e8e8e8; border-radius: 4px;">
              <table style="width: 100%; border-collapse: collapse; background: white;">
                <thead style=" position: sticky; top: 0; z-index: 1;background: #f5f5f5;">
                  <tr>
                    <th style="padding: 8px 12px; font-weight: 500; text-align: left; border-bottom: 1px solid #e8e8e8;">ID</th>
                    <th style="padding: 8px 12px; font-weight: 500; text-align: left; border-bottom: 1px solid #e8e8e8;">{{ t('geneset.list.headerGeneId') }}</th>
                    <th style="padding: 8px 12px; font-weight: 500; text-align: left; border-bottom: 1px solid #e8e8e8;">{{ t('geneset.list.headerFilePath') }}</th>
                    <th style="padding: 8px 12px; font-weight: 500; text-align: left; border-bottom: 1px solid #e8e8e8;">{{ t('geneset.list.headerCreateTime') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(gene, index) in row.detailList" :key="gene.id" 
                      :style="{ backgroundColor: index % 2 === 1 ? '#fafafa' : 'white' }">
                    <td style="padding: 8px 12px; border-bottom: 1px solid #f0f0f0;">{{ gene.id }}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #f0f0f0;">{{ gene.gene_id }}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #f0f0f0;">{{ gene.file_path }}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #f0f0f0;">
                      {{ gene.create_time ? new Date(gene.create_time * 1000).toLocaleString() : '-' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>

        <template #action="{ row }">
          <TableAction
            :actions="[
              {
                icon: IconEnum.DELETE,
                danger: true,
                label: t('component.action.delete'),
                popConfirm: {
                  title: t('common.delMessage'),
                  placement: 'left',
                  confirm: handleAction.bind(null, 'delete', row),
                },
              },
            ]"
          />
        </template>
      </Grid>
    </div>

    <!-- 未选择基因组时的提示 -->
    <div
      v-else
      style="
        display: flex;
        align-items: center;
        justify-content: center;
        height: 300px;
        font-size: 16px;
        color: #999;
      "
    >
      {{ t('geneset.list.selectGenomeFirst') }}
    </div>
  </Page>
</template>

<style lang="scss" scoped>
:deep(.vxe-table--empty-content) {
  padding-top: 20px;
  padding-bottom: 10px;
}
</style> 
