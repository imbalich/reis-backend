import asyncio
import math
from datetime import date
from types import SimpleNamespace

import pytest
from reliability.Distributions import Exponential_Distribution

from backend.app.calcu.service import science_warehouse_service_change as service_module
from backend.app.task.tasks.science_warehouse_task import tasks as task_module

Service = service_module.ScienceWarehouseServiceChange


class _SessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _exp_delta(lam: float, t0: float, t1: float) -> float:
    return math.exp(-lam * t0) - math.exp(-lam * t1)


def _patch_context_sources(monkeypatch, failure_count: int, bl_quantity: int = 2):
    calls = {}

    async def _fake_despatchs(db, model, product_config_code=None):
        calls["despatch_config"] = product_config_code
        return []

    async def _fake_failures(db, model, part, input_date, product_config_code=None):
        calls["failure_config"] = product_config_code
        return [
            {
                "product_number": f"P{i}",
                "manufacturing_date": "2020-01-01",
                "product_lifetime_stage": "新造",
                "discovery_date": "2022-01-01",
            }
            for i in range(failure_count)
        ]

    async def _fake_ebom(db, model, product_config_code, part):
        return [object()]

    async def _fake_product(db, model, product_config_code=None):
        calls["product_config"] = product_config_code
        return {
            "id": 1, "sub_saet": "S", "model": model,
            "avg_worktime": 20, "avg_speed": None, "year_days": 365,
        }

    monkeypatch.setattr(service_module, "async_db_session", lambda: _SessionContext())
    monkeypatch.setattr(service_module.despatch_dao, "get_despatchs_by_model", _fake_despatchs)
    monkeypatch.setattr(service_module.failure_dao, "get_by_model_and_part", _fake_failures)
    monkeypatch.setattr(service_module, "get_ebom_tree_with_parents", _fake_ebom)
    monkeypatch.setattr(service_module, "convert_to_total_quantity", lambda rows, part: bl_quantity)
    monkeypatch.setattr(service_module.product_dao, "get_by_model", _fake_product)
    return calls


def test_mapping_dedupe_keeps_each_product_config_code(monkeypatch) -> None:
    def _row(config):
        return SimpleNamespace(
            product_model="M", product_config_code=config,
            original_part_name="件", original_part_code="P",
            spare_part_name="备", spare_part_code="S",
            created_by=None, changed_time=None,
        )

    async def _fake_get(db, spare_part_code):
        return [_row(None), _row("PS00"), _row("PS01")]

    monkeypatch.setattr(service_module, "async_db_session", lambda: _SessionContext())
    monkeypatch.setattr(service_module.part_spare_mapping_dao, "get_by_spare_part_code", _fake_get)

    mappings = asyncio.run(Service.get_spare_models_by_spare_part_code("S"))

    assert [m["product_config_code"] for m in mappings] == ["PS00", "PS01"]


def test_build_units_expands_bom_and_uses_earliest_life_start() -> None:
    despatch = [
        {"model": "M", "identifier": "A", "life_cycle_time": date(2020, 1, 1)},
        {"model": "M", "identifier": "B", "life_cycle_time": date(2021, 1, 1)},
    ]
    failures = [
        {
            "product_number": "B",
            "manufacturing_date": "2020-06-01",
            "product_lifetime_stage": "新造",
            "discovery_date": "2022-01-01",
        }
    ]

    units = service_module.build_units_by_product("M", despatch, failures, 4)

    assert units["A"] == [date(2020, 1, 1)] * 4
    assert units["B"] == [date(2020, 6, 1)] * 4


def test_quantity_counts_every_bom_position() -> None:
    lam = 1e-4
    distribution = Exponential_Distribution(Lambda=lam)
    input_date = date(2025, 1, 1)
    life_start = date(2024, 1, 1)
    units = {"A": [life_start] * 4, "B": [life_start] * 4}

    quantity = Service.calculate_spare_quantity_by_units(
        distribution, units, ["A"], 10.0, input_date, 100
    )

    t0 = (input_date - life_start).days * 10.0
    assert quantity == pytest.approx(4 * _exp_delta(lam, t0, t0 + 1000.0))


def test_enough_failures_use_cached_aaron_distribution(monkeypatch) -> None:
    calls = _patch_context_sources(monkeypatch, failure_count=5)
    called = []

    async def _fake_get_or_create(model, part, input_date, product_config_code):
        called.append((model, part, input_date, product_config_code))
        return Exponential_Distribution(Lambda=1e-5)

    monkeypatch.setattr(Service, "_get_or_create_aaron_distribution", staticmethod(_fake_get_or_create))

    context = asyncio.run(Service.get_mapping_context("M", "", "P", date(2025, 12, 30)))

    assert context["fit_type"] == "fitted"
    assert called == [("M", "P", date(2025, 12, 30), "PS00")]
    assert calls == {"despatch_config": "PS00", "failure_config": "PS00", "product_config": "PS00"}
    assert context["bl_quantity"] == 2
    assert context["hours_per_day"] == pytest.approx(20.0)
    assert all(len(v) == 2 for v in context["units_by_product"].values())


