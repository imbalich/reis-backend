import asyncio
from datetime import date

from backend.app.calcu.service import science_warehouse_service_change as service_module
from backend.app.task.tasks.science_warehouse_task import tasks as task_module
from backend.common.exception.errors import FailureCheckError


def test_enough_samples_use_aaron_instead_of_old_curve(monkeypatch) -> None:
    calls = []

    async def _fake_part_tag_process(*args, **kwargs):
        calls.append(("tags", kwargs.get("product_config_code")))
        return [[1, 2, 3]]

    async def _fake_get_or_create(model, part, input_date, product_config_code):
        calls.append((model, part, input_date, product_config_code))
        return "aaron-distribution"

    monkeypatch.setattr(
        service_module.part_strategy_service,
        "part_tag_process",
        _fake_part_tag_process,
    )
    monkeypatch.setattr(
        service_module.ScienceWarehouseServiceChange,
        "_get_or_create_aaron_distribution",
        staticmethod(_fake_get_or_create),
    )

    distribution, fit_type = asyncio.run(
        service_module.ScienceWarehouseServiceChange.get_distribution_by_model_and_part(
            "CR400AF",
            "P-001",
            date(2025, 12, 30),
            product_config_code="",
        )
    )

    assert distribution == "aaron-distribution"
    assert fit_type == "fitted"
    assert calls[0] == ("tags", "PS00")
    assert calls[1] == ("CR400AF", "P-001", date(2025, 12, 30), "PS00")


def test_small_sample_keeps_exponential_path(monkeypatch) -> None:
    aaron_called = []

    async def _fake_part_tag_process(*args, **kwargs):
        raise FailureCheckError(msg="故障数量不足")

    async def _fake_get_or_create(*args, **kwargs):
        aaron_called.append(True)
        return "should-not-run"

    async def _fake_get_by_model_and_part(*args, **kwargs):
        return [object(), object()]

    async def _fake_total_run_time(*args, **kwargs):
        return 10

    class _SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(service_module, "async_db_session", lambda: _SessionContext())
    monkeypatch.setattr(
        service_module.part_strategy_service,
        "part_tag_process",
        _fake_part_tag_process,
    )
    monkeypatch.setattr(
        service_module.ScienceWarehouseServiceChange,
        "_get_or_create_aaron_distribution",
        staticmethod(_fake_get_or_create),
    )
    monkeypatch.setattr(
        service_module.fit_part_dao,
        "get_by_model_and_part",
        _fake_get_by_model_and_part,
    )
    monkeypatch.setattr(
        service_module.datacheckutils,
        "total_run_time",
        _fake_total_run_time,
    )

    distribution, fit_type = asyncio.run(
        service_module.ScienceWarehouseServiceChange.get_distribution_by_model_and_part(
            "CR400AF",
            "P-001",
            date(2025, 12, 30),
        )
    )

    assert fit_type == "exponential_fit"
    assert distribution is not None
    assert aaron_called == []


def test_calculation_task_uses_original_batch_flow(monkeypatch) -> None:
    captured = {}

    class _Inventory:
        warehouse_code = "WH-001"
        part_code = "SP-001"

    class _SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _fake_get_all(db):
        return [_Inventory(), _Inventory()]

    async def _fake_batch(**kwargs):
        captured.update(kwargs)
        return {
            "calculation_id": "SW_1",
            "total_pairs": 1,
            "success_count": 1,
            "failed_count": 0,
        }

    monkeypatch.setattr(task_module, "async_db_session", lambda: _SessionContext())
    monkeypatch.setattr(task_module.warehouse_inventory_dao, "get_all", _fake_get_all)
    monkeypatch.setattr(
        task_module.ScienceWarehouseServiceChange,
        "batch_warehouse_spare_calculate",
        staticmethod(_fake_batch),
    )

    result = asyncio.run(task_module.science_warehouse_calculation_task(180, None))

    assert "SW_1" in result
    assert captured["input_date"] == date(2025, 12, 30)
    assert captured["warehouse_spare_pairs"] == [("WH-001", "SP-001")]
    assert captured["save_to_db"] is True
