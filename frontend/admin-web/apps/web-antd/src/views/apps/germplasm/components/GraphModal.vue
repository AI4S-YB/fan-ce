<script setup lang="ts">
import type { GermplasmItem } from '../types';
import type { GraphData, GraphNode } from '#/components/KnowledgeGraph/types';

import { ref, watch } from 'vue';

import { ReloadOutlined } from '@ant-design/icons-vue';
import { Button, message, Modal } from 'ant-design-vue';

import { $t } from '@vben/locales';
import { KnowledgeGraph } from '#/components/KnowledgeGraph';
import { filterGraphData } from '#/components/KnowledgeGraph/utils';

import { getGermplasmBatchRelationshipsApi, getGermplasmListApi } from '../api';

const MAX_NODES = 80;

const ROLE_COLORS = {
  selected: '#f59e0b',
  placeholder: '#cbd5e1',
} as const;

interface Props {
  open: boolean;
  taxonomyTaxId?: number;
  batchId?: number;
  selectedNodes?: string[];
}

const props = defineProps<Props>();
const emit = defineEmits<{ (e: 'update:open', value: boolean): void }>();

const visible = ref(false);
const loading = ref(false);
const graphData = ref<GraphData>({ edges: [], nodes: [] });

function buildGraphFromItems(items: GermplasmItem[]): GraphData {
  const nodes = new Map<string, GraphNode>();
  const edges: GraphData['edges'] = [];
  const edgeIds = new Set<string>();
  const degreeMap: Record<string, number> = {};

  items.forEach((item) => {
    const accessionId = item.accession_id || item.id;
    degreeMap[accessionId] = 0;
    nodes.set(accessionId, {
      id: accessionId,
      label: item.display_name || accessionId,
      degree: 0,
      attributes: {
        accession_id: accessionId,
        batch_code: item.batch_code,
        display_name: item.display_name,
        english_name: item.english_name,
        father_accession: item.father_accession,
        mother_accession: item.mother_accession,
        source_filename: item.source_filename,
        status: item.status,
        ...item.attributes,
      },
    });
  });

  const addEdge = (sourceId: string, targetId: string, relType: string) => {
    if (!nodes.has(sourceId) || !nodes.has(targetId)) return;
    const edgeId = `${sourceId}->${targetId}:${relType}`;
    if (edgeIds.has(edgeId)) return;
    edgeIds.add(edgeId);
    degreeMap[sourceId] = (degreeMap[sourceId] || 0) + 1;
    degreeMap[targetId] = (degreeMap[targetId] || 0) + 1;
    edges.push({
      id: edgeId,
      source: sourceId,
      target: targetId,
      relationshipType: relType,
      weight: 1,
    });
  };

  items.forEach((item) => {
    const accessionId = item.accession_id || item.id;
    if (item.father_accession) addEdge(item.father_accession, accessionId, 'father');
    if (item.mother_accession) addEdge(item.mother_accession, accessionId, 'mother');
  });

  nodes.forEach((node, nodeId) => {
    node.degree = degreeMap[nodeId] || 0;
  });

  return { edges, nodes: [...nodes.values()] };
}

function normalizeBatchGraph(response: any): GraphData {
  const nodes = ((response?.nodes || []) as any[]).map((node: any) => ({
    id: node.id,
    label: node.label || node.id,
    degree: Number(node.degree || 0),
    selected: Boolean(node.selected),
    attributes: {
      ...node.attributes,
      display_name: node.attributes?.display_name || node.label || node.id,
    },
  }));
  const edges = ((response?.edges || []) as any[]).map((edge: any) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    relationshipType: edge.relationship_type,
    weight: edge.weight || 1,
  }));
  return { edges, nodes };
}

function applySelectionHighlight(data: GraphData, selectedNodeIds: string[]) {
  const selectedSet = new Set(selectedNodeIds);
  data.nodes.forEach((node) => {
    if (selectedSet.has(node.id)) {
      node.color = ROLE_COLORS.selected;
    }
  });
}

async function loadGraphData() {
  if (!props.taxonomyTaxId) {
    message.warning($t('germplasm.graph.missingTaxonomyWarning'));
    return;
  }

  loading.value = true;
  try {
    const selectedNodeIds = [...new Set((props.selectedNodes || []).filter(Boolean))];
    const hasFocusedSelection = selectedNodeIds.length > 0;

    if (hasFocusedSelection) {
      const graphResponse = await getGermplasmBatchRelationshipsApi({
        batch_id: props.batchId,
        include_external: false,
        include_internal: true,
        max_connections_per_node: 30,
        selected_nodes: selectedNodeIds,
        taxonomy_tax_id: props.taxonomyTaxId,
      });
      graphData.value = normalizeBatchGraph(graphResponse);
    } else {
      const listResponse = await getGermplasmListApi({
        batch_id: props.batchId,
        page: 1,
        size: 10_000,
        status: 'active',
        taxonomy_tax_id: props.taxonomyTaxId,
      });
      const items =
        (listResponse as any)?.items ?? (listResponse as any)?.data?.items ?? [];
      graphData.value = buildGraphFromItems(items as GermplasmItem[]);
    }

    applySelectionHighlight(graphData.value, selectedNodeIds);
    graphData.value = filterGraphData(graphData.value, { maxNodes: MAX_NODES, minDegree: 0 });
  } catch (error) {
    console.error('load germplasm pedigree failed', error);
    message.error($t('germplasm.graph.loadError'));
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.open, props.taxonomyTaxId, props.batchId, props.selectedNodes?.join(',')],
  ([open]) => {
    visible.value = Boolean(open);
    if (!open) return;
    loadGraphData();
  },
  { immediate: true },
);

watch(() => visible.value, (value) => emit('update:open', value));
</script>

<template>
  <Modal
    v-model:open="visible"
    :title="$t('germplasm.graph.title')"
    width="95%"
    :footer="null"
    :destroy-on-close="true"
  >
    <div class="graph-modal">
      <div class="graph-toolbar">
        <span class="graph-summary">
          {{ $t('germplasm.graph.visibleMaterial') }}: {{ graphData.nodes.length }}
          &nbsp;|&nbsp;
          {{ $t('germplasm.graph.lineageEdge') }}: {{ graphData.edges.length }}
        </span>
        <Button type="primary" :loading="loading" @click="loadGraphData">
          <template #icon><ReloadOutlined /></template>
          {{ $t('germplasm.graph.refreshLineage') }}
        </Button>
      </div>
      <KnowledgeGraph
        :data="graphData"
        layout-mode="generation"
        :width="980"
        :height="620"
        :loading="loading"
      />
    </div>
  </Modal>
</template>

<style scoped lang="less">
.graph-modal {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.graph-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
}

.graph-summary {
  color: #6b7280;
  font-size: 13px;
}

:deep(.ant-modal-body) {
  background: #f5f7f2;
}
</style>
