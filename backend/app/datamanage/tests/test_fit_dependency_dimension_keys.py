import asyncio

from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.app.datamanage.crud.crud_repair import repair_dao
from backend.app.datamanage.schema.despatch import GetDespatchDetails
from backend.app.datamanage.schema.ebom import GetEbomDetails
from backend.app.datamanage.schema.failure import GetFailureDetails
from backend.app.datamanage.schema.repair import GetRepairDetails


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

    def scalar_one_or_none(self):
        return self._values[0] if self._values else None


class _FakeSession:
    def __init__(self):
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _FakeResult()


def test_despatch_schema_exposes_product_config_code() -> None:
    payload = GetDespatchDetails.model_validate(
        {
            "id": 1,
            "model": "CR400AF",
            "product_config_code": "A01",
            "identifier": "1001",
            "repair_level": "新造",
            "life_cycle_time": "2026-04-01",
        }
    )
    assert payload.product_config_code == "A01"


def test_ebom_schema_exposes_product_config_code() -> None:
    payload = GetEbomDetails.model_validate(
        {
            "id": "node-1",
            "prd_no": "CR400AF",
            "product_config_code": "A01",
        }
    )
    assert payload.product_config_code == "A01"


def test_repair_schema_exposes_product_config_code() -> None:
    payload = GetRepairDetails.model_validate(
        {
            "id": 1,
            "model": "CR400AF",
            "product_config_code": "A01",
        }
    )
    assert payload.product_config_code == "A01"


def test_failure_schema_exposes_is_warranty_fault() -> None:
    payload = GetFailureDetails.model_validate(
        {
            "pk": 1,
            "report_id": "R-1",
            "is_warranty_fault": "Y",
        }
    )
    assert payload.is_warranty_fault == "Y"


def test_despatch_query_keys_by_product_config_code() -> None:
    async def _run() -> str:
        db = _FakeSession()
        await despatch_dao.get_despatchs_by_model(
            db,
            model="CR400AF",
            product_config_code="A01",
        )
        return _compile_sql(db.statements[-1])

    sql = asyncio.run(_run())

    assert "product_config_code" in sql
    assert "dm_despatch" in sql


def test_ebom_query_keys_by_product_config_code() -> None:
    async def _run() -> str:
        db = _FakeSession()
        await ebom_dao.get_by_model_and_part(
            db,
            model="CR400AF",
            product_config_code="A01",
            part="P-001",
        )
        return _compile_sql(db.statements[-1])

    sql = asyncio.run(_run())

    assert "product_config_code" in sql
    assert "dm_ebom" in sql


def test_repair_query_keys_by_product_config_code() -> None:
    async def _run() -> str:
        db = _FakeSession()
        await repair_dao.get_by_model(
            db,
            model="CR400AF",
            product_config_code="A01",
        )
        return _compile_sql(db.statements[-1])

    sql = asyncio.run(_run())

    assert "product_config_code" in sql
    assert "dm_repair" in sql
