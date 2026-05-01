<script setup lang="ts">
import type { GermplasmItem } from '../types';

import type { GraphData, GraphNode } from '#/components/KnowledgeGraph/types';

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import { ReloadOutlined } from '@ant-design/icons-vue';
import {
  Button,
  Card,
  Checkbox,
  Empty,
  InputNumber,
  message,
  Modal,
  Radio,
  Space,
  Tag,
} from 'ant-design-vue';

import { $t } from '@vben/locales';
import { KnowledgeGraph } from '#/components/KnowledgeGraph';
import {
  filterGraphData,
  findImportantNodes,
} from '#/components/KnowledgeGraph/utils';

import { getGermplasmBatchRelationshipsApi, getGermplasmListApi } from '../api';

interface Props {
  open: boolean;
  taxonomyTaxId?: number;
  batchId?: number;
  selectedNodes?: string[];
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const router = useRouter();

const visible = ref(false);
const loading = ref(false);
const includeInternal = ref(true);
const includeExternal = ref(true);
const layoutMode = ref<'force' | 'generation'>('generation');
const maxNodes = ref(120);
const minDegree = ref(0);
const graphWidth = ref(940);
const graphHeight = ref(700);
const rawGraphData = ref<GraphData>({ edges: [], nodes: [] });
const filteredGraphData = ref<GraphData>({ edges: [], nodes: [] });
const materialItems = ref<GermplasmItem[]>([]);
const activeNodeId = ref('');

const ROLE_COLORS = {
  current: '#f59e0b',
  currentSoft: 'rgba(245, 158, 11, 0.12)',
  father: '#2563eb',
  fatherSoft: 'rgba(37, 99, 235, 0.1)',
  mother: '#db2777',
  motherSoft: 'rgba(219, 39, 119, 0.1)',
  offspring: '#1f6d42',
  offspringSoft: 'rgba(31, 109, 66, 0.12)',
  placeholder: '#cbd5e1',
} as const;

const IMAGE_ATTRIBUTE_KEYS = [
  'image',
  'image_url',
  'photo',
  'photo_url',
  'picture',
  'picture_url',
  'thumbnail',
  'thumbnail_url',
  'cover_image',
  'cover_image_url',
] as const;

const NOTE_ATTRIBUTE_KEYS = [
  'remark',
  'remarks',
  'note',
  'notes',
  'memo',
  'comment',
  'comments',
  'description',
  'breeding_note',
  'collector_note',
] as const;

const selectedNodeIds = computed(() => {
  const items = props.selectedNodes || [];
  return [...new Set(items.filter(Boolean))];
});

const hasFocusedSelection = computed(() => selectedNodeIds.value.length > 0);

const materialMap = computed(() =>
  Object.fromEntries(
    materialItems.value.map((item) => [item.accession_id || item.id, item]),
  ),
);

const nodeMap = computed(() =>
  Object.fromEntries(
    filteredGraphData.value.nodes.map((node) => [node.id, node]),
  ),
);

const activeNode = computed(() => nodeMap.value[activeNodeId.value] || null);

const fatherEdgeCount = computed(
  () =>
    filteredGraphData.value.edges.filter(
      (edge) => edge.relationshipType === 'father',
    ).length,
);

const motherEdgeCount = computed(
  () =>
    filteredGraphData.value.edges.filter(
      (edge) => edge.relationshipType === 'mother',
    ).length,
);

const incomingCountMap = computed(() => {
  const counts: Record<string, number> = {};
  filteredGraphData.value.nodes.forEach((node) => {
    counts[node.id] = 0;
  });
  filteredGraphData.value.edges.forEach((edge) => {
    const targetId =
      typeof edge.target === 'string' ? edge.target : edge.target.id;
    counts[targetId] = (counts[targetId] || 0) + 1;
  });
  return counts;
});

const outgoingCountMap = computed(() => {
  const counts: Record<string, number> = {};
  filteredGraphData.value.nodes.forEach((node) => {
    counts[node.id] = 0;
  });
  filteredGraphData.value.edges.forEach((edge) => {
    const sourceId =
      typeof edge.source === 'string' ? edge.source : edge.source.id;
    counts[sourceId] = (counts[sourceId] || 0) + 1;
  });
  return counts;
});

const rootNodeCount = computed(
  () =>
    filteredGraphData.value.nodes.filter(
      (node) => (incomingCountMap.value[node.id] || 0) === 0,
    ).length,
);

const leafNodeCount = computed(
  () =>
    filteredGraphData.value.nodes.filter(
      (node) => (outgoingCountMap.value[node.id] || 0) === 0,
    ).length,
);

const focusCandidates = computed(() => {
  if (hasFocusedSelection.value) {
    return selectedNodeIds.value
      .map((nodeId) => nodeMap.value[nodeId])
      .filter(Boolean) as GraphNode[];
  }
  return findImportantNodes(filteredGraphData.value, 8);
});

const parentEdges = computed(() =>
  filteredGraphData.value.edges.filter((edge) => {
    const targetId =
      typeof edge.target === 'string' ? edge.target : edge.target.id;
    return targetId === activeNodeId.value;
  }),
);

const childEdges = computed(() =>
  filteredGraphData.value.edges.filter((edge) => {
    const sourceId =
      typeof edge.source === 'string' ? edge.source : edge.source.id;
    return sourceId === activeNodeId.value;
  }),
);

const fatherNode = computed(() => {
  const edge = parentEdges.value.find(
    (item) => item.relationshipType === 'father',
  );
  if (!edge) {
    return null;
  }
  const sourceId =
    typeof edge.source === 'string' ? edge.source : edge.source.id;
  return nodeMap.value[sourceId] || null;
});

const motherNode = computed(() => {
  const edge = parentEdges.value.find(
    (item) => item.relationshipType === 'mother',
  );
  if (!edge) {
    return null;
  }
  const sourceId =
    typeof edge.source === 'string' ? edge.source : edge.source.id;
  return nodeMap.value[sourceId] || null;
});

const childNodes = computed(
  () =>
    childEdges.value
      .map((edge) => {
        const targetId =
          typeof edge.target === 'string' ? edge.target : edge.target.id;
        return nodeMap.value[targetId];
      })
      .filter(Boolean) as GraphNode[],
);

const displayedGraphData = computed<GraphData>(() => {
  const fatherId = fatherNode.value?.id || '';
  const motherId = motherNode.value?.id || '';
  const childIdSet = new Set(childNodes.value.map((node) => node.id));

  return {
    edges: filteredGraphData.value.edges,
    nodes: filteredGraphData.value.nodes.map((node) => {
      let color = node.attributes?.is_placeholder
        ? ROLE_COLORS.placeholder
        : undefined;

      switch (true) {
        case node.id === activeNodeId.value: {
          color = ROLE_COLORS.current;
          break;
        }
        case node.id === fatherId: {
          color = ROLE_COLORS.father;
          break;
        }
        case node.id === motherId: {
          color = ROLE_COLORS.mother;
          break;
        }
        case childIdSet.has(node.id): {
          color = ROLE_COLORS.offspring;
          break;
        }
        default: {
          break;
        }
      }

      return {
        ...node,
        color,
      };
    }),
  };
});

const activeDisplayName = computed(() => {
  if (!activeNode.value) {
    return '-';
  }
  return (
    String(activeNode.value.attributes?.display_name || '').trim() ||
    materialMap.value[activeNode.value.id]?.display_name ||
    activeNode.value.label ||
    activeNode.value.id
  );
});

const activeEnglishName = computed(
  () => activeNode.value?.attributes?.english_name || '-',
);

const activeBatchCode = computed(() => {
  const item = materialMap.value[activeNodeId.value];
  return item?.batch_code || activeNode.value?.attributes?.batch_code || '-';
});

const activeSourceFilename = computed(() => {
  const item = materialMap.value[activeNodeId.value];
  return (
    item?.source_filename ||
    activeNode.value?.attributes?.source_filename ||
    '-'
  );
});

function findAttributeString(
  source: null | Record<string, any> | undefined,
  keys: readonly string[],
) {
  if (!source) {
    return '';
  }
  for (const key of keys) {
    const value = source[key];
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }
  return '';
}

const activeArchiveImage = computed(() => {
  const materialAttributes = materialMap.value[activeNodeId.value]?.attributes;
  return (
    findAttributeString(activeNode.value?.attributes, IMAGE_ATTRIBUTE_KEYS) ||
    findAttributeString(materialAttributes, IMAGE_ATTRIBUTE_KEYS)
  );
});

const activeArchiveNote = computed(() => {
  const materialAttributes = materialMap.value[activeNodeId.value]?.attributes;
  return (
    findAttributeString(activeNode.value?.attributes, NOTE_ATTRIBUTE_KEYS) ||
    findAttributeString(materialAttributes, NOTE_ATTRIBUTE_KEYS)
  );
});

const activeArchiveInitial = computed(() => {
  const seed = activeDisplayName.value || activeNode.value?.id || '?';
  return seed.trim().slice(0, 1).toUpperCase() || '?';
});

const fatherSnapshotName = computed(() => {
  const source = activeNode.value?.attributes || {};
  return (
    findAttributeString(source, ['father_name_snapshot']) ||
    fatherNode.value?.attributes?.display_name ||
    fatherNode.value?.label ||
    $t('germplasm.graph.unrecorded')
  );
});

const motherSnapshotName = computed(() => {
  const source = activeNode.value?.attributes || {};
  return (
    findAttributeString(source, ['mother_name_snapshot']) ||
    motherNode.value?.attributes?.display_name ||
    motherNode.value?.label ||
    $t('germplasm.graph.unrecorded')
  );
});

const attributeEntries = computed(() => {
  if (!activeNode.value?.attributes) {
    return [];
  }
  const ignoreKeys = new Set([
    'accession_id',
    'batch_code',
    'batch_id',
    'display_name',
    'english_name',
    'father_accession',
    'is_placeholder',
    'mother_accession',
    'source_filename',
    'status',
  ]);
  return Object.entries(activeNode.value.attributes)
    .filter(
      ([key, value]) =>
        !ignoreKeys.has(key) &&
        value !== null &&
        value !== undefined &&
        String(value).trim() !== '',
    )
    .slice(0, 10)
    .map(([key, value]) => ({
      key,
      value: typeof value === 'object' ? JSON.stringify(value) : String(value),
    }));
});

function updateGraphViewport() {
  graphWidth.value = Math.min(Math.max(window.innerWidth - 760, 640), 980);
  graphHeight.value = Math.min(Math.max(window.innerHeight - 300, 520), 760);
}

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

