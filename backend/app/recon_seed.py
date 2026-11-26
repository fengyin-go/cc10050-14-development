"""告警核对（规则版本 × 已确认变价）示例数据。

相对 ``seed.py`` 的通用样例，这里沉淀一条可追溯的业务链：
- ``change_history`` 追加 H34~H37 四个真实变价事件，带价格版本与价格来源；
- ``price_alert`` 追加一条带版本历史的 10% 阈值规则；
- ``alert_gap`` 是告警缺项单，区分「规则升级」与「同一变价更正」两类缺口；
- ``alert_receipt`` 是补算判定回执，记录每次计算实际消费的规则版本与价格来源。

所有时间统一用固定字符串，保证演示与核对脚本结果稳定。
"""
from __future__ import annotations

from typing import Any

# 一条规则两个版本：v1 阈值 15%，v2 升级为 10%。
RULE_ALERT_10 = {
    "id": 20,
    "status": "已生效",
    "pending": False,
    "abnormal": False,
    "规则名称": "H 系列 10% 变价告警规则",
    "监控商品": "H34,H35,H36,H37",
    "价差阈值": "10%",
    "连续次数": "1",
    "通知渠道": "运营值班群",
    "rule_code": "AR-10",
    "current_version": "v2",
    "version_history": [
        {
            "version": "v1",
            "threshold": "15%",
            "change_note": "初版口径，阈值 15%",
            "effective_at": "2026-11-20T09:00:00Z",
        },
        {
            "version": "v2",
            "threshold": "10%",
            "change_note": "规则升级：阈值收紧到 10%",
            "effective_at": "2026-11-24T09:00:00Z",
        },
    ],
}

# 变价事件。price_versions 保留每次价格快照，旧证据永不被覆盖。
CHANGE_EVENTS: list[dict[str, Any]] = [
    {
        "id": 34,
        "status": "已确认",
        "pending": False,
        "abnormal": False,
        "商品标识": "H34",
        "旧价格": 100,
        "新价格": 88,
        "变化幅度": "-12.00%",
        "发现时间": "2026-11-25T10:00:00Z",
        "event_code": "EVT-H34-01",
        "price_source": "站点A 抓取快照",
        "current_price_version": "v1",
        "price_versions": [
            {
                "version": "v1",
                "old_price": 100,
                "new_price": 88,
                "source": "站点A 抓取快照",
                "captured_at": "2026-11-25T10:00:00Z",
                "note": "首次采集证据",
            }
        ],
        "linked_rule": "AR-10",
        "linked_gaps": [1],
        "receipts": [],
    },
    {
        "id": 35,
        "status": "已确认",
        "pending": False,
        "abnormal": False,
        "商品标识": "H35",
        "旧价格": 100,
        "新价格": 82,
        "变化幅度": "-18.00%",
        "发现时间": "2026-11-25T10:05:00Z",
        "event_code": "EVT-H35-01",
        "price_source": "站点A 抓取快照",
        "current_price_version": "v1",
        "price_versions": [
            {
                "version": "v1",
                "old_price": 100,
                "new_price": 82,
                "source": "站点A 抓取快照",
                "captured_at": "2026-11-25T10:05:00Z",
                "note": "首次采集证据",
            }
        ],
        "linked_rule": "AR-10",
        "linked_gaps": [2],
        "receipts": [],
    },
    {
        "id": 36,
        "status": "已确认",
        "pending": False,
        "abnormal": False,
        "商品标识": "H36",
        "旧价格": 100,
        "新价格": 86,
        "变化幅度": "-14.00%",
        "发现时间": "2026-11-22T14:00:00Z",
        "event_code": "EVT-H36-01",
        "price_source": "站点B 抓取快照",
        "current_price_version": "v1",
        "price_versions": [
            {
                "version": "v1",
                "old_price": 100,
                "new_price": 86,
                "source": "站点B 抓取快照",
                "captured_at": "2026-11-22T14:00:00Z",
                "note": "首次采集证据",
            }
        ],
        "linked_rule": "AR-10",
        "linked_gaps": [3],
        "receipts": [],
    },
    {
        "id": 37,
        "status": "已确认",
        "pending": False,
        "abnormal": False,
        "商品标识": "H37",
        "旧价格": 100,
        "新价格": 80,
        "变化幅度": "-20.00%",
        "发现时间": "2026-11-21T09:30:00Z",
        "event_code": "EVT-H37-01",
        "price_source": "站点C 抓取快照",
        "current_price_version": "v2",
        "price_versions": [
            {
                "version": "v1",
                "old_price": 100,
                "new_price": 78,
                "source": "站点C 抓取快照",
                "captured_at": "2026-11-21T09:30:00Z",
                "note": "首次采集证据（后被更正）",
            },
            {
                "version": "v2",
                "old_price": 100,
                "new_price": 80,
                "source": "站点C 人工复核回写",
                "captured_at": "2026-11-23T11:00:00Z",
                "note": "同一变价更正：新价 78 → 80",
            },
        ],
        "linked_rule": "AR-10",
        "linked_gaps": [4],
        "receipts": ["R-0001"],
    },
]

