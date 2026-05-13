<script setup lang="ts">
import type { UploadFile } from 'ant-design-vue';

import type {
  GermplasmFieldSchemaItem,
  GermplasmImportValidationResult,
  GermplasmTaxonomyOption,
} from './types';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  message,
  Modal,
  Progress,
  Select,
  Space,
  Steps,
  Table,
  Tag,
  TypographyParagraph,
  Upload,
} from 'ant-design-vue';

import {
  commitGermplasmImportApi,
  getGermplasmTaxonomyOptionsApi,
  validateGermplasmImportApi,
} from './api';

import { $t } from '@vben/locales';

defineOptions({ name: 'GermplasmImportPage' });

const router = useRouter();

const templateProfile = ref('crop_germplasm_v1');
const taxonomyTaxId = ref<number | undefined>(undefined);
const taxonomyOptions = ref<
  Array<{ label: string; raw: GermplasmTaxonomyOption; value: number }>
>([]);
const selectedTaxonomy = ref<GermplasmTaxonomyOption | null>(null);
const selectedFile = ref<File | null>(null);
const fileList = ref<UploadFile[]>([]);
const validating = ref(false);
const committing = ref(false);
const uploadPercent = ref<number>(0);
const validationResult = ref<GermplasmImportValidationResult | null>(null);
const helpVisible = ref(false);

const currentStep = computed(() => {
  if (committing.value) {
    return 3;
  }
  if (validationResult.value) {
    return validationResult.value.summary.passed ? 2 : 2;
  }
  if (selectedFile.value) {
    return 1;
  }
  return 0;
});

const canValidate = computed(
  () => !!selectedFile.value && !!taxonomyTaxId.value && !validating.value,
);
const canCommit = computed(
  () =>
    !!validationResult.value?.summary?.passed &&
    !!validationResult.value?.validation_token &&
    !committing.value,
);
const templateDownloadUrl = computed(() => {
  if (templateProfile.value === 'crop_germplasm_v1') {
    return '/static/templates/germplasm/crop_germplasm_v1.xlsx';
  }
  return '';
});
const demoDownloadUrl =
  '/static/templates/germplasm/crop_germplasm_rice_demo.xlsx';

function downloadTemplateExample() {
  if (!templateDownloadUrl.value) {
    message.warning($t('germplasm.import.noTemplateExample'));
    return;
  }
  window.open(templateDownloadUrl.value, '_blank', 'noopener,noreferrer');
}

function downloadDemoData() {
  window.open(demoDownloadUrl, '_blank', 'noopener,noreferrer');
}

const templateFieldColumns = [
  { title: $t('germplasm.import.field'), dataIndex: 'field', key: 'field', width: 130 },
  { title: $t('germplasm.import.required'), dataIndex: 'required', key: 'required', width: 90 },
  { title: $t('germplasm.import.description'), dataIndex: 'description', key: 'description' },
  { title: $t('germplasm.import.example'), dataIndex: 'example', key: 'example', width: 180 },
];

const templateFieldRows = [
  {
    field: 'ID',
    required: $t('germplasm.detail.yes'),
    description: $t('germplasm.import.tfFieldId'),
    example: 'RH00004',
  },
  {
    field: 'chinese_name',
    required: $t('germplasm.detail.yes'),
    description: $t('germplasm.import.tfFieldChineseName'),
    example: $t('germplasm.import.tfExampleChineseName'),
  },
  {
    field: 'english_name',
    required: $t('germplasm.detail.no'),
    description: $t('germplasm.import.tfFieldEnglishName'),
    example: 'Outta The Blue',
  },
  {
    field: 'P',
    required: $t('germplasm.detail.no'),
    description: $t('germplasm.import.tfFieldP'),
    example: 'RH00010',
  },
  {
    field: 'M',
    required: $t('germplasm.detail.no'),
    description: $t('germplasm.import.tfFieldM'),
    example: 'RH00011',
  },
  {
    field: 'P_name',
    required: $t('germplasm.detail.no'),
    description: $t('germplasm.import.tfFieldPName'),
    example: $t('germplasm.import.tfExamplePName'),
  },
  {
    field: 'M_name',
    required: $t('germplasm.detail.no'),
    description: $t('germplasm.import.tfFieldMName'),
    example: $t('germplasm.import.tfExampleMName'),
  },
];

const customFieldColumns = [
  { title: $t('germplasm.import.rule'), dataIndex: 'rule', key: 'rule', width: 160 },
  { title: $t('germplasm.import.description'), dataIndex: 'description', key: 'description' },
  { title: $t('germplasm.import.example'), dataIndex: 'example', key: 'example', width: 220 },
];