  const addEdge = (
    sourceId: string,
    targetId: string,
    relationshipType: string,
  ) => {
    if (!nodes.has(sourceId) || !nodes.has(targetId)) {
      return;
    }
    const edgeId = `${sourceId}->${targetId}:${relationshipType}`;
    if (edgeIds.has(edgeId)) {
      return;
    }
    edgeIds.add(edgeId);
    degreeMap[sourceId] = (degreeMap[sourceId] || 0) + 1;
    degreeMap[targetId] = (degreeMap[targetId] || 0) + 1;
    edges.push({
      id: edgeId,
      source: sourceId,
      target: targetId,
      relationshipType,
      weight: 1,
    });
  };

  items.forEach((item) => {
    const accessionId = item.accession_id || item.id;
    if (item.father_accession) {
      addEdge(item.father_accession, accessionId, 'father');
    }
    if (item.mother_accession) {
      addEdge(item.mother_accession, accessionId, 'mother');
    }
  });

  nodes.forEach((node, nodeId) => {
    node.degree = degreeMap[nodeId] || 0;
  });

  return {
    edges,
    nodes: [...nodes.values()],
  };
}

function normalizeBatchGraph(response: any): GraphData {
  const nodes = ((response?.nodes || []) as any[]).map((node) => ({
    id: node.id,
    label: node.label || node.id,
    degree: Number(node.degree || 0),
    selected: Boolean(node.selected),
    attributes: {
      ...node.attributes,
      display_name: node.attributes?.display_name || node.label || node.id,
    },
  }));
  const edges = ((response?.edges || []) as any[]).map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    relationshipType: edge.relationship_type,
    weight: edge.weight || 1,
  }));
  return { edges, nodes };
}

