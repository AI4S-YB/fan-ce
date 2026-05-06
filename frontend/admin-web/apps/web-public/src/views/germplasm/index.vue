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
const showDrawer = ref(false);

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
  selectedItem.value = null;
  showDrawer.value = true;
  try {
    const data: any = await post(`${PRE}/info`, {
      accession_id: item.accession_id,
      taxonomy_tax_id: item.taxonomy_tax_id,
    });
    selectedItem.value = data;
  } catch (e) {
    console.error('Failed to load detail:', e);
  }
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

    <!-- Detail Drawer -->
    <el-drawer v-model="showDrawer" title="Germplasm Detail" size="640px">
      <template v-if="selectedItem">
        <!-- Basic Info -->
        <h4 style="margin-top:0;">Basic Information</h4>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="Accession">{{ selectedItem.accession_id }}</el-descriptions-item>
          <el-descriptions-item label="Name">{{ selectedItem.display_name }}</el-descriptions-item>
          <el-descriptions-item label="English Name">{{ selectedItem.english_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Species">
            <span style="font-style:italic;">{{ selectedItem?.taxonomy?.scientific_name || '-' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="Taxonomy Rank">{{ selectedItem?.taxonomy?.rank || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Import Batch">{{ selectedItem?.audit?.batch_code || '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- Parents -->
        <h4 style="margin-top:20px;">Parents</h4>
        <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;">
          <el-card shadow="hover" size="small" style="flex:1;min-width:200px;">
            <template #header><span style="font-size:13px;font-weight:600;">Father</span></template>
            <div v-if="selectedItem.father_accession">
              <div><strong>{{ selectedItem.father_accession }}</strong></div>
              <div v-if="selectedItem.father_name_snapshot" style="color:#888;font-size:12px;">
                {{ selectedItem.father_name_snapshot }}
              </div>
            </div>
            <span v-else style="color:#ccc;">Unknown</span>
          </el-card>
          <span style="font-size:20px;color:#ccc;">×</span>
          <el-card shadow="hover" size="small" style="flex:1;min-width:200px;">
            <template #header><span style="font-size:13px;font-weight:600;">Mother</span></template>
            <div v-if="selectedItem.mother_accession">
              <div><strong>{{ selectedItem.mother_accession }}</strong></div>
              <div v-if="selectedItem.mother_name_snapshot" style="color:#888;font-size:12px;">
                {{ selectedItem.mother_name_snapshot }}
              </div>
            </div>
            <span v-else style="color:#ccc;">Unknown</span>
          </el-card>
        </div>

        <!-- Lineage Graph -->
        <div v-if="selectedItem?.lineage_summary?.parents?.length">
          <h4 style="margin-top:20px;">Recorded Lineage</h4>
          <el-table :data="selectedItem.lineage_summary.parents" border size="small">
            <el-table-column prop="parent_accession" label="Parent Accession" width="180" />
            <el-table-column prop="parent_role" label="Role" width="120">
              <template #default="{ row }">
                <el-tag size="small" :type="row.parent_role === 'father' ? 'primary' : 'danger'">
                  {{ row.parent_role }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- Children -->
        <div v-if="selectedItem?.lineage_summary?.children?.length">
          <h4 style="margin-top:20px;">Progeny ({{ selectedItem.lineage_summary.child_count }})</h4>
          <el-table :data="selectedItem.lineage_summary.children" border size="small" max-height="300">
            <el-table-column prop="child_accession" label="Child Accession" width="180" />
            <el-table-column prop="parent_role" label="As" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="row.parent_role === 'father' ? 'primary' : 'danger'">
                  {{ row.parent_role }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- Dynamic attributes -->
        <div v-if="selectedItem.attributes && Object.keys(selectedItem.attributes).length > 0" style="margin-top:20px;">
          <h4>Germplasm Attributes</h4>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item v-for="(val, key) in selectedItem.attributes" :key="key" :label="String(key)">
              <pre style="margin:0;white-space:pre-wrap;font-family:inherit;">{{ formatKw(val) }}</pre>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </template>
      <el-empty v-else description="Loading..." />
    </el-drawer>
  </div>
</template>
