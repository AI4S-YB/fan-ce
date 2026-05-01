<script setup lang="ts">
import type { TreeActionItem, TreeItem } from '#/components/Tree';

import { defineExpose, h, onMounted, reactive, ref, unref } from 'vue';
import { useRouter } from 'vue-router';

import {
  DeleteOutlined,
  DragOutlined,
  EditOutlined,
  PlusSquareOutlined,
} from '@ant-design/icons-vue';
import { Button, Tag } from 'ant-design-vue';

import { getMenuTreeApi } from '#/api/system';
import { BasicTree } from '#/components/Tree';
import { $t } from '@vben/locales';
import { eachTree, findNodeByKey } from '#/utils/helper/treeHelper';

const props = defineProps({
  query: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(['add', 'edit', 'select', 'delete']);
const { currentRoute } = useRouter();
const treeRef = ref<any>(null);
const treeData = ref<TreeItem[]>([]);
const treeLoading = ref<boolean>(false);
const data = reactive<Recordable>({
  applicationList: [],
  appDisabled: false,
});

function getTree() {
  const tree = unref(treeRef);
  if (!tree) {
    throw new Error('Tree instance is not available');
  }
  return tree;
}
const handleAdd = () => {};
const handleBatchDelete = () => {};
const openModal = (open: any, node: any) => {
  console.error(open, node);
};
const batchDelete = (id: any) => {
  console.error(id);
};

let actionList: TreeActionItem[] = [];
// let getRightMenuList = (_: any): ContextMenuItem[] => {
//   return [];
// };
function handleMove(current = {}) {
  openModal(true, {
    current,
  });
}

// 悬停图标
actionList = [
  {
    render: (node) => {
      return h(DragOutlined, {
        class: 'ml-2',
        title: $t('common.title.move'),
        onClick: (e: Event) => {
          e?.stopPropagation();
          e?.preventDefault();
          handleMove(findNodeByKey(node.id, treeData.value));
        },
      });
    },
  },
  {
    render: (node) => {
      return h(PlusSquareOutlined, {
        class: 'ml-2',
        title: $t('component.action.create'),
        onClick: (e: Event) => {
          e?.stopPropagation();
          e?.preventDefault();
          emit('add', node, {});
        },
      });
    },
  },
  {
    render: (node) => {
      return h(EditOutlined, {
        class: 'ml-2',
        title: $t('component.action.edit'),
        onClick: (e: Event) => {
          e?.stopPropagation();
          e?.preventDefault();
          // const current = findNodeByKey(node?.id, treeData.value);
          const parent = findNodeByKey(node?.parentId, treeData.value);
          emit('edit', parent, node);
        },
      });
    },
  },
  {
    render: (node) => {
      return h(DeleteOutlined, {
        class: 'ml-2',
        title: $t('component.action.delete'),
        style: { color: '#ED6F6F' },
        onClick: (e: Event) => {
          e?.stopPropagation();
          e?.preventDefault();
          batchDelete([node.id]);
          emit('delete', node);
        },
      });
    },
  },
];

// 右键菜单

const handleSelect = (keys: string[]) => {
  if (keys[0]) {
    const node = findNodeByKey(keys[0], treeData.value);
    findNodeByKey(node?.parentId, treeData.value);
    emit('select', keys[0]);
  }
};
const fetch = async () => {
  try {
    treeLoading.value = true;
    treeData.value = (await getMenuTreeApi({})) as unknown as TreeItem[];
    eachTree(
      treeData.value,
      (item: any, parent: any) => {
        item.key = item.id;
        item.keyLinks = [...(parent.keyLinks || []), item.id];
        // item.slots = { icon: 'icon' };
        return item;
      },
      {},
    );

    setTimeout(() => {
      getTree().setCheckedKeys({ checked: [], halfChecked: [] });
    }, 1000);
  } catch {
    treeLoading.value = false;
  } finally {
    treeLoading.value = false;
  }
};
onMounted(async () => {
  const params = currentRoute.value?.params;
  data.appDisabled = !!params?.id;
  await fetch();
});
defineExpose({
  fetch,
});
</script>
<template>
  <div class="mr-2 overflow-hidden bg-white">
    <div class="m-4">
      <Button
        class="mr-2"
        pre-icon="ant-design:plus-outlined"
        @click="handleAdd()"
      >
        {{ $t('component.action.create') }}
      </Button>
      <Button
        class="mr-2"
        pre-icon="ant-design:delete-outlined"
        @click="handleBatchDelete()"
      >
        {{ $t('component.action.delete') }}
      </Button>
      <Button
        class="mr-2"
        pre-icon="ant-design:reload-outlined"
        @click="fetch()"
      >
        {{ $t('common.redo') }}
      </Button>
    </div>
    <BasicTree
      ref="treeRef"
      :action-list="actionList"
      :click-row-to-expand="false"
      :loading="treeLoading"
      :title="$t('system.menu.resourceList')"
      :tree-data="treeData"
      check-strictly
      checkable
      highlight
      search
      toolbar
      @select="handleSelect"
    >
      <template #title="item">
        <div v-if="item.type === 1">
          <Tag color="green">{{ $t('system.menu.dirType') }}</Tag>{{ item.title }}
        </div>
        <div v-else-if="item.type === 2">
          <Tag color="cyan">{{ $t('system.menu.menuType') }}</Tag>{{ item.title }}
        </div>
        <div v-else-if="item.type === 3">
          <Tag color="purple">{{ $t('system.menu.buttonType') }}</Tag>{{ item.title }}
        </div>
      </template>
    </BasicTree>
  </div>
</template>