# 告警缺项单。gap_type 区分两类缺口；evidence 固化建单时的实际证据。
ALERT_GAPS: list[dict[str, Any]] = [
    {
        "id": 1,
        "gap_no": "GAP-0001",
        "status": "待处理",
        "gap_type": "同一变价更正",
        "event_id": 34,
        "event_code": "EVT-H34-01",
        "goods_id": "H34",
        "rule_code": "AR-10",
        "rule_version_at_gap": "v2",
        "price_version_at_gap": "v1",
        "evidence": {
            "old_price": 100,
            "new_price": 88,
            "source": "站点A 抓取快照",
            "captured_at": "2026-11-25T10:00:00Z",
            "note": "建单时证据：新价 88",
        },
        "conflict": False,
        "receipt_no": None,
        "created_at": "2026-11-25T12:00:00Z",
        "processed_at": None,
    },
    {
        "id": 2,
        "gap_no": "GAP-0002",
        "status": "待处理",
        "gap_type": "规则升级",
        "event_id": 35,
        "event_code": "EVT-H35-01",
        "goods_id": "H35",
        "rule_code": "AR-10",
        "rule_version_at_gap": "v2",
        "price_version_at_gap": "v1",
        "evidence": {
            "old_price": 100,
            "new_price": 82,
            "source": "站点A 抓取快照",
            "captured_at": "2026-11-25T10:05:00Z",
            "note": "规则升级到 v2 后，该事件未按新口径补算",
        },
        "conflict": False,
        "receipt_no": None,
        "created_at": "2026-11-25T12:00:00Z",
        "processed_at": None,
    },
    {
        "id": 3,
        "gap_no": "GAP-0003",
        "status": "待处理",
        "gap_type": "规则升级",
        "event_id": 36,
        "event_code": "EVT-H36-01",
        "goods_id": "H36",
        "rule_code": "AR-10",
        "rule_version_at_gap": "v2",
        "price_version_at_gap": "v1",
        "evidence": {
            "old_price": 100,
            "new_price": 86,
            "source": "站点B 抓取快照",
            "captured_at": "2026-11-22T14:00:00Z",
            "note": "v1（15%）判定不触发，升级 v2（10%）后需补算",
        },
        "conflict": False,
        "receipt_no": None,
        "created_at": "2026-11-24T10:00:00Z",
        "processed_at": None,
    },
    {
        "id": 4,
        "gap_no": "GAP-0004",
        "status": "已处理",
        "gap_type": "同一变价更正",
        "event_id": 37,
        "event_code": "EVT-H37-01",
        "goods_id": "H37",
        "rule_code": "AR-10",
        "rule_version_at_gap": "v1",
        "price_version_at_gap": "v2",
        "evidence": {
            "old_price": 100,
            "new_price": 80,
            "source": "站点C 人工复核回写",
            "captured_at": "2026-11-23T11:00:00Z",
            "note": "更正后证据：新价 80",
        },
        "conflict": False,
        "receipt_no": "R-0001",
        "created_at": "2026-11-23T12:00:00Z",
        "processed_at": "2026-11-23T12:20:00Z",
    },
]

# 补算判定回执：固化每次计算消费的规则版本、价格来源与判定理由。
ALERT_RECEIPTS: list[dict[str, Any]] = [
    {
        "id": 1,
        "receipt_no": "R-0001",
        "gap_no": "GAP-0004",
        "event_id": 37,
        "event_code": "EVT-H37-01",
        "goods_id": "H37",
        "rule_code": "AR-10",
        "rule_version": "v1",
        "rule_threshold": "15%",
        "price_version": "v2",
        "price_source": "站点C 人工复核回写",
        "old_price": 100,
        "new_price": 80,
        "diff_amount": -20,
        "diff_ratio": -0.2,
        "threshold_value": 0.15,
        "triggered": True,
        "decision": "变化幅度 20.00% 达到 v1 阈值 15%，应发告警",
        "channel": "运营值班群",
        "conflict_at_run": False,
        "created_at": "2026-11-23T12:20:00Z",
        "idempotent_key": "GAP-0004:AR-10:v1:EVT-H37-01:v2",
    },
]

RECON_SEED: dict[str, list[dict[str, Any]]] = {
    "alert_gap": ALERT_GAPS,
    "alert_receipt": ALERT_RECEIPTS,
}