function applyFilters() {
  filteredGraphData.value = filterGraphData(rawGraphData.value, {
    maxNodes: maxNodes.value,
    minDegree: minDegree.value,
  });
  if (
    activeNodeId.value &&
    !filteredGraphData.value.nodes.some(
      (node) => node.id === activeNodeId.value,
    )
  ) {
    activeNodeId.value = filteredGraphData.value.nodes[0]?.id || '';
  }
}

async function loadGraphData() {
  if (!props.taxonomyTaxId) {
    message.warning($t('germplasm.graph.missingTaxonomyWarning'));
    return;
  }
  if (
    hasFocusedSelection.value &&
    !includeInternal.value &&
    !includeExternal.value
  ) {
    message.warning($t('germplasm.graph.keepOneScopeWarning'));
    includeInternal.value = true;
  }

  loading.value = true;
  try {
    const listResponse = await getGermplasmListApi({
      batch_id: props.batchId,
      page: 1,
      size: 10_000,
      status: 'active',
      taxonomy_tax_id: props.taxonomyTaxId,
    });
    const items =
      (listResponse as any)?.items ?? (listResponse as any)?.data?.items ?? [];
    materialItems.value = items;

    if (hasFocusedSelection.value) {
      const graphResponse = await getGermplasmBatchRelationshipsApi({
        batch_id: props.batchId,
        include_external: includeExternal.value,
        include_internal: includeInternal.value,
        max_connections_per_node: 30,
        selected_nodes: selectedNodeIds.value,
        taxonomy_tax_id: props.taxonomyTaxId,
      });
      rawGraphData.value = normalizeBatchGraph(graphResponse);
    } else {
      rawGraphData.value = buildGraphFromItems(items);
    }

    applyFilters();
    activeNodeId.value =
      selectedNodeIds.value.find((nodeId) =>
        filteredGraphData.value.nodes.some((node) => node.id === nodeId),
      ) ||
      filteredGraphData.value.nodes[0]?.id ||
      '';
  } catch (error) {
    console.error('load germplasm pedigree failed', error);
    message.error($t('germplasm.graph.loadError'));
  } finally {
    loading.value = false;
  }
}

