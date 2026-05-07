import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'lucide:flask-conical',
      order: 800,
      title: '数据分析',
    },
    name: 'AnalysisParent',
    path: '/analysis',
    redirect: '/analysis/tools',
    children: [
      {
        name: 'AnalysisTools',
        path: '/analysis/tools',
        component: () => import('#/views/apps/analysis/index.vue'),
        meta: {
          icon: 'lucide:package',
          title: '工具插件',
        },
      },
      {
        name: 'AnalysisJobs',
        path: '/analysis/jobs',
        component: () => import('#/views/apps/analysis/jobs.vue'),
        meta: {
          icon: 'lucide:list-checks',
          title: '任务管理',
        },
      },
    ],
  },
];

export default routes;
