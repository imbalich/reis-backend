import asyncio

from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.fit.crud.crud_fit_product import fit_product_dao
from backend.app.fit.schema.fit_param import (
    CreatePartDistributionParam,
    CreateProductDistributionParam,
    FitCheckType,
    FitMethodType,
)


def _compile_sql(stmt) -> str:
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


class _FakeScalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values

    def first(self):
        return self._values[0] if self._values else None


class _FakeResult:
    def __init__(self, values=None):
        self._values = values or []

    def scalars(self):
        return _FakeScalars(self._values)


class _FakeSession:
    def __init__(self):
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _FakeResult()


def test_fit_product_distribution_payload_contains_dimension_key() -> None:
    payload = CreateProductDistributionParam(
        group_id="group-1",
        model="CR400AF",
        product_config_code="A01",
        input_date="2026-04-01",
        method=FitMethodType.MLE,
        distribution="Weibull_2P",
        source=False,
    )

    assert payload.product_config_code == "A01"


def test_fit_part_distribution_payload_contains_dimension_key() -> None:
    payload = CreatePartDistributionParam(
        group_id="group-1",
        model="CR400AF",
        product_config_code="A01",
        part="P-001",
        input_date="2026-04-01",
        method=FitMethodType.MLE,
        distribution="Weibull_2P",
        source=False,
    )

    assert (payload.model, payload.product_config_code, payload.part) == ("CR400AF", "A01", "P-001")


def test_fit_product_latest_group_query_keys_by_product_config_code() -> None:
    async def _run() -> str:
        db = _FakeSession()
        await fit_product_dao.get_by_model(
            db,
            model="CR400AF",
            product_config_code="A01",
            input_date="2026-04-01",
            method=FitMethodType.MLE,
            check=FitCheckType.BIC,
            source=False,
        )
        return _compile_sql(db.statements[-1])

    sql = asyncio.run(_run())

    assert "product_config_code" in sql
    assert "fit_product" in sql


def test_fit_product_best_result_query_keys_by_product_config_code() -> None:
    async def _run() -> str:
        db = _FakeSession()
        await fit_product_dao.get_by_model_and_distribution(
            db,
            model="CR400AF",
            product_config_code="A01",
            distribution="Weibull_2P",
            input_date="2026-04-01",
            method=FitMethodType.MLE,
            check=FitCheckType.BIC,
            source=False,
        )
        return _compile_sql(db.statements[-1])

    sql = asyncio.run(_run())

    assert "product_config_code" in sql
    assert "fit_product" in sql


def test_fit_part_latest_group_query_keys_by_product_config_code_and_part() -> None:
    async def _run() -> str:
        db = _FakeSession()
        await fit_part_dao.get_by_model_and_part(
            db,
            model="CR400AF",
            product_config_code="A01",
            part="P-001",
            input_date="2026-04-01",
            method=FitMethodType.MLE,
            check=FitCheckType.BIC,
            source=False,
        )
        return _compile_sql(db.statements[-1])

    sql = asyncio.run(_run())

    assert "product_config_code" in sql
    assert "part" in sql


def test_fit_part_best_result_query_keys_by_product_config_code_and_part() -> None:
    async def _run() -> str:
        db = _FakeSession()
        await fit_part_dao.get_by_model_and_part_and_distribution(
            db,
            model="CR400AF",
            product_config_code="A01",
            part="P-001",
            distribution="Weibull_2P",
            input_date="2026-04-01",
            method=FitMethodType.MLE,
            check=FitCheckType.BIC,
            source=False,
        )
        return _compile_sql(db.statements[-1])

    sql = asyncio.run(_run())

    assert "product_config_code" in sql
    assert "part" in sql
