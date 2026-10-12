# 知识提供者（API / FAQ / RAG）
import json, asyncio
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
from conf.config import settings
from domain.state import DialogueState
from infrastructure import http_client

class KnowledgeChunk(BaseModel):
    """
    知识块
    """
    content: str # 内容

class KnowledgeProvider(ABC):
    """
    知识提供者
    """
    #知识提供者的ID
    @abstractmethod
    async def retrieve(self,state:DialogueState)->list[KnowledgeChunk]:
        """
        提供检索方法
        """
        pass

class ProductAPIProvider(KnowledgeProvider):
    """
    产品API提供者
    """
    provider_id = "api.product"
    async def retrieve(self,state:DialogueState)->list[KnowledgeChunk]:
        #检索
        product_id = state.focused_object.id
        data:dict[str,Any] = await self._get_product_info_by_id(product_id)
        text = json.dumps(data,ensure_ascii=False,indent=2)
        return [KnowledgeChunk(content=f"商品信息:\n{text}")]
    async def _get_product_info_by_id(self, product_id: str) -> dict[str, Any]:
        #通过ID获取产品信息
        url = f"{settings.commerce_api_base_url}/products/{product_id}"
        response = await http_client.http_client.get(url)
        return response.json()["data"]

class OrderAPIProvider(KnowledgeProvider):
    """
    订单API提供者
    """
    provider_id = 'api.order'
    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        #检索
        #订单id
        order_number = state.focused_object.id
        #订单数据，物流数据
        order_payload,logistics_payload = await asyncio.gather(
            self._fetch_order(order_number),
            self._fetch_logistics(order_number),
        )
        return [
            KnowledgeChunk(
                content="订单与物流信息：\n"
                        + json.dumps(
                    {
                        "order_number": order_number,
                        "order": order_payload,
                        "logistics": logistics_payload,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        ]

    async def _fetch_order(self, order_number) -> dict[str, Any]:
        #获取订单
        url = f"{settings.commerce_api_base_url}/orders/{order_number}"
        response = await http_client.http_client.get(url)
        return response.json()["data"]

    async def _fetch_logistics(self, order_number) -> dict[str, Any]:
        #获取物流
        url = f"{settings.commerce_api_base_url}/orders/{order_number}/logistics"
        response = await http_client.http_client.get(url)
        return response.json().get("data", {})

class FAQProvider(KnowledgeProvider):
    #FAQ提供者
    provider_id = 'faq.default'
    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        #检索
        #TODO
        return [KnowledgeChunk(content="FAQ:未检索到相关问题")]

class RAGProvider(KnowledgeProvider):
    """
    RAG提供者
    """
    provider_id = 'rag.default'
    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        #TODO
        return [KnowledgeChunk(content="RAG:未检索到相关信息")]



















