<script setup lang="ts">
import { ref } from 'vue';
import { useRequest } from '@/composables/useRequest';

const { post } = useRequest();
const PRE = '/public/germplasm';

const loading = ref(false);
const items = ref<any[]>([]);
const total = ref(0);
const keyword = ref('');
const page = ref(1);
const size = ref(20);
const selectedItem = ref<any>(null);
const showDialog = ref(false);
const detailLoading = ref(false);

async function search(pno?: number) {
  loading.value = true;
  try {
    const pageNum = pno || 1;
    page.value = pageNum;
    const data: any = await post(`${PRE}/list`, {
      page: pageNum,
      size: size.value,
      keyword: keyword.value || undefined,
    });
    items.value = data?.items || [];
    total.value = data?.total || 0;
  } finally {
    loading.value = false;
  }
}

async function viewDetail(item: any) {
  await loadDetail(item.accession_id, item.taxonomy_tax_id);
}

async function loadDetail(accessionId: string, taxonomyTaxId: number) {
  showDialog.value = true;
  detailLoading.value = true;
  try {
    const data: any = await post(`${PRE}/info`, {
      accession_id: accessionId,
      taxonomy_tax_id: taxonomyTaxId,
    });
    if (data) {
      selectedItem.value = data;
    } else {
      selectedItem.value = { _notPublic: true, _accessionId: accessionId };
    }
  } catch (e) {
    console.error('Failed to load detail:', e);
    selectedItem.value = { _notPublic: true, _accessionId: accessionId };
  } finally {
    detailLoading.value = false;
  }
}

function navToGermplasm(accessionId: string) {
  loadDetail(accessionId, selectedItem.value?.taxonomy?.tax_id);
}

function formatKw(val: any): string {
  if (val == null) return '-';
  if (typeof val === 'object') return JSON.stringify(val, null, 2);
  return String(val);
}

search();
</script>

