<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';

import { WorkbenchHeader } from '@vben/common-ui';
import { preferences } from '@vben/preferences';
import { useUserStore } from '@vben/stores';

import { $t } from '@vben/locales';

import { getDatasetListApi } from '#/api/apps/dataset';
import { getBreedingProgramListApi } from '#/api/breeding/program';
import { useProgramStoreWithOut } from '#/store/modules/program';

import ChatPanel from './ChatPanel.vue';
import SessionSidebar from './SessionSidebar.vue';

const userStore = useUserStore();
const programStore = useProgramStoreWithOut();

const programCount = ref(0);
const datasetCount = ref(0);

const workspaceDescription = computed(() => {
  const projectName = programStore.getProgramInfo?.name?.trim?.();

  if (projectName) {
    return $t('workspace.currentProject', { name: projectName });
  }
  return $t('workspace.fallbackDesc');
});

async function loadStats() {
  try {
    const [progRes, dsRes] = await Promise.all([
      getBreedingProgramListApi({ page: 1, size: 1, keyword: undefined, species_name: undefined, status: 'active' }),
      getDatasetListApi({ page: 1, size: 1 }),
    ]);
    programCount.value = progRes?.total ?? 0;
    datasetCount.value = dsRes?.total ?? 0;
  } catch (error) {
    console.error('Load stats failed:', error);
  }
}

onMounted(() => {
  void loadStats();
});
</script>

<template>
  <div class="p-5">
    <WorkbenchHeader
      :avatar="userStore.userInfo?.avatar || preferences.app.defaultAvatar"
    >
      <template #title>
        {{ $t('workspace.greeting.morning', { name: userStore.userInfo?.realName }) }}
      </template>
      <template #description>
        {{ workspaceDescription }}
      </template>
      <template #stats>
        <div class="flex flex-col justify-center text-right">
          <span class="text-foreground/80"> {{ $t('workspace.stats.project') }} </span>
          <span class="text-2xl">{{ programCount }}</span>
        </div>
        <div class="mx-12 flex flex-col justify-center text-right md:mx-16">
          <span class="text-foreground/80"> {{ $t('workspace.stats.dataset') }} </span>
          <span class="text-2xl">{{ datasetCount }}</span>
        </div>
      </template>
    </WorkbenchHeader>

    <div class="workspace-body mt-5">
      <SessionSidebar />
      <ChatPanel />
    </div>
  </div>
</template>

<style scoped>
.workspace-body {
  display: flex;
  height: calc(100vh - 220px);
  min-height: 600px;
  border: 1px solid #e8edf4;
  border-radius: 18px;
  overflow: hidden;
  background: #ffffff;
}

@media (max-width: 768px) {
  .workspace-body {
    flex-direction: column;
  }
}
</style>
