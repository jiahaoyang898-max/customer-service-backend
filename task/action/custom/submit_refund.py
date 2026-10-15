from typing import Any

from domain.state import DialogueState
from task.action.base import Action, ActionResult
from task.action.custom.shared import submit_refund_application
import logging

logger = logging.getLogger(__name__)

#提交退款申请（真实落库，不再是纯话术）
class SubmitRefundAction(Action):
    """
    调用电商服务真实创建退款申请，并把结果写进槽位，
    由 user_flows.yml 的分支话术保证「说的 = 做的」。
    """
    name = "action_submit_refund"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        slots = state.active_task.slots if state.active_task else {}
        order_number = str(slots.get("order_number") or "").strip()
        reason = str(slots.get("refund_reason") or "").strip()
        operator = state.sender_id

        # 缺参数：不发起写请求，直接给出「未提交」结果
        if not order_number or not reason:
            logger.warning("退款提交缺少参数: sender=%s order=%s reason=%s", operator, order_number, reason)
            return ActionResult(slot_updates={"refund_result": "failed", "refund_id": ""})

        status_code, data, error_detail = await submit_refund_application(order_number, reason, operator)

        if status_code is None:
            # 请求没发出去 / 超时：数据库里一定没有新记录
            logger.warning("退款提交网络异常: sender=%s order=%s detail=%s", operator, order_number, error_detail)
            return ActionResult(slot_updates={"refund_result": "failed", "refund_id": ""})

        if 200 <= status_code < 300:
            refund_id = str((data or {}).get("request_id") or "").strip()
            logger.info(
                "退款提交成功: sender=%s order=%s refund_id=%s status=%s",
                operator, order_number, refund_id or "-", status_code,
            )
            return ActionResult(slot_updates={
                "refund_result": "success",
                "refund_id": refund_id,
                "refund_order_id": str((data or {}).get("order_id") or order_number),
            })

        if status_code == 409:
            logger.info("退款提交被拒(已存在进行中申请): sender=%s order=%s", operator, order_number)
            return ActionResult(slot_updates={"refund_result": "duplicate", "refund_id": ""})

        if status_code == 404:
            logger.info("退款提交被拒(订单不存在): sender=%s order=%s", operator, order_number)
            return ActionResult(slot_updates={"refund_result": "not_found", "refund_id": ""})

        # 400 / 422 / 5xx 等：电商侧未落库
        logger.warning(
            "退款提交失败: sender=%s order=%s status=%s detail=%s",
            operator, order_number, status_code, error_detail,
        )
        return ActionResult(slot_updates={"refund_result": "failed", "refund_id": ""})
