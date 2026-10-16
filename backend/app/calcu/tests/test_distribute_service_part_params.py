import asyncio

from backend.app.calcu.service import distribute_service as distribute_module
from backend.app.fit.schema.fit_param import FitCheckType, FitMethodType


class _SessionContext:
    async def __aenter__(self):
        return "db"

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_part_distribution_params_passes_distribution_and_config_correctly(monkeypatch) -> None:
    captured = {}

    async def _fake_get(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "row"

    monkeypatch.setattr(distribute_module, "async_db_session", lambda: _SessionContext())
    monkeypatch.setattr(
        distribute_module.fit_part_dao, "get_by_model_and_part_and_distribution", _fake_get
    )

    result = asyncio.run(
        distribute_module.DistributeService.get_part_distribution_params(
            "M", "P", "PS00", "Weibull_2P", source=True
        )
    )

    assert result == "row"
    assert captured["args"] == ("db", "M", "P", "Weibull_2P")
    assert captured["kwargs"] == {
        "method": FitMethodType.MLE,
        "check": FitCheckType.BIC,
        "source": True,
        "product_config_code": "PS00",
    }
