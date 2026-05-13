<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  materials: any[];
  trials: any[];
  plots: any[];
  observations: any[];
  biosamples: any[];
  assays: any[];
  dataFiles: any[];
}>();

const emit = defineEmits<{ (e: 'navigate', tab: string): void }>();

interface Stage {
  key: string;
  label: string;
  tab: string;
  count: number;
  items: any[];
  issues: string[];
}

const stages = computed<Stage[]>(() => [
  {
    key: 'materials',
    label: 'Germplasm',
    tab: 'materials',
    count: props.materials.length,
    items: props.materials,
    issues: props.materials.length === 0 ? ['No materials registered'] : [],
  },
  {
    key: 'trials',
    label: 'Trials',
    tab: 'trials',
    count: props.trials.length,
    items: props.trials,
    issues: props.trials.length === 0 ? ['No trials created'] : [],
  },
  {
    key: 'plots',
    label: 'Plots',
    tab: 'plots',
    count: props.plots.length,
    items: props.plots,
    issues: props.plots.length === 0 ? ['No plots assigned'] : [],
  },
  {
    key: 'observations',
    label: 'Observations',
    tab: 'observations',
    count: props.observations.length,
    items: props.observations,
    issues: [
      ...(props.observations.length === 0 ? ['No observations recorded'] : []),
      ...(props.plots.length > 0 && props.observations.length === 0 ? ['Plots have no observations'] : []),
    ],
  },
  {
    key: 'biosamples',
    label: 'Biosamples',
    tab: 'biosamples',
    count: props.biosamples.length,
    items: props.biosamples,
    issues: props.biosamples.length === 0 ? ['No biosamples collected'] : [],
  },
  {
    key: 'assays',
    label: 'Assays & Files',
    tab: 'omics',
    count: props.assays.length,
    items: props.assays,
    issues: [
      ...(props.assays.length === 0 ? ['No assays performed'] : []),
      ...(props.biosamples.length > 0 && props.assays.length === 0 ? ['Biosamples have no assays'] : []),
      ...(props.dataFiles.length === 0 && props.assays.length > 0 ? ['Assays have no data files'] : []),
    ],
  },
]);

const allIssues = computed(() => stages.value.flatMap((s) => s.issues));
</script>

<template>
  <div style="padding: 16px">
    <!-- Data Integrity Panel -->
    <div
      v-if="allIssues.length > 0"
      style="
        margin-bottom: 20px;
        padding: 12px 16px;
        background: #fff7e6;
        border: 1px solid #ffd591;
        border-radius: 6px;
      "
    >
      <h4 style="margin: 0 0 8px; color: #d46b08">
        Data Integrity Issues ({{ allIssues.length }})
      </h4>
      <div
        v-for="(issue, i) in allIssues"
        :key="i"
        style="font-size: 13px; color: #ad6800; margin-bottom: 2px"
      >
        {{ issue }}
      </div>
    </div>
    <div
      v-else
      style="
        margin-bottom: 20px;
        padding: 12px 16px;
        background: #f6ffed;
        border: 1px solid #b7eb8f;
        border-radius: 6px;
        color: #389e0d;
        font-size: 13px;
      "
    >
      All data integrity checks passed
    </div>

    <!-- Timeline -->
    <div
      style="
        display: flex;
        align-items: flex-start;
        gap: 0;
        overflow-x: auto;
        padding-bottom: 16px;
      "
    >
      <template v-for="(stage, i) in stages" :key="stage.key">
        <div
          class="timeline-stage"
          @click="emit('navigate', stage.tab)"
        >
          <div style="font-size: 28px; margin-bottom: 4px">
            {{ stage.count || '—' }}
          </div>
          <div style="font-size: 13px; font-weight: 600; color: #303133">
            {{ stage.label }}
          </div>
          <div
            v-if="stage.issues.length > 0"
            style="margin-top: 6px; font-size: 11px; color: #ff4d4f"
          >
            {{ stage.issues.length }} issue{{ stage.issues.length > 1 ? 's' : '' }}
          </div>
        </div>
        <div
          v-if="i < stages.length - 1"
          style="
            display: flex;
            align-items: center;
            padding: 0 4px;
            color: #ccc;
            font-size: 20px;
          "
        >
          &rarr;
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.timeline-stage {
  cursor: pointer;
  min-width: 140px;
  flex: 1;
  text-align: center;
  padding: 16px 12px;
  border-radius: 8px;
  border: 2px solid #e8e8e8;
  transition: all 0.2s;
  background: #fff;
}

.timeline-stage:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}
</style>
