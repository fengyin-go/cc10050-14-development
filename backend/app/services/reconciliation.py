"""告警核对领域服务：把「已确认变价」与「告警规则版本」逐事件核对，
负责告警缺项单、补算判定、版本化回执与流水回写。

设计约束（对应运营核对场景）：
- 补算严格限定在运营勾选的商品与变价事件内，同一规则覆盖的其他商品不会被捎带；
- 同一缺口的同一规则版本 × 价格版本只确认一次，重提返回既有回执（幂等）；
- 回执固化计算时实际消费的规则版本、价格来源与判定理由，历史回执按版本可查；
- 同一变价被更正后，旧证据保留在价格版本链里，缺口标记证据冲突，
  补算按当前价格版本计算，并在回执中同时展示两版价格。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.store import store

GAP_TABLE = "alert_gap"
RECEIPT_TABLE = "alert_receipt"
HISTORY_TABLE = "change_history"
RULE_TABLE = "price_alert"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_float(value: Any) -> float:
    return float(str(value).replace("%", ""))


class ReconciliationService:
    """告警核对服务：不继承通用 CRUD 骨架，全部为领域动作。"""

    # ---------- 工具方法 ----------

    def _find_gap(self, gap_id: int) -> dict[str, Any] | None:
        return store.find(GAP_TABLE, gap_id)

    def _find_event(self, event_id: int) -> dict[str, Any] | None:
        return store.find(HISTORY_TABLE, event_id)

    def _find_rule(self, rule_code: str) -> dict[str, Any] | None:
        for rule in store.rows(RULE_TABLE):
            if rule.get("rule_code") == rule_code:
                return rule
        return None

    def _rule_version(self, rule: dict[str, Any], version: str) -> dict[str, Any] | None:
        for item in rule.get("version_history", []):
            if item.get("version") == version:
                return item
        return None

    def _current_price(self, event: dict[str, Any]) -> dict[str, Any]:
        versions = event.get("price_versions", [])
        current = event.get("current_price_version")
        for item in versions:
            if item.get("version") == current:
                return item
        return versions[-1] if versions else {}

    def _find_receipt(
        self, gap_no: str, rule_code: str, rule_version: str,
        event_code: str, price_version: str,
    ) -> dict[str, Any] | None:
        key = f"{gap_no}:{rule_code}:{rule_version}:{event_code}:{price_version}"
        for receipt in store.rows(RECEIPT_TABLE):
            if receipt.get("idempotent_key") == key:
                return receipt
        return None

    def _refresh_gap_conflict(self, gap: dict[str, Any]) -> bool:
        """对比缺口建单证据与事件当前价格版本，刷新冲突标记。"""
        event = self._find_event(int(gap.get("event_id", 0)))
        if event is None:
            return bool(gap.get("conflict"))
        current = self._current_price(event)
        conflict = current.get("version") != gap.get("price_version_at_gap")
        gap["conflict"] = conflict
        return conflict

    # ---------- 查询视图 ----------

    def reconciliation_view(self) -> dict[str, Any]:
        """变价历史流水的核对视图：每条已确认变价带规则版本、价格版本与回执。"""
        items: list[dict[str, Any]] = []
        for event in store.rows(HISTORY_TABLE):
            if not event.get("event_code"):
                continue
            rule = self._find_rule(str(event.get("linked_rule", "")))
            current_price = self._current_price(event)
            gap_nos = [
                g.get("gap_no")
                for g in store.rows(GAP_TABLE)
                if g.get("event_id") == event.get("id")
            ]
            items.append({
                "event_id": event.get("id"),
                "event_code": event.get("event_code"),
                "goods_id": event.get("商品标识"),
                "status": event.get("status"),
                "old_price": event.get("旧价格"),
                "new_price": event.get("新价格"),
                "ratio": event.get("变化幅度"),
                "found_at": event.get("发现时间"),
                "price_source": event.get("price_source"),
                "current_price_version": event.get("current_price_version"),
                "price_versions": event.get("price_versions", []),
                "rule_code": event.get("linked_rule"),
                "rule_current_version": rule.get("current_version") if rule else None,
                "rule_threshold": rule.get("价差阈值") if rule else None,
                "linked_gap_nos": gap_nos,
                "receipt_nos": list(event.get("receipts", [])),
            })
        items.sort(key=lambda row: str(row.get("found_at", "")), reverse=True)
        return {"ok": True, "message": "核对视图已生成", "items": items, "total": len(items)}

    def list_gaps(self, status: str | None = None) -> dict[str, Any]:
        """告警缺项单：列出已处理与待处理记录，并附带每条的实际证据与冲突态。"""
        gaps = [dict(gap) for gap in store.rows(GAP_TABLE)]
        for gap in gaps:
            self._refresh_gap_conflict(gap)
        if status:
            gaps = [gap for gap in gaps if gap.get("status") == status]
        gaps.sort(key=lambda gap: int(gap.get("id", 0)))
        pending = sum(1 for gap in store.rows(GAP_TABLE) if gap.get("status") == "待处理")
        processed = sum(1 for gap in store.rows(GAP_TABLE) if gap.get("status") == "已处理")
        conflicted = sum(1 for gap in store.rows(GAP_TABLE) if gap.get("conflict"))
        return {
            "ok": True,
            "message": "告警缺项单读取完成",
            "items": gaps,
            "total": len(gaps),
            "pending_count": pending,
            "processed_count": processed,
            "conflict_count": conflicted,
        }

    def list_receipts(self, rule_version: str | None = None) -> dict[str, Any]:
        """补算回执查询：可按规则版本过滤，保证既有回执按那次的版本可查。"""
        receipts = list(store.rows(RECEIPT_TABLE))
        if rule_version:
            receipts = [r for r in receipts if r.get("rule_version") == rule_version]
        receipts.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
        return {
            "ok": True,
            "message": "补算回执读取完成",
            "items": receipts,
            "total": len(receipts),
        }

    def rule_versions(self, rule_code: str) -> dict[str, Any]:
        """展示所查规则的版本历史与当前生效版本。"""
        rule = self._find_rule(rule_code)
        if rule is None:
            return {"ok": False, "message": f"规则 {rule_code} 不存在"}
        return {
            "ok": True,
            "message": "规则版本读取完成",
            "rule_code": rule_code,
            "current_version": rule.get("current_version"),
            "current_threshold": rule.get("价差阈值"),
            "version_history": rule.get("version_history", []),
        }

    # ---------- 补算（核心领域动作） ----------

    def submit_recalculation(self, gap_ids: list[int]) -> dict[str, Any]:
        """按勾选的缺口逐笔补算。

        - 只处理入参里的缺口，其他商品即使共用同一规则也不会被代算；
        - 已处理缺口重提时返回原回执，不重复确认（幂等）；
        - 证据冲突时按事件当前价格版本计算，回执同时保留两版价格。
        """
        if not gap_ids:
            return {"ok": False, "message": "请先勾选需要补算的告警缺口"}
        selected = sorted(set(int(gid) for gid in gap_ids))
        processed: list[dict[str, Any]] = []
        reused: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []

        selected_set = set(selected)
        for gap in store.rows(GAP_TABLE):
            if int(gap.get("id", 0)) not in selected_set:
                # 未勾选的缺口（含同规则的其他商品）原样保留，不产生任何回执。
                continue

            event = self._find_event(int(gap.get("event_id", 0)))
            rule = self._find_rule(str(gap.get("rule_code", "")))
            if event is None or rule is None:
                skipped.append({
                    "gap_id": gap.get("id"),
                    "gap_no": gap.get("gap_no"),
                    "reason": "关联变价事件或告警规则缺失",
                })
                continue

            rule_version = str(rule.get("current_version", ""))
            version_meta = self._rule_version(rule, rule_version)
            threshold_text = str(version_meta.get("threshold", rule.get("价差阈值", "0%")))
            threshold_value = _to_float(threshold_text) / 100

            price_snapshot = self._current_price(event)
            price_version = str(price_snapshot.get("version", ""))

            existing = self._find_receipt(
                str(gap.get("gap_no")), str(rule.get("rule_code")),
                rule_version, str(event.get("event_code")), price_version,
            )
            if existing is not None:
                # 幂等：同一缺口 × 同一规则版本 × 同一价格版本只确认一次。
                reused.append({
                    "gap_id": gap.get("id"),
                    "gap_no": gap.get("gap_no"),
                    "receipt_no": existing.get("receipt_no"),
                    "message": "该缺口已按相同版本确认，沿用既有回执",
                })
                gap["status"] = "已处理"
                gap["receipt_no"] = existing.get("receipt_no")
                if not gap.get("processed_at"):
                    gap["processed_at"] = existing.get("created_at")
                continue

            old_price = _to_float(price_snapshot.get("old_price", 0))
            new_price = _to_float(price_snapshot.get("new_price", 0))
            diff_amount = round(new_price - old_price, 4)
            diff_ratio = (new_price - old_price) / old_price if old_price else 0.0
            triggered = abs(diff_ratio) >= threshold_value
            conflict = self._refresh_gap_conflict(gap)

            receipt_no = self._next_receipt_no()
            receipt = {
                "id": self._next_receipt_id(),
                "receipt_no": receipt_no,
                "gap_no": gap.get("gap_no"),
                "event_id": event.get("id"),
                "event_code": event.get("event_code"),
                "goods_id": event.get("商品标识"),
                "rule_code": rule.get("rule_code"),
                "rule_version": rule_version,
                "rule_threshold": threshold_text,
                "price_version": price_version,
                "price_source": price_snapshot.get("source", ""),
                "old_price": old_price,
                "new_price": new_price,
                "diff_amount": diff_amount,
                "diff_ratio": round(diff_ratio, 6),
                "threshold_value": threshold_value,
                "triggered": triggered,
                "decision": (
                    f"变化幅度 {abs(diff_ratio):.2%} "
                    f"{'达到' if triggered else '未达到'} {rule_version} 阈值 "
                    f"{threshold_text}，{'应发告警' if triggered else '不发告警'}"
                ),
                "channel": rule.get("通知渠道", "") if triggered else "",
                "conflict_at_run": conflict,
                "evidence_at_gap": dict(gap.get("evidence", {})),
                "current_evidence": {
                    "old_price": old_price,
                    "new_price": new_price,
                    "source": price_snapshot.get("source", ""),
                    "price_version": price_version,
                },
                "created_at": _now(),
                "idempotent_key": (
                    f"{gap.get('gap_no')}:{rule.get('rule_code')}:{rule_version}:"
                    f"{event.get('event_code')}:{price_version}"
                ),
            }
            store.rows(RECEIPT_TABLE).append(receipt)

            # 事件关联回写：把计算结论与处理回执沉淀回变价历史流水。
            event["receipts"] = list(event.get("receipts", [])) + [receipt_no]
            event["last_receipt"] = {
                "receipt_no": receipt_no,
                "rule_version": rule_version,
                "price_version": price_version,
                "price_source": price_snapshot.get("source", ""),
                "diff_amount": diff_amount,
                "diff_ratio": round(diff_ratio, 6),
                "triggered": triggered,
                "decision": receipt["decision"],
                "conflict_at_run": conflict,
            }
            event["新价格"] = new_price
            event["旧价格"] = old_price
            event["变化幅度"] = f"{diff_ratio:.2%}"
            event["price_source"] = price_snapshot.get("source", event.get("price_source", ""))

            gap["status"] = "已处理"
            gap["receipt_no"] = receipt_no
            gap["processed_at"] = receipt["created_at"]
            gap["conflict"] = conflict
            processed.append({
                "gap_id": gap.get("id"),
                "gap_no": gap.get("gap_no"),
                "goods_id": event.get("商品标识"),
                "receipt_no": receipt_no,
                "triggered": triggered,
                "conflict": conflict,
            })

        not_found = [gid for gid in selected if self._find_gap(gid) is None]
        untouched = [
            {"gap_id": g.get("id"), "gap_no": g.get("gap_no"), "goods_id": g.get("goods_id")}
            for g in store.rows(GAP_TABLE)
            if g.get("status") == "待处理" and int(g.get("id", 0)) not in selected_set
        ]
        return {
            "ok": True,
            "message": (
                f"补算完成：新确认 {len(processed)} 条，幂等沿用 {len(reused)} 条，"
                f"未勾选待处理 {len(untouched)} 条未被代算"
            ),
            "processed": processed,
            "reused": reused,
            "skipped": skipped,
            "not_found": not_found,
            "untouched": untouched,
        }

    def _next_receipt_id(self) -> int:
        return max((int(r.get("id", 0)) for r in store.rows(RECEIPT_TABLE)), default=0) + 1

    def _next_receipt_no(self) -> str:
        return f"R-{self._next_receipt_id():04d}"

    # ---------- 同一变价更正 ----------

    def correct_price(
        self, event_id: int, new_price: float, source: str, note: str,
    ) -> dict[str, Any]:
        """更正同一变价事件的新价：追加价格版本，旧证据保留不覆盖。

        已关联缺口若仍待处理，则标记证据冲突；已处理缺口的历史回执不受影响，
        仍可按当时的规则版本与价格版本查到。
        """
        event = self._find_event(event_id)
        if event is None:
            return {"ok": False, "message": f"变价事件 {event_id} 不存在"}
        try:
            new_price = float(new_price)
        except (TypeError, ValueError):
            return {"ok": False, "message": "更正后的新价格式无效"}
        old_price = _to_float(event.get("旧价格", 0))
        if old_price <= 0:
            return {"ok": False, "message": "事件旧价格无效，无法核算变化幅度"}

        versions = event.setdefault("price_versions", [])
        next_index = len(versions) + 1
        new_version = f"v{next_index}"
        versions.append({
            "version": new_version,
            "old_price": old_price,
            "new_price": new_price,
            "source": source or "人工更正",
            "captured_at": _now(),
            "note": note or f"同一变价更正：新价更正为 {new_price}",
        })
        event["current_price_version"] = new_version
        event["新价格"] = new_price
        event["变化幅度"] = f"{(new_price - old_price) / old_price:.2%}"
        event["price_source"] = source or event.get("price_source", "")

        affected_gaps: list[dict[str, Any]] = []
        for gap in store.rows(GAP_TABLE):
            if gap.get("event_id") != event_id:
                continue
            before = gap.get("conflict")
            conflict = self._refresh_gap_conflict(gap)
            affected_gaps.append({
                "gap_no": gap.get("gap_no"),
                "status": gap.get("status"),
                "conflict": conflict,
                "changed": conflict != before,
            })

        return {
            "ok": True,
            "message": f"事件 {event.get('event_code')} 新价已更正为 {new_price:g}",
            "event_id": event_id,
            "event_code": event.get("event_code"),
            "goods_id": event.get("商品标识"),
            "new_price_version": new_version,
            "old_price": old_price,
            "new_price": new_price,
            "ratio": f"{(new_price - old_price) / old_price:.2%}",
            "affected_gaps": affected_gaps,
        }

    # ---------- 规则升级 ----------

    def upgrade_rule(
        self, rule_code: str, new_threshold: str, note: str,
    ) -> dict[str, Any]:
        """升级告警规则：追加规则版本，历史版本保留，供回执按版本核对。"""
        rule = self._find_rule(rule_code)
        if rule is None:
            return {"ok": False, "message": f"规则 {rule_code} 不存在"}
        threshold_text = str(new_threshold).strip()
        if not threshold_text.endswith("%"):
            return {"ok": False, "message": "新阈值必须以百分号结尾，例如 10%"}
        try:
            threshold_value = _to_float(threshold_text)
        except ValueError:
            return {"ok": False, "message": "新阈值数值无效"}
        if threshold_value <= 0:
            return {"ok": False, "message": "阈值必须为正数"}

        history = rule.setdefault("version_history", [])
        next_index = len(history) + 1
        new_version = f"v{next_index}"
        history.append({
            "version": new_version,
            "threshold": threshold_text,
            "change_note": note or f"规则升级：阈值调整为 {threshold_text}",
            "effective_at": _now(),
        })
        rule["current_version"] = new_version
        rule["价差阈值"] = threshold_text

        # 已确认但尚未按新版本核对的事件，形成「规则升级」类缺口。
        opened: list[str] = []
        monitored = {item.strip() for item in str(rule.get("监控商品", "")).split(",") if item.strip()}
        existing_event_ids = {g.get("event_id") for g in store.rows(GAP_TABLE) if g.get("status") == "待处理"}
        for event in store.rows(HISTORY_TABLE):
            if event.get("商品标识") not in monitored or event.get("status") != "已确认":
                continue
            if event.get("id") in existing_event_ids:
                continue
            price_snapshot = self._current_price(event)
            gap_id = max((int(g.get("id", 0)) for g in store.rows(GAP_TABLE)), default=0) + 1
            gap_no = f"GAP-{gap_id:04d}"
            store.rows(GAP_TABLE).append({
                "id": gap_id,
                "gap_no": gap_no,
                "status": "待处理",
                "gap_type": "规则升级",
                "event_id": event.get("id"),
                "event_code": event.get("event_code"),
                "goods_id": event.get("商品标识"),
                "rule_code": rule_code,
                "rule_version_at_gap": new_version,
                "price_version_at_gap": price_snapshot.get("version"),
                "evidence": {
                    "old_price": price_snapshot.get("old_price"),
                    "new_price": price_snapshot.get("new_price"),
                    "source": price_snapshot.get("source"),
                    "captured_at": price_snapshot.get("captured_at"),
                    "note": f"规则升级到 {new_version}（{threshold_text}）后需补算",
                },
                "conflict": False,
                "receipt_no": None,
                "created_at": _now(),
                "processed_at": None,
            })
            event.setdefault("linked_gaps", []).append(gap_id)
            opened.append(gap_no)

        return {
            "ok": True,
            "message": f"规则 {rule_code} 已升级到 {new_version}（{threshold_text}）",
            "rule_code": rule_code,
            "new_version": new_version,
            "threshold": threshold_text,
            "opened_gaps": opened,
        }


reconciliation_service = ReconciliationService()