<template>
  <div>
    <h2>Germplasm Browser</h2>

    <div style="display:flex;gap:12px;margin-bottom:16px;">
      <el-input v-model="keyword" placeholder="Search by ID, name, or English name..."
        style="width:360px;" clearable @keyup.enter="search()" @clear="search()">
        <template #append>
          <el-button :loading="loading" @click="search()">Search</el-button>
        </template>
      </el-input>
    </div>

    <el-table :data="items" border size="small" v-loading="loading" stripe max-height="600">
      <el-table-column prop="accession_id" label="Accession" width="140" />
      <el-table-column prop="display_name" label="Name" min-width="160" />
      <el-table-column prop="english_name" label="English Name" min-width="160" />
      <el-table-column label="Taxonomy" width="180">
        <template #default="{ row }">
          <span style="font-style:italic;">{{ row?.taxonomy?.scientific_name || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="Parents" width="160">
        <template #default="{ row }">
          <span v-if="row.father_accession || row.mother_accession"
            style="font-size:12px;">
            {{ row.father_accession || '?' }} × {{ row.mother_accession || '?' }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="" width="80" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="viewDetail(row)">Detail</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div style="display:flex;justify-content:center;margin-top:16px;">
      <el-pagination
        v-model:current-page="page"
        :page-size="size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="(p: number) => search(p)"
      />
    </div>

    <!-- Centered dialog instead of drawer -->
    <el-dialog v-model="showDialog" :title="selectedItem?._notPublic ? 'Not Available' : (selectedItem?.display_name || 'Germplasm Detail')"
      width="90%" top="3vh" :close-on-click-modal="false" destroy-on-close>
      <div v-if="selectedItem?._notPublic" style="text-align:center;padding:60px 20px;">
        <el-icon :size="48" style="color:#e6a23c;"><svg viewBox="0 0 1024 1024" width="1em" height="1em" fill="currentColor"><path d="M512 64a448 448 0 110 896 448 448 0 010-896zm0 832a384 384 0 100-768 384 384 0 000 768zm-42.667-597.333h85.334v256h-85.334V298.667zM512 682.667a42.667 42.667 0 110 85.333 42.667 42.667 0 010-85.333z"/></svg></el-icon>
        <p style="font-size:16px;color:#e6a23c;margin:16px 0 8px;">
          Germplasm <strong>{{ selectedItem._accessionId }}</strong> is not publicly available
        </p>
        <p style="font-size:13px;color:#909399;">
          This germplasm is being curated and will be published once ready.
        </p>
      </div>
      <template v-else-if="selectedItem">
        <el-row :gutter="16">
          <!-- Left: basic info + attributes -->
          <el-col :span="12">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="Accession">{{ selectedItem.accession_id }}</el-descriptions-item>
              <el-descriptions-item label="English Name">{{ selectedItem.english_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="Species">
                <span style="font-style:italic;">{{ selectedItem?.taxonomy?.scientific_name || '-' }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="Rank">{{ selectedItem?.taxonomy?.rank || '-' }}</el-descriptions-item>
            </el-descriptions>

            <div v-if="selectedItem.attributes && Object.keys(selectedItem.attributes).length > 0" style="margin-top:16px;">
              <h4 style="margin:0 0 8px;">Attributes</h4>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item v-for="(val, key) in selectedItem.attributes" :key="key" :label="String(key)">
                  <pre style="margin:0;white-space:pre-wrap;font-family:inherit;font-size:12px;">{{ formatKw(val) }}</pre>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-col>

          <!-- Right: lineage -->
          <el-col :span="12">
            <!-- Parents -->
            <h4 style="margin:0 0 8px;">Parents</h4>
            <div style="display:flex;gap:8px;align-items:center;">
              <div v-if="selectedItem.father_accession"
                style="flex:1;padding:12px;background:#f0f5ff;border-radius:6px;text-align:center;cursor:pointer;"
                @click="navToGermplasm(selectedItem.father_accession)">
                <div style="font-size:11px;color:#888;">Father</div>
                <div style="font-weight:600;color:#409eff;">{{ selectedItem.father_accession }}</div>
                <div v-if="selectedItem.father_name_snapshot" style="font-size:11px;color:#666;">
                  {{ selectedItem.father_name_snapshot }}
                </div>
              </div>
              <div v-else style="flex:1;padding:12px;background:#fafafa;border-radius:6px;text-align:center;">
                <div style="font-size:11px;color:#888;">Father</div>
                <div style="color:#ccc;">Unknown</div>
              </div>
              <span style="font-size:18px;color:#bbb;">×</span>
              <div v-if="selectedItem.mother_accession"
                style="flex:1;padding:12px;background:#fff0f0;border-radius:6px;text-align:center;cursor:pointer;"
                @click="navToGermplasm(selectedItem.mother_accession)">
                <div style="font-size:11px;color:#888;">Mother</div>
                <div style="font-weight:600;color:#409eff;">{{ selectedItem.mother_accession }}</div>
                <div v-if="selectedItem.mother_name_snapshot" style="font-size:11px;color:#666;">
                  {{ selectedItem.mother_name_snapshot }}
                </div>
              </div>
              <div v-else style="flex:1;padding:12px;background:#fafafa;border-radius:6px;text-align:center;">
                <div style="font-size:11px;color:#888;">Mother</div>
                <div style="color:#ccc;">Unknown</div>
              </div>
            </div>

            <!-- Recorded lineage -->
            <template v-if="selectedItem?.lineage_summary?.parents?.length">
              <h4 style="margin:16px 0 8px;">Recorded Lineage</h4>
              <el-table :data="selectedItem.lineage_summary.parents" border size="small" @row-click="(r: any) => navToGermplasm(r.parent_accession)">
                <el-table-column prop="parent_accession" label="Parent">
                  <template #default="{ row }">
                    <span style="color:#409eff;cursor:pointer;">{{ row.parent_accession }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="parent_role" label="Role" width="90">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.parent_role === 'father' ? '' : 'danger'">
                      {{ row.parent_role }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </template>

            <!-- Progeny -->
            <template v-if="selectedItem?.lineage_summary?.children?.length">
              <h4 style="margin:16px 0 8px;">
                Progeny
                <span style="font-weight:400;color:#888;">({{ selectedItem.lineage_summary.child_count }})</span>
              </h4>
              <el-table :data="selectedItem.lineage_summary.children" border size="small" max-height="260"
                @row-click="(r: any) => navToGermplasm(r.child_accession)">
                <el-table-column prop="child_accession" label="Child">
                  <template #default="{ row }">
                    <span style="color:#409eff;cursor:pointer;">{{ row.child_accession }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="parent_role" label="As" width="90">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.parent_role === 'father' ? '' : 'danger'">
                      {{ row.parent_role }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </template>

            <div v-if="!selectedItem?.lineage_summary?.parents?.length && !selectedItem?.lineage_summary?.children?.length"
              style="color:#ccc;text-align:center;padding:40px;">
              No lineage records
            </div>
          </el-col>
        </el-row>
      </template>
      <el-empty v-else-if="!detailLoading" description="Not found" />
      <div v-else style="text-align:center;padding:40px;">Loading...</div>
    </el-dialog>
  </div>
</template>
