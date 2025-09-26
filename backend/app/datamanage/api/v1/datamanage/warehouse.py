#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Query, File, UploadFile

from backend.app.datamanage.schema.warehouse import (
    GetWarehouseDetails,
    WarehouseImportResponse,
    WarehouseExcelImportResponse,
)
from backend.app.datamanage.service.warehouse_service import warehouse_service
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import (
    ResponseModel,
    ResponseSchemaModel,
    response_base,
    CustomResponse,
)
from backend.database.db import CurrentSession

router = APIRouter()

"""
接口需求:
1. 分页获取所有仓库数据（支持区域、库存地、实际库存地模糊查询）
2. CSV导入仓库数据（完全覆盖）
"""


@router.get("", summary="分页获取所有仓库数据", dependencies=[DependsPagination])
async def get_pagination_warehouse(
    db: CurrentSession,
    area: Annotated[str | None, Query()] = None,
    name: Annotated[str | None, Query()] = None,
    code: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetWarehouseDetails]]:
    warehouse_select = await warehouse_service.get_select(
        area=area, name=name, code=code
    )
    page_data = await paging_data(db, warehouse_select)
    return response_base.success(data=page_data)


@router.post("/import", summary="Excel导入仓库数据（完全覆盖）")
async def import_warehouse_excel(
    file: UploadFile = File(..., description="Excel文件"),
) -> ResponseModel:
    """
    导入Excel文件，完全覆盖现有仓库数据

    Excel格式要求：
    - Sheet名称：配置表
    - 列名：区域、库房编号、库房名称、二级配属、创建人、更新时间
    - 库房编号、库房名称、二级配属为必填项
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        return response_base.fail(
            res=CustomResponse(400, "请上传Excel文件(.xlsx或.xls)")
        )

    excel_content = await file.read()
    result = await warehouse_service.import_from_excel(excel_content)

    if result.failed_rows > 0:
        return response_base.fail(
            res=CustomResponse(400, f"导入完成，但有{result.failed_rows}行数据失败"),
            data=result,
        )

    return response_base.success(data=result)
