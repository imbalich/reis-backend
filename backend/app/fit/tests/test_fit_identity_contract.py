from backend.app.fit.schema.fit_param import CreateFitPartInParam, CreateFitProductInParam


def test_fit_product_input_requires_product_config_code() -> None:
    payload = CreateFitProductInParam.model_validate(
        {
            "model": "CR400AF",
            "product_config_code": "A01",
            "input_date": "2026-04-01",
            "method": "MLE",
        }
    )
    assert payload.product_config_code == "A01"


def test_fit_part_input_requires_product_config_code() -> None:
    payload = CreateFitPartInParam.model_validate(
        {
            "model": "CR400AF",
            "product_config_code": "A01",
            "part": "P-001",
            "input_date": "2026-04-01",
            "method": "MLE",
        }
    )
    assert payload.product_config_code == "A01"