function selectNode(nodeId: string) {
  activeNodeId.value = nodeId;
}

function handleNodeClick(node: GraphNode) {
  activeNodeId.value = node.id;
}

function displayNodeTitle(nodeId: string) {
  const node = nodeMap.value[nodeId];
  if (node?.label) {
    return node.label;
  }
  const item = materialMap.value[nodeId];
  return item?.display_name || nodeId;
}

function openNodeDetail(nodeId: string) {
  if (!props.taxonomyTaxId) {
    return;
  }
  router.push({
    path: '/germplasm/info',
    query: {
      id: nodeId,
      taxonomy_tax_id: String(props.taxonomyTaxId),
    },
  });
}

watch(
  () => [
    props.open,
    props.taxonomyTaxId,
    props.batchId,
    selectedNodeIds.value.join(','),
  ],
  async ([open]) => {
    visible.value = Boolean(open);
    if (!open) {
      return;
    }
    await nextTick();
    updateGraphViewport();
    await loadGraphData();
  },
  { immediate: true },
);

watch(
  () => visible.value,
  (value) => {
    emit('update:open', value);
  },
);

onMounted(() => {
  updateGraphViewport();
  window.addEventListener('resize', updateGraphViewport);
});

onUnmounted(() => {
  window.removeEventListener('resize', updateGraphViewport);
});
</script>

