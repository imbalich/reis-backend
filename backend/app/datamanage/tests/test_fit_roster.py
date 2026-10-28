#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import inspect
from io import BytesIO

import pandas as pd
import pytest

from backend.app.datamanage.api.v1.datamanage.fit_roster import get_pagination_fit_roster
from backend.app.datamanage.model.fit_roster import FitRoster
from backend.app.datamanage.schema.fit_roster import CreateFitRosterParam
from backend.app.datamanage.service.fit_roster_service import (
    diff_fit_roster,
    fit_roster_service,
    parse_fit_roster_excel,
)
from backend.common.exception import errors


def _workbook(rows: list[dict]) -> bytes:
    frame = pd.DataFrame(rows)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="寿命拟合名单", index=False)
    return buffer.getvalue()


def _row(model: str, part: str, name: str = "", family: str | None = None, config: str = "PS00"):
    return FitRoster(
        product_model=model,
        product_config_code=config,
        part_code=part,
        part_name=name,
        family=family,
    )


def test_fit_roster_api_uses_product_config_code() -> None:
    params = inspect.signature(get_pagination_fit_roster).parameters
    assert "product_config_code" in params
    assert "derived_code" not in params


def test_parse_normalizes_blank_config_and_numeric_part_code() -> None:
    content = _workbook(
        [
            {
                "产品型号": "YGZN2Q271",
                "派生码": None,
                "零部件物料编码": 622161,
                "零部件名称": "电压检测板",
                "族": "变流器",
            }
        ]
    )
    rows, parse_errors, total = parse_fit_roster_excel(content)
    assert parse_errors == []
    assert total == 1
    assert rows[0]["product_config_code"] == "PS00"
    assert rows[0]["part_code"] == "622161"
    assert rows[0]["family"] == "变流器"


def test_parse_rejects_duplicate_and_empty_file() -> None:
    duplicated = _workbook(
        [
            {"产品型号": "YJ85A", "派生码": "PS00", "零部件物料编码": "A"},
            {"产品型号": "YJ85A", "派生码": "", "零部件物料编码": "A"},
        ]
    )
    rows, parse_errors, _ = parse_fit_roster_excel(duplicated)
    assert rows == []
    assert any("重复" in item for item in parse_errors)

    empty = BytesIO()
    with pd.ExcelWriter(empty, engine="openpyxl") as writer:
        pd.DataFrame(columns=["产品型号", "零部件物料编码"]).to_excel(
            writer, sheet_name="寿命拟合名单", index=False
        )
    rows, parse_errors, _ = parse_fit_roster_excel(empty.getvalue())
    assert rows == []
    assert parse_errors


def test_diff_reports_add_remove_and_update() -> None:
    current = [
        _row("YGZN2Q271", "A", "旧名称", "变流器"),
        _row("YGZN2Q271", "B", "保留", "变流器"),
        _row("YJ85A", "C", "电机件", "电机"),
    ]
    incoming = [
        {
            "product_model": "YGZN2Q271",
            "product_config_code": "PS00",
            "part_code": "A",
            "part_name": "新名称",
            "family": "变流器",
            "created_by": None,
        },
        {
            "product_model": "YGZN2Q271",
            "product_config_code": "PS00",
            "part_code": "B",
            "part_name": "保留",
            "family": "变流器",
            "created_by": None,
        },
        {
            "product_model": "YGZN2Q239",
            "product_config_code": "PS00",
            "part_code": "D",
            "part_name": "新件",
            "family": "变流器",
            "created_by": None,
        },
    ]
    preview = diff_fit_roster(current, incoming)
    assert preview.can_replace is True
    assert [item.part_code for item in preview.to_add] == ["D"]
    assert [item.part_code for item in preview.to_remove] == ["C"]
    assert [item.part_code for item in preview.to_update] == ["A"]
    assert preview.to_update[0].current_part_name == "旧名称"
    assert preview.unchanged == 1


def test_preview_does_not_replace_when_file_is_invalid(monkeypatch) -> None:
    called = {"replace": False}

    async def _list_all():
        return []

    async def _replace_all(*_args, **_kwargs):
        called["replace"] = True

    monkeypatch.setattr(fit_roster_service, "list_all", _list_all)
    monkeypatch.setattr(
        "backend.app.datamanage.service.fit_roster_service.fit_roster_dao.replace_all",
        _replace_all,
    )

    async def _run():
        content = _workbook([{"产品型号": "", "零部件物料编码": ""}])
        preview = await fit_roster_service.preview_import(content)
        assert preview.can_replace is False
        with pytest.raises(errors.RequestError):
            await fit_roster_service.replace_import(content)

    import asyncio

    asyncio.run(_run())
    assert called["replace"] is False


def test_create_normalizes_config(monkeypatch) -> None:
    captured = {}

    class _Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_args):
            return False

    async def _get_by_key(*_args, **_kwargs):
        return None

    async def _create(_db, data):
        captured.update(data)
        return _row(data["product_model"], data["part_code"], config=data["product_config_code"])

    monkeypatch.setattr(
        "backend.app.datamanage.service.fit_roster_service.async_db_session",
        _Session,
    )
    monkeypatch.setattr(
        "backend.app.datamanage.service.fit_roster_service.fit_roster_dao.get_by_key",
        _get_by_key,
    )
    monkeypatch.setattr(
        "backend.app.datamanage.service.fit_roster_service.fit_roster_dao.create",
        _create,
    )

    import asyncio

    asyncio.run(
        fit_roster_service.create(
            CreateFitRosterParam(
                product_model=" YGZN2Q271 ",
                product_config_code="  ",
                part_code=" CNR0000622161 ",
                part_name="电压检测板",
                family="变流器",
            )
        )
    )
    assert captured["product_model"] == "YGZN2Q271"
    assert captured["product_config_code"] == "PS00"
    assert captured["part_code"] == "CNR0000622161"
