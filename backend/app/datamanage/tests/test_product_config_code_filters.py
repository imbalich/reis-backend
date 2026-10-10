from types import SimpleNamespace

from backend.common.product_config import (
    DEFAULT_PRODUCT_CONFIG_CODE,
    normalize_product_config_code,
    product_config_codes_equal,
)
from backend.app.datamanage.service.product_service import _deduplicate_dimension_pairs


def test_normalize_product_config_code_maps_empty_and_null_to_ps00() -> None:
    assert normalize_product_config_code(None) == DEFAULT_PRODUCT_CONFIG_CODE
    assert normalize_product_config_code("") == DEFAULT_PRODUCT_CONFIG_CODE
    assert normalize_product_config_code("   ") == DEFAULT_PRODUCT_CONFIG_CODE
    assert normalize_product_config_code("A01") == "A01"


def test_product_config_codes_equal_treats_empty_as_ps00() -> None:
    assert product_config_codes_equal("", "PS00")
    assert product_config_codes_equal(None, "PS00")
    assert product_config_codes_equal("  ", None)
    assert not product_config_codes_equal("A01", "PS00")


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
