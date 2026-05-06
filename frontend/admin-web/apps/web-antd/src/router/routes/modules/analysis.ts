import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'lucide:flask-conical',
      order: 800,
      title: 'Analysis Tools',
    },
    name: 'AnalysisTools',
    path: '/analysis',
    component: () => import('#/views/apps/analysis/index.vue'),
  },
];

export default routes;
