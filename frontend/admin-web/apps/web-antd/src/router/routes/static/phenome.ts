import type { RouteRecordRaw } from 'vue-router';

const BasicLayout = () => import('#/layouts/basic.vue');

const routes: RouteRecordRaw[] = [
  {
    name: 'PhenomeStaticPages',
    path: '/apps/phenome',
    meta: {
      hideInMenu: true,
      hideInBreadcrumb: true,
      title: 'page.phenome',
    },
    component: BasicLayout,
    children: [
      {
        name: 'PhenomeQueryPage',
        path: '/apps/phenome/query',
        component: () => import('#/views/apps/phenome/query.vue'),
        meta: {
          hideInMenu: true,
          title: 'page.phenomeQuery',
        },
      },
    ],
  },
];

export default routes;
