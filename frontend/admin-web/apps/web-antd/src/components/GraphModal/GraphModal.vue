<template>
  <Modal
    v-model:open="visible"
    :title="modalTitle"
    width="90%"
    :footer="null"
    :destroyOnClose="true"
    @cancel="handleCancel"
  >
    <div class="graph-modal-content">
      <div class="control-bar">
        <Space>
          <Button type="primary" @click="loadGraphData" :loading="loading">
            <template #icon>
              <ReloadOutlined />
            </template>
            {{ $t('component.graph.reload') }}
          </Button>
          
          <!-- 关系类型选择 -->
          <div v-if="showRelationshipControls" class="control-group">
            <Tooltip :title="$t('component.graph.internalRelationTooltip')">
              <Checkbox v-model:checked="includeInternal" @change="handleRelationshipChange">
                {{ $t('component.graph.internalRelation') }}
              </Checkbox>
            </Tooltip>
            <Tooltip :title="$t('component.graph.externalRelationTooltip')">
              <Checkbox v-model:checked="includeExternal" @change="handleRelationshipChange">
                {{ $t('component.graph.externalRelation') }}
              </Checkbox>
            </Tooltip>
          </div>
          
          <!-- 过滤参数 -->
          <div class="control-group">
            <InputNumber
              v-model:value="maxNodes"
              :min="10"
              :max="100"
              :placeholder="$t('component.graph.maxNodes')"
              style="width: 130px"
              @change="handleFilterChange"
            />
            <span class="control-label">{{ $t('component.graph.maxNodes') }}</span>
          </div>

          <div class="control-group">
            <InputNumber
              v-model:value="minDegree"
              :min="0"
              :max="20"
              :placeholder="$t('component.graph.minConnections')"
              style="width: 130px"
              @change="handleFilterChange"
            />
            <span class="control-label">{{ $t('component.graph.minConnections') }}</span>
          </div>
        </Space>
        <div class="stats-info">
          {{ $t('component.graph.nodes') }}: {{ filteredGraphData.nodes.length }}
          <span v-if="rawGraphData.nodes.length !== filteredGraphData.nodes.length" class="raw-count">
            / {{ rawGraphData.nodes.length }}
          </span>
          | {{ $t('component.graph.connections') }}: {{ filteredGraphData.edges.length }}
          <span v-if="rawGraphData.edges.length !== filteredGraphData.edges.length" class="raw-count">
            / {{ rawGraphData.edges.length }}
          </span>
          <span v-if="showRelationshipControls && selectedNodes && selectedNodes.length > 0" class="relationship-info">
            | {{ getRelationshipTypeText() }}
          </span>
        </div>
      </div>

      <div class="graph-wrapper" :style="{ height: modalHeight + 'px' }">
        <KnowledgeGraph
          :data="filteredGraphData"
          :width="modalWidth"
          :height="modalHeight"
          :loading="loading"
          @nodeClick="handleNodeClick"
        />
      </div>
    </div>

    <!-- 节点详情弹窗 -->
    <Modal
      v-model:open="nodeDetailVisible"
      :title="`${$t('component.graph.nodeDetail')} - ${selectedNode?.id}`"
      :footer="null"
      width="500px"
    >
      <Descriptions v-if="selectedNode" bordered :column="1" size="small">
        <DescriptionsItem :label="$t('component.graph.nodeId')">{{ selectedNode.id }}</DescriptionsItem>
        <DescriptionsItem :label="$t('component.graph.connectionCount')">{{ selectedNode.degree }}</DescriptionsItem>

        <!-- 动态显示属性 -->
        <template v-if="selectedNode.attributes">
          <DescriptionsItem
            v-for="(value, key) in filteredAttributes"
            :key="key"
            :label="formatLabel(String(key))"
          >
            <span v-if="Array.isArray(value)">{{ value.join(', ') }}</span>
            <span v-else>{{ value }}</span>
          </DescriptionsItem>
        </template>
      </Descriptions>
    </Modal>
  </Modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue';
