"""告警核对路由：核对视图、告警缺项单、补算回执、价格更正与规则升级。

与通用资源路由分开注册，路径全部为固定名词，避免与 ``/api/{module}`` 冲突。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.reconciliation import reconciliation_service as service

router = APIRouter(prefix="/api/reconciliation", tags=["告警核对"])


class RecalculationPayload(BaseModel):
    gap_ids: list[int] = Field(default_factory=list)


class PriceCorrectionPayload(BaseModel):
    new_price: float
    source: str = "人工更正"
    note: str = ""


class RuleUpgradePayload(BaseModel):
    new_threshold: str
    note: str = ""


@router.get("/change-events")
def reconciliation_view() -> dict[str, Any]:
    """变价历史流水核对视图：已确认变价 × 告警规则版本 × 回执。"""
    return service.reconciliation_view()


@router.get("/gaps")
def list_gaps(status: str | None = None) -> dict[str, Any]:
    """告警缺项单：已处理 / 待处理记录与每条实际证据。"""
    return service.list_gaps(status=status)


@router.post("/gaps/recalculate")
def submit_recalculation(payload: RecalculationPayload) -> dict[str, Any]:
    """按勾选缺口补算，严格限定选中的商品与变价事件，重提幂等。"""
    return service.submit_recalculation(payload.gap_ids)


@router.get("/receipts")
def list_receipts(rule_version: str | None = None) -> dict[str, Any]:
    """补算回执查询，可按规则版本回溯。"""
    return service.list_receipts(rule_version=rule_version)


@router.post("/change-events/{event_id}/corrections")
def correct_price(event_id: int, payload: PriceCorrectionPayload) -> dict[str, Any]:
    """同一变价更正：追加价格版本，旧证据保留，关联缺口标记冲突。"""
    return service.correct_price(event_id, payload.new_price, payload.source, payload.note)


@router.post("/rules/{rule_code}/upgrade")
def upgrade_rule(rule_code: str, payload: RuleUpgradePayload) -> dict[str, Any]:
    """规则升级：追加规则版本并为未核对事件开「规则升级」缺口。"""
    return service.upgrade_rule(rule_code, payload.new_threshold, payload.note)


@router.get("/rules/{rule_code}/versions")
def rule_versions(rule_code: str) -> dict[str, Any]:
    """展示所查规则的版本历史。"""
    return service.rule_versions(rule_code)
