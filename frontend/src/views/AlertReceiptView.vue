<template>
  <section class="page" data-module="price_alert_recon">
    <header class="page-head">
      <div>
        <h2>变价告警规则 · 补算判定跟进</h2>
        <p class="page-desc">
          从告警缺口清单读取实际变价事件，按规则版本核对补算结论与处理回执；
          每次补算消费的价格来源、差值与判定理由均可追溯。
        </p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/alert_gap">返回告警缺项单</RouterLink>
        <RouterLink class="btn" to="/change_history_recon">查看变价流水</RouterLink>
      </div>
    </header>

    <div v-if="ruleMeta" class="result-panel">
      <h4>所查规则 {{ ruleMeta.rule_code }} 版本历史</h4>
      <p class="page-desc">
        当前生效：<strong>{{ ruleMeta.current_version }}（{{ ruleMeta.current_threshold }}）</strong>
      </p>
      <table class="data-table">
        <thead>
          <tr><th>规则版本</th><th>价差阈值</th><th>变更说明</th><th>生效时间</th></tr>
        </thead>
        <tbody>
          <tr v-for="version in ruleMeta.version_history" :key="version.version">
            <td>
              <span class="badge" :class="version.version === ruleMeta.current_version ? 'blue' : 'gray'">
                {{ version.version }}
              </span>
            </td>
            <td>{{ version.threshold }}</td>
            <td>{{ version.change_note }}</td>
            <td>{{ version.effective_at }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="filter-bar">
      <label class="filter-item">
        <span>按规则版本过滤回执</span>
        <select v-model="versionFilter" data-testid="receipt-version-filter" @change="loadReceipts">
          <option value="">全部版本</option>
          <option v-for="version in versionOptions" :key="version" :value="version">{{ version }}</option>
        </select>
      </label>
      <button class="btn" data-testid="refresh-receipts" type="button" @click="loadReceipts">刷新回执</button>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <div v-for="receipt in receipts" :key="receipt.receipt_no" class="receipt-card" :data-testid="`receipt-card-${receipt.goods_id}`">
      <div class="receipt-head">
        <div>
          <strong>{{ receipt.receipt_no }}</strong>
          <span class="badge gray" style="margin-left: 8px">{{ receipt.gap_no }}</span>
          <span class="badge gray" style="margin-left: 4px">{{ receipt.goods_id }} · {{ receipt.event_code }}</span>
        </div>
        <span class="badge" :class="receipt.triggered ? 'red' : 'green'" data-testid="trigger-badge">
          {{ receipt.triggered ? '应发告警' : '不发告警' }}
        </span>
      </div>
      <dl>
        <dt>规则版本</dt><dd>{{ receipt.rule_code }} {{ receipt.rule_version }}（阈值 {{ receipt.rule_threshold }}）</dd>
        <dt>价格版本</dt><dd>{{ receipt.price_version }}（{{ receipt.price_source }}）</dd>
        <dt>消费价格</dt><dd>{{ receipt.old_price }} → {{ receipt.new_price }}</dd>
        <dt>差值 / 幅度</dt><dd>{{ receipt.diff_amount }} / {{ formatRatio(receipt.diff_ratio) }}</dd>
        <dt>判定理由</dt><dd colspan="3">{{ receipt.decision }}</dd>
        <dt>通知渠道</dt><dd>{{ receipt.channel || '—' }}</dd>
        <dt>计算时间</dt><dd>{{ receipt.created_at }}</dd>
        <dt>幂等键</dt><dd class="src">{{ receipt.idempotent_key }}</dd>
      </dl>
      <div v-if="receipt.conflict_at_run" class="badge amber" style="margin-top: 6px">
        计算时检测到证据冲突：建单证据（{{ receipt.evidence_at_gap?.new_price }}）
        与当前价格（{{ receipt.current_evidence?.new_price }}）不一致，已按当前价格版本补算
      </div>
      <div v-if="receipt.evidence_at_gap" style="margin-top: 6px; font-size: 12px" class="src">
        建单旧证据：{{ receipt.evidence_at_gap.old_price }} → {{ receipt.evidence_at_gap.new_price }}
        （{{ receipt.evidence_at_gap.source }}）；
        补算实际消费：{{ receipt.current_evidence?.old_price }} → {{ receipt.current_evidence?.new_price }}
        （{{ receipt.current_evidence?.source }} / {{ receipt.current_evidence?.price_version }}）
      </div>
    </div>

    <div v-if="!receipts.length" class="result-panel empty-state">该版本下暂无补算回执</div>

    <footer class="page-foot">
      <span>共 {{ receipts.length }} 张补算回执，历史回执按当时规则版本永久可查</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchReceipts, fetchRuleVersions } from '@/api/reconciliation'
import type { AlertReceipt, RuleVersion } from '@/domain/reconciliation'

const receipts = ref<AlertReceipt[]>([])
const versionFilter = ref('')
const errorMessage = ref('')
const ruleMeta = ref<{
  rule_code: string
  current_version: string
  current_threshold: string
  version_history: RuleVersion[]
} | null>(null)

const versionOptions = computed(() =>
  Array.from(new Set(receipts.value.map((receipt) => receipt.rule_version))).sort(),
)

function formatRatio(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

async function loadReceipts() {
  errorMessage.value = ''
  try {
    const result = await fetchReceipts(versionFilter.value || undefined)
    receipts.value = result.items
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '补算回执读取失败'
  }
}

onMounted(async () => {
  await loadReceipts()
  try {
    ruleMeta.value = await fetchRuleVersions('AR-10')
  } catch {
    ruleMeta.value = null
  }
})
</script>
