import asyncio
from datetime import date
from types import SimpleNamespace

from backend.app.calcu.service import science_warehouse_service as science_warehouse_service_module


def _build_failure(
    *,
    failure_id: int,
    product_number: str,
    product_config_code: str,
    fault_material_code: str = "P-001",
):
    return SimpleNamespace(
        id=failure_id,
        product_number=product_number,
        discovery_date="2026-04-01",
        product_model="CR400AF",
        product_config_code=product_config_code,
        fault_material_code=fault_material_code,
    )


def test_perform_spare_calculation_splits_by_product_config_code(monkeypatch) -> None:
    lookup_calls = []
    quantity_calls = []

    failures = [
        _build_failure(
            failure_id=index + 1,
            product_number=f"train-a-{(index % 2) + 1}",
            product_config_code="A01",
        )
        for index in range(5)
    ] + [
        _build_failure(
            failure_id=index + 101,
            product_number=f"train-b-{(index % 2) + 1}",
            product_config_code="B02",
        )
        for index in range(5)
    ]

    async def _fake_get_or_create(
        product_model, part_code, product_config_code, input_date
    ):
        lookup_calls.append(
            {
                "product_model": product_model,
                "part_code": part_code,
                "product_config_code": product_config_code,
            }
        )
        return product_config_code

    async def _fake_calculate_spare_quantity_by_interval(
        best_distribution, time_interval_days, product_failures, input_date
    ):
        quantity_calls.append(
            {
                "best_distribution": best_distribution,
                "failure_ids": [failure.id for failure in product_failures],
            }
        )
        return 1.2 if best_distribution == "A01" else 2.1

    async def _fake_check_maintenance_responsibility(
        product_number, warehouse_code, spare_part_code
    ):
        return {"responsible": True}

    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "get_or_create_aaron_distribution",
        staticmethod(_fake_get_or_create),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "calculate_spare_quantity_by_interval",
        staticmethod(_fake_calculate_spare_quantity_by_interval),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "check_maintenance_responsibility",
        staticmethod(_fake_check_maintenance_responsibility),
    )

    result = asyncio.run(
        science_warehouse_service_module.ScienceWarehouseService.perform_spare_calculation_with_fit(
            failures=failures,
            time_interval_days=180,
            input_date=date(2026, 4, 27),
            warehouse_code="WH-001",
            spare_part_code="SP-001",
        )
    )

    assert result["success"] is True
    assert [call["product_config_code"] for call in lookup_calls] == ["A01", "B02"]
    assert quantity_calls == [
        {
            "best_distribution": "A01",
            "failure_ids": [1, 2, 3, 4, 5],
        },
        {
            "best_distribution": "B02",
            "failure_ids": [101, 102, 103, 104, 105],
        },
    ]


def test_perform_spare_calculation_sums_each_dimension_once(monkeypatch) -> None:
    failures = [
        _build_failure(
            failure_id=index + 1,
            product_number=f"train-a-{(index % 2) + 1}",
            product_config_code="A01",
        )
        for index in range(5)
    ] + [
        _build_failure(
            failure_id=index + 101,
            product_number=f"train-b-{(index % 2) + 1}",
            product_config_code="B02",
        )
        for index in range(5)
    ]

    async def _fake_get_or_create(
        product_model, part_code, product_config_code, input_date
    ):
        return product_config_code

    async def _fake_calculate_spare_quantity_by_interval(
        best_distribution, time_interval_days, product_failures, input_date
    ):
        return 1.2 if best_distribution == "A01" else 2.1

    async def _fake_check_maintenance_responsibility(
        product_number, warehouse_code, spare_part_code
    ):
        return {"responsible": True}

    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "get_or_create_aaron_distribution",
        staticmethod(_fake_get_or_create),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "calculate_spare_quantity_by_interval",
        staticmethod(_fake_calculate_spare_quantity_by_interval),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "check_maintenance_responsibility",
        staticmethod(_fake_check_maintenance_responsibility),
    )

    result = asyncio.run(
        science_warehouse_service_module.ScienceWarehouseService.perform_spare_calculation_with_fit(
            failures=failures,
            time_interval_days=180,
            input_date=date(2026, 4, 27),
            warehouse_code="WH-001",
            spare_part_code="SP-001",
        )
    )

    assert result["success"] is True
    assert result["quantity"] == 4