import {
  Modal,
  Button,
  Space,
  InputNumber,
  Descriptions,
  DescriptionsItem,
  Checkbox,
  Tooltip,
  message
} from 'ant-design-vue';
import { ReloadOutlined } from '@ant-design/icons-vue';
import { $t } from '@vben/locales';
import { KnowledgeGraph } from '#/components/KnowledgeGraph';
import { useKnowledgeGraph } from '#/components/KnowledgeGraph/useKnowledgeGraph';
import type { GraphData, GraphNode } from '#/components/KnowledgeGraph/types';

interface Props {
  open: boolean;
  title?: string;
  filePath?: string;
  requestParams?: Record<string, any>;
  selectedNodes?: string[];
  showRelationshipControls?: boolean;
  dataLoader?: (params: any) => Promise<any>;
  listDataLoader?: (params: any) => Promise<any>;
  buildOptions?: {
    parentKey?: string;
    motherKey?: string;
    enableCrossingEdges?: boolean;
  };
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = withDefaults(defineProps<Props>(), {
  title: $t('component.graph.knowledgeGraph'),
  showRelationshipControls: true,
  buildOptions: () => ({
    parentKey: 'P',
    motherKey: 'M',
    enableCrossingEdges: true,
  }),
});
const emit = defineEmits<Emits>();

// 响应式数据
const visible = ref(false);

// 使用知识图谱Hook
const {
  loading,
  filteredGraphData,
  rawGraphData,
  maxNodes,
  minDegree,
  buildGraphFromData,
  setFilters,
  resetGraph,
  applyFilters
} = useKnowledgeGraph();

const nodeDetailVisible = ref(false);
const selectedNode = ref<GraphNode | null>(null);

// 关系查询参数
const includeInternal = ref(true);  // 包含内部关系
const includeExternal = ref(true);  // 包含外部关系

// 模态框尺寸
const modalWidth = ref(1400);
const modalHeight = ref(700);

// 计算模态框标题
const modalTitle = computed(() => props.title);

// 计算过滤后的属性
const filteredAttributes = computed(() => {
  if (!selectedNode.value?.attributes) return {};

  const attrs = { ...selectedNode.value.attributes };
  // 排除一些不需要显示的属性
  delete attrs.neighbors;
  delete attrs.neighbor_count;

  return attrs;
});

// 格式化标签
const formatLabel = (key: string): string => {
  const labelMap: Record<string, string> = {
    'id': 'ID',
    'degree': $t('component.graph.degree'),
    'neighbor_count': $t('component.graph.neighborCount'),
    // 可以添加更多的标签映射
  };

  return labelMap[key] || key;
};

// 获取关系类型描述
const getRelationshipTypeText = (): string => {
  const types = [];
  if (includeInternal.value) types.push($t('component.graph.internal'));
  if (includeExternal.value) types.push($t('component.graph.external'));
  return types.length > 0 ? `${types.join('+')}${$t('component.graph.relation')}` : '';
};

// 监听打开状态
watch(
  () => props.open,
  async (val) => {
    visible.value = val;
    if (val && (props.filePath || props.requestParams)) {
      await nextTick();
      updateModalSize();
      await loadGraphData();
    }
  },
  { immediate: true }
);

watch(
  () => visible.value,
  (v) => emit('update:open', v)
);

// 更新模态框尺寸
const updateModalSize = () => {
  // 根据窗口大小调整图谱尺寸
  const windowWidth = window.innerWidth;
  const windowHeight = window.innerHeight;

  modalWidth.value = Math.min(windowWidth * 0.85, 1400);
  modalHeight.value = Math.min(windowHeight * 0.7, 700);
};

// 加载图谱数据
const loadGraphData = async () => {
  if (!props.filePath && !props.requestParams) {
    message.warning($t('component.graph.queryParamsEmpty'));
    return;
  }

  try {
    let graphData: GraphData;
    const baseParams = {
      ...(props.requestParams || {}),
      ...(props.filePath ? { file_path: props.filePath } : {}),
    };

    if (props.selectedNodes && props.selectedNodes.length > 0 && props.dataLoader) {
      // 基于勾选节点获取批量关系数据
      const response = await props.dataLoader({
        ...baseParams,
        selected_nodes: props.selectedNodes,
        include_internal: includeInternal.value,
        include_external: includeExternal.value,
        max_connections_per_node: 30,
      });
      const graphResponse = response?.data ?? response;

      if (graphResponse?.nodes && graphResponse?.edges) {
        // 直接使用批量接口返回的图谱数据
        graphData = {
          nodes: graphResponse.nodes.map((node: any) => ({
            id: node.id,
            label: node.label || node.id,
            degree: node.degree,
            attributes: node.attributes,
            // 标记勾选的节点
            selected: node.selected || false
          })),
          edges: graphResponse.edges.map((edge: any) => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            relationshipType: edge.relationship_type,
            weight: edge.weight || 1
          }))
        };

        // 使用Hook设置图谱数据
        resetGraph();
        const { nodes, edges } = graphData;
        // 先设置原始数据，再应用过滤器
        rawGraphData.value = { nodes, edges };
        applyFilters();

        const relationshipTypes: string[] = [];
        if (includeInternal.value) relationshipTypes.push($t('component.graph.internalRelation'));
        if (includeExternal.value) relationshipTypes.push($t('component.graph.externalRelation'));

        message.success($t('component.graph.loadSuccessWithRelation', { nodes: nodes.length, edges: edges.length, types: relationshipTypes.join('+') }));
      } else {
        message.error($t('component.graph.batchFailed'));
      }
    } else if (props.listDataLoader) {
      // 获取所有数据（原有逻辑）
      const response = await props.listDataLoader({
        ...baseParams,
        page: 1,
        page_size: 10000,
      });
      const listResponse = response?.data ?? response;

      if (listResponse?.items?.length !== 0) {
        const dataList = listResponse.items;

        // 使用Hook构建图谱数据
        graphData = buildGraphFromData(dataList, props.buildOptions);

        message.success($t('component.graph.loadSuccess', { nodes: graphData.nodes.length, edges: graphData.edges.length }));
      } else {
        message.error($t('component.graph.loadFailedData'));
      }
    } else {
      message.error($t('component.graph.noLoader'));
    }
  } catch (error) {
    console.error('加载图谱数据失败:', error);
    message.error($t('component.graph.loadFailed'));
  }
};

