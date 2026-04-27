import asyncio
from datetime import date
from types import SimpleNamespace

from backend.app.calcu.service import science_warehouse_service as science_warehouse_service_module
from backend.app.datamanage.crud.crud_part_spare_mapping import CRUDPartSpareMapping
from backend.app.datamanage.model.part_spare_mapping import PartSpareMapping


class _Sentinel:
    pass


def test_get_part_spare_mapping_passes_product_config_code(monkeypatch) -> None:
    captured = {}

    async def _fake_get_by_original_part_code(
        db, product_model, product_config_code, original_part_code
    ):
        captured["db"] = db
        captured["product_model"] = product_model
        captured["product_config_code"] = product_config_code
        captured["original_part_code"] = original_part_code
        return {"matched": True}

    monkeypatch.setattr(
        science_warehouse_service_module.part_spare_mapping_dao,
        "get_by_original_part_code",
        _fake_get_by_original_part_code,
    )

    class _SessionContext:
        async def __aenter__(self):
            return _Sentinel()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        science_warehouse_service_module,
        "async_db_session",
        lambda: _SessionContext(),
    )

    result = asyncio.run(
        science_warehouse_service_module.ScienceWarehouseService.get_part_spare_mapping(
            "CR400AF",
            "A01",
            "P-001",
        )
    )

    assert result == {"matched": True}
    assert captured["product_model"] == "CR400AF"
    assert captured["product_config_code"] == "A01"
    assert captured["original_part_code"] == "P-001"


def test_part_spare_mapping_model_exposes_product_config_code() -> None:
    assert hasattr(PartSpareMapping, "product_config_code")
    assert not hasattr(PartSpareMapping, "derived_code")


def test_part_spare_mapping_select_filters_product_config_code() -> None:
    async def _run():
        crud = CRUDPartSpareMapping(PartSpareMapping)
        return await crud.get_select(product_config_code="A01")

    stmt = asyncio.run(_run())
    sql = str(stmt)

    assert "product_config_code" in sql
    assert "derived_code" not in sql


def test_calculate_spare_requirement_uses_failure_product_config_code(monkeypatch) -> None:
    captured = {}

    async def _fake_get_warehouse_allotments(warehouse_code):
        return ["BJ"]

    async def _fake_get_models_using_spare(spare_part_code):
        return ["CR400AF"]

    async def _fake_get_products_by_allotment_two_and_models(
        allotment_two, related_models
    ):
        return ["train-1"]

    async def _fake_get_failures_by_product_number(product_number):
        return [
            SimpleNamespace(
                id=1,
                product_number=product_number,
                discovery_date="2026-04-01",
                product_model="CR400AF",
                product_config_code="A01",
                fault_material_code="P-001",
            )
        ]

    async def _fake_get_part_spare_mapping(
        product_model, product_config_code, original_part_code
    ):
        captured["product_model"] = product_model
        captured["product_config_code"] = product_config_code
        captured["original_part_code"] = original_part_code
        return SimpleNamespace(spare_part_code="SP-001")

    async def _fake_perform_spare_calculation_with_fit(*args, **kwargs):
        return {
            "success": True,
            "quantity": 2,
            "confidence": 0.9,
            "maintenance_analysis": {},
        }

    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "get_warehouse_allotments",
        staticmethod(_fake_get_warehouse_allotments),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "get_models_using_spare",
        staticmethod(_fake_get_models_using_spare),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "get_products_by_allotment_two_and_models",
        staticmethod(_fake_get_products_by_allotment_two_and_models),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "get_failures_by_product_number",
        staticmethod(_fake_get_failures_by_product_number),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "get_part_spare_mapping",
        staticmethod(_fake_get_part_spare_mapping),
    )
    monkeypatch.setattr(
        science_warehouse_service_module.ScienceWarehouseService,
        "perform_spare_calculation_with_fit",
        staticmethod(_fake_perform_spare_calculation_with_fit),
    )

    result = asyncio.run(
        science_warehouse_service_module.ScienceWarehouseService.calculate_spare_requirement_with_coverage(
            warehouse_code="WH-001",
            spare_part={"part_code": "SP-001", "part_name": "spare", "default_quantity": 1},
            time_interval_days=180,
            input_date=date(2026, 4, 27),
        )
    )

    assert result["calculated"] is True
    assert captured == {
        "product_model": "CR400AF",
        "product_config_code": "A01",
        "original_part_code": "P-001",
    }