def test_empty_and_ps00_failures_share_one_dimension_group() -> None:
    failures = [
        _build_failure(failure_id=1, product_number="t-1", product_config_code=""),
        _build_failure(failure_id=2, product_number="t-2", product_config_code="PS00"),
        _build_failure(failure_id=3, product_number="t-3", product_config_code=None),
    ]
    grouped = science_warehouse_service_module.ScienceWarehouseService.group_failures_by_dimension(
        failures
    )
    assert len(grouped) == 1
    key = next(iter(grouped))
    assert "_PS00_" in key
    assert len(grouped[key]) == 3


def test_small_sample_exponential_fit_ignores_non_responsible_dimension_group(
    monkeypatch,
) -> None:
    failures = [
        _build_failure(
            failure_id=1,
            product_number="train-a-1",
            product_config_code="A01",
        ),
        _build_failure(
            failure_id=2,
            product_number="train-a-2",
            product_config_code="A01",
        ),
        _build_failure(
            failure_id=101,
            product_number="train-b-1",
            product_config_code="B02",
            fault_material_code="P-002",
        ),
        _build_failure(
            failure_id=102,
            product_number="train-b-2",
            product_config_code="B02",
            fault_material_code="P-002",
        ),
    ]

    responsibility_calls = []

    async def _fake_exponential_fit_for_insufficient_data(
        model_part_failures,
        product_model,
        product_config_code,
        part_code,
        time_interval_days,
        input_date,
    ):
        if product_config_code == "A01":
            return 1.2
        return 2.1

    async def _fake_check_maintenance_responsibility(
        product_number, warehouse_code, spare_part_code
    ):
        responsibility_calls.append(product_number)
        return {"responsible": product_number.startswith("train-a")}

    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "exponential_fit_for_insufficient_data",
        staticmethod(_fake_exponential_fit_for_insufficient_data),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "check_maintenance_responsibility",
        staticmethod(_fake_check_maintenance_responsibility),
    )

    result = asyncio.run(
        science_warehouse_service_module.ScienceWarehouseService.perform_spare_calculation_with_fit(
            failures=failures,
            time_interval_days=180,
            input_date=date(2026, 4, 27),
            warehouse_code="WH-001",
            spare_part_code="SP-001",
        )
    )

    assert result["success"] is True
    assert result["quantity"] == 2
    assert sorted(responsibility_calls) == [
        "train-a-1",
        "train-a-2",
        "train-b-1",
        "train-b-2",
    ]
    assert result["maintenance_analysis"]["responsible_products"] == 2
    assert result["maintenance_analysis"]["non_responsible_products"] == 2
    assert result["maintenance_analysis"]["exponential_fit_success_count"] == 1


def test_small_sample_exponential_fit_checks_unique_products_once_per_dimension(
    monkeypatch,
) -> None:
    failures = [
        _build_failure(
            failure_id=1,
            product_number="train-a-1",
            product_config_code="A01",
        ),
        _build_failure(
            failure_id=2,
            product_number="train-a-1",
            product_config_code="A01",
        ),
        _build_failure(
            failure_id=3,
            product_number="train-a-2",
            product_config_code="A01",
        ),
    ]

    responsibility_calls = []

    async def _fake_exponential_fit_for_insufficient_data(
        model_part_failures,
        product_model,
        product_config_code,
        part_code,
        time_interval_days,
        input_date,
    ):
        return 2.1

    async def _fake_check_maintenance_responsibility(
        product_number, warehouse_code, spare_part_code
    ):
        responsibility_calls.append(product_number)
        return {"responsible": True}

    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "exponential_fit_for_insufficient_data",
        staticmethod(_fake_exponential_fit_for_insufficient_data),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "check_maintenance_responsibility",
        staticmethod(_fake_check_maintenance_responsibility),
    )

    result = asyncio.run(
        science_warehouse_service_module.ScienceWarehouseService.perform_spare_calculation_with_fit(
            failures=failures,
            time_interval_days=180,
            input_date=date(2026, 4, 27),
            warehouse_code="WH-001",
            spare_part_code="SP-001",
        )
    )

    assert result["success"] is True
    assert result["quantity"] == 3
    assert sorted(responsibility_calls) == ["train-a-1", "train-a-2"]
    assert result["maintenance_analysis"]["responsible_products"] == 2
    assert result["maintenance_analysis"]["non_responsible_products"] == 0
    assert result["maintenance_analysis"]["exponential_fit_success_count"] == 1