<template>
  <Modal
    v-model:open="visible"
    :title="$t('germplasm.graph.title')"
    width="95%"
    :footer="null"
    :destroy-on-close="true"
  >
    <div class="lineage-modal">
      <div class="lineage-hero">
        <div>
          <div class="hero-eyebrow">{{ $t('germplasm.graph.heroEyebrow') }}</div>
          <h2 class="hero-title">{{ $t('germplasm.graph.heroTitle') }}</h2>
          <p class="hero-description">
            {{ $t('germplasm.graph.heroDescription') }}
          </p>
        </div>
        <Space wrap>
          <Tag v-if="props.taxonomyTaxId" color="green">
            {{ $t('germplasm.graph.taxonomyTag', { id: props.taxonomyTaxId }) }}
          </Tag>
          <Tag v-if="props.batchId" color="gold">
            {{ $t('germplasm.graph.batch') }} {{ props.batchId }}
          </Tag>
          <Button type="primary" :loading="loading" @click="loadGraphData">
            <template #icon>
              <ReloadOutlined />
            </template>
            {{ $t('germplasm.graph.refreshLineage') }}
          </Button>
        </Space>
      </div>

      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-label">{{ $t('germplasm.graph.focusMaterial') }}</div>
          <div class="summary-value">
            {{ hasFocusedSelection ? selectedNodeIds.length : $t('germplasm.graph.wholeBatch') }}
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-label">{{ $t('germplasm.graph.visibleMaterial') }}</div>
          <div class="summary-value">{{ filteredGraphData.nodes.length }}</div>
          <div
            v-if="rawGraphData.nodes.length !== filteredGraphData.nodes.length"
            class="summary-meta"
          >
            {{ $t('germplasm.graph.original') }} {{ rawGraphData.nodes.length }}
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-label">{{ $t('germplasm.graph.lineageEdge') }}</div>
          <div class="summary-value">{{ filteredGraphData.edges.length }}</div>
          <div class="summary-meta">
            {{ $t('germplasm.graph.fatherEdge') }} {{ fatherEdgeCount }} / {{ $t('germplasm.graph.motherEdge') }} {{ motherEdgeCount }}
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-label">{{ $t('germplasm.graph.founderMaterial') }}</div>
          <div class="summary-value">{{ rootNodeCount }}</div>
          <div class="summary-meta">{{ $t('germplasm.graph.endMaterial') }} {{ leafNodeCount }}</div>
        </div>
      </div>

      <div class="lineage-layout">
        <aside class="left-panel">
          <Card :bordered="false" class="panel-card">
            <template #title>{{ $t('germplasm.graph.browseScope') }}</template>
            <div class="scope-stack">
              <div class="scope-item">
                <span class="scope-label">{{ $t('germplasm.graph.mode') }}</span>
                <span class="scope-value">
                  {{ hasFocusedSelection ? $t('germplasm.graph.focusLineage') : $t('germplasm.graph.wholeBatchInternal') }}
                </span>
              </div>
              <div class="scope-item">
                <span class="scope-label">{{ $t('germplasm.graph.batchScope') }}</span>
                <span class="scope-value">
                  {{ props.batchId ? `${$t('germplasm.graph.batch')} ${props.batchId}` : $t('germplasm.graph.allActiveGermplasm') }}
                </span>
              </div>
              <div v-if="hasFocusedSelection" class="focus-tags">
                <Tag
                  v-for="nodeId in selectedNodeIds"
                  :key="nodeId"
                  color="gold"
                >
                  {{ displayNodeTitle(nodeId) }}
                </Tag>
              </div>
            </div>
          </Card>

          <Card :bordered="false" class="panel-card">
            <template #title>{{ $t('germplasm.graph.controlTitle') }}</template>
            <div class="control-stack">
              <div class="scope-item">
                <span class="scope-label">{{ $t('germplasm.graph.viewLayout') }}</span>
                <Radio.Group
                  v-model:value="layoutMode"
                  button-style="solid"
                  size="small"
                >
                  <Radio.Button value="generation">{{ $t('germplasm.graph.generationLayer') }}</Radio.Button>
                  <Radio.Button value="force">{{ $t('germplasm.graph.forceLayout') }}</Radio.Button>
                </Radio.Group>
              </div>
              <div v-if="hasFocusedSelection" class="check-group">
                <Checkbox
                  v-model:checked="includeInternal"
                  @change="loadGraphData"
                >
                  {{ $t('germplasm.graph.betweenFocus') }}
                </Checkbox>
                <Checkbox
                  v-model:checked="includeExternal"
                  @change="loadGraphData"
                >
                  {{ $t('germplasm.graph.externalExtension') }}
                </Checkbox>
              </div>
              <div v-else class="control-hint">
                {{ $t('germplasm.graph.wholeBatchHint') }}
              </div>

              <div class="filter-row">
                <span class="filter-label">{{ $t('germplasm.graph.maxDisplay') }}</span>
                <InputNumber
                  v-model:value="maxNodes"
                  :min="20"
                  :max="500"
                  style="width: 120px"
                  @change="applyFilters"
                />
                <span class="filter-unit">{{ $t('germplasm.graph.materialUnit') }}</span>
              </div>
              <div class="filter-row">
                <span class="filter-label">{{ $t('germplasm.graph.minDegree') }}</span>
                <InputNumber
                  v-model:value="minDegree"
                  :min="0"
                  :max="20"
                  style="width: 120px"
                  @change="applyFilters"
                />
              </div>
            </div>
          </Card>

          <Card :bordered="false" class="panel-card">
            <template #title>{{ $t('germplasm.graph.legend') }}</template>
            <div class="legend-stack">
              <div class="legend-item">
                <span class="legend-dot current"></span>
                <span>{{ $t('germplasm.graph.currentFocus') }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-dot father"></span>
                <span>{{ $t('germplasm.graph.fatherLegend') }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-dot mother"></span>
                <span>{{ $t('germplasm.graph.motherLegend') }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-dot offspring"></span>
                <span>{{ $t('germplasm.graph.offspring') }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-dot placeholder"></span>
                <span>{{ $t('germplasm.graph.externalParentInLineage') }}</span>
              </div>
            </div>
          </Card>

          <Card :bordered="false" class="panel-card">
            <template #title>{{ $t('germplasm.graph.keyMaterial') }}</template>
            <div v-if="focusCandidates.length > 0" class="focus-list">
              <button
                v-for="node in focusCandidates"
                :key="node.id"
                class="focus-button"
                :class="{ active: activeNodeId === node.id }"
                type="button"
                @click="selectNode(node.id)"
              >
                <span class="focus-name">{{ node.label || node.id }}</span>
                <span class="focus-meta">{{ $t('germplasm.graph.connect') }} {{ node.degree }}</span>
              </button>
            </div>
            <Empty v-else :description="$t('germplasm.graph.noKeyMaterial')" />
          </Card>
        </aside>

        <section class="graph-panel">
          <Card :bordered="false" class="graph-card">
            <template #title>{{ $t('germplasm.graph.lineageView') }}</template>
            <template #extra>
              <span class="graph-card-meta">
                {{ $t('germplasm.graph.clickNodeHint') }}
              </span>
            </template>
            <KnowledgeGraph
              :data="displayedGraphData"
              :layout-mode="layoutMode"
              :width="graphWidth"
              :height="graphHeight"
              :loading="loading"
              @node-click="handleNodeClick"
            />
          </Card>
        </section>

        <aside class="right-panel">
          <Card :bordered="false" class="panel-card detail-card">
            <template #title>{{ $t('germplasm.graph.currentDetail') }}</template>
            <template #extra>
              <Button
                v-if="activeNode && !activeNode.attributes?.is_placeholder"
                size="small"
                @click="openNodeDetail(activeNode.id)"
              >
                {{ $t('germplasm.graph.openDetail') }}
              </Button>
            </template>
            <template v-if="activeNode">
              <div class="detail-header">
                <div>
                  <div class="detail-title">{{ activeDisplayName }}</div>
                  <div class="detail-subtitle">{{ activeNode.id }}</div>
                </div>
                <Tag
                  :style="
                    activeNode.attributes?.is_placeholder
                      ? undefined
                      : {
                          color: ROLE_COLORS.current,
                          background: ROLE_COLORS.currentSoft,
                          borderColor: 'rgba(245, 158, 11, 0.24)',
                        }
                  "
                >
                  {{
                    activeNode.attributes?.is_placeholder
                      ? $t('germplasm.graph.externalParent')
                      : $t('germplasm.graph.currentMaterial')
                  }}
                </Tag>
              </div>

              <div class="detail-kv-grid">
                <div class="detail-kv">
                  <span class="detail-kv-label">{{ $t('germplasm.graph.englishName') }}</span>
                  <span class="detail-kv-value">{{ activeEnglishName }}</span>
                </div>
                <div class="detail-kv">
                  <span class="detail-kv-label">{{ $t('germplasm.graph.degree') }}</span>
                  <span class="detail-kv-value">{{ activeNode.degree }}</span>
                </div>
                <div class="detail-kv">
                  <span class="detail-kv-label">{{ $t('germplasm.graph.batch') }}</span>
                  <span class="detail-kv-value">
                    {{ activeBatchCode }}
                  </span>
                </div>
                <div class="detail-kv">
                  <span class="detail-kv-label">{{ $t('germplasm.graph.sourceFile') }}</span>
                  <span class="detail-kv-value">
                    {{ activeSourceFilename }}
                  </span>
                </div>
              </div>

              <div class="archive-hero-card">
                <div
                  class="archive-media"
                  :class="{ placeholder: !activeArchiveImage }"
                >
                  <img
                    v-if="activeArchiveImage"
                    :src="activeArchiveImage"
                    :alt="activeDisplayName"
                  />
                  <div v-else class="archive-initial">
                    {{ activeArchiveInitial }}
                  </div>
                </div>
                <div class="archive-meta">
                  <div class="archive-eyebrow">{{ $t('germplasm.graph.archiveEyebrow') }}</div>
                  <div class="archive-heading">{{ $t('germplasm.graph.materialArchiveCard') }}</div>
                  <div class="archive-note-block">
                    <div class="archive-note-label">{{ $t('germplasm.graph.remark') }}</div>
                    <div class="archive-note-value">
                      {{
                        activeArchiveNote ||
                        $t('germplasm.graph.noRemarkHint')
                      }}
                    </div>
                  </div>
                </div>
              </div>

              <div class="relationship-block">
                <div class="section-title">{{ $t('germplasm.graph.parentSection') }}</div>
                <div class="parent-grid">
                  <button
                    class="parent-card father"
                    type="button"
                    :disabled="!fatherNode"
                    @click="fatherNode && selectNode(fatherNode.id)"
                  >
                    <span class="parent-role">{{ $t('germplasm.graph.fatherEdge') }}</span>
                    <span class="parent-name">
                      {{
                        fatherNode ? displayNodeTitle(fatherNode.id) : $t('germplasm.graph.unrecorded')
                      }}
                    </span>
                    <span class="parent-snapshot">
                      {{ $t('germplasm.graph.nameSnapshot') }} {{ fatherSnapshotName }}
                    </span>
                    <span class="parent-id">
                      {{ fatherNode?.id || '-' }}
                    </span>
                  </button>
                  <button
                    class="parent-card mother"
                    type="button"
                    :disabled="!motherNode"
                    @click="motherNode && selectNode(motherNode.id)"
                  >
                    <span class="parent-role">{{ $t('germplasm.graph.motherEdge') }}</span>
                    <span class="parent-name">
                      {{
                        motherNode ? displayNodeTitle(motherNode.id) : $t('germplasm.graph.unrecorded')
                      }}
                    </span>
                    <span class="parent-snapshot">
                      {{ $t('germplasm.graph.nameSnapshot') }} {{ motherSnapshotName }}
                    </span>
                    <span class="parent-id">
                      {{ motherNode?.id || '-' }}
                    </span>
                  </button>
                </div>
              </div>

              <div class="relationship-block">
                <div class="section-title">{{ $t('germplasm.graph.offspringSection') }}</div>
                <div v-if="childNodes.length > 0" class="child-list">
                  <button
                    v-for="child in childNodes"
                    :key="child.id"
                    class="child-chip"
                    :class="{
                      placeholder: child.attributes?.is_placeholder,
                    }"
                    type="button"
                    @click="selectNode(child.id)"
                  >
                    {{ displayNodeTitle(child.id) }}
                  </button>
                </div>
                <Empty v-else :description="$t('germplasm.graph.noOffspringInView')" />
              </div>

              <div class="relationship-block">
                <div class="section-title">{{ $t('germplasm.graph.extendedAttributes') }}</div>
                <div v-if="attributeEntries.length > 0" class="attribute-list">
                  <div
                    v-for="item in attributeEntries"
                    :key="item.key"
                    class="attribute-row"
                  >
                    <span class="attribute-key">{{ item.key }}</span>
                    <span class="attribute-value">{{ item.value }}</span>
                  </div>
                </div>
                <Empty v-else :description="$t('germplasm.graph.noExtendedAttributes')" />
              </div>
            </template>
            <Empty v-else :description="$t('germplasm.graph.clickToViewHint')" />
          </Card>
        </aside>
      </div>
    </div>
  </Modal>
</template>

<style scoped lang="less">
.lineage-modal {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.lineage-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 22px;
  border: 1px solid #d7e7d8;
  border-radius: 20px;
  background:
    radial-gradient(
      circle at top right,
      rgba(116, 173, 93, 0.18),
      transparent 34%
    ),
    linear-gradient(135deg, #fbf8ef 0%, #f5f8f1 100%);
}

.hero-eyebrow {
  color: #567b4d;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-title {
  margin: 8px 0 10px;
  color: #243126;
  font-size: 28px;
  font-weight: 700;
}

.hero-description {
  max-width: 860px;
  margin: 0;
  color: #5f6d61;
  line-height: 1.75;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  padding: 18px 20px;
  border: 1px solid #e5ecd9;
  border-radius: 18px;
  background: #fffdf8;
}

.summary-label {
  color: #72806f;
  font-size: 13px;
}

.summary-value {
  margin-top: 8px;
  color: #243126;
  font-size: 30px;
  font-weight: 700;
  line-height: 1.1;
}

.summary-meta {
  margin-top: 8px;
  color: #7f8d7a;
  font-size: 12px;
}

.lineage-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 340px;
  gap: 16px;
  align-items: start;
}

.panel-card,
.graph-card {
  border: 1px solid #ebefe4;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 12px 40px rgba(39, 58, 41, 0.06);
}

.left-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.scope-stack,
.control-stack,
.legend-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.scope-item,
.filter-row,
.legend-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.scope-label,
.filter-label {
  color: #71816e;
  font-size: 13px;
}

.scope-value,
.filter-unit {
  color: #243126;
  font-size: 13px;
  font-weight: 600;
}

.focus-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.check-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.control-hint {
  color: #66765f;
  font-size: 13px;
  line-height: 1.7;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
}

.legend-dot.focus {
  background: #f59e0b;
}

.legend-dot.current {
  background: v-bind('ROLE_COLORS.current');
}

.legend-dot.father {
  background: v-bind('ROLE_COLORS.father');
}

.legend-dot.mother {
  background: v-bind('ROLE_COLORS.mother');
}

.legend-dot.offspring {
  background: v-bind('ROLE_COLORS.offspring');
}

.legend-dot.placeholder {
  background: v-bind('ROLE_COLORS.placeholder');
}

.focus-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.focus-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e4eadd;
  border-radius: 14px;
  background: #fafcf8;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.focus-button:hover,
.focus-button.active {
  border-color: rgba(245, 158, 11, 0.4);
  box-shadow: 0 10px 24px rgba(245, 158, 11, 0.14);
  transform: translateY(-1px);
}

.focus-name {
  color: #243126;
  font-size: 13px;
  font-weight: 600;
  text-align: left;
}

.focus-meta {
  color: #7c8875;
  font-size: 12px;
  white-space: nowrap;
}

.graph-card-meta {
  color: #7a8673;
  font-size: 12px;
}

.detail-card {
  min-height: 100%;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.detail-title {
  color: #243126;
  font-size: 22px;
  font-weight: 700;
}

.detail-subtitle {
  margin-top: 4px;
  color: #7a8673;
  font-size: 12px;
}

.detail-kv-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 18px;
}

.archive-hero-card {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 14px;
  margin-bottom: 18px;
  padding: 14px;
  border: 1px solid #ece6d8;
  border-radius: 18px;
  background:
    radial-gradient(
      circle at top right,
      rgba(245, 158, 11, 0.12),
      transparent 32%
    ),
    linear-gradient(135deg, #fffaf2 0%, #fffdf9 100%);
}

.archive-media {
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  border-radius: 16px;
  background: #f6f1e7;
  border: 1px solid rgba(180, 146, 92, 0.18);
}

.archive-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.archive-media.placeholder {
  background:
    radial-gradient(circle at top, rgba(245, 158, 11, 0.12), transparent 42%),
    linear-gradient(180deg, #f9f3e8 0%, #f4ece1 100%);
}

.archive-initial {
  color: #9a6a18;
  font-size: 44px;
  font-weight: 700;
}

.archive-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.archive-eyebrow {
  color: #9a6a18;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.archive-heading {
  color: #2b2317;
  font-size: 18px;
  font-weight: 700;
}

.archive-note-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.archive-note-label {
  color: #8a7353;
  font-size: 12px;
  font-weight: 600;
}

.archive-note-value {
  color: #5b4930;
  font-size: 13px;
  line-height: 1.75;
  word-break: break-word;
}

.detail-kv {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border: 1px solid #ebefe4;
  border-radius: 14px;
  background: #fafcf8;
}

.detail-kv-label {
  color: #7a8673;
  font-size: 12px;
}

.detail-kv-value {
  color: #243126;
  font-size: 13px;
  font-weight: 600;
}

.relationship-block {
  margin-top: 18px;
}

.section-title {
  margin-bottom: 10px;
  color: #354536;
  font-size: 14px;
  font-weight: 700;
}

.parent-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.parent-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
  padding: 14px;
  border: 1px solid #e4eadd;
  border-radius: 16px;
  background: #fff;
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.parent-card:disabled {
  cursor: default;
  opacity: 0.7;
}

.parent-card:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}

.parent-card.father {
  border-color: rgba(37, 99, 235, 0.22);
  background: v-bind('ROLE_COLORS.fatherSoft');
}

.parent-card.mother {
  border-color: rgba(219, 39, 119, 0.22);
  background: v-bind('ROLE_COLORS.motherSoft');
}

.parent-role {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.parent-card.father .parent-role {
  color: v-bind('ROLE_COLORS.father');
}

.parent-card.mother .parent-role {
  color: v-bind('ROLE_COLORS.mother');
}

.parent-name {
  color: #243126;
  font-size: 12px;
  font-size: 14px;
  font-weight: 600;
  text-align: left;
}

.parent-id {
  color: #7a8673;
  font-size: 12px;
}

.parent-snapshot {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
  text-align: left;
}

.child-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.child-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid rgba(31, 109, 66, 0.22);
  border-radius: 999px;
  background: v-bind('ROLE_COLORS.offspringSoft');
  color: v-bind('ROLE_COLORS.offspring');
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.child-chip:hover {
  transform: translateY(-1px);
  border-color: rgba(31, 109, 66, 0.36);
  box-shadow: 0 10px 24px rgba(31, 109, 66, 0.14);
}

.child-chip.placeholder {
  border-color: rgba(203, 213, 225, 0.8);
  background: rgba(203, 213, 225, 0.18);
  color: #64748b;
}

.attribute-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attribute-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid #edf1e7;
  border-radius: 12px;
  background: #fcfdfb;
}

.attribute-key {
  color: #7a8673;
  font-size: 12px;
}

.attribute-value {
  color: #2d3d2e;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}

:deep(.ant-modal-body) {
  padding-top: 16px;
  background: #f5f7f2;
}

:deep(.knowledge-graph .graph-header) {
  padding: 14px 16px;
  border-bottom: 1px solid #e7ecdf;
  background: linear-gradient(180deg, #fbfcfa 0%, #f6f8f3 100%);
}

:deep(.knowledge-graph .graph-container) {
  border-radius: 16px;
  background:
    radial-gradient(circle at top, rgba(120, 160, 110, 0.08), transparent 26%),
    #ffffff;
}

@media (max-width: 1440px) {
  .lineage-layout {
    grid-template-columns: 260px minmax(0, 1fr) 320px;
  }
}

@media (max-width: 1200px) {
  .summary-grid,
  .lineage-layout,
  .archive-hero-card,
  .detail-kv-grid,
  .parent-grid {
    grid-template-columns: 1fr;
  }
}
</style>
