from backend.app.calcu.schema.science_warehouse import ScienceWarehouseRequest
from backend.app.calcu.schema.spare_statistics import (
    ModelPartItem,
    PredictSpareRequest,
    FailureCountRequest,
)
from backend.app.calcu.api.v1.calcu.science_warehouse import router as science_router


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
