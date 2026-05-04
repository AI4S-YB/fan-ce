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
  {
    path: '/genome/:id',
    component: () => import('@/views/genome/Overview.vue'),
    children: [
      { path: '', redirect: (to: any) => ({ path: 'home', query: to.query }) },
      { path: 'home', component: () => import('@/views/genome/Home.vue') },
      { path: 'search', component: () => import('@/views/genome/Search.vue') },
      { path: 'batch', component: () => import('@/views/genome/BatchQuery.vue') },
      { path: 'blast', component: () => import('@/views/genome/Blast.vue') },
      { path: 'download', component: () => import('@/views/genome/Download.vue') },
      { path: 'geneinfo', component: () => import('@/views/genome/GeneInfo.vue') },
    ],
  },
  { path: '/expression', component: () => import('@/views/expression/index.vue') },
  { path: '/genotype', component: () => import('@/views/genotype/index.vue') },
  { path: '/germplasm', component: () => import('@/views/germplasm/index.vue') },
  { path: '/phenotype', component: () => import('@/views/phenotype/index.vue') },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
