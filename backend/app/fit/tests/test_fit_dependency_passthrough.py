import asyncio

from backend.app.fit.utils import convert_model


class _Sentinel:
    pass


def test_get_ebom_tree_with_parents_passes_product_config_code(monkeypatch) -> None:
    captured = {}

    async def _fake_get_by_model_and_part(db, model, product_config_code, part):
        captured["model"] = model
        captured["product_config_code"] = product_config_code
        captured["part"] = part
        return []

    monkeypatch.setattr(
        convert_model.ebom_dao,
        "get_by_model_and_part",
        _fake_get_by_model_and_part,
    )

    async def _run() -> None:
        await convert_model.get_ebom_tree_with_parents(
            _Sentinel(),
            "CR400AF",
            "A01",
            "P-001",
        )

    asyncio.run(_run())

    assert captured == {
        "model": "CR400AF",
        "product_config_code": "A01",
        "part": "P-001",
    }
