import type { RouteRecordRaw } from 'vue-router';

const BasicLayout = () => import('#/layouts/basic.vue');

const routes: RouteRecordRaw[] = [
  {
    name: 'GermplasmStaticPages',
    path: '/germplasm',
    meta: {
      hideInMenu: true,
      hideInBreadcrumb: true,
      title: 'page.germplasm',
    },
    component: BasicLayout,
    children: [
      {
        name: 'GermplasmInfoPage',
        path: '/germplasm/info',
        component: () => import('#/views/app/germplasm/info.vue'),
        meta: {
          hideInMenu: true,
          title: 'page.germplasmDetail',
        },
      },
    ],
  },
];

export default routes;