const customFieldRows = [
  {
    rule: $t('germplasm.import.cfRuleStartPositionLabel'),
    description: $t('germplasm.import.cfRuleStartPosition'),
    example: $t('germplasm.import.cfExStartPosition'),
  },
  {
    rule: $t('germplasm.import.cfRuleFieldNamingLabel'),
    description: $t('germplasm.import.cfRuleFieldNaming'),
    example: $t('germplasm.import.cfExFieldNaming'),
  },
  {
    rule: $t('germplasm.import.cfRuleFieldValueLabel'),
    description: $t('germplasm.import.cfRuleFieldValue'),
    example: $t('germplasm.import.cfExFieldValue'),
  },
  {
    rule: $t('germplasm.import.cfRuleEmptyHeaderLabel'),
    description: $t('germplasm.import.cfRuleEmptyHeader'),
    example: $t('germplasm.import.cfExEmptyHeader'),
  },
];

const validationRuleColumns = [
  { title: $t('germplasm.import.validationItem'), dataIndex: 'rule', key: 'rule', width: 180 },
  { title: $t('germplasm.import.description'), dataIndex: 'description', key: 'description' },
];

const validationRuleRows = [
  {
    rule: $t('germplasm.import.vrRuleRequiredFixedLabel'),
    description: $t('germplasm.import.vrRuleRequiredFixed'),
  },
  {
    rule: $t('germplasm.import.vrRuleDuplicateHeaderLabel'),
    description: $t('germplasm.import.vrRuleDuplicateHeader'),
  },
  {
    rule: $t('germplasm.import.vrRuleEmptyHeaderLabel'),
    description: $t('germplasm.import.vrRuleEmptyHeader'),
  },
  {
    rule: $t('germplasm.import.vrRuleIdUniqueLabel'),
    description: $t('germplasm.import.vrRuleIdUnique'),
  },
  {
    rule: $t('germplasm.import.vrRuleSelfRefLabel'),
    description: $t('germplasm.import.vrRuleSelfRef'),
  },
  {
    rule: $t('germplasm.import.vrRuleCommentRowLabel'),
    description: $t('germplasm.import.vrRuleCommentRow'),
  },
];

async function loadTaxonomyOptions(keyword?: string) {
  const response = await getGermplasmTaxonomyOptionsApi({
    keyword,
    limit: 100,
    active_only: 1,
    with_germplasm_only: 0,
  });
  const items =
    (response as any)?.items ?? (response as any)?.data?.items ?? [];
  taxonomyOptions.value = items.map((item: GermplasmTaxonomyOption) => ({
    label: item.common_name
      ? `${item.scientific_name} (${item.common_name})`
      : `${item.scientific_name || item.tax_id}`,
    value: item.tax_id,
    raw: item,
  }));
  if (taxonomyTaxId.value) {
    selectedTaxonomy.value =
      taxonomyOptions.value.find((item) => item.value === taxonomyTaxId.value)
        ?.raw || null;
  }
}

function handleUploadChange(info: { fileList: UploadFile[] }) {
  fileList.value = info.fileList.slice(-1);
  const current = info.fileList[0];
  selectedFile.value = (current?.originFileObj as File) || null;
  validationResult.value = null;
  uploadPercent.value = 0;
}

function handleTaxonomyChange(value: any, option: any) {
  taxonomyTaxId.value =
    value !== undefined && value !== null ? Number(value) : undefined;
  selectedTaxonomy.value = option?.raw || null;
  validationResult.value = null;
}

async function runValidation() {
  if (!selectedFile.value || !taxonomyTaxId.value) {
    message.warning($t('germplasm.import.selectSpeciesAndUpload'));
    return;
  }
  validating.value = true;
  validationResult.value = null;
  uploadPercent.value = 0;
  try {
    const response = await validateGermplasmImportApi(
      {
        file: selectedFile.value,
        taxonomy_tax_id: String(taxonomyTaxId.value),
        template_profile: templateProfile.value,
      },
      (event) => {
        if (event.total) {
          uploadPercent.value = Math.round((event.loaded / event.total) * 100);
        }
      },
    );
    validationResult.value = response as any;
    if (validationResult.value?.summary?.passed) {
      message.success($t('germplasm.import.validationSuccess'));
    } else {
      message.warning($t('germplasm.import.validationNotPassed'));
    }
  } catch {
    validationResult.value = null;
  } finally {
    validating.value = false;
  }
}

