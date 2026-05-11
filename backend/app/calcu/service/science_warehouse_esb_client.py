#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

import httpx


@dataclass(frozen=True)
class EsbResponse:
    """ESB HTTP 响应。"""

    http_status: int
    headers: dict[str, str]
    body_text: str

    @property
    def success(self) -> bool:
        """HTTP 成功且 ESB 未显式返回失败时视为成功。"""
        return self.http_status == 200 and self.headers.get("statusFlag") in (
            None,
            "1",
        )


def _payload_size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def chunk_payload_records(
    records: Sequence[dict[str, Any]],
    base_payload: dict[str, Any],
    max_bytes: int,
) -> list[list[dict[str, Any]]]:
    """按完整业务 payload 的 UTF-8 字节数切分 results。"""
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    for record in records:
        single_payload = {**base_payload, "results": [record]}
        if _payload_size(single_payload) > max_bytes:
            raise ValueError("单条科学库存推送记录超过ESB报文大小限制")

        candidate = [*current, record]
        candidate_payload = {**base_payload, "results": candidate}
        if current and _payload_size(candidate_payload) > max_bytes:
            chunks.append(current)
            current = [record]
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks


class ScienceWarehouseEsbClient:
    """科学库存 ESB 调用客户端。"""

    @staticmethod
    def build_headers(source_system: str, service_name: str) -> dict[str, str]:
        request_id = str(uuid.uuid4())
        return {
            "Content-Type": "application/json",
            "requestId": request_id,
            "trackId": uuid.uuid4().hex,
            "sourceSystem": source_system,
            "serviceName": service_name,
            "requestTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    async def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> EsbResponse:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
        return EsbResponse(
            http_status=response.status_code,
            headers=dict(response.headers),
            body_text=response.text,
        )


science_warehouse_esb_client = ScienceWarehouseEsbClient()
