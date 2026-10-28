#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
from typing import Any

import pandas as pd

from backend.app.datamanage.crud.crud_fit_roster import fit_roster_dao
from backend.app.datamanage.model.fit_roster import FitRoster
from backend.app.datamanage.schema.fit_roster import (
    CreateFitRosterParam,
    FitRosterChangeItem,
    FitRosterImportPreview,
    UpdateFitRosterParam,
)
from backend.common.exception import errors
from backend.common.product_config import normalize_product_config_code
from backend.database.db import async_db_session

SHEET_NAME = "寿命拟合名单"
REQUIRED_COLUMNS = ("产品型号", "零部件物料编码")


def _cell_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value).strip()
    if number.is_integer():
        return str(int(number))
    return str(value).strip()


def _optional_text(value: str) -> str | None:
    return value or None


def _column(frame: pd.DataFrame, *names: str) -> str | None:
    for name in names:
        if name in frame.columns:
            return name
    return None


def parse_fit_roster_excel(excel_content: bytes) -> tuple[list[dict[str, Any]], list[str], int]:
    """解析名单文件。返回行、错误、数据行数。有错误时行列表为空。"""
    try:
        workbook = pd.ExcelFile(io.BytesIO(excel_content))
    except Exception as exc:
        return [], [f"Excel文件解析失败: {exc}"], 0

    sheet = SHEET_NAME if SHEET_NAME in workbook.sheet_names else workbook.sheet_names[0]
    frame = pd.read_excel(workbook, sheet_name=sheet)
    missing = [name for name in REQUIRED_COLUMNS if name not in frame.columns]
    if missing:
        return [], [f"缺少必要列: {', '.join(missing)}"], 0
    if frame.empty:
        return [], ["文件没有数据，不能用空文件清空名单"], 0

    name_column = _column(frame, "零部件名称")
    family_column = _column(frame, "族")
    config_column = _column(frame, "派生码", "product_config_code")
    created_by_column = _column(frame, "创建人")

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for index, record in frame.iterrows():
        line_no = int(index) + 2
        product_model = _cell_text(record["产品型号"])
        part_code = _cell_text(record["零部件物料编码"])
        if not product_model or not part_code:
            errors.append(f"第{line_no}行: 产品型号和零部件物料编码为必填项")
            continue
        product_config_code = normalize_product_config_code(
            _cell_text(record[config_column]) if config_column else None
        )
        key = (product_model, product_config_code, part_code)
        if key in seen:
            errors.append(
                f"第{line_no}行: 型号 {product_model}、派生码 {product_config_code}、件号 {part_code} 重复"
            )
            continue
        seen.add(key)
        rows.append(
            {
                "product_model": product_model,
                "product_config_code": product_config_code,
                "part_code": part_code,
                "part_name": _cell_text(record[name_column]) if name_column else "",
                "family": _optional_text(_cell_text(record[family_column]) if family_column else ""),
                "created_by": _optional_text(
                    _cell_text(record[created_by_column]) if created_by_column else ""
                ),
            }
        )

    if errors:
        return [], errors, len(frame)
    return rows, [], len(frame)


def diff_fit_roster(
    current: list[FitRoster],
    incoming: list[dict[str, Any]],
) -> FitRosterImportPreview:
    """比较当前名单和文件。文件是更换后的完整名单。"""
    current_by_key = {
        (row.product_model, row.product_config_code, row.part_code): row for row in current
    }
    incoming_by_key = {
        (row["product_model"], row["product_config_code"], row["part_code"]): row
        for row in incoming
    }
    to_add: list[FitRosterChangeItem] = []
    to_update: list[FitRosterChangeItem] = []
    unchanged = 0
    for key, data in incoming_by_key.items():
        existing = current_by_key.get(key)
        item = FitRosterChangeItem(
            product_model=data["product_model"],
            product_config_code=data["product_config_code"],
            part_code=data["part_code"],
            part_name=data["part_name"],
            family=data["family"],
            current_part_name=None if existing is None else existing.part_name,
            current_family=None if existing is None else existing.family,
        )
        if existing is None:
            to_add.append(item)
        elif existing.part_name != data["part_name"] or existing.family != data["family"]:
            to_update.append(item)
        else:
            unchanged += 1
    to_remove = [
        FitRosterChangeItem(
            product_model=row.product_model,
            product_config_code=row.product_config_code,
            part_code=row.part_code,
            part_name=row.part_name,
            family=row.family,
            current_part_name=row.part_name,
            current_family=row.family,
        )
        for key, row in current_by_key.items()
        if key not in incoming_by_key
    ]
    return FitRosterImportPreview(
        can_replace=True,
        total_rows=len(incoming),
        to_add=to_add,
        to_remove=to_remove,
        to_update=to_update,
        unchanged=unchanged,
    )


