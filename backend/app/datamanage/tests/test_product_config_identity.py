from backend.app.datamanage.model.failure import Failure
from backend.app.datamanage.model.product import Product


def test_failure_model_exposes_product_config_code() -> None:
    assert hasattr(Failure, "product_config_code")


def test_product_model_exposes_product_config_code() -> None:
    assert hasattr(Product, "product_config_code")
