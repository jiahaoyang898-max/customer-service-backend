from typing import Any

from domain.state import DialogueState
from task.action.base import Action, ActionResult
from task.action.custom.shared import fetch_logistics, fetch_order, strip_trailing_punct

# 尚未交给物流的订单状态：这类订单本来就没有物流记录，不能报「未知配送」
NOT_SHIPPED_STATUSES = {"待付款", "待发货", "待揽收"}


#查物流
class LookupLogisticsAction(Action):
    name = "action_lookup_logistics"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        order_number = state.active_task.slots.get("order_number")
        payload = await fetch_logistics(order_number)

        if payload is not None:
            return ActionResult(slot_updates={
                "logistics_found": "yes",
                "logistics_missing_reason": "",
                "tracking_number": strip_trailing_punct(payload.get("tracking_number")) or "未知",
                "logistics_company": strip_trailing_punct(payload.get("logistics_company")) or "未知",
                "logistics_status": strip_trailing_punct(
                    payload.get("status_desc") or payload.get("status")
                ) or "暂无更多进度信息",
            })

        # 查不到物流时先确认订单状态，区分「还没发货」与「真的查询失败」
        order = await fetch_order(order_number)
        order_status = str((order or {}).get("status") or "").strip()
        if order_status in NOT_SHIPPED_STATUSES:
            return ActionResult(slot_updates={
                "logistics_found": "no",
                "logistics_missing_reason": "not_shipped",
                "order_status": order_status,
            })

        return ActionResult(slot_updates={
            "logistics_found": "no",
            "logistics_missing_reason": "query_failed",
        })