async function commitImport() {
  if (!validationResult.value?.validation_token) {
    return;
  }
  committing.value = true;
  try {
    const result = await commitGermplasmImportApi({
      validation_token: validationResult.value.validation_token,
    });
    message.success($t('germplasm.import.importSuccess'));
    router.push({
      path: '/germplasm/list',
      query: {
        taxonomy_tax_id: String(validationResult.value.summary.taxonomy_tax_id),
      },
    });
    return result;
  } finally {
    committing.value = false;
  }
}

function resetPage() {
  selectedFile.value = null;
  fileList.value = [];
  validationResult.value = null;
  uploadPercent.value = 0;
}

onMounted(() => {
  void loadTaxonomyOptions();
});

const issueColumns = [
  { title: $t('germplasm.import.rowNo'), dataIndex: 'row_no', key: 'row_no', width: 90 },
  { title: $t('germplasm.import.columnName'), dataIndex: 'column_name', key: 'column_name', width: 140 },
  { title: $t('germplasm.import.issueType'), dataIndex: 'error_code', key: 'error_code', width: 180 },
  { title: $t('germplasm.import.description'), dataIndex: 'message', key: 'message' },
];

const previewColumns = [
  {
    title: $t('germplasm.list.id'),
    dataIndex: 'accession_id',
    key: 'accession_id',
    width: 140,
  },
  {
    title: $t('germplasm.list.displayName'),
    dataIndex: 'display_name',
    key: 'display_name',
    width: 160,
  },
  {
    title: $t('germplasm.list.englishName'),
    dataIndex: 'english_name',
    key: 'english_name',
    width: 200,
  },
  {
    title: $t('germplasm.detail.father'),
    dataIndex: 'father_accession',
    key: 'father_accession',
    width: 120,
  },
  {
    title: $t('germplasm.detail.mother'),
    dataIndex: 'mother_accession',
    key: 'mother_accession',
    width: 120,
  },
  {
    title: $t('germplasm.import.excelRowNo'),
    dataIndex: 'source_row_no',
    key: 'source_row_no',
    width: 100,
  },
];

const fieldSchemaColumns = [
  { title: $t('germplasm.import.fieldName'), dataIndex: 'field_label', key: 'field_label', width: 160 },
  {
    title: $t('germplasm.import.sourceColumn'),
    dataIndex: 'source_header',
    key: 'source_header',
    width: 160,
  },
  { title: $t('germplasm.import.systemKey'), dataIndex: 'field_key', key: 'field_key', width: 180 },
  { title: $t('germplasm.import.type'), dataIndex: 'data_type', key: 'data_type', width: 100 },
];

function fieldSchemaRowKey(record: GermplasmFieldSchemaItem) {
  return `${record.field_key}-${record.source_header}`;
}
</script>

