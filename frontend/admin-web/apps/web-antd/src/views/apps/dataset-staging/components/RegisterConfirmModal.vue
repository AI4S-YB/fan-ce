<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import {
  Button,
  Form,
  Input,
  Modal,
  Radio,
  Select,
  Tag,
} from 'ant-design-vue';
import type { DirectoryTreeNode } from '#/api/apps/dataset';
import { registerCandidateApi, createRegistrationCandidateApi } from '#/api/apps/dataset';
import { useMessage } from '#/hooks/web/useMessage';
import { $t } from '@vben/locales';

defineOptions({ name: 'RegisterConfirmModal' });

const props = defineProps<{
  visible: boolean;
  files: DirectoryTreeNode[];
  scanRootId?: number;
}>();

const emit = defineEmits<{
  'update:visible': [value: boolean];
  registered: [];
}>();

const { createMessage } = useMessage();
const loading = ref(false);

const DATASET_TYPE_OPTIONS = [
  { label: $t('dataset.staging.type_genome'), value: 'genome' },
  { label: $t('dataset.staging.type_transcriptome'), value: 'transcriptome' },
  { label: $t('dataset.staging.type_variome'), value: 'variome' },
  { label: $t('dataset.staging.type_phenome'), value: 'phenome' },
  { label: $t('dataset.staging.type_generic'), value: 'generic' },
];

const REGISTRATION_MODE_OPTIONS = [
  { label: $t('dataset.staging.prebuiltRegistration'), value: 'prebuilt' },
  { label: $t('dataset.staging.hybridRegistration'), value: 'hybrid' },
  { label: $t('dataset.staging.recipeBuildMode'), value: 'recipe_build' },
];

// --- Inference ---
const inferredDatasetType = computed(() => {
  const counts: Record<string, number> = {};
  for (const file of props.files) {
    const type = formatToType(file.format);
    counts[type] = (counts[type] || 0) + 1;
  }
  const maxCount = Math.max(...Object.values(counts), 0);
  const top = Object.entries(counts).filter(([, c]) => c === maxCount);
  return top.length === 1 ? top[0]![0]! : 'generic';
});

const inferredMode = computed(() => {
  const prebuiltFormats = new Set(['db', 'sqlite', 'h5', 'hdf5', 'tbi', 'csi']);
  let hasPrebuilt = false;
  let hasSource = false;
  for (const file of props.files) {
    if (prebuiltFormats.has(file.format)) {
      hasPrebuilt = true;
    } else {
      hasSource = true;
    }
  }
  if (hasPrebuilt && hasSource) return 'hybrid';
  if (hasPrebuilt) return 'prebuilt';
  return 'recipe_build';
});

const directoryName = computed(() => {
  if (props.files.length === 0) return 'unknown';
  const parts = props.files[0]!.path.split('/').filter(Boolean);
  // Use the parent directory name of the first file
  return parts.length >= 2 ? parts[parts.length - 2]! : (parts[0] || 'unknown');
});

function formatToType(format: string): string {
  const map: Record<string, string> = {
    fa: 'genome', fasta: 'genome', fna: 'genome',
    'fa.gz': 'genome', 'fasta.gz': 'genome', 'fna.gz': 'genome',
    vcf: 'variome', 'vcf.gz': 'variome', bcf: 'variome',
    h5: 'transcriptome', hdf5: 'transcriptome',
    xlsx: 'phenome', xls: 'phenome', csv: 'phenome', tsv: 'phenome',
    gff: 'annotation', 'gff.gz': 'annotation', gff3: 'annotation',
    'gff3.gz': 'annotation', gtf: 'annotation', 'gtf.gz': 'annotation',
    bed: 'signal', 'bed.gz': 'signal', bw: 'signal', bigwig: 'signal',
    bedpe: 'interaction', 'bedpe.gz': 'interaction',
    pairs: 'interaction', 'pairs.gz': 'interaction',
    cool: 'interaction', mcool: 'interaction',
    sqlite: 'generic', db: 'generic',
  };
  return map[format] || 'generic';
}

