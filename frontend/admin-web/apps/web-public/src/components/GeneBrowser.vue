<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { createViewState, JBrowseLinearGenomeView } from '@jbrowse/react-linear-genome-view';
import { createElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';

const props = defineProps<{
  seqName: string;
  seq: string;
  start: number;
  stop: number;
  exons: any[];
  geneId: string;
}>();

const container = ref<HTMLElement>();
let root: Root | null = null;
let mounted = false;

function buildFeatures(): any[] {
  const ref = props.seqName || 'ref';
  const strand = props.exons[0]?.strand === '-' ? -1 : 1;
  const pad = 150;
  const seqStart = props.start - pad;

  const geneId = `${props.geneId}-gene`;
  const subfeatures: any[] = [];

  props.exons
    .filter((e: any) => e.feature_type === 'exon' || e.feature_type === 'CDS')
    .forEach((e: any, i: number) => {
      subfeatures.push({
        refName: ref,
        uniqueId: `${props.geneId}-${e.feature_type}-${i}`,
        start: e.start - seqStart,
        end: e.stop - seqStart,
        type: e.feature_type,
      });
    });

  return [{
    refName: ref,
    uniqueId: geneId,
    start: props.start - seqStart,
    end: props.stop - seqStart,
    type: 'gene',
    name: props.geneId,
    strand,
    subfeatures,
  }];
}

onMounted(() => {
  if (!container.value || !props.seq || !props.exons.length || mounted) return;
  mounted = true;

  const ref = props.seqName || 'ref';
  const seqLen = props.seq.length;
  const features = buildFeatures();

  const config = {
    assembly: {
      name: props.geneId,
      sequence: {
        type: 'ReferenceSequenceTrack',
        trackId: `${props.geneId}-ref`,
        adapter: {
          type: 'FromConfigSequenceAdapter',
          features: [{
            refName: ref,
            uniqueId: ref,
            start: 0,
            end: seqLen,
            seq: props.seq,
          }],
        },
      },
    },
    tracks: [{
      type: 'FeatureTrack',
      trackId: `${props.geneId}-features`,
      name: 'Gene Features',
      rendererType: 'SvgFeatureRenderer',
      assemblyNames: [props.geneId],
      adapter: {
        type: 'FromConfigAdapter',
        features,
      },
    }],
    defaultSession: {
      name: props.geneId,
      view: {
        id: 'linearGenomeView',
        type: 'LinearGenomeView',
        tracks: [
          { type: 'ReferenceSequenceTrack', configuration: `${props.geneId}-ref`, displays: [{ type: 'LinearReferenceSequenceDisplay', configuration: `${props.geneId}-ref-LinearReferenceSequenceDisplay` }] },
          { type: 'FeatureTrack', configuration: `${props.geneId}-features`, displays: [{ type: 'LinearBasicDisplay', configuration: `${props.geneId}-features-LinearBasicDisplay` }] },
        ],
        displayedRegions: [{
          assemblyName: props.geneId,
          refName: ref,
          start: 0,
          end: seqLen,
        }],
      },
    },
  };

  try {
    const state = createViewState(config);
    root = createRoot(container.value);
    root.render(createElement(JBrowseLinearGenomeView, { viewState: state }));
  } catch (e) {
    console.warn('JBrowse render failed:', e);
    container.value.innerHTML = '<div style="padding:20px;color:#999;text-align:center;">Genome browser unavailable — please check browser console for details.</div>';
  }
});

onUnmounted(() => {
  if (root) { root.unmount(); root = null; }
});
</script>

<template>
  <div ref="container" style="min-height:200px;width:100%;" />
</template>
