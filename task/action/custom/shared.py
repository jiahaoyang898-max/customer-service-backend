#调接口的工具函数
from typing import Any
from urllib.parse import quote
import logging

from conf.config import settings
from infrastructure import http_client as _http_module

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return settings.commerce_api_base_url.rstrip("/")

#提取数据
def _extract_data(result: dict | None) -> dict | None:
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else None


def strip_trailing_punct(value: Any) -> str:
    """
    统一约定：写入槽位的文案不带结尾标点，句读由话术模板负责，
    避免出现「…请稍后再试。。」这类双句号。
    """
    return str(value or "").strip().rstrip("。；！!")

#查订单
async def fetch_order(order_id: str) -> dict | None:
    try:
        r = await _http_module.http_client.get(f"{_base_url()}/orders/{quote(order_id)}")
        return _extract_data(r.json())
    except Exception:
        return None

#查物流
async def fetch_logistics(order_id: str) -> dict | None:
    try:
        r = await _http_module.http_client.get(f"{_base_url()}/orders/{quote(order_id)}/logistics")
        return _extract_data(r.json())
    except Exception:
        return None

#查商品
async def fetch_product(product_id: str) -> dict | None:
    try:
        r = await _http_module.http_client.get(f"{_base_url()}/products/{quote(product_id)}")
        return _extract_data(r.json())
    except Exception:
        return None

def _build_order_summary(payload: dict[str, Any]) -> str:
    parts = []
    if payload.get("amount"):
        parts.append(f"订单金额 ¥{payload['amount']}")
    items = payload.get("items") or []
    if items:
        # 电商 /orders/{id} 返回的明细字段叫 title（DB 侧是 title_snapshot），两种命名都兼容
        titles = [str(item.get("title") or item.get("title_snapshot") or "").strip()
                  for item in items[:2] if (item.get("title") or item.get("title_snapshot"))]
        if titles:
            parts.append("商品：" + "、".join(titles))
    # 约定：槽值不带结尾标点，标点由话术模板负责
    return "。".join(parts)


#提交退款申请（真实写接口）
async def submit_refund_application(
        order_id: str,
        reason: str,
        submitted_by: str,
) -> tuple[int | None, dict | None, str | None]:
    """
    调用电商 POST /orders/{order_id}/refund-applications 真实落库。

    与上面的 GET 工具函数不同：这里必须把 HTTP 状态码回传给上层，
    让 Action 能区分 200 / 409 / 404 / 400 / 422 / 网络异常，
    从而保证话术与真实落库结果一致。

    返回 (status_code, data, error_detail)：
      - status_code:  HTTP 状态码；None 表示请求没发出去/超时等异常
      - data:         2xx 时的响应 data（含 refund 单号 request_id），否则 None
      - error_detail: 非 2xx 或异常时，服务端 detail 或异常摘要，否则 None
    """
    url = f"{_base_url()}/orders/{quote(order_id)}/refund-applications"
    body = {"reason": reason, "submitted_by": submitted_by}
    try:
        r = await _http_module.http_client.post(url, json=body)
    except Exception as exc:
        logger.warning("提交退款申请请求异常: order_id=%s err=%s", order_id, exc)
        return None, None, f"请求电商退款接口失败：{exc}"

    status_code = r.status_code
    try:
        parsed = r.json()
    except Exception:
        parsed = None

    if 200 <= status_code < 300:
        return status_code, _extract_data(parsed), None

    detail = None
    if isinstance(parsed, dict):
        detail = parsed.get("detail") or parsed.get("message")
    return status_code, None, str(detail) if detail else f"HTTP {status_code}"
