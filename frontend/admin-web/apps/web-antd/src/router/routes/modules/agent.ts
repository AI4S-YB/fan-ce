import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    name: 'Agent',
    path: '/agent',
    meta: {
      icon: 'lucide:bot',
      order: 520,
      title: 'page.agent',
    },
    children: [
      {
        name: 'AgentChat',
        path: '/agent/chat',
        component: () => import('#/views/agent/chat/index.vue'),
        meta: {
          title: 'AI Chat',
          requiresAuth: true,
        },
      },
    ],
  },
]

export default routes