// --- Form ---
const form = reactive({
  candidateName: directoryName.value,
  datasetType: inferredDatasetType.value,
  registrationMode: inferredMode.value as 'prebuilt' | 'hybrid' | 'recipe_build',
  versionName: '',
  organism: '',
  assembly: '',
});

watch(() => props.visible, (val) => {
  if (val) {
    form.candidateName = directoryName.value;
    form.datasetType = inferredDatasetType.value;
    form.registrationMode = inferredMode.value as 'prebuilt' | 'hybrid' | 'recipe_build';
    form.versionName = '';
    form.organism = '';
    form.assembly = '';
  }
});

async function handleSubmit() {
  if (!form.candidateName.trim()) {
    createMessage.error($t('dataset.staging.fillCandidateName'));
    return;
  }
  loading.value = true;
  try {
    // Step 1: create candidate
    const candidateResult = await createRegistrationCandidateApi({
      candidate_name: form.candidateName.trim(),
      dataset_type: form.datasetType,
      registration_mode: form.registrationMode,
      version_name: form.versionName || undefined,
      organism: form.organism || undefined,
      assembly: form.assembly || undefined,
      scan_root_id: props.scanRootId,
      items: props.files.map((f, i) => ({
        staging_file_id: f.staging_id || 0,
        is_primary: i === 0,
      })),
    });
    const candidateData = candidateResult as any;
    const candidateId = candidateData?.id || candidateData?.candidate_id;
    if (candidateId) {
      await registerCandidateApi(candidateId, {});
    }
    createMessage.success($t('dataset.staging.registrationSubmitted'));
    emit('update:visible', false);
    emit('registered');
  } catch (error: any) {
    createMessage.error(error?.message || $t('dataset.staging.registerFailed'));
  } finally {
    loading.value = false;
  }
}

function handleCancel() {
  emit('update:visible', false);
}
</script>

<template>
  <Modal
    :open="visible"
    :title="$t('dataset.staging.registerConfirm')"
    :confirm-loading="loading"
    @ok="handleSubmit"
    @cancel="handleCancel"
    :ok-text="$t('dataset.staging.confirmRegister')"
    :cancel-text="$t('platform.setting.cancelText')"
    width="640px"
  >
    <Form layout="vertical">
      <Form.Item :label="$t('dataset.staging.candidateName')">
        <Input v-model:value="form.candidateName" />
      </Form.Item>

      <Form.Item :label="$t('dataset.staging.dataType')">
        <Select v-model:value="form.datasetType" :options="DATASET_TYPE_OPTIONS" />
      </Form.Item>

      <Form.Item :label="$t('dataset.staging.registrationMode')">
        <Radio.Group v-model:value="form.registrationMode">
          <Radio.Button
            v-for="opt in REGISTRATION_MODE_OPTIONS"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </Radio.Button>
        </Radio.Group>
      </Form.Item>

      <Form.Item :label="$t('dataset.list.targetVersion')">
        <Input v-model:value="form.versionName" :placeholder="$t('dataset.staging.optional')" />
      </Form.Item>

      <Form.Item :label="$t('geneset.list.species')">
        <Input v-model:value="form.organism" :placeholder="$t('dataset.staging.optional')" />
      </Form.Item>

      <Form.Item :label="$t('dataset.staging.assembly')">
        <Input v-model:value="form.assembly" :placeholder="$t('dataset.staging.optional')" />
      </Form.Item>
    </Form>

    <div class="file-list-preview">
      <div class="preview-title">{{ $t('dataset.staging.awaitingRegistrationFiles', { count: files.length }) }}</div>
      <div v-for="file in files" :key="file.path" class="preview-file-row">
        <Tag color="green">OK</Tag>
        {{ file.name }}
        <Tag>{{ file.format }}</Tag>
        <span class="file-size">{{ (file.size / 1024 / 1024).toFixed(1) }} MB</span>
      </div>
    </div>
  </Modal>
</template>

<style scoped>
.file-list-preview {
  margin-top: 16px;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
}

.preview-title {
  font-weight: 500;
  margin-bottom: 8px;
}

.preview-file-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
  font-size: 13px;
}

.file-size {
  color: #999;
  margin-left: auto;
}
</style>