// 处理过滤器变化
const handleFilterChange = () => {
  setFilters({
    maxNodes: maxNodes.value,
    minDegree: minDegree.value,
  });
};

// 处理关系参数变化
const handleRelationshipChange = async () => {
  // 防止两个参数都被取消选中
  if (!includeInternal.value && !includeExternal.value) {
    message.warning($t('component.graph.selectOneRelation'));
    // 恢复到至少有一个选中的状态
    includeInternal.value = true;
    return;
  }
  
  // 如果有选中节点，自动重新加载数据
  if (props.selectedNodes && props.selectedNodes.length > 0 && (props.filePath || props.requestParams)) {
    await loadGraphData();
  }
};

// 处理节点点击
const handleNodeClick = (node: GraphNode) => {
  selectedNode.value = node;
  nodeDetailVisible.value = true;
};

// 处理关闭
const handleCancel = () => {
  visible.value = false;
  // 清理数据
  resetGraph();
  selectedNode.value = null;
};

// 窗口大小变化监听
onMounted(() => {
  window.addEventListener('resize', updateModalSize);
});
</script>

<style scoped>
.graph-modal-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.control-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  margin-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.control-label {
  margin-left: 8px;
  font-size: 12px;
  color: #8c8c8c;
}

.control-group {
  display: flex;
  gap: 8px;
  align-items: center;
}

.stats-info {
  font-size: 14px;
  font-weight: 500;
  color: #666;
}

.relationship-info {
  margin-left: 4px;
  font-size: 12px;
  color: #1890ff;
}

.raw-count {
  font-size: 12px;
  color: #999;
}

.graph-wrapper {
  flex: 1;
  overflow: hidden;
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
}

:deep(.ant-modal-body) {
  height: calc(90vh - 150px);
  padding: 24px;
}

:deep(.ant-descriptions-item-label) {
  font-weight: 500;
  background: #fafafa;
}

:deep(.ant-descriptions-item-content) {
  word-break: break-word;
}
</style>
