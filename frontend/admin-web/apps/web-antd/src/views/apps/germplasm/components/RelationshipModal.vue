<template>
  <Modal v-model:open="visible" :title="$t('germplasm.relationship.title')" width="640px" @cancel="handleCancel" :footer="null">
    <div v-if="data" class="space-y-4">
      <Descriptions bordered :column="1">
        <DescriptionsItem :label="$t('germplasm.relationship.node1')">
          {{ renderNode(data.node1) }}
        </DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.relationship.node2')">
          {{ renderNode(data.node2) }}
        </DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.relationship.relationType')">{{ data.relationship_type }}</DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.relationship.relationDirection')">{{ data.relationship_direction || '-' }}</DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.relationship.exists')">{{ data.exists ? $t('germplasm.detail.yes') : $t('germplasm.detail.no') }}</DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.relationship.path')">{{ data.path_nodes?.join(' -> ') || '-' }}</DescriptionsItem>
        <DescriptionsItem :label="$t('germplasm.relationship.generatedAt')">{{ data.generated_at || '-' }}</DescriptionsItem>
      </Descriptions>

      <Card :title="$t('germplasm.relationship.directEdge')" size="small">
        <div v-if="data.direct_edges?.length" class="relation-list">
          <div v-for="edge in data.direct_edges" :key="`${edge.parent_accession}-${edge.child_accession}-${edge.parent_role}`" class="relation-item">
            <span>{{ edge.parent_accession }} -> {{ edge.child_accession }}</span>
            <Tag color="blue">{{ edge.parent_role }}</Tag>
          </div>
        </div>
        <div v-else class="text-gray-500">{{ $t('germplasm.relationship.noDirectEdge') }}</div>
      </Card>

      <Card :title="$t('germplasm.relationship.sharedParent')" size="small">
        <div v-if="data.shared_parents?.length" class="relation-list">
          <div v-for="parent in data.shared_parents" :key="parent.parent_accession" class="relation-item">
            <span>{{ parent.parent_accession }}</span>
            <Tag color="cyan">{{ parent.roles.join(', ') }}</Tag>
          </div>
        </div>
        <div v-else class="text-gray-500">{{ $t('germplasm.relationship.noSharedParent') }}</div>
      </Card>

      <Card :title="$t('germplasm.relationship.sharedChild')" size="small">
        <div v-if="data.shared_children?.length" class="relation-list">
          <Tag v-for="child in data.shared_children" :key="child.child_accession" color="gold">
            {{ child.child_accession }}
          </Tag>
        </div>
        <div v-else class="text-gray-500">{{ $t('germplasm.relationship.noSharedChild') }}</div>
      </Card>
    </div>
    <div v-else class="text-center text-gray-500">{{ $t('germplasm.relationship.noData') }}</div>
  </Modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Modal, Descriptions, DescriptionsItem, Card, Tag, message } from 'ant-design-vue';
import { $t } from '@vben/locales';
import { getGermplasmRelationshipApi } from '../api';
import type { GermplasmRelationshipResult } from '../types';

interface Props {
  open: boolean;
  taxonomyTaxId?: number;
  accessionId1?: string;
  accessionId2?: string;
  batchId?: number;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(false);
const data = ref<GermplasmRelationshipResult | null>(null);

watch(
  () => props.open,
  async (val) => {
    visible.value = val;
    if (val && props.accessionId1 && props.accessionId2 && props.taxonomyTaxId) {
      await fetchData();
    }
  },
  { immediate: true },
);

watch(
  () => visible.value,
  (v) => emit('update:open', v),
);

async function fetchData() {
  try {
    const res: any = await getGermplasmRelationshipApi({
      taxonomy_tax_id: props.taxonomyTaxId!,
      accession_id_1: props.accessionId1!,
      accession_id_2: props.accessionId2!,
      batch_id: props.batchId,
    });
    data.value = res?.data ?? res;
  } catch (e) {
    message.error($t('germplasm.relationship.fetchError'));
  }
}

function renderNode(accessionId: string) {
  const displayName = data.value?.node_snapshots?.[accessionId]?.display_name;
  return displayName ? `${accessionId} / ${displayName}` : accessionId;
}

function handleCancel() {
  visible.value = false;
}
</script>

<style scoped>
.space-y-4 > * + * {
  margin-top: 1rem;
}

.relation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.relation-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  background: #f8fbff;
}
</style>