<template>
  <Page auto-content-height content-class="p-5">
    <div class="germplasm-import-page">
      <Card :bordered="false" class="hero-card">
        <template #extra>
          <Space>
            <Button @click="router.push('/germplasm/list')">
              {{ $t('germplasm.import.backToList') }}
            </Button>
            <Button @click="router.push('/germplasm/import-batches')">
              {{ $t('germplasm.import.importRecord') }}
            </Button>
            <Button @click="resetPage">{{ $t('germplasm.import.reset') }}</Button>
          </Space>
        </template>
        <div class="hero-eyebrow">{{ $t('germplasm.import.heroEyebrow') }}</div>
        <h2 class="hero-title">{{ $t('germplasm.import.title') }}</h2>
        <p class="hero-description">
          {{ $t('germplasm.import.descriptionHero') }}
        </p>
      </Card>

      <Card :bordered="false">
        <Steps
          :current="currentStep"
          :items="[
            { title: $t('germplasm.import.basicConfig') },
            { title: $t('germplasm.import.uploadFile') },
            { title: $t('germplasm.import.validationResult') },
            { title: $t('germplasm.import.submitImport') },
          ]"
        />
      </Card>

      <div class="page-grid">
        <Card :bordered="false" :title="$t('germplasm.import.basicConfig')">
          <div class="section-stack">
            <div>
              <div class="field-label">{{ $t('germplasm.import.template') }}</div>
              <div class="field-helper">
                {{ $t('germplasm.import.templateHelperText') }}
              </div>
              <Select
                v-model:value="templateProfile"
                style="width: 100%"
                :options="[
                  { label: 'crop_germplasm_v1', value: 'crop_germplasm_v1' },
                ]"
              />
              <Space style="margin-top: 12px">
                <Button type="primary" ghost @click="downloadTemplateExample">
                  {{ $t('germplasm.import.downloadTemplateExample') }}
                </Button>
                <Button @click="downloadDemoData">{{ $t('germplasm.import.downloadDemoData') }}</Button>
                <Button @click="helpVisible = true">{{ $t('germplasm.import.viewFieldHelp') }}</Button>
                <span class="field-helper">
                  {{ $t('germplasm.import.downloadHint') }}
                </span>
              </Space>
              <TypographyParagraph class="template-note">
                {{ $t('germplasm.import.templateNote1') }}<br />
                1. {{ $t('germplasm.import.templateNote2') }}<br />
                2. {{ $t('germplasm.import.templateNote3') }}<br />
                3. {{ $t('germplasm.import.templateNote4') }}<br />
                4. {{ $t('germplasm.import.templateNote5') }}<br />
                5. {{ $t('germplasm.import.templateNote6') }}
              </TypographyParagraph>
              <TypographyParagraph class="template-note">
                {{ $t('germplasm.import.testSuggestion') }}
              </TypographyParagraph>
            </div>

            <div>
              <div class="field-label">{{ $t('germplasm.import.taxonomyAnchor') }}</div>
              <div class="field-helper">
                {{ $t('germplasm.import.taxonomyHint') }}
              </div>
              <Select
                v-model:value="taxonomyTaxId"
                show-search
                :filter-option="false"
                style="width: 100%"
                :placeholder="$t('germplasm.import.taxonomyPlaceholder')"
                :options="taxonomyOptions"
                @search="loadTaxonomyOptions"
                @change="handleTaxonomyChange"
              />
            </div>

            <Descriptions
              v-if="selectedTaxonomy"
              bordered
              :column="1"
              size="small"
            >
              <Descriptions.Item :label="$t('germplasm.import.taxonomyIdLabel')">
                {{ selectedTaxonomy.tax_id }}
              </Descriptions.Item>
              <Descriptions.Item :label="$t('germplasm.import.scientificName')">
                {{ selectedTaxonomy.scientific_name || '-' }}
              </Descriptions.Item>
              <Descriptions.Item :label="$t('germplasm.import.commonName')">
                {{ selectedTaxonomy.common_name || '-' }}
              </Descriptions.Item>
              <Descriptions.Item :label="$t('germplasm.import.taxonomicRank')">
                {{ selectedTaxonomy.rank || '-' }}
              </Descriptions.Item>
              <Descriptions.Item :label="$t('germplasm.import.cacheSource')">
                {{ selectedTaxonomy.source || '-' }}
              </Descriptions.Item>
              <Descriptions.Item :label="$t('germplasm.import.lastSync')">
                {{ selectedTaxonomy.last_sync_time || '-' }}
              </Descriptions.Item>
              <Descriptions.Item :label="$t('germplasm.import.lineageLabel')">
                {{ selectedTaxonomy.lineage || '-' }}
              </Descriptions.Item>
            </Descriptions>
            <Empty v-else :description="$t('germplasm.import.noTaxonomySelected')" />
          </div>
        </Card>

        <Card :bordered="false" :title="$t('germplasm.import.uploadAndValidation')">
          <div class="section-stack">
            <Upload
              :before-upload="() => false"
              :max-count="1"
              :file-list="fileList"
              accept=".xls,.xlsx"
              @change="handleUploadChange"
            >
              <Button>{{ $t('germplasm.import.selectExcel') }}</Button>
            </Upload>

            <TypographyParagraph type="secondary">
              {{ $t('germplasm.import.fileRequirements') }}
            </TypographyParagraph>

            <Progress
              v-if="validating"
              :percent="uploadPercent"
              status="active"
            />

            <Space>
              <Button
                type="primary"
                :loading="validating"
                :disabled="!canValidate"
                @click="runValidation"
              >
                {{ $t('germplasm.import.startValidation') }}
              </Button>
              <Button
                type="primary"
                ghost
                :loading="committing"
                :disabled="!canCommit"
                @click="commitImport"
              >
                {{ $t('germplasm.import.confirmImport') }}
              </Button>
            </Space>
          </div>
        </Card>
      </div>

      <template v-if="validationResult">
        <div class="summary-grid">
          <Card :bordered="false">
            <div class="summary-label">{{ $t('germplasm.import.totalRows') }}</div>
            <div class="summary-value">
              {{ validationResult.summary.total_rows }}
            </div>
          </Card>
          <Card :bordered="false">
            <div class="summary-label">{{ $t('germplasm.import.validRows') }}</div>
            <div class="summary-value">
              {{ validationResult.summary.valid_rows }}
            </div>
          </Card>
          <Card :bordered="false">
            <div class="summary-label">{{ $t('germplasm.import.errorRows') }}</div>
            <div class="summary-value danger">
              {{ validationResult.summary.error_rows }}
            </div>
          </Card>
          <Card :bordered="false">
            <div class="summary-label">{{ $t('germplasm.import.warningRows') }}</div>
            <div class="summary-value warning">
              {{ validationResult.summary.warning_rows }}
            </div>
          </Card>
        </div>

        <Alert
          :type="validationResult.summary.passed ? 'success' : 'warning'"
          show-icon
          :message="
            validationResult.summary.passed
              ? $t('germplasm.import.validationPassed')
              : $t('germplasm.import.validationFailed')
          "
        />

        <div class="page-grid">
          <Card :bordered="false" :title="$t('germplasm.import.fixedFieldRecognition')">
            <Table
              size="small"
              :columns="fieldSchemaColumns"
              :data-source="validationResult.builtin_fields || []"
              :pagination="false"
              :row-key="fieldSchemaRowKey"
            />
          </Card>

          <Card :bordered="false" :title="$t('germplasm.import.batchDynamicFields')">
            <Table
              size="small"
              :columns="fieldSchemaColumns"
              :data-source="validationResult.dynamic_fields || []"
              :pagination="false"
              :row-key="fieldSchemaRowKey"
            />
          </Card>
        </div>

        <div class="page-grid">
          <Card :bordered="false" :title="$t('germplasm.import.errorDetail')">
            <Table
              size="small"
              :columns="issueColumns"
              :data-source="validationResult.errors"
              :pagination="{ pageSize: 5 }"
              row-key="message"
            />
          </Card>

          <Card :bordered="false" :title="$t('germplasm.import.warningDetail')">
            <Table
              size="small"
              :columns="issueColumns"
              :data-source="validationResult.warnings"
              :pagination="{ pageSize: 5 }"
              row-key="message"
            />
          </Card>
        </div>

        <Card :bordered="false" :title="$t('germplasm.import.importPreview')">
          <Table
            size="small"
            :columns="previewColumns"
            :data-source="validationResult.preview_rows"
            :pagination="{ pageSize: 10 }"
            row-key="accession_id"
          />
        </Card>
      </template>
    </div>
    <Modal
      v-model:open="helpVisible"
      :title="$t('germplasm.import.templateFieldHelp')"
      :footer="null"
      width="960px"
    >
      <div class="help-stack">
        <Alert
          type="info"
          show-icon
          :message="$t('germplasm.import.fillConvention')"
          :description="$t('germplasm.import.fillConventionDesc')"
        />
        <Alert
          type="warning"
          show-icon
          :message="$t('germplasm.import.importScope')"
          :description="$t('germplasm.import.importScopeDesc')"
        />
        <Alert
          type="success"
          show-icon
          :message="$t('germplasm.import.dynamicFieldRule')"
          :description="$t('germplasm.import.dynamicFieldRuleDesc')"
        />
        <Table
          size="small"
          :columns="templateFieldColumns"
          :data-source="templateFieldRows"
          :pagination="false"
          row-key="field"
        />
        <Table
          size="small"
          :columns="customFieldColumns"
          :data-source="customFieldRows"
          :pagination="false"
          row-key="rule"
        />
        <Table
          size="small"
          :columns="validationRuleColumns"
          :data-source="validationRuleRows"
          :pagination="false"
          row-key="rule"
        />
      </div>
    </Modal>
  </Page>
</template>

<style scoped lang="less">
.germplasm-import-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card {
  background:
    radial-gradient(
      circle at top right,
      rgba(22, 119, 255, 0.12),
      transparent 36%
    ),
    linear-gradient(135deg, #f8fbff 0%, #f6f8fc 100%);
}

.hero-eyebrow {
  color: #1677ff;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-title {
  margin: 8px 0;
  color: #13213a;
  font-size: 28px;
  font-weight: 700;
}

.hero-description {
  max-width: 860px;
  margin: 0;
  color: #516074;
  line-height: 1.7;
}

.page-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.section-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field-label {
  margin-bottom: 8px;
  color: #516074;
  font-size: 13px;
  font-weight: 600;
}

.field-helper {
  margin-bottom: 8px;
  color: #6a778b;
  font-size: 12px;
  line-height: 1.6;
}

.template-note {
  margin: 12px 0 0;
  color: #516074;
}

.help-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-label {
  color: #6a778b;
  font-size: 13px;
}

.summary-value {
  margin-top: 8px;
  color: #13213a;
  font-size: 28px;
  font-weight: 700;
}

.summary-value.danger {
  color: #d4380d;
}

.summary-value.warning {
  color: #d48806;
}

@media (max-width: 960px) {
  .page-grid,
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
