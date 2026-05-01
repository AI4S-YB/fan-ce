import type { RouteRecordRaw } from 'vue-router';

const BasicLayout = () => import('#/layouts/basic.vue');

const routes: RouteRecordRaw[] = [
  {
    name: 'BreedingStaticPages',
    path: '/breeding',
    meta: {
      hideInMenu: true,
      hideInBreadcrumb: true,
      title: 'page.breeding',
    },
    component: BasicLayout,
    children: [
      {
        name: 'BreedingProgramDetail',
        path: '/breeding/program/detail/:id',
        component: () => import('#/views/breeding/program/detail.vue'),
        meta: {
          hideInMenu: true,
          title: 'page.breedingDetail',
        },
      },
    ],
  },
];

export default routes;
