#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Annotated
from fastapi import APIRouter, Query, File, UploadFile

from backend.app.datamanage.schema.warehouse_inventory import (
    GetWarehouseInventoryDetails,
    WarehouseInventoryExcelImportResponse,
)
from backend.app.datamanage.service.warehouse_inventory_service import (
    warehouse_inventory_service,
)
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
1. 分页获取所有库房备品清单数据（支持库房编号、库房名称、零部件编码、零部件名称模糊查询）
2. Excel导入库房备品清单数据（完全覆盖）
"""


@router.get(
    "", summary="分页获取所有库房备品清单数据", dependencies=[DependsPagination]
)
async def get_pagination_warehouse_inventory(
    db: CurrentSession,
    warehouse_code: Annotated[str | None, Query()] = None,
    warehouse_name: Annotated[str | None, Query()] = None,
    part_code: Annotated[str | None, Query()] = None,
    part_name: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetWarehouseInventoryDetails]]:
    warehouse_inventory_select = await warehouse_inventory_service.get_select(
        warehouse_code=warehouse_code,
        warehouse_name=warehouse_name,
        part_code=part_code,
        part_name=part_name,
    )
    page_data = await paging_data(db, warehouse_inventory_select)
    return response_base.success(data=page_data)


@router.post("/import", summary="Excel导入库房备品清单数据（完全覆盖）")
async def import_warehouse_inventory_excel(
    file: UploadFile = File(..., description="Excel文件"),
) -> ResponseModel:
    """
    导入Excel文件，完全覆盖现有库房备品清单数据

    Excel格式要求：
    - Sheet名称：配置表
    - 列名：库房编号、库房名称、零部件物料编码、零部件名称、默认数量、创建人、更新时间
    - 库房编号、零部件物料编码为必填项
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        return response_base.fail(
            res=CustomResponse(400, "请上传Excel文件(.xlsx或.xls)")
        )

    excel_content = await file.read()
    result = await warehouse_inventory_service.import_from_excel(excel_content)

    if result.failed_rows > 0:
        return response_base.fail(
            res=CustomResponse(400, f"导入完成，但有{result.failed_rows}行数据失败"),
            data=result,
        )

    return response_base.success(data=result)
