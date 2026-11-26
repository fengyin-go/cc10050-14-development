/** 告警核对领域类型：与后端 reconciliation 路由的返回结构保持一致。 */

export type PriceVersion = {
  version: string
  old_price: number
  new_price: number
  source: string
  captured_at: string
  note: string
}

export type RuleVersion = {
  version: string
  threshold: string
  change_note: string
  effective_at: string
}

export type ChangeEventView = {
  event_id: number
  event_code: string
  goods_id: string
  status: string
  old_price: number
  new_price: number
  ratio: string
  found_at: string
  price_source: string
  current_price_version: string
  price_versions: PriceVersion[]
  rule_code: string
  rule_current_version: string
  rule_threshold: string
  linked_gap_nos: string[]
  receipt_nos: string[]
}

export type GapEvidence = {
  old_price: number
  new_price: number
  source: string
  captured_at?: string
  note: string
}

export type AlertGap = {
  id: number
  gap_no: string
  status: string
  gap_type: string
  event_id: number
  event_code: string
  goods_id: string
  rule_code: string
  rule_version_at_gap: string
  price_version_at_gap: string
  evidence: GapEvidence
  conflict: boolean
  receipt_no: string | null
  created_at: string
  processed_at: string | null
}

export type GapListResult = {
  ok: boolean
  message: string
  items: AlertGap[]
  total: number
  pending_count: number
  processed_count: number
  conflict_count: number
}

export type RecalculationResult = {
  ok: boolean
  message: string
  processed: {
    gap_id: number
    gap_no: string
    goods_id: string
    receipt_no: string
    triggered: boolean
    conflict: boolean
  }[]
  reused: { gap_id: number; gap_no: string; receipt_no: string; message: string }[]
  skipped: { gap_id: number; gap_no: string; reason: string }[]
  not_found: number[]
  untouched: { gap_id: number; gap_no: string; goods_id: string }[]
}

export type AlertReceipt = {
  id: number
  receipt_no: string
  gap_no: string
  event_id: number
  event_code: string
  goods_id: string
  rule_code: string
  rule_version: string
  rule_threshold: string
  price_version: string
  price_source: string
  old_price: number
  new_price: number
  diff_amount: number
  diff_ratio: number
  threshold_value: number
  triggered: boolean
  decision: string
  channel: string
  conflict_at_run: boolean
  evidence_at_gap?: GapEvidence
  current_evidence?: {
    old_price: number
    new_price: number
    source: string
    price_version: string
  }
  created_at: string
  idempotent_key: string
}

export type CorrectionResult = {
  ok: boolean
  message: string
  event_id: number
  event_code: string
  goods_id: string
  new_price_version: string
  old_price: number
  new_price: number
  ratio: string
  affected_gaps: {
    gap_no: string
    status: string
    conflict: boolean
    changed: boolean
  }[]
}
