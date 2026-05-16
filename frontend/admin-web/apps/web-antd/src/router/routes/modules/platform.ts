import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'lucide:settings',
      order: 1000,
      title: 'page.platform',
    },
    name: 'Platform',
    path: '/platform',
    redirect: '/platform/setup/taxonomy',
    children: [
      {
        name: 'PlatformTaxonomySetup',
        path: '/platform/setup/taxonomy',
        component: () => import('#/views/platform/setup-taxonomy.vue'),
        meta: {
          icon: 'lucide:database-backup',
          title: 'page.taxonomyInit',
        },
      },
      {
        name: 'PlatformSettingManagement',
        path: '/platform/setting',
        component: () => import('#/views/platform/setting.vue'),
        meta: {
          icon: 'lucide:sliders-horizontal',
          title: 'page.platformSetting',
        },
      },
      {
        name: 'PlatformApiManagement',
        path: '/platform/api',
        component: () => import('#/views/platform/api/index.vue'),
        meta: {
          icon: 'lucide:blocks',
          title: 'page.apiManagement',
        },
      },
      {
        name: 'NewsManagement',
        path: '/platform/news',
        component: () => import('#/views/platform/news/index.vue'),
        meta: {
          icon: 'lucide:message-square',
          title: 'page.newsManagement',
          auth: 'platform:news:list',
        },
      },
      {
        name: 'PlatformSites',
        path: '/platform/sites',
        component: () => import('#/views/platform/sites.vue'),
        meta: {
          icon: 'lucide:globe',
          title: '站点管理',
        },
      },
      {
        name: 'PlatformSiteDatasets',
        path: '/platform/sites/:siteCode/datasets',
        component: () => import('#/views/platform/site-datasets.vue'),
        meta: {
          title: '数据集分配',
        },
      },
    ],
  },
];

export default routes;
