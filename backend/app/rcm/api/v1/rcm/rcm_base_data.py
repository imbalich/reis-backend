#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : rcm_base_data.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : RCM基础数据API接口
"""

from typing import Annotated

from fastapi import APIRouter, Query, File, UploadFile

from backend.app.rcm.schema.rcm_base_data import (
    GetRcmBaseDataDetails,
    RcmExcelImportResponse,
)
from backend.app.rcm.service.rcm_base_data_service import rcm_base_data_service
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
1. 分页获取所有RCM基础数据（支持多条件模糊查询）
2. Excel导入RCM基础数据（完全覆盖）
3. 获取产品型号列表（用于前端下拉框）
4. 根据产品型号获取部件名称列表（用于前端级联查询）
5. 根据产品型号获取故障模式列表（用于前端级联查询）
"""


@router.get("", summary="分页获取所有RCM基础数据", dependencies=[DependsPagination])
async def get_pagination_rcm_base_data(
    db: CurrentSession,
    product_model: Annotated[str | None, Query()] = None,
    component_name: Annotated[str | None, Query()] = None,
    component_material_code: Annotated[str | None, Query()] = None,
    failure_mode: Annotated[str | None, Query()] = None,
    is_key_component: Annotated[bool | None, Query()] = None,
    is_consumable_part: Annotated[bool | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetRcmBaseDataDetails]]:
    """分页获取RCM基础数据，支持多条件模糊查询"""
    rcm_select = await rcm_base_data_service.get_select(
        product_model=product_model,
        component_name=component_name,
        component_material_code=component_material_code,
        failure_mode=failure_mode,
        is_key_component=is_key_component,
        is_consumable_part=is_consumable_part,
    )
    page_data = await paging_data(db, rcm_select)
    return response_base.success(data=page_data)


@router.post("/import", summary="Excel导入RCM基础数据（完全覆盖）")
async def import_rcm_base_data_excel(
    file: UploadFile = File(..., description="Excel文件"),
) -> ResponseModel:
    """
    导入Excel文件，完全覆盖现有RCM基础数据

    Excel格式要求：
    - Sheet名称：RCM基础数据
            - 列名：产品型号、派生码、部件名称、零部件物料编码、故障模式、来源、是否关键部件、是否耗损型部件、故障率预计值、增加预防性维修的、改进前LCC、改进后LCC、状态是否可在线、故障率变化趋势是否达到预警值、创建人、更新时间
    - 产品型号、部件名称、零部件物料编码、故障模式为必填项
            - 字段分组：黄色组(来源+是否关键部件)、橙色组(是否耗损型部件)、绿色组(故障率预计值)、红色组(增加预防性维修的)、浅蓝色组(改进前LCC+改进后LCC)、灰色组(状态是否可在线+故障率变化趋势是否达到预警值)
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        return response_base.fail(
            res=CustomResponse(400, "请上传Excel文件(.xlsx或.xls)")
        )

    excel_content = await file.read()
    result = await rcm_base_data_service.import_from_excel(excel_content)

    if result.failed_rows > 0:
        return response_base.fail(
            res=CustomResponse(400, f"导入完成，但有{result.failed_rows}行数据失败"),
            data=result,
        )

    return response_base.success(data=result)


@router.get("/product-models", summary="获取所有产品型号")
async def get_rcm_product_models() -> ResponseModel:
    """获取RCM基础数据中所有产品型号，用于前端下拉框选择"""
    models = await rcm_base_data_service.get_product_models()
    return response_base.success(data=models)


@router.get("/component-names", summary="根据产品型号获取部件名称列表")
async def get_rcm_component_names_by_model(
    product_model: Annotated[str, Query(description="产品型号")],
) -> ResponseModel:
    """根据产品型号获取部件名称列表，用于前端级联查询"""
    component_names = await rcm_base_data_service.get_component_names_by_model(
        product_model
    )
    return response_base.success(data=component_names)


@router.get("/failure-modes", summary="根据产品型号获取故障模式列表")
async def get_rcm_failure_modes_by_model(
    product_model: Annotated[str, Query(description="产品型号")],
) -> ResponseModel:
    """根据产品型号获取故障模式列表，用于前端级联查询"""
    failure_modes = await rcm_base_data_service.get_failure_modes_by_model(
        product_model
    )
    return response_base.success(data=failure_modes)
