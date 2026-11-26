import { createRouter, createWebHistory } from 'vue-router'

import Overview from '@/views/Overview.vue'
import WorkbenchView from '@/views/WorkbenchView.vue'
import AlertGapView from '@/views/AlertGapView.vue'
import ChangeHistoryReconView from '@/views/ChangeHistoryReconView.vue'
import AlertReceiptView from '@/views/AlertReceiptView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'overview', component: Overview },
    // 告警核对专属页面：固定路径需排在 /:moduleKey 动态路由之前。
    { path: '/alert_gap', name: 'alert-gap', component: AlertGapView },
    { path: '/change_history_recon', name: 'change-history-recon', component: ChangeHistoryReconView },
    { path: '/alert_receipts', name: 'alert-receipts', component: AlertReceiptView },
    { path: '/:moduleKey', name: 'module', component: WorkbenchView, props: true },
  ],
})

export default router
