<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createViewState, JBrowseLinearGenomeView } from '@jbrowse/react-linear-genome-view';
import { createRoot, type Root } from 'react-dom/client';
import { createElement } from 'react';

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
let blobUrls: string[] = [];

function buildGff3(): string {
  const lines = ['##gff-version 3'];
  const ref = props.seqName || 'ref';
  const strand = props.exons[0]?.strand || '+';

  props.exons
    .filter((e: any) => e.feature_type === 'exon' || e.feature_type === 'CDS')
    .forEach((e: any, i: number) => {
      const ftype = e.feature_type === 'CDS' ? 'CDS' : 'exon';
      const s = e.start as number;
      const epos = e.stop as number;
      lines.push(`${ref}\t.\t${ftype}\t${s}\t${epos}\t.\t${strand}\t.\tID=${ftype}-${i}`);
    });

  lines.push(`${ref}\t.\tgene\t${props.start}\t${props.stop}\t.\t${strand}\t.\tID=${props.geneId}`);
  return lines.join('\n');
}

// Parse GFF3 into JBrowse's inline feature format
function parseGff3Inline(gff3: string): any[] {
  return gff3
    .split('\n')
    .filter(l => l && !l.startsWith('#'))
    .map((line, i) => {
      const parts = line.split('\t');
      if (parts.length < 9) return null;
      const attrs: Record<string, string> = {};
      parts[8].split(';').forEach(p => {
        const [k, v] = p.split('=');
        if (k && v) attrs[k] = v;
      });
      return {
        refName: parts[0],
        start: parseInt(parts[3]),
        end: parseInt(parts[4]),
        type: parts[2],
        name: attrs['ID'] || `feature-${i}`,
        strand: parts[6] === '-' ? -1 : 1,
      };
    })
    .filter(Boolean);
}

function createBlobUrl(content: string): string {
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  blobUrls.push(url);
  return url;
}

function revokeBlobUrls() {
  blobUrls.forEach(url => URL.revokeObjectURL(url));
  blobUrls = [];
}

function buildConfig() {
  // Clean up any existing blob URLs
  revokeBlobUrls();

  const gff3 = buildGff3();
  const seqLen = props.seq.length;
  const ref = props.seqName || 'ref';
  const fastaContent = `>${ref}\n${props.seq}\n`;

  // Create FASTA blob URL
  const fastaUrl = createBlobUrl(fastaContent);

  // Create .fai index: seqName\tlength\toffset\tlineBases\tlineWidth
  // For a single-line FASTA: header is ">ref\n" (length ref.length+2), then sequence on one line
  const headerLen = ref.length + 2; // ">ref\n"
  const faiContent = `${ref}\t${seqLen}\t${headerLen}\t${seqLen}\t${seqLen + 1}\n`;
  const faiUrl = createBlobUrl(faiContent);

  return {
    assembly: {
      name: props.geneId,
      sequence: {
        type: 'ReferenceSequenceTrack',
        trackId: `${props.geneId}-ref`,
        adapter: {
          type: 'IndexedFastaAdapter',
          fastaLocation: { uri: fastaUrl },
          faiLocation: { uri: faiUrl },
        },
      },
    },
    tracks: [
      {
        type: 'FeatureTrack',
        trackId: `${props.geneId}-features`,
        name: 'Gene Features',
        assemblyNames: [props.geneId],
        adapter: {
          type: 'FromConfigAdapter',
          features: parseGff3Inline(gff3),
        },
      },
    ],
    defaultSession: {
      name: props.geneId,
      view: {
        id: 'linearGenomeView',
        type: 'LinearGenomeView',
        displayedRegions: [
          {
            assemblyName: props.geneId,
            refName: ref,
            start: 0,
            end: seqLen,
          },
        ],
      },
    },
  };
}

function render() {
  if (!container.value || !props.seq) return;

  // Clean up previous React root
  if (root) {
    root.unmount();
    root = null;
  }

  try {
    const config = buildConfig();
    const state = createViewState(config);
    const reactEl = createElement(JBrowseLinearGenomeView, { viewState: state });
    root = createRoot(container.value);
    root.render(reactEl);
  } catch (e) {
    console.warn('JBrowse render failed:', e);
  }
}

onMounted(() => {
  if (props.seq) render();
});

onUnmounted(() => {
  if (root) {
    root.unmount();
    root = null;
  }
  revokeBlobUrls();
});

watch(
  () => [props.seq, props.exons],
  () => {
    if (props.seq) render();
  },
  { deep: true },
);
</script>

<template>
  <div ref="container" style="min-height:200px;width:100%;" />
</template>
