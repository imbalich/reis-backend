import asyncio
from datetime import date

from backend.app.calcu.model.science_warehouse_result import ScienceWarehouseResult
from backend.app.calcu.schema.science_warehouse import ScienceWarehouseRequest
from backend.app.calcu.schema.science_warehouse import (
    ScienceWarehouseListDetails,
    ScienceWarehouseResultDetails,
)
from backend.app.calcu.schema.spare_statistics import (
    ModelPartItem,
    PredictSpareRequest,
    FailureCountRequest,
)
from backend.app.calcu.api.v1.calcu.science_warehouse import router as science_router
from backend.app.calcu.service import science_warehouse_service as science_service_module
from backend.app.task.tasks.science_warehouse_task import __all__ as science_task_exports


def test_science_warehouse_request_accepts_product_dimension_filters() -> None:
    payload = ScienceWarehouseRequest.model_validate(
        {
            "time_interval_days": 180,
            "input_date": "2026-04-01",
            "product_model": "CR400AF",
            "product_config_code": "A01",
        }
    )
    assert payload.product_model == "CR400AF"
    assert payload.product_config_code == "A01"


def test_science_warehouse_result_model_keeps_warehouse_spare_dimension_only() -> None:
    assert not hasattr(ScienceWarehouseResult, "product_model")
    assert not hasattr(ScienceWarehouseResult, "product_config_code")


def test_science_warehouse_result_schemas_do_not_expose_source_dimensions() -> None:
    assert "product_model" not in ScienceWarehouseResultDetails.model_fields
    assert "product_config_code" not in ScienceWarehouseResultDetails.model_fields
    assert "product_model" not in ScienceWarehouseListDetails.model_fields
    assert "product_config_code" not in ScienceWarehouseListDetails.model_fields


def test_save_calculation_results_does_not_persist_source_dimensions(monkeypatch) -> None:
    captured_rows = []

    class _SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _fake_clear_by_calculation_id(db, calculation_id):
        return None

    async def _fake_bulk_create(db, result_data):
        captured_rows.extend(result_data)
        return []

    async def _fake_get_warehouse_name(warehouse_code):
        return "库房A"

    monkeypatch.setattr(
        science_service_module,
        "async_db_session",
        lambda: _SessionContext(),
    )
    monkeypatch.setattr(
        science_service_module.science_warehouse_result_dao,
        "clear_by_calculation_id",
        _fake_clear_by_calculation_id,
    )
    monkeypatch.setattr(
        science_service_module.science_warehouse_result_dao,
        "bulk_create",
        _fake_bulk_create,
    )
    monkeypatch.setattr(
        science_service_module.ScienceWarehouseService,
        "get_warehouse_name",
        staticmethod(_fake_get_warehouse_name),
    )

    asyncio.run(
        science_service_module.ScienceWarehouseService.save_calculation_results(
            calculation_id="SW_123",
            results={
                "WH-001": {
                    "SP-001": {
                        "part_name": "备品A",
                        "required_quantity": 3,
                        "calculation_method": "fitted",
                        "confidence": 0.8,
                    }
                }
            },
            statistics={},
            time_interval_days=180,
            input_date=date(2026, 4, 27),
            product_model="CR400AF",
            product_config_code="A01",
        )
    )

    assert captured_rows
    assert "product_model" not in captured_rows[0]
    assert "product_config_code" not in captured_rows[0]


def test_spare_statistics_model_part_item_accepts_product_config_code() -> None:
    payload = ModelPartItem.model_validate(
        {
            "model": "CR400AF",
            "product_config_code": "A01",
            "part": "P-001",
            "failure_count": 12,
        }
    )
    assert payload.product_config_code == "A01"


def test_spare_statistics_predict_request_preserves_product_config_code() -> None:
    payload = PredictSpareRequest.model_validate(
        {
            "model_part_list": [
                {
                    "model": "CR400AF",
                    "product_config_code": "A01",
                    "part": "P-001",
                    "failure_count": 12,
                }
            ],
            "input_date": "2026-04-01",
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
        }
    )
    assert payload.model_part_list[0].product_config_code == "A01"


def test_spare_statistics_failure_count_request_preserves_product_config_code() -> None:
    payload = FailureCountRequest.model_validate(
        {
            "model_part_list": [
                {
                    "model": "CR400AF",
                    "product_config_code": "A01",
                    "part": "P-001",
                    "failure_count": 12,
                }
            ],
            "input_date": "2026-04-01",
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
        }
    )
    assert payload.model_part_list[0].product_config_code == "A01"


def test_science_warehouse_routes_do_not_expose_calculate_v2() -> None:
    paths = {route.path for route in science_router.routes}
    assert "/calculate-v2" not in paths


def test_science_warehouse_task_exports_main_calculation_and_push_flows() -> None:
    assert science_task_exports == [
        "science_warehouse_calculation_task",
        "science_warehouse_push_task",
    ]
