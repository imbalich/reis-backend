#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Annotated
from fastapi import APIRouter, Query, File, UploadFile

from backend.app.datamanage.schema.part_spare_mapping import (
    GetPartSpareMappingDetails,
    PartSpareMappingExcelImportResponse,
)
from backend.app.datamanage.service.part_spare_mapping_service import (
    part_spare_mapping_service,
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
1. 分页获取所有部件与备品对应关系数据（支持产品型号、派生码、零部件名称、零部件编码模糊查询）
2. Excel导入部件与备品对应关系数据（完全覆盖）
"""


@router.get(
    "",
    summary="分页获取所有部件与备品对应关系数据",
    dependencies=[DependsPagination],
)
async def get_pagination_part_spare_mapping(
    db: CurrentSession,
    product_model: Annotated[str | None, Query()] = None,
    product_config_code: Annotated[str | None, Query()] = None,
    original_part_name: Annotated[str | None, Query()] = None,
    original_part_code: Annotated[str | None, Query()] = None,
    spare_part_name: Annotated[str | None, Query()] = None,
    spare_part_code: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetPartSpareMappingDetails]]:
    part_spare_mapping_select = await part_spare_mapping_service.get_select(
        product_model=product_model,
        product_config_code=product_config_code,
        original_part_name=original_part_name,
        original_part_code=original_part_code,
        spare_part_name=spare_part_name,
        spare_part_code=spare_part_code,
    )
    page_data = await paging_data(db, part_spare_mapping_select)
    return response_base.success(data=page_data)


@router.post("/import", summary="Excel导入部件与备品对应关系数据（完全覆盖）")
async def import_part_spare_mapping_excel(
    file: UploadFile = File(..., description="Excel文件"),
) -> ResponseModel:
    """
    导入Excel文件，完全覆盖现有部件与备品对应关系数据

    Excel格式要求：
    - Sheet名称：配置表
    - 列名：产品型号、派生码、零部件名称（原装）、零部件物料编码（原装）、零部件名称（备品）、零部件物料编码（备品）、创建人、更新时间
    - 产品型号、零部件名称和编码为必填项，派生码为可选项
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        return response_base.fail(
            res=CustomResponse(400, "请上传Excel文件(.xlsx或.xls)")
        )

    excel_content = await file.read()
    result = await part_spare_mapping_service.import_from_excel(excel_content)

    if result.failed_rows > 0:
        return response_base.fail(
            res=CustomResponse(400, f"导入完成，但有{result.failed_rows}行数据失败"),
            data=result,
        )

    return response_base.success(data=result)
