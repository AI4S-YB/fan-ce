<script setup lang="ts">
import type {
  PlatformSetupCurrentResponse,
  PlatformSetupJobStatusResponse,
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
  Tag,
} from 'ant-design-vue';

import {
  getPlatformSetupStatusApi,
  getPlatformTaxonomyCurrentApi,
  getPlatformTaxonomyImportStatusApi,
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
const latestJob = ref<null | PlatformSetupJobStatusResponse>(null);
const forceReinstall = ref(false);
const customDumpPath = ref('');
const pollTimer = ref<null | ReturnType<typeof setTimeout>>(null);
const redirecting = ref(false);

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
  return !importSubmitting.value && !activeJob.value;
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
    const [status, current, job] = await Promise.all([
      getPlatformSetupStatusApi(),
      getPlatformTaxonomyCurrentApi(),
      getPlatformTaxonomyImportStatusApi().catch(() => null),
    ]);
    setupStatus.value = status;
    platformSetupStore.setTaxonomyStatus(status);
    taxonomyCurrent.value = current;
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

async function handleStartImport(force: boolean) {
  importSubmitting.value = true;
  try {
    const job = await startPlatformTaxonomyImportApi({
      force_reinstall: force,
      dump_path: customDumpPath.value || null,
    });
    latestJob.value = {
      ...job,
      setup_state: {
        lock: taxonomyCurrent.value?.lock || {
          is_locked: 1,
          lock_code: 'taxonomy_required',
          reason: $t('dataset.staging.taxonomyImporting'),
          required_action: 'install_taxonomy',
        },
        ready: false,
        node_count: taxonomyCurrent.value?.node_count || 0,
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
  await handleStartImport(forceReinstall.value);
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
            :title="$t('dataset.staging.taxonomyNodeCount')"
            :value="taxonomyCurrent?.node_count || 0"
          />
          <div class="summary-help">
            {{ $t('platform.taxonomy.lastLoadTime') }}{{
              formatDateTime(taxonomyCurrent?.latest_job?.finished_at)
            }}
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
            {{ forceReinstall ? $t('dataset.staging.taxonomyReinstallStarted') : $t('dataset.staging.taxonomyImportStarted') }}
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
          <div class="start-panel__path">
            <span class="path-label">{{ $t('platform.taxonomy.customPath') }}</span>
            <input
              v-model="customDumpPath"
              type="text"
              :placeholder="$t('platform.taxonomy.customPathPlaceholder')"
              class="path-input"
            />
          </div>
        </div>
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
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
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0 16px;
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

.start-panel__path {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e8edea;
}

.path-label {
  color: #5c6e67;
  font-size: 13px;
  white-space: nowrap;
}

.path-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #d0d9d3;
  border-radius: 6px;
  color: #2c4439;
  font-size: 13px;
  background: #fafbfa;
  outline: none;
  transition: border-color 0.2s;
}

.path-input:focus {
  border-color: #0f8a56;
}

.path-input::placeholder {
  color: #a0b0a8;
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
