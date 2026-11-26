/** 告警核对接口：核对视图、缺项单、补算、回执、价格更正、规则升级。 */
import { fetchJson, request } from './client'
import type {
  ChangeEventView,
  CorrectionResult,
  GapListResult,
  RecalculationResult,
  AlertReceipt,
  RuleVersion,
} from '@/domain/reconciliation'

export async function fetchChangeEvents(): Promise<{ items: ChangeEventView[]; total: number }> {
  return fetchJson('/api/reconciliation/change-events')
}

export async function fetchGaps(status?: string): Promise<GapListResult> {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  return fetchJson(`/api/reconciliation/gaps${query}`)
}

export async function recalculateGaps(gapIds: number[]): Promise<RecalculationResult> {
  const response = await request('/api/reconciliation/gaps/recalculate', {
    method: 'POST',
    body: JSON.stringify({ gap_ids: gapIds }),
  })
  if (!response.ok) throw new Error('补算请求提交失败')
  return await response.json()
}

export async function fetchReceipts(ruleVersion?: string): Promise<{ items: AlertReceipt[]; total: number }> {
  const query = ruleVersion ? `?rule_version=${encodeURIComponent(ruleVersion)}` : ''
  return fetchJson(`/api/reconciliation/receipts${query}`)
}

export async function correctPrice(
  eventId: number,
  newPrice: number,
  source: string,
  note: string,
): Promise<CorrectionResult> {
  const response = await request(`/api/reconciliation/change-events/${eventId}/corrections`, {
    method: 'POST',
    body: JSON.stringify({ new_price: newPrice, source, note }),
  })
  if (!response.ok) throw new Error('价格更正失败')
  return await response.json()
}

export async function fetchRuleVersions(ruleCode: string): Promise<{
  ok: boolean
  message: string
  rule_code: string
  current_version: string
  current_threshold: string
  version_history: RuleVersion[]
}> {
  return fetchJson(`/api/reconciliation/rules/${encodeURIComponent(ruleCode)}/versions`)
}
