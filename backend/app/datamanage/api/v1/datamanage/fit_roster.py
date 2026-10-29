#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from backend.app.datamanage.schema.fit_roster import (
    CreateFitRosterParam,
    DeleteFitRosterParam,
    FitRosterImportPreview,
    GetFitRosterDetail,
    UpdateFitRosterParam,
)
from backend.app.datamanage.service.fit_roster_service import fit_roster_service
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import (
    CustomResponse,
    ResponseModel,
    ResponseSchemaModel,
    response_base,
)
from backend.database.db import CurrentSession

router = APIRouter()


def _excel_file(file: UploadFile) -> bool:
    filename = file.filename or ""
    return filename.endswith((".xlsx", ".xls"))


@router.get(
    "",
    summary="分页查询寿命拟合名单",
    dependencies=[DependsPagination],
)
async def get_pagination_fit_roster(
    db: CurrentSession,
    product_model: Annotated[str | None, Query(description="产品型号")] = None,
    product_config_code: Annotated[str | None, Query(description="派生码")] = None,
    part_code: Annotated[str | None, Query(description="零部件物料编码")] = None,
    part_name: Annotated[str | None, Query(description="零部件名称")] = None,
    family: Annotated[str | None, Query(description="产品族")] = None,
) -> ResponseSchemaModel[PageData[GetFitRosterDetail]]:
    stmt = await fit_roster_service.get_select(
        product_model=product_model,
        product_config_code=product_config_code,
        part_code=part_code,
        part_name=part_name,
        family=family,
    )
    page_data = await paging_data(db, stmt)
    return response_base.success(data=page_data)


@router.get("/export", summary="导出寿命拟合名单")
async def export_fit_roster() -> StreamingResponse:
    rows = await fit_roster_service.list_all()
    content = fit_roster_service.export_excel(rows)
    filename = quote("寿命拟合名单.xlsx")
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("", summary="新增寿命拟合名单")
async def create_fit_roster(
    obj: CreateFitRosterParam,
) -> ResponseSchemaModel[GetFitRosterDetail]:
    row = await fit_roster_service.create(obj)
    return response_base.success(data=row)


@router.post("/delete", summary="批量删除寿命拟合名单")
async def delete_fit_roster_batch(obj: DeleteFitRosterParam) -> ResponseModel:
    count = await fit_roster_service.delete_batch(obj.ids)
    return response_base.success(data={"deleted": count})


@router.post("/import/preview", summary="预览寿命拟合名单更换差异")
async def preview_fit_roster_import(
    file: UploadFile = File(..., description="Excel文件"),
) -> ResponseSchemaModel[FitRosterImportPreview]:
    if not _excel_file(file):
        return response_base.fail(res=CustomResponse(400, "请上传Excel文件(.xlsx或.xls)"))
    preview = await fit_roster_service.preview_import(await file.read())
    return response_base.success(data=preview)


@router.post("/import/replace", summary="按文件更换寿命拟合名单")
async def replace_fit_roster_import(
    file: UploadFile = File(..., description="Excel文件"),
) -> ResponseSchemaModel[FitRosterImportPreview]:
    if not _excel_file(file):
        return response_base.fail(res=CustomResponse(400, "请上传Excel文件(.xlsx或.xls)"))
    preview = await fit_roster_service.replace_import(await file.read())
    return response_base.success(data=preview)


@router.put("/{pk}", summary="修改寿命拟合名单的名称和族")
async def update_fit_roster(
    pk: int,
    obj: UpdateFitRosterParam,
) -> ResponseSchemaModel[GetFitRosterDetail]:
    row = await fit_roster_service.update(pk, obj)
    return response_base.success(data=row)


@router.delete("/{pk}", summary="删除寿命拟合名单")
async def delete_fit_roster(pk: int) -> ResponseModel:
    await fit_roster_service.delete(pk)
    return response_base.success()