def test_calculate_spare_quantity_by_interval_queries_product_with_product_config_code(
    monkeypatch,
) -> None:
    captured = {}

    failures = [
        _build_failure(
            failure_id=1,
            product_number="train-a-1",
            product_config_code="A01",
        )
    ]

    async def _fake_get_by_model(db, product_model, product_config_code=None):
        captured["product_model"] = product_model
        captured["product_config_code"] = product_config_code
        return SimpleNamespace(year_days=365, avg_worktime=1)

    async def _fake_select_models(db, identifier__in=None, repair_level__eq=None):
        return [SimpleNamespace(identifier="train-a-1", life_cycle_time=date(2026, 4, 1))]

    class _SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        science_warehouse_service_module,
        "async_db_session",
        lambda: _SessionContext(),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.product_dao,
        "get_by_model",
        _fake_get_by_model,
    )
    monkeypatch.setattr(
        science_warehouse_service_module.despatch_dao,
        "select_models",
        _fake_select_models,
    )
    monkeypatch.setattr(
        science_warehouse_service_module,
        "convert_to_pydantic_model",
        lambda data, _: data,
        raising=False,
    )

    class _Distribution:
        @staticmethod
        def cdf(value):
            return value

    asyncio.run(
        science_warehouse_service_module.ScienceWarehouseService.calculate_spare_quantity_by_interval(
            best_distribution=_Distribution(),
            time_interval_days=1,
            product_failures=failures,
            input_date=date(2026, 4, 27),
        )
    )

    assert captured["product_model"] == "CR400AF"
    assert captured["product_config_code"] == "A01"


def test_get_or_create_aaron_distribution_reads_then_creates(monkeypatch) -> None:
    lookups = []
    creates = []

    async def _fake_get_part_distribution(*args, **kwargs):
        lookups.append(kwargs)
        if not creates:
            return None
        return "aaron-dist"

    class _FakePartFitService:
        async def create(self, obj):
            creates.append(obj)

    monkeypatch.setattr(
        science_warehouse_service_module.distribute_service,
        "get_part_distribution",
        _fake_get_part_distribution,
    )
    monkeypatch.setattr(
        science_warehouse_service_module,
        "part_fit_service",
        _FakePartFitService(),
    )

    result = asyncio.run(
        science_warehouse_service_module.ScienceWarehouseService.get_or_create_aaron_distribution(
            product_model="CR400AF",
            part_code="P-001",
            product_config_code="",
            input_date=date(2025, 12, 30),
        )
    )

    assert result == "aaron-dist"
    assert creates[0].product_config_code == "PS00"
    assert creates[0].input_date == "2025-12-30"
    assert creates[0].model == "CR400AF"
    assert creates[0].part == "P-001"
    assert len(lookups) == 3


def test_calculate_science_warehouse_defaults_cutoff_to_2025_12_30(monkeypatch) -> None:
    captured = {}

    async def _fake_get_all_warehouse_spare_list():
        return {}

    async def _fake_save_calculation_results(
        calculation_id,
        results,
        statistics,
        time_interval_days,
        input_date,
        product_model=None,
        product_config_code=None,
    ):
        captured["input_date"] = input_date

    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "get_all_warehouse_spare_list",
        staticmethod(_fake_get_all_warehouse_spare_list),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "save_calculation_results",
        staticmethod(_fake_save_calculation_results),
    )

    asyncio.run(
        science_warehouse_service_module.ScienceWarehouseService.calculate_science_warehouse_requirements(
            time_interval_days=180,
            input_date=None,
        )
    )

    assert captured["input_date"] == date(2025, 12, 30)
