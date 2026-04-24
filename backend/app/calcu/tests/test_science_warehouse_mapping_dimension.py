import asyncio

from backend.app.calcu.service import science_warehouse_service as science_warehouse_service_module


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
