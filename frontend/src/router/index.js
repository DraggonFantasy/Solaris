import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/', component: () => import('../views/HomeView.vue'), name: 'home' },
  { path: '/login', component: () => import('../views/LoginView.vue'), name: 'login' },
  { path: '/register', component: () => import('../views/RegisterView.vue'), name: 'register' },
  { path: '/sections', component: () => import('../views/SectionsView.vue'), name: 'sections' },
  { path: '/sections/:slug', component: () => import('../views/SectionDetailView.vue'), name: 'section-detail' },
  { path: '/dialogues/:id', component: () => import('../views/DialogueDetailView.vue'), name: 'dialogue-detail' },
  {
    path: '/profile',
    component: () => import('../views/ProfileView.vue'),
    name: 'profile',
    meta: { requiresAuth: true }
  },
  {
    path: '/dialogues/create',
    component: () => import('../views/CreateDialogueView.vue'),
    name: 'create-dialogue',
    meta: { requiresAuth: true }
  },
  {
    path: '/dialogues/submitted',
    component: () => import('../views/DialogueSubmittedView.vue'),
    name: 'dialogue-submitted',
    meta: { requiresAuth: true }
  },
  {
    path: '/my-dialogues',
    component: () => import('../views/MyDialoguesView.vue'),
    name: 'my-dialogues',
    meta: { requiresAuth: true }
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router
