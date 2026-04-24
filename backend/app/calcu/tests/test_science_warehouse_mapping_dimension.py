import asyncio

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
