<script setup lang="ts">
import type {
  PlatformSetupCurrentResponse,
  PlatformSetupJobStatusResponse,
  PlatformSetupPackage,
  PlatformSetupStatusResponse,
} from '#/api/platform/setup';

import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Empty,
  Progress,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  getPlatformSetupStatusApi,
  getPlatformTaxonomyCurrentApi,
  getPlatformTaxonomyImportStatusApi,
  getPlatformTaxonomyPackagesApi,
  startPlatformTaxonomyImportApi,
} from '#/api/platform/setup';
import { useMessage } from '#/hooks/web/useMessage';
import { usePlatformSetupStoreWithOut } from '#/store';
import { $t } from '@vben/locales';

defineOptions({ name: 'PlatformSetupTaxonomyPage' });

const route = useRoute();
const router = useRouter();
const { createMessage } = useMessage();
const platformSetupStore = usePlatformSetupStoreWithOut();

const pageLoading = ref(false);
const importSubmitting = ref(false);
const setupStatus = ref<null | PlatformSetupStatusResponse>(null);
const taxonomyCurrent = ref<null | PlatformSetupCurrentResponse>(null);
const packageRows = ref<PlatformSetupPackage[]>([]);
const recommendedPackageId = ref<null | number>(null);
const latestJob = ref<null | PlatformSetupJobStatusResponse>(null);
const forceReinstall = ref(false);
const pollTimer = ref<null | ReturnType<typeof setTimeout>>(null);
const redirecting = ref(false);

const packageColumns = [
  {
    title: $t('dataset.staging.packageName'),
    dataIndex: 'package_name',
    key: 'package_name',
  },
  {
    title: $t('system.menu.type'),
    dataIndex: 'package_type',
    key: 'package_type',
  },
  {
    title: $t('phenome.query.source'),
    dataIndex: 'source',
    key: 'source',
  },
  {
    title: $t('phenome.query.version'),
    dataIndex: 'source_version',
    key: 'source_version',
  },
  {
    title: $t('platform.setting.status'),
    dataIndex: 'status',
    key: 'status',
  },
  {
    title: $t('component.upload.fileSize'),
    dataIndex: 'file_size',
    key: 'file_size',
  },
  {
    title: $t('platform.setting.action'),
    key: 'action',
    width: 220,
  },
];

const statusMeta = computed(() => {
  const status =
    taxonomyCurrent.value?.status ||
    setupStatus.value?.taxonomy_status ||
    'not_installed';
  const mapping: Record<string, { color: string; label: string }> = {
    failed: { color: 'red', label: $t('dataset.staging.importFailed') },
    importing: { color: 'processing', label: $t('dataset.staging.importing') },
    not_installed: { color: 'default', label: $t('dataset.staging.notInstalled') },
    package_ready: { color: 'gold', label: $t('dataset.staging.packageReady') },
    ready: { color: 'green', label: $t('dataset.staging.ready') },
  };
  return mapping[status] || { color: 'default', label: status };
});

const activeJob = computed(() => {
  const job = latestJob.value || taxonomyCurrent.value?.latest_job;
  if (!job) {
    return null;
  }
  return ['pending', 'running'].includes(job.status) ? job : null;
});

const canStartImport = computed(() => {
  return (
    !importSubmitting.value && !activeJob.value && packageRows.value.length > 0
  );
});

const redirectTarget = computed(() => {
  const rawValue = route.query.redirect;
  if (typeof rawValue !== 'string' || !rawValue) {
    return null;
  }
  try {
    const decoded = decodeURIComponent(rawValue);
    return decoded && decoded !== '/platform/setup/taxonomy' ? decoded : null;
  } catch {
    return rawValue;
  }
});

