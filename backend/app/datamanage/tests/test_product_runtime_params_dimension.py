import asyncio

from backend.app.datamanage.service import product_service as product_service_module


class _Sentinel:
    pass


def test_get_run_time_parameters_passes_product_config_code(monkeypatch) -> None:
    captured = {}

    async def _fake_get_by_model(db, model, product_config_code=None):
        captured["db"] = db
        captured["model"] = model
        captured["product_config_code"] = product_config_code
        return type(
            "Product",
            (),
            {"year_days": 300, "avg_worktime": 12, "avg_speed": 80},
        )()

    monkeypatch.setattr(
        product_service_module.product_dao,
        "get_by_model",
        _fake_get_by_model,
    )

    class _SessionContext:
        async def __aenter__(self):
            return _Sentinel()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        product_service_module,
        "async_db_session",
        lambda: _SessionContext(),
    )

    result = asyncio.run(
        product_service_module.product_service.get_run_time_parameters(
            "YJ90A1",
            product_config_code="PS00",
        )
    )

    assert result == [300, 12, 80]
    assert captured["model"] == "YJ90A1"
    assert captured["product_config_code"] == "PS00"
