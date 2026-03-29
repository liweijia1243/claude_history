import { createRouter, createWebHistory } from 'vue-router'

import Dashboard from './views/Dashboard.vue'
import HistoryView from './views/HistoryView.vue'
import PlansView from './views/PlansView.vue'
import ProjectsView from './views/ProjectsView.vue'
import ProjectDetailView from './views/ProjectDetailView.vue'
import ConversationView from './views/ConversationView.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/history', component: HistoryView },
  { path: '/plans', component: PlansView },
  { path: '/projects', component: ProjectsView },
  { path: '/projects/:projectId', component: ProjectDetailView, props: true },
  { path: '/projects/:projectId/sessions/:sessionId', component: ConversationView, props: true },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