def test_small_sample_uses_aaron_exponential_rate(monkeypatch) -> None:
    _patch_context_sources(monkeypatch, failure_count=3)
    none_tag_calls = []

    async def _fake_none_tag_fit(db, model, part, input_date, product_config_code=None):
        none_tag_calls.append(product_config_code)
        return 0.001

    async def _should_not_run(*args, **kwargs):
        raise AssertionError("样本不足时不应走 Aaron 拟合")

    monkeypatch.setattr(service_module.aaron_part_fit_service, "none_tag_fit", _fake_none_tag_fit)
    monkeypatch.setattr(Service, "_get_or_create_aaron_distribution", staticmethod(_should_not_run))

    context = asyncio.run(Service.get_mapping_context("M", None, "P", date(2025, 12, 30)))

    assert context["fit_type"] == "exponential_fit"
    assert context["distribution"].Lambda == pytest.approx(0.001)
    assert none_tag_calls == ["PS00"]


def test_use_cached_fit_false_fits_in_memory(monkeypatch) -> None:
    _patch_context_sources(monkeypatch, failure_count=6)

    async def _fake_tags(model, part, input_date, product_config_code=None):
        return [["A", "A-1", date(2020, 1, 1), "2022-01-01", 700, 1000.0, "failure"]]

    async def _fake_tag_fit(tags, method):
        return SimpleNamespace(best_distribution=Exponential_Distribution(Lambda=2e-5))

    async def _should_not_run(*args, **kwargs):
        raise AssertionError("测试口径不应读写 fit_part")

    monkeypatch.setattr(service_module.aaron_part_strategy_service, "part_tag_process", _fake_tags)
    monkeypatch.setattr(service_module.aaron_part_fit_service, "tag_fit", _fake_tag_fit)
    monkeypatch.setattr(Service, "_get_or_create_aaron_distribution", staticmethod(_should_not_run))

    context = asyncio.run(
        Service.get_mapping_context("M", "PS00", "P", date(2025, 12, 30), use_cached_fit=False)
    )

    assert context["fit_type"] == "fitted"
    assert context["distribution"].Lambda == pytest.approx(2e-5)


def test_single_calculation_filters_products_by_config(monkeypatch) -> None:
    lam = 1e-4
    input_date = date(2025, 12, 30)
    life_start = date(2024, 12, 30)
    distribution = Exponential_Distribution(Lambda=lam)

    async def _fake_spare(warehouse_code, spare_part_code):
        return SimpleNamespace(warehouse_name="库房", part_name="备品")

    async def _fake_mappings(spare_part_code):
        return [
            {"product_model": "M", "product_config_code": config, "original_part_code": "P"}
            for config in ("PS00", "PS01")
        ]

    async def _fake_allotments(warehouse_code):
        return ["A2"]

    async def _fake_products(allotment_two, model):
        return ["P1", "P2", "P3"]

    async def _fake_failure_count(*args, **kwargs):
        return 0

    async def _fake_context(model, product_config_code, part, input_date, use_cached_fit=True, cache=None):
        units = {"PS00": {"P1": [life_start] * 4}, "PS01": {"P2": [life_start] * 2}}
        return {
            "units_by_product": units[product_config_code],
            "bl_quantity": 4 if product_config_code == "PS00" else 2,
            "hours_per_day": 10.0,
            "failure_count": 9,
            "distribution": distribution,
            "distribution_name": "Exponential",
            "fit_type": "fitted",
            "error": None,
        }

    monkeypatch.setattr(Service, "get_single_warehouse_spare", staticmethod(_fake_spare))
    monkeypatch.setattr(Service, "get_spare_models_by_spare_part_code", staticmethod(_fake_mappings))
    monkeypatch.setattr(Service, "get_allotments_by_warehouse_code", staticmethod(_fake_allotments))
    monkeypatch.setattr(Service, "get_products_by_allotment_two_and_model", staticmethod(_fake_products))
    monkeypatch.setattr(
        Service, "get_failure_count_by_model_and_part_in_products", staticmethod(_fake_failure_count)
    )
    monkeypatch.setattr(Service, "get_mapping_context", staticmethod(_fake_context))

    result = asyncio.run(Service.single_warehouse_single_spare_calculate(180, input_date, "WH", "S"))

    details = result["statistics"]["mapping_details"]
    assert [(d["product_config_code"], d["product_count"], d["unit_count"]) for d in details] == [
        ("PS00", 1, 4),
        ("PS01", 1, 2),
    ]
    t0 = (input_date - life_start).days * 10.0
    expected = 6 * _exp_delta(lam, t0, t0 + 1800.0)
    assert float(result["quantity"]) == pytest.approx(expected, abs=1e-5)


def test_calculation_task_uses_original_batch_flow(monkeypatch) -> None:
    captured = {}

    class _Inventory:
        warehouse_code = "WH-001"
        part_code = "SP-001"

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
