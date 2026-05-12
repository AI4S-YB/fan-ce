import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/home/index.vue'),
  },
  {
    path: '/dataset/:id',
    name: 'dataset-detail',
    component: () => import('@/views/dataset/Detail.vue'),
  },
  { path: '/genomes', component: () => import('@/views/genome/GenomeList.vue') },
  {
    path: '/genome/:id',
    component: () => import('@/views/genome/Overview.vue'),
    children: [
      { path: '', redirect: (to: any) => `/genome/${to.params.id}/home` },
      { path: 'home', component: () => import('@/views/genome/Home.vue') },
      { path: 'search', component: () => import('@/views/genome/GeneSearch.vue') },
      { path: 'tf', component: () => import('@/views/genome/TranscriptionFactors.vue') },
      { path: 'tools/:tool', component: () => import('@/views/genome/Tools.vue') },
      { path: 'geneinfo', component: () => import('@/views/genome/GeneInfo.vue') },
    ],
  },
  // Sequence analysis tool pages (pre-filled from gene context)
  { path: '/tools/blast', component: () => import('@/views/tools/ToolRunner.vue'), name: 'tool-blast' },
  { path: '/tools/primer', component: () => import('@/views/tools/ToolRunner.vue'), name: 'tool-primer' },
  { path: '/tools/grna', component: () => import('@/views/tools/ToolRunner.vue'), name: 'tool-grna' },
  { path: '/tools/msa', component: () => import('@/views/tools/ToolRunner.vue'), name: 'tool-msa' },
  { path: '/tools/motif', component: () => import('@/views/tools/ToolRunner.vue'), name: 'tool-motif' },
  // Analysis tools — each tool has its own route
  { path: '/analysis/blast', component: () => import('@/views/tools/ToolRunner.vue'), name: 'analysis-blast' },
  { path: '/analysis/primer', component: () => import('@/views/tools/ToolRunner.vue'), name: 'analysis-primer' },
  { path: '/analysis/grna', component: () => import('@/views/tools/ToolRunner.vue'), name: 'analysis-grna' },
  { path: '/analysis/msa', component: () => import('@/views/tools/ToolRunner.vue'), name: 'analysis-msa' },
  { path: '/analysis/motif', component: () => import('@/views/tools/ToolRunner.vue'), name: 'analysis-motif' },
  { path: '/analysis/go_enrich', component: () => import('@/views/tools/ToolRunner.vue'), name: 'analysis-go' },
  { path: '/analysis/kegg_enrich', component: () => import('@/views/tools/ToolRunner.vue'), name: 'analysis-kegg' },
  // Catch-all for future plugins
  { path: '/analysis/:toolId', component: () => import('@/views/tools/ToolRunner.vue') },
  // Standalone tools (no genome selected)
  { path: '/tools/:tool', component: () => import('@/views/genome/Tools.vue') },
  { path: '/community/:type', component: () => import('@/views/community/List.vue') },
  { path: '/expression', component: () => import('@/views/expression/index.vue') },
  { path: '/genotype', component: () => import('@/views/genotype/index.vue') },
  { path: '/germplasm', component: () => import('@/views/germplasm/index.vue') },
  { path: '/chat', component: () => import('@/views/chat/index.vue') },
  { path: '/analysis', component: () => import('@/views/analysis/index.vue') },
  { path: '/phenotype', component: () => import('@/views/phenotype/index.vue') },
  {
    path: '/:pathMatch(.*)*',
    component: { template: '<div style="text-align:center;padding:80px 20px;"><h2 style="color:#999;">404</h2><p style="color:#bbb;">Page not found</p><router-link to="/" style="color:#409eff;">Back to Home</router-link></div>' },
  },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