function formatFileSize(size?: null | number) {
  if (!size || size <= 0) {
    return '-';
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = size;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(unitIndex === 0 ? 0 : 2)} ${units[unitIndex]}`;
}

function formatDateTime(value?: null | string) {
  if (!value) {
    return '-';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function clearPollTimer() {
  if (pollTimer.value) {
    clearTimeout(pollTimer.value);
    pollTimer.value = null;
  }
}

async function maybeRedirectAfterReady() {
  const isReady =
    taxonomyCurrent.value?.ready || setupStatus.value?.taxonomy_ready || false;
  if (!isReady || !redirectTarget.value || redirecting.value) {
    return;
  }
  redirecting.value = true;
  createMessage.success($t('dataset.staging.taxonomyInitComplete'));
  await router.replace(redirectTarget.value).catch(() => {
    redirecting.value = false;
  });
}

function scheduleStatusPolling(jobId?: number) {
  clearPollTimer();
  pollTimer.value = setTimeout(async () => {
    try {
      const job = await getPlatformTaxonomyImportStatusApi(jobId);
      latestJob.value = job || null;
      if (job?.status && ['pending', 'running'].includes(job.status)) {
        scheduleStatusPolling(job.id);
      } else {
        await loadPageData();
      }
    } catch {
      clearPollTimer();
    }
  }, 3000);
}

async function loadPageData() {
  pageLoading.value = true;
  try {
    const [status, current, packages, job] = await Promise.all([
      getPlatformSetupStatusApi(),
      getPlatformTaxonomyCurrentApi(),
      getPlatformTaxonomyPackagesApi(),
      getPlatformTaxonomyImportStatusApi().catch(() => null),
    ]);
    setupStatus.value = status;
    platformSetupStore.setTaxonomyStatus(status);
    taxonomyCurrent.value = current;
    packageRows.value = packages.items || [];
    recommendedPackageId.value =
      packages.recommended_package?.id || current.current_package?.id || null;
    latestJob.value = job;
    if (job?.status && ['pending', 'running'].includes(job.status)) {
      scheduleStatusPolling(job.id);
    } else {
      clearPollTimer();
    }
    await maybeRedirectAfterReady();
  } finally {
    pageLoading.value = false;
  }
}

async function handleStartImport(packageId: number, force: boolean) {
  importSubmitting.value = true;
  try {
    const job = await startPlatformTaxonomyImportApi({
      package_id: packageId,
      force_reinstall: force,
    });
    latestJob.value = {
      ...job,
      setup_state: {
        job,
        lock: taxonomyCurrent.value?.lock || {
          is_locked: 1,
          lock_code: 'taxonomy_required',
          reason: $t('dataset.staging.taxonomyImporting'),
          required_action: 'install_taxonomy',
        },
        package:
          packageRows.value.find((item) => item.id === job.package_id) ||
          taxonomyCurrent.value?.current_package ||
          null,
        ready: false,
        snapshot: taxonomyCurrent.value?.current_snapshot || null,
        status: 'importing',
      },
    };
    createMessage.success(
      force ? $t('dataset.staging.taxonomyReinstallStarted') : $t('dataset.staging.taxonomyImportStarted'),
    );
    scheduleStatusPolling(job.id);
    await loadPageData();
  } finally {
    importSubmitting.value = false;
  }
}

async function handleStartRecommended() {
  const targetPackageId =
    recommendedPackageId.value || packageRows.value[0]?.id;
  if (!targetPackageId) {
    createMessage.warning($t('dataset.staging.noAvailablePackage'));
    return;
  }
  await handleStartImport(targetPackageId, forceReinstall.value);
}

function goToPlatformSetting() {
  router.push('/platform/setting').catch(() => undefined);
}

function goToRedirectTarget() {
  if (!redirectTarget.value) {
    return;
  }
  router.push(redirectTarget.value).catch(() => undefined);
}

onMounted(() => {
  void loadPageData();
});

onBeforeUnmount(() => {
  clearPollTimer();
});
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <div class="taxonomy-setup-page">
      <Card :bordered="false" class="hero-card">
        <div class="hero-title-wrap">
          <div>
            <div class="hero-eyebrow">System Initialization Package</div>
            <h2 class="hero-title">{{ $t('platform.taxonomy.pageTitle') }}</h2>
            <p class="hero-description">
              {{ $t('platform.taxonomy.pageDescription') }}
            </p>
          </div>
          <div class="hero-actions">
            <Button @click="goToPlatformSetting">{{ $t('platform.taxonomy.backToSetting') }}</Button>
            <Button
              :loading="pageLoading"
              type="primary"
              ghost
              @click="loadPageData"
            >
              {{ $t('platform.taxonomy.refreshStatus') }}
            </Button>
          </div>
        </div>
      </Card>

      <Alert
        show-icon
        :type="
          taxonomyCurrent?.ready ? 'success' : activeJob ? 'info' : 'warning'
        "
        :message="$t('platform.taxonomy.initNote')"
        :description="
          taxonomyCurrent?.ready
            ? $t('dataset.staging.taxonomyInitDone')
            : activeJob
              ? $t('dataset.staging.taxonomyImportRunning')
              : $t('dataset.staging.taxonomyNotInitialized')
        "
      />

      <Alert
        v-if="taxonomyCurrent?.ready && redirectTarget"
        show-icon
        type="success"
        :message="$t('platform.taxonomy.canReturnTitle')"
        :description="$t('platform.taxonomy.canReturnDesc', { target: redirectTarget })"
      >
        <template #action>
          <Button size="small" type="primary" @click="goToRedirectTarget">
            {{ $t('platform.taxonomy.returnToOriginal') }}
          </Button>
        </template>
      </Alert>

      <div class="summary-grid">
        <Card :bordered="false">
          <Statistic :title="$t('platform.taxonomy.currentStatus')">
            <template #formatter>
              <Tag :color="statusMeta.color">{{ statusMeta.label }}</Tag>
            </template>
          </Statistic>
          <div class="summary-help">
            {{
              taxonomyCurrent?.lock?.reason ||
              setupStatus?.locks?.[0]?.reason ||
              $t('platform.taxonomy.statusUnknown')
            }}
          </div>
        </Card>

        <Card :bordered="false">
          <Statistic
            :title="$t('dataset.staging.currentSnapshotVersion')"
            :value="
              taxonomyCurrent?.current_snapshot?.source_version || $t('dataset.staging.notInstalled')
            "
          />
          <div class="summary-help">
            {{ $t('platform.taxonomy.lastLoadTime') }}{{
              formatDateTime(taxonomyCurrent?.current_snapshot?.loaded_at)
            }}
          </div>
        </Card>

        <Card :bordered="false">
          <Statistic
            :title="$t('dataset.staging.taxonomyNodeCount')"
            :value="taxonomyCurrent?.current_snapshot?.node_count || 0"
          />
          <div class="summary-help">
            {{ $t('platform.taxonomy.nameCount') }}{{ taxonomyCurrent?.current_snapshot?.name_count || 0 }}
          </div>
        </Card>
      </div>

      <Card :title="$t('dataset.staging.importJobs')" :bordered="false" :loading="pageLoading">
        <div v-if="latestJob" class="job-panel">
          <div class="job-header">
            <Space wrap>
              <Tag
                :color="
                  latestJob.status === 'success'
                    ? 'green'
                    : latestJob.status === 'failed'
                      ? 'red'
                      : 'processing'
                "
              >
                {{ latestJob.status }}
              </Tag>
              <span>{{ $t('dataset.staging.jobId') }}{{ latestJob.id }}</span>
              <span>{{ $t('dataset.staging.stage') }}{{ latestJob.stage || '-' }}</span>
            </Space>
            <span class="job-time">
              {{ $t('platform.taxonomy.updateTime') }}{{ formatDateTime(latestJob.updated_at) }}
            </span>
          </div>
          <Progress
            :percent="Number(latestJob.progress_percent || 0)"
            :status="
              latestJob.status === 'failed'
                ? 'exception'
                : latestJob.status === 'success'
                  ? 'success'
                  : 'active'
            "
          />
          <div class="job-message">
            {{ latestJob.message || $t('dataset.staging.waitingJobMessage') }}
          </div>
          <Alert
            v-if="latestJob.error_message"
            type="error"
            show-icon
            :message="latestJob.error_message"
          />
        </div>
        <Empty v-else :description="$t('dataset.staging.noTaxonomyJobs')" />
      </Card>

      <Card :title="$t('dataset.staging.startImport')" :bordered="false" :loading="pageLoading">
        <div class="start-panel">
          <div class="start-panel__text">
            {{ $t('platform.taxonomy.recommendedPackage') }}
            <strong>
              {{
                packageRows.find((item) => item.id === recommendedPackageId)
                  ?.package_name || $t('dataset.staging.noRecommendedPackage')
              }}
            </strong>
          </div>
          <div class="start-panel__actions">
            <div class="force-switch">
              <span>{{ $t('dataset.staging.forceReinstall') }}</span>
              <Switch v-model:checked="forceReinstall" />
            </div>
            <Button
              type="primary"
              :disabled="!canStartImport"
              :loading="importSubmitting"
              @click="handleStartRecommended"
            >
              {{ forceReinstall ? $t('dataset.staging.startReinstall') : $t('dataset.staging.startImport') }}
            </Button>
          </div>
        </div>
      </Card>

      <Card :title="$t('dataset.staging.availablePackages')" :bordered="false" :loading="pageLoading">
        <Table
          :columns="packageColumns"
          :data-source="packageRows"
          :pagination="false"
          :scroll="{ x: 1080 }"
          row-key="id"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'package_type'">
              <Tag color="blue">{{ record.package_type }}</Tag>
            </template>
            <template v-else-if="column.key === 'status'">
              <Tag :color="record.status === 'ready' ? 'green' : 'default'">
                {{ record.status }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'file_size'">
              {{ formatFileSize(record.file_size) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <Space wrap>
                <Button
                  size="small"
                  type="primary"
                  :disabled="!!activeJob"
                  @click="handleStartImport(record.id, false)"
                >
                  {{ $t('platform.taxonomy.importAction') }}
                </Button>
                <Button
                  size="small"
                  danger
                  ghost
                  :disabled="!!activeJob"
                  @click="handleStartImport(record.id, true)"
                >
                  {{ $t('platform.taxonomy.reinstallAction') }}
                </Button>
              </Space>
            </template>
          </template>
          <template #emptyText>
            <Empty :description="$t('dataset.staging.noAvailablePackage')" />
          </template>
        </Table>
      </Card>
    </div>
  </Page>
</template>

<style scoped lang="less">
.taxonomy-setup-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card {
  overflow: hidden;
  background:
    radial-gradient(
      circle at top left,
      rgba(19, 145, 89, 0.16),
      transparent 34%
    ),
    linear-gradient(135deg, #f7fbf7 0%, #f1f6f4 100%);
}

.hero-title-wrap {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.hero-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.hero-eyebrow {
  margin-bottom: 8px;
  color: #0f8a56;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-title {
  margin: 0;
  color: #183128;
  font-size: 28px;
  font-weight: 700;
}

.hero-description {
  max-width: 760px;
  margin: 12px 0 0;
  color: #496259;
  font-size: 14px;
  line-height: 1.75;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.summary-help {
  margin-top: 10px;
  color: #5c6e67;
  font-size: 13px;
}

.job-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.job-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.job-time,
.job-message {
  color: #5c6e67;
  font-size: 13px;
}

.start-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.start-panel__text {
  color: #2c4439;
  font-size: 14px;
}

.start-panel__actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.force-switch {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #4f5f58;
}

@media (max-width: 960px) {
  .hero-title-wrap,
  .start-panel,
  .job-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .start-panel__actions,
  .hero-actions {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
