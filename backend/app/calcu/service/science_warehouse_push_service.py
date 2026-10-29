#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from datetime import datetime
from typing import Any, Sequence

from backend.app.calcu.crud.crud_science_warehouse_push_log import (
    science_warehouse_push_log_dao,
)
from backend.app.calcu.crud.crud_science_warehouse_push_result import (
    science_warehouse_push_result_dao,
)
from backend.app.calcu.service.science_warehouse_esb_client import (
    chunk_payload_records,
    science_warehouse_esb_client,
)
from backend.common.exception import errors
from backend.core.conf import settings
from backend.database.db import async_db_session


def build_science_warehouse_push_payload(
    calculation_id: str,
    push_reason: str,
    rows: Sequence[Any],
) -> dict[str, Any]:
    """构建符合 WMS 接口文档的科学库存推送报文。"""
    return {
        "push_source": "REIS系统",
        "push_time": datetime.now().replace(microsecond=0).isoformat(),
        "push_reason": push_reason,
        "calculation_id": calculation_id,
        "results": [
            {
                "calculation_id": row.calculation_id,
                "warehouse_code": row.warehouse_code,
                "warehouse_name": row.warehouse_name,
                "spare_part_code": row.spare_part_code,
                "spare_part_name": row.spare_part_name,
                "max_failure_count": row.max_failure_count,
                "required_quantity": row.required_quantity,
            }
            for row in rows
        ],
    }


def _payload_size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


class ScienceWarehousePushService:
    """科学库存推送服务。"""

    async def push_by_calculation_id(
        self, calculation_id: str, push_reason: str
    ) -> dict[str, Any]:
        async with async_db_session() as db:
            rows = await science_warehouse_push_result_dao.get_by_calculation_id(
                db, calculation_id
            )
            if not rows:
                raise errors.NotFoundError(
                    msg=f"计算批次 {calculation_id} 没有待推送数据"
                )

            full_payload = build_science_warehouse_push_payload(
                calculation_id=calculation_id,
                push_reason=push_reason,
                rows=rows,
            )
            base_payload = {k: v for k, v in full_payload.items() if k != "results"}
            chunks = chunk_payload_records(
                full_payload["results"],
                base_payload=base_payload,
                max_bytes=settings.SCIENCE_WAREHOUSE_ESB_MAX_PAYLOAD_BYTES,
            )

            success_chunks = 0
            failed_chunks = 0

            for index, chunk in enumerate(chunks, start=1):
                payload = {**base_payload, "results": chunk}
                headers = science_warehouse_esb_client.build_headers(
                    source_system=settings.SCIENCE_WAREHOUSE_ESB_SOURCE_SYSTEM,
                    service_name=settings.SCIENCE_WAREHOUSE_ESB_SERVICE_NAME,
                )
                log = await science_warehouse_push_log_dao.create_log(
                    db,
                    {
                        "calculation_id": calculation_id,
                        "push_reason": push_reason,
                        "push_status": "running",
                        "chunk_no": index,
                        "chunk_total": len(chunks),
                        "total_records": len(chunk),
                        "request_id": headers["requestId"],
                        "track_id": headers["trackId"],
                        "service_name": headers["serviceName"],
                        "payload_size_bytes": _payload_size(payload),
                    },
                )

                try:
                    response = await science_warehouse_esb_client.post_json(
                        url=settings.SCIENCE_WAREHOUSE_ESB_URL,
                        headers=headers,
                        payload=payload,
                        timeout_seconds=settings.SCIENCE_WAREHOUSE_ESB_TIMEOUT_SECONDS,
                    )
                    if response.success:
                        success_chunks += 1
                        await science_warehouse_push_log_dao.update_log(
                            db,
                            log,
                            {
                                "push_status": "success",
                                "esb_status_flag": response.headers.get("statusFlag"),
                                "esb_code": response.headers.get("esbCode"),
                                "esb_desc": response.headers.get("esbDesc"),
                                "response_body": response.body_text,
                                "pushed_time": datetime.now(),
                            },
                        )
                    else:
                        failed_chunks += 1
                        await science_warehouse_push_log_dao.update_log(
                            db,
                            log,
                            {
                                "push_status": "failed",
                                "esb_status_flag": response.headers.get("statusFlag"),
                                "esb_code": response.headers.get("esbCode"),
                                "esb_desc": response.headers.get("esbDesc"),
                                "response_body": response.body_text,
                                "error_message": f"ESB响应失败: HTTP {response.http_status}",
                                "pushed_time": datetime.now(),
                            },
                        )
                except Exception as e:
                    failed_chunks += 1
                    await science_warehouse_push_log_dao.update_log(
                        db,
                        log,
                        {
                            "push_status": "failed",
                            "error_message": str(e),
                            "pushed_time": datetime.now(),
                        },
                    )

            status = "success"
            if failed_chunks and success_chunks:
                status = "partial_success"
            elif failed_chunks:
                status = "failed"

            return {
                "calculation_id": calculation_id,
                "total_records": len(rows),
                "success_chunks": success_chunks,
                "failed_chunks": failed_chunks,
                "status": status,
            }


science_warehouse_push_service = ScienceWarehousePushService()
