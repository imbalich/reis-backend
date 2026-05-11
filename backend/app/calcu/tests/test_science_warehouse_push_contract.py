from types import SimpleNamespace

from backend.app.calcu.api.v1.calcu.science_warehouse import router as science_router
from backend.app.calcu.crud.crud_science_warehouse_push_log import (
    science_warehouse_push_log_dao,
)
from backend.app.calcu.crud.crud_science_warehouse_push_result import (
    science_warehouse_push_result_dao,
)
from backend.app.calcu.model.science_warehouse_push_log import ScienceWarehousePushLog
from backend.app.calcu.model.science_warehouse_push_result import (
    ScienceWarehousePushResult,
)
from backend.app.calcu.schema.science_warehouse import (
    ScienceWarehousePushRequest,
    ScienceWarehousePushTaskResponse,
)
from backend.app.calcu.service.science_warehouse_esb_client import (
    ScienceWarehouseEsbClient,
    chunk_payload_records,
)
from backend.app.calcu.service.science_warehouse_push_service import (
    build_science_warehouse_push_payload,
)


def test_science_warehouse_push_request_requires_reason() -> None:
    payload = ScienceWarehousePushRequest.model_validate(
        {"push_reason": "月度库存审查完成后推送"}
    )
    assert payload.push_reason == "月度库存审查完成后推送"


def test_science_warehouse_push_task_response_contract() -> None:
    payload = ScienceWarehousePushTaskResponse.model_validate(
        {
            "task_id": "celery-task-id",
            "task_name": "science_warehouse_push_task",
            "calculation_id": "SW_123",
            "message": "科学库存推送任务已提交",
        }
    )
    assert payload.calculation_id == "SW_123"


def test_science_warehouse_push_model_table_names() -> None:
    assert (
        ScienceWarehousePushResult.__tablename__
        == "calcu_science_warehouse_push_result"
    )
    assert ScienceWarehousePushLog.__tablename__ == "calcu_science_warehouse_push_log"


def test_science_warehouse_push_result_matches_corrected_result_dimension() -> None:
    assert not hasattr(ScienceWarehousePushResult, "product_model")
    assert not hasattr(ScienceWarehousePushResult, "product_config_code")


def test_science_warehouse_push_daos_use_expected_models() -> None:
    assert (
        science_warehouse_push_result_dao.model.__tablename__
        == "calcu_science_warehouse_push_result"
    )
    assert (
        science_warehouse_push_log_dao.model.__tablename__
        == "calcu_science_warehouse_push_log"
    )


def test_esb_headers_include_required_fields() -> None:
    headers = ScienceWarehouseEsbClient.build_headers(
        source_system="REIS",
        service_name="S_REIS_WMS_ScienceWarehousePush_S",
    )
    assert headers["Content-Type"] == "application/json"
    assert headers["sourceSystem"] == "REIS"
    assert headers["serviceName"] == "S_REIS_WMS_ScienceWarehousePush_S"
    assert "requestId" in headers
    assert "trackId" in headers
    assert "requestTime" in headers


def test_chunk_payload_records_respects_byte_limit() -> None:
    records = [{"spare_part_name": "A" * 200, "required_quantity": 1} for _ in range(10)]
    chunks = chunk_payload_records(
        records,
        base_payload={"calculation_id": "SW_123"},
        max_bytes=900,
    )
    assert len(chunks) > 1
    assert sum(len(chunk) for chunk in chunks) == 10


def test_build_science_warehouse_push_payload_maps_reviewed_rows() -> None:
    rows = [
        SimpleNamespace(
            calculation_id="SW_123",
            warehouse_code="GK27",
            warehouse_name="新乡机务段库",
            spare_part_code="CNR0000231122",
            spare_part_name="备品名称",
            max_failure_count=5,
            required_quantity=10,
        )
    ]
    payload = build_science_warehouse_push_payload(
        calculation_id="SW_123",
        push_reason="审查完成",
        rows=rows,
    )
    assert payload["push_source"] == "REIS系统"
    assert payload["calculation_id"] == "SW_123"
    assert payload["results"][0]["required_quantity"] == 10


def test_science_warehouse_exposes_push_route() -> None:
    paths = {route.path for route in science_router.routes}
    assert "/push/{calculation_id}" in paths
