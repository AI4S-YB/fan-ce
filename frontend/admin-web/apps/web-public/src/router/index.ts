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
  // Standalone tools (no genome selected)
  { path: '/tools/:tool', component: () => import('@/views/genome/Tools.vue') },
  { path: '/community/:type', component: () => import('@/views/community/List.vue') },
  { path: '/expression', component: () => import('@/views/expression/index.vue') },
  { path: '/genotype', component: () => import('@/views/genotype/index.vue') },
  { path: '/germplasm', component: () => import('@/views/germplasm/index.vue') },
  { path: '/chat', component: () => import('@/views/chat/index.vue') },
  { path: '/analysis', component: () => import('@/views/analysis/index.vue') },
  { path: '/analysis/:toolId', component: () => import('@/views/analysis/index.vue') },
  { path: '/phenotype', component: () => import('@/views/phenotype/index.vue') },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
