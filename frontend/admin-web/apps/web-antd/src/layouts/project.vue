<script lang="ts" setup>
// import { useUserStore } from '@vben/stores';
// import type { ProjectRowType } from '#/api/system/project';

import { computed, ref, watch } from 'vue';

import { useRefresh } from '@vben/hooks';

import { $t } from '@vben/locales';
import { Select, Tag } from 'ant-design-vue';

import { useProjectStoreWithOut } from '#/store/modules/project';

defineOptions({
  name: 'HeaderProject',
});

const { refresh } = useRefresh();
const proStore = useProjectStoreWithOut();
const fieldNames = { label: 'name', value: 'id' };
const options = computed(() => proStore.getProjectOptions);
// const selected = ref<any>(proStore.projectInfo?.id);
const loading = ref(false);

const selected = computed(() => proStore.getProjectInfo?.id);
/**
 * 处理项目选择变化的函数。
 * 当用户选择一个新项目时，此函数会被调用，并更新当前应用用户的项目ID。
 * @param value - 用户选择的新项目的ID。
 */
const handleChange = (value: any) => {
  const project_info = options?.value?.find((item: any) => item.id === value);
  proStore.setProjectInfo({
    id: project_info?.id,
    name: project_info?.name,
  });
};

watch(() => selected.value, refresh);
</script>
<template>
  <div class="flex">
    <div class="text-foreground project">{{ $t('system.project.title') }}:</div>
    <div class="project-v ml-1">
      <Select
        :loading="loading"
        class="ml-1 w-full"
        :default-open="false"
        :field-names="fieldNames"
        v-model:value="selected"
        popup-class-name="aant-select-dropdown"
        :bordered="false"
        :options="options"
        @change="handleChange"
      >
        <!-- <select-option v-for="item in options" :key="item.id" :value="item.id"
        >{{ item }}
      </select-option> -->
        <template #option="{ name, isPublic }">
          <div class="text-foreground">
            {{ name }}
            <Tag
              class="ml-21"
              style="float: right"
              v-if="isPublic"
              color="blue"
            >
              {{ $t('dataset.list.visibility_public') }}
            </Tag>
            <Tag class="ml-2" style="float: right" v-else color="purple">
              {{ $t('dataset.list.visibility_private') }}
            </Tag>
          </div>
        </template>
      </Select>
    </div>
  </div>
</template>

<style scoped>
:deep() {
  .ant-select-selection-item {
    color: hsl(var(--foreground));
  }

  .ant-select-arrow {
    color: hsl(var(--foreground));
  }

  .aant-select-dropdown {
    background-color: #c71515;
  }

  :where(
      .css-dev-only-do-not-override-1bgsqih
    ).ant-select-single.ant-select-open
    .ant-select-selection-item {
    color: hsl(var(--foreground));
  }
}

.project {
  padding: 7px;
  padding-right: 15px;
  padding-left: 15px;
  background-color: hsl(var(--accent));
  border-radius: 4px;
}

.project-v {
  width: 250px;
  border: 1px, solid, hsl(var(--accent));
}

.dropdown-class-name1 {
  width: 1400px;
  color: #a71a1a;
}
</style>
<style lang="scss">
.t-antd-select-dropdown {
  .t-table-select__table {
    padding: 10px;

    .ant-table-body,
    .ant-table-header {
      margin: 0;
    }

    .ant-table-body {
      .ant-table-tbody {
        .ant-table-row {
          cursor: pointer;
        }

        .ant-table-row-selected,
        .active-selected-row {
          color: #409eff;
          background-color: #ecf5ff;
        }
      }
    }
  }

  .ant-pagination {
    flex-wrap: nowrap;
  }
}
</style>
