<script setup lang="ts">
import { ref, computed, watch } from 'vue';

const props = defineProps<{
  samples: string[];
  loading?: boolean;
}>();

const emit = defineEmits<{
  update: [selected: string[]];
}>();

const expanded = ref(false);
const selected = ref<string[]>([]);
const searchText = ref('');

const filteredSamples = computed(() => {
  const q = searchText.value.toLowerCase();
  if (!q) return props.samples;
  return props.samples.filter(s => s.toLowerCase().includes(q));
});

watch(selected, (v) => emit('update', v), { deep: true });

function selectAll() { selected.value = [...props.samples]; }
function clearAll() { selected.value = []; }
</script>

<template>
  <div>
    <el-button text size="small" @click="expanded = !expanded">
      {{ expanded ? '▲' : '▼' }} Samples ({{ samples.length }})
    </el-button>
    <div v-if="expanded" style="margin-top:8px;padding:12px;background:#fafafa;border-radius:6px;">
      <el-input v-model="searchText" placeholder="Filter samples..." size="small" style="margin-bottom:8px;" clearable />
      <div style="margin-bottom:4px;display:flex;gap:8px;align-items:center;">
        <el-button text size="small" @click="selectAll">Select All</el-button>
        <el-button text size="small" @click="clearAll">Clear</el-button>
        <span style="color:#888;font-size:12px;">{{ selected.length }} selected</span>
      </div>
      <el-select v-model="selected" multiple style="width:100%;" collapse-tags collapse-tags-tooltip>
        <el-option v-for="s in filteredSamples" :key="s" :label="s" :value="s" />
      </el-select>
    </div>
  </div>
</template>