class FitRosterService:
    @staticmethod
    async def get_select(
        product_model: str | None = None,
        product_config_code: str | None = None,
        part_code: str | None = None,
        part_name: str | None = None,
        family: str | None = None,
    ):
        config = (
            normalize_product_config_code(product_config_code)
            if product_config_code is not None and str(product_config_code).strip()
            else None
        )
        return await fit_roster_dao.get_select(
            product_model=product_model,
            product_config_code=config,
            part_code=part_code,
            part_name=part_name,
            family=family,
        )

    @staticmethod
    def _row_data(obj: CreateFitRosterParam) -> dict[str, Any]:
        product_model = obj.product_model.strip()
        part_code = obj.part_code.strip()
        if not product_model or not part_code:
            raise errors.RequestError(msg="产品型号和零部件物料编码为必填项")
        return {
            "product_model": product_model,
            "product_config_code": normalize_product_config_code(obj.product_config_code),
            "part_code": part_code,
            "part_name": obj.part_name.strip(),
            "family": obj.family.strip() if obj.family else None,
            "created_by": obj.created_by.strip() if obj.created_by else None,
        }

    @staticmethod
    async def create(obj: CreateFitRosterParam) -> FitRoster:
        data = FitRosterService._row_data(obj)
        async with async_db_session() as db:
            exists = await fit_roster_dao.get_by_key(
                db,
                data["product_model"],
                data["product_config_code"],
                data["part_code"],
            )
            if exists is not None:
                raise errors.ConflictError(msg="该型号、派生码、零部件已在寿命拟合名单中")
            return await fit_roster_dao.create(db, data)

    @staticmethod
    async def update(pk: int, obj: UpdateFitRosterParam) -> FitRoster:
        async with async_db_session() as db:
            row = await fit_roster_dao.get(db, pk)
            if row is None:
                raise errors.NotFoundError(msg="寿命拟合名单记录不存在")
            data = {
                "part_name": obj.part_name.strip(),
                "family": obj.family.strip() if obj.family else None,
            }
            if obj.created_by is not None and obj.created_by.strip():
                data["created_by"] = obj.created_by.strip()
            return await fit_roster_dao.update_fields(db, row, data)

    @staticmethod
    async def delete(pk: int) -> int:
        async with async_db_session() as db:
            count = await fit_roster_dao.delete_ids(db, [pk])
        if count == 0:
            raise errors.NotFoundError(msg="寿命拟合名单记录不存在")
        return count

    @staticmethod
    async def delete_batch(ids: list[int]) -> int:
        async with async_db_session() as db:
            return await fit_roster_dao.delete_ids(db, ids)

    @staticmethod
    async def list_all() -> list[FitRoster]:
        async with async_db_session() as db:
            return await fit_roster_dao.get_all(db)

    @staticmethod
    async def preview_import(excel_content: bytes) -> FitRosterImportPreview:
        rows, parse_errors, total_rows = parse_fit_roster_excel(excel_content)
        if parse_errors:
            return FitRosterImportPreview(
                can_replace=False,
                total_rows=total_rows,
                errors=parse_errors,
            )
        current = await FitRosterService.list_all()
        return diff_fit_roster(current, rows)

    @staticmethod
    async def replace_import(excel_content: bytes) -> FitRosterImportPreview:
        preview = await FitRosterService.preview_import(excel_content)
        if not preview.can_replace:
            raise errors.RequestError(msg="文件不能用于更换名单", data=preview)
        rows, _, _ = parse_fit_roster_excel(excel_content)
        async with async_db_session() as db:
            await fit_roster_dao.replace_all(db, rows)
        return preview

    @staticmethod
    def export_excel(rows: list[FitRoster]) -> bytes:
        frame = pd.DataFrame(
            [
                {
                    "产品型号": row.product_model,
                    "派生码": row.product_config_code,
                    "零部件物料编码": row.part_code,
                    "零部件名称": row.part_name,
                    "族": row.family or "",
                    "创建人": row.created_by or "",
                }
                for row in rows
            ]
        )
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            frame.to_excel(writer, sheet_name=SHEET_NAME, index=False)
        return buffer.getvalue()


fit_roster_service = FitRosterService()
