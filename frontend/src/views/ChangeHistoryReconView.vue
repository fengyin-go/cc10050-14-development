<template>
  <section class="page" data-module="change_history_recon">
    <header class="page-head">
      <div>
        <h2>变价历史流水 · 规则版本核对</h2>
        <p class="page-desc">
          已确认变价按告警规则版本核对，展示每条事件的价格来源、价格版本链与补算回执；
          支持对同一变价更正新价，旧证据保留不覆盖。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn" data-testid="refresh-events" type="button" @click="loadEvents">刷新流水</button>
        <RouterLink class="btn" to="/alert_gap">打开告警缺项单</RouterLink>
      </div>
    </header>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <table class="data-table recon-table">
      <thead>
        <tr>
          <th>商品 / 事件</th>
          <th>旧价 → 新价</th>
          <th>变化幅度</th>
          <th>价格来源 / 版本链</th>
          <th>核对规则版本</th>
          <th>关联缺口</th>
          <th>补算回执</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="event in events" :key="event.event_id" :data-testid="`event-row-${event.goods_id}`">
          <td>
            <div>{{ event.goods_id }}</div>
            <div class="src">{{ event.event_code }}</div>
            <span class="badge green">{{ event.status }}</span>
          </td>
          <td>
            <div>{{ event.old_price }} → {{ event.new_price }}</div>
            <div v-if="event.price_versions.length > 1" class="src" data-testid="two-price-versions">
              建单旧证据：{{ firstVersion(event).old_price }} → {{ firstVersion(event).new_price }}
              （{{ firstVersion(event).version }}）
            </div>
          </td>
          <td>{{ event.ratio }}</td>
          <td>
            <div class="version-chain">
              <div v-for="version in event.price_versions" :key="version.version">
                <span class="badge" :class="version.version === event.current_price_version ? 'blue' : 'gray'">
                  {{ version.version }}
                </span>
                {{ version.old_price }} → {{ version.new_price }}
                <span class="src">{{ version.source }}</span>
              </div>
            </div>
          </td>
          <td>
            <div>{{ event.rule_code }} {{ event.rule_current_version }}</div>
            <div class="src">当前阈值 {{ event.rule_threshold }}</div>
          </td>
          <td>
            <span v-for="gapNo in event.linked_gap_nos" :key="gapNo" class="badge gray">{{ gapNo }}</span>
            <span v-if="!event.linked_gap_nos.length" class="src">—</span>
          </td>
          <td>
            <RouterLink
              v-for="receiptNo in event.receipt_nos"
              :key="receiptNo"
              to="/alert_receipts"
              class="badge green"
              :data-testid="`event-receipt-${event.goods_id}`"
            >
              {{ receiptNo }}
            </RouterLink>
            <span v-if="!event.receipt_nos.length" class="src" :data-testid="`no-receipt-${event.goods_id}`">
              未补算
            </span>
          </td>
          <td class="row-actions">
            <button
              class="link"
              type="button"
              :data-testid="`correct-${event.goods_id}`"
              @click="openCorrection(event)"
            >
              更正新价
            </button>
            <button class="link" type="button" @click="toggleDetail(event.event_id)">
              {{ expandedId === event.event_id ? '收起证据' : '查看证据' }}
            </button>
          </td>
        </tr>
        <tr v-if="!events.length">
          <td colspan="8" class="empty-state">暂无可核对的已确认变价事件</td>
        </tr>
      </tbody>
    </table>

    <div v-if="expandedEvent" class="detail-drawer" style="margin-top: 10px" data-testid="evidence-drawer">
      <h4 style="margin: 4px 0 8px">{{ expandedEvent.goods_id }} 实际证据明细</h4>
      <dl>
        <dt>变价事件</dt><dd>{{ expandedEvent.event_code }}（{{ expandedEvent.found_at }}）</dd>
        <dt>当前价格版本</dt><dd>{{ expandedEvent.current_price_version }}</dd>
        <dt>价格来源</dt><dd>{{ expandedEvent.price_source }}</dd>
        <dt>规则版本</dt><dd>{{ expandedEvent.rule_code }} {{ expandedEvent.rule_current_version }} / {{ expandedEvent.rule_threshold }}</dd>
      </dl>
      <table class="data-table" style="margin-top: 8px">
        <thead>
          <tr><th>价格版本</th><th>旧价</th><th>新价</th><th>来源</th><th>采集时间</th><th>说明</th></tr>
        </thead>
        <tbody>
          <tr v-for="version in expandedEvent.price_versions" :key="version.version">
            <td>{{ version.version }}</td>
            <td>{{ version.old_price }}</td>
            <td>{{ version.new_price }}</td>
            <td>{{ version.source }}</td>
            <td>{{ version.captured_at }}</td>
            <td>{{ version.note }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showCorrection" class="modal-backdrop" data-testid="correction-modal">
      <form class="modal" @submit.prevent="submitCorrection">
        <h3>同一变价更正 · {{ correctionForm.goodsId }}</h3>
        <p class="page-desc">
          事件 {{ correctionForm.eventCode }}，旧价 {{ correctionForm.oldPrice }}。
          更正会追加新价格版本，原证据保留；待处理缺口将标记证据冲突。
        </p>
        <label class="create-field">
          <span>更正后新价</span>
          <input v-model.number="correctionForm.newPrice" type="number" step="0.01" required data-testid="correction-price" />
        </label>
        <label class="create-field">
          <span>价格来源</span>
          <input v-model="correctionForm.source" required data-testid="correction-source" />
        </label>
        <label class="create-field">
          <span>更正说明</span>
          <input v-model="correctionForm.note" data-testid="correction-note" />
        </label>
        <p v-if="correctionMessage" class="error-text">{{ correctionMessage }}</p>
        <div class="page-actions">
          <button class="btn" type="button" @click="showCorrection = false">取消</button>
          <button class="btn primary" data-testid="submit-correction" type="submit" :disabled="correcting">
            {{ correcting ? '提交中…' : '提交更正' }}
          </button>
        </div>
      </form>
    </div>

    <footer class="page-foot">
      <span>共 {{ events.length }} 条已确认变价事件，证据按版本留存</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

import { correctPrice, fetchChangeEvents } from '@/api/reconciliation'
import type { ChangeEventView, PriceVersion } from '@/domain/reconciliation'

const events = ref<ChangeEventView[]>([])
const expandedId = ref<number | null>(null)
const errorMessage = ref('')
const showCorrection = ref(false)
const correcting = ref(false)
const correctionMessage = ref('')
const correctionForm = ref({
  eventId: 0,
  eventCode: '',
  goodsId: '',
  oldPrice: 0,
  newPrice: 0,
  source: '站点A 人工复核回写',
  note: '',
})

const expandedEvent = computed(() =>
  events.value.find((event) => event.event_id === expandedId.value) ?? null,
)

function firstVersion(event: ChangeEventView): PriceVersion {
  return event.price_versions[0]
}

function toggleDetail(eventId: number) {
  expandedId.value = expandedId.value === eventId ? null : eventId
}

function openCorrection(event: ChangeEventView) {
  correctionForm.value = {
    eventId: event.event_id,
    eventCode: event.event_code,
    goodsId: event.goods_id,
    oldPrice: event.old_price,
    newPrice: event.new_price,
    source: event.price_source,
    note: `同一变价更正：${event.goods_id} 新价更正`,
  }
  correctionMessage.value = ''
  showCorrection.value = true
}

async function submitCorrection() {
  correcting.value = true
  correctionMessage.value = ''
  try {
    const result = await correctPrice(
      correctionForm.value.eventId,
      Number(correctionForm.value.newPrice),
      correctionForm.value.source,
      correctionForm.value.note,
    )
    if (!result.ok) throw new Error(result.message)
    showCorrection.value = false
    await loadEvents()
  } catch (error) {
    correctionMessage.value = error instanceof Error ? error.message : '价格更正失败'
  } finally {
    correcting.value = false
  }
}

async function loadEvents() {
  errorMessage.value = ''
  try {
    const result = await fetchChangeEvents()
    events.value = result.items
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '变价流水读取失败'
  }
}

function onFocus() {
  void loadEvents()
}

onMounted(() => {
  void loadEvents()
  window.addEventListener('focus', onFocus)
})
onUnmounted(() => window.removeEventListener('focus', onFocus))
</script>
