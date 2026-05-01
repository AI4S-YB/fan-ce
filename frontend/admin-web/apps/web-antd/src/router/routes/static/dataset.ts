import type { RouteRecordRaw } from 'vue-router';

const BasicLayout = () => import('#/layouts/basic.vue');

const routes: RouteRecordRaw[] = [
  {
    name: 'DatasetStaticPages',
    path: '/dataset',
    redirect: '/apps/dataset',
    meta: {
      hideInMenu: true,
      title: 'page.datasetCenter',
    },
    component: BasicLayout,
    children: [
      {
        name: 'DatasetDetail',
        path: ':id',
        component: () => import('#/views/apps/dataset/Detail.vue'),
        meta: {
          hideInMenu: true,
          title: 'page.datasetDetail',
        },
      },
      {
        name: 'DatasetQuery',
        path: ':id/query',
        component: () => import('#/views/apps/dataset/Query.vue'),
        meta: {
          hideInMenu: true,
          title: 'page.dataQuery',
        },
      },
    ],
  },
];

export default routes;
