import asyncio
import inspect
from io import BytesIO

import pandas as pd

from backend.app.datamanage.api.v1.datamanage.part_spare_mapping import (
    get_pagination_part_spare_mapping,
)
from backend.app.datamanage.schema.part_spare_mapping import (
    GetPartSpareMappingDetails,
    PartSpareMappingExcelImportRow,
    PartSpareMappingFilterParam,
)
from backend.app.datamanage.service import (
    part_spare_mapping_service as part_spare_mapping_service_module,
)


def test_part_spare_mapping_schemas_expose_product_config_code_only() -> None:
    for schema in (
        GetPartSpareMappingDetails,
        PartSpareMappingFilterParam,
        PartSpareMappingExcelImportRow,
    ):
        assert "product_config_code" in schema.model_fields
        assert "derived_code" not in schema.model_fields


def test_part_spare_mapping_api_uses_product_config_code_query_param() -> None:
    params = inspect.signature(get_pagination_part_spare_mapping).parameters

    assert "product_config_code" in params
    assert "derived_code" not in params


def test_part_spare_mapping_service_get_select_passes_product_config_code(
    monkeypatch,
) -> None:
    captured = {}

    async def _fake_get_select(**kwargs):
        captured.update(kwargs)
        return "stmt"

    monkeypatch.setattr(
        part_spare_mapping_service_module.part_spare_mapping_dao,
        "get_select",
        _fake_get_select,
    )

    result = asyncio.run(
        part_spare_mapping_service_module.part_spare_mapping_service.get_select(
            product_model="CR400AF",
            product_config_code="A01",
            original_part_code="P-001",
        )
    )

    assert result == "stmt"
    assert captured["product_config_code"] == "A01"
    assert "derived_code" not in captured


def test_part_spare_mapping_import_writes_product_config_code(monkeypatch) -> None:
    captured = {}

    async def _fake_clear_all(db):
        captured["cleared"] = True

    async def _fake_bulk_create(db, mapping_data):
        captured["mapping_data"] = mapping_data
        return []

    class _SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        part_spare_mapping_service_module.part_spare_mapping_dao,
        "clear_all",
        _fake_clear_all,
    )
    monkeypatch.setattr(
        part_spare_mapping_service_module.part_spare_mapping_dao,
        "bulk_create",
        _fake_bulk_create,
    )
    monkeypatch.setattr(
        part_spare_mapping_service_module,
        "async_db_session",
        lambda: _SessionContext(),
    )

    dataframe = pd.DataFrame(
        [
            {
                "产品型号": "CR400AF",
                "派生码": "A01",
                "零部件名称（原装）": "原件",
                "零部件物料编码（原装）": "P-001",
                "零部件名称（备品）": "备件",
                "零部件物料编码（备品）": "SP-001",
                "创建人": "tester",
                "更新时间": "2026-04-27",
            }
        ]
    )
    buffer = BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        dataframe.to_excel(writer, sheet_name="配置表", index=False)

    result = asyncio.run(
        part_spare_mapping_service_module.part_spare_mapping_service.import_from_excel(
            buffer.getvalue()
        )
    )

    assert result.success_rows == 1
    assert captured["cleared"] is True
    assert captured["mapping_data"][0]["product_config_code"] == "A01"
    assert "derived_code" not in captured["mapping_data"][0]
