<template>
  <section class="page" data-module="alert_gap">
    <header class="page-head">
      <div>
        <h2>告警缺项单</h2>
        <p class="page-desc">
          按已确认变价与告警规则版本核对出的缺口，区分「规则升级」与「同一变价更正」，
          勾选后仅对选中商品与变价事件发起补算。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn" data-testid="refresh-gaps" type="button" @click="loadGaps">刷新缺口</button>
      </div>
    </header>

    <div class="stat-row">
      <article class="stat-card">
        <span class="stat-label">缺口总数</span>
        <strong class="stat-value">{{ summary.total }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">待处理</span>
        <strong class="stat-value">{{ summary.pending }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">已处理</span>
        <strong class="stat-value">{{ summary.processed }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">证据冲突</span>
        <strong class="stat-value" data-testid="conflict-count">{{ summary.conflict }}</strong>
      </article>
    </div>

    <div class="filter-bar">
      <div class="seg-bar" role="group" aria-label="缺口状态过滤">
        <button
          v-for="option in statusOptions"
          :key="option.value"
          type="button"
          :class="{ active: statusFilter === option.value }"
          :data-testid="`gap-filter-${option.value || 'all'}`"
          @click="changeFilter(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
      <div style="flex: 1"></div>
      <label class="filter-item">
        <span>已勾选 {{ selectedIds.length }} 条（仅这些商品/事件会被补算）</span>
      </label>
      <button
        class="btn primary"
        data-testid="submit-recalc"
        type="button"
        :disabled="!selectedIds.length || submitting"
        @click="submit"
      >
        {{ submitting ? '补算中…' : '对勾选缺口补算' }}
      </button>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <table class="data-table recon-table">
      <thead>
        <tr>
          <th style="width: 42px">勾选</th>
          <th>缺口编号</th>
          <th>缺口类型</th>
          <th>商品 / 变价事件</th>
          <th>建单实际证据（旧价 → 新价 / 来源）</th>
          <th>规则版本</th>
          <th>价格版本</th>
          <th>状态</th>
          <th>回执</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="gap in gaps"
          :key="gap.id"
          :data-testid="`gap-row-${gap.id}`"
          :data-status="gap.status"
          :data-conflict="String(gap.conflict)"
        >
          <td>
            <input
              v-if="gap.status === '待处理'"
              v-model="selectedIds"
              type="checkbox"
              :value="gap.id"
              :data-testid="`gap-check-${gap.goods_id}`"
            />
            <span v-else class="badge gray">已办结</span>
          </td>
          <td>{{ gap.gap_no }}</td>
          <td>
            <span class="badge" :class="gap.gap_type === '规则升级' ? 'blue' : 'amber'">
              {{ gap.gap_type }}
            </span>
          </td>
          <td>
            <div>{{ gap.goods_id }}</div>
            <div class="src">{{ gap.event_code }}</div>
          </td>
          <td>
            <div class="evidence-cell">
              <span :class="{ strike: gap.conflict }">
                {{ gap.evidence.old_price }} → {{ gap.evidence.new_price }}
              </span>
              <span class="src">{{ gap.evidence.source }}</span>
              <span class="src">{{ gap.evidence.note }}</span>
              <span v-if="gap.conflict" class="badge red" data-testid="conflict-badge">
                证据冲突：变价已被更正，请刷新流水核对
              </span>
            </div>
          </td>
          <td>
            <span class="badge gray">{{ gap.rule_code }} {{ gap.rule_version_at_gap }}</span>
          </td>
          <td>
            <span class="badge" :class="gap.conflict ? 'red' : 'gray'">
              {{ gap.price_version_at_gap }}
            </span>
          </td>
          <td>
            <span class="badge" :class="gap.status === '已处理' ? 'green' : 'amber'">
              {{ gap.status }}
            </span>
          </td>
          <td>
            <RouterLink v-if="gap.receipt_no" :to="`/alert_receipts`" class="link" :data-testid="`receipt-link-${gap.id}`">
              {{ gap.receipt_no }}
            </RouterLink>
            <span v-else class="src">—</span>
          </td>
        </tr>
        <tr v-if="!gaps.length">
          <td colspan="9" class="empty-state">当前过滤条件下没有告警缺口</td>
        </tr>
      </tbody>
    </table>

    <div v-if="lastResult" class="result-panel" data-testid="recalc-result">
      <h4>本次补算结果（{{ lastResult.message }}）</h4>
      <ul v-if="lastResult.processed.length">
        <li v-for="item in lastResult.processed" :key="item.gap_id">
          新确认：{{ item.gap_no }}（{{ item.goods_id }}）→ 回执 {{ item.receipt_no }}，
          <span :class="item.triggered ? '' : 'src'">
            {{ item.triggered ? '应发告警' : '不发告警' }}
          </span>
          <span v-if="item.conflict" class="badge red">按更正后价格计算</span>
        </li>
      </ul>
      <ul v-if="lastResult.reused.length">
        <li v-for="item in lastResult.reused" :key="item.gap_id">
          幂等沿用：{{ item.gap_no }} 已按相同版本确认，沿用回执 {{ item.receipt_no }}，未重复计算
        </li>
      </ul>
      <ul v-if="lastResult.untouched.length">
        <li v-for="item in lastResult.untouched" :key="item.gap_id" :data-testid="`untouched-${item.goods_id}`">
          未勾选未代算：{{ item.gap_no }}（{{ item.goods_id }}）保持待处理
        </li>
      </ul>
      <div class="page-actions">
        <button class="btn" type="button" @click="goReceipts">前往告警页面查看判定回执</button>
      </div>
    </div>

    <footer class="page-foot">
      <span>共 {{ gaps.length }} 条缺口记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchGaps, recalculateGaps } from '@/api/reconciliation'
import type { AlertGap, RecalculationResult } from '@/domain/reconciliation'

const router = useRouter()
const gaps = ref<AlertGap[]>([])
const selectedIds = ref<number[]>([])
const statusFilter = ref('')
const submitting = ref(false)
const errorMessage = ref('')
const lastResult = ref<RecalculationResult | null>(null)

const statusOptions = [
  { label: '全部', value: '' },
  { label: '待处理', value: '待处理' },
  { label: '已处理', value: '已处理' },
]

const summary = computed(() => ({
  total: gaps.value.length,
  pending: gaps.value.filter((gap) => gap.status === '待处理').length,
  processed: gaps.value.filter((gap) => gap.status === '已处理').length,
  conflict: gaps.value.filter((gap) => gap.conflict).length,
}))

async function loadGaps() {
  errorMessage.value = ''
  try {
    const result = await fetchGaps(statusFilter.value || undefined)
    // 已处理或已消失的勾选要清掉，避免把旧选择捎带进下一次补算。
    const validIds = new Set(result.items.filter((gap) => gap.status === '待处理').map((gap) => gap.id))
    selectedIds.value = selectedIds.value.filter((id) => validIds.has(id))
    gaps.value = result.items
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '告警缺项单读取失败'
  }
}

function changeFilter(value: string) {
  statusFilter.value = value
  void loadGaps()
}

async function submit() {
  if (!selectedIds.value.length) return
  submitting.value = true
  errorMessage.value = ''
  try {
    lastResult.value = await recalculateGaps([...selectedIds.value])
    selectedIds.value = []
    await loadGaps()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '补算提交失败'
  } finally {
    submitting.value = false
  }
}

function goReceipts() {
  void router.push('/alert_receipts')
}

// 模拟「另一个标签页修正价格」：窗口重新获得焦点时拉取最新冲突状态。
function onFocus() {
  void loadGaps()
}

onMounted(() => {
  void loadGaps()
  window.addEventListener('focus', onFocus)
})
onUnmounted(() => window.removeEventListener('focus', onFocus))
</script>
