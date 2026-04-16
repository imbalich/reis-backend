from types import SimpleNamespace

from backend.app.datamanage.service.product_service import _deduplicate_dimension_pairs


def test_get_product_model_and_config_pairs_deduplicate_by_new_dimension() -> None:
    rows = [
        SimpleNamespace(model="CR400AF", product_config_code="A01"),
        SimpleNamespace(model="CR400AF", product_config_code="A01"),
        SimpleNamespace(model="CR400AF", product_config_code="B02"),
    ]
    pairs = _deduplicate_dimension_pairs(rows)
    assert set(map(tuple, pairs)) == {
        ("CR400AF", "A01"),
        ("CR400AF", "B02"),
    }
