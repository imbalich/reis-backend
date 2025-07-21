#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：configuration.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/5/20 09:52
"""
from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.datamanage.service.configuration_service import configuration_service
from backend.common.response.response_schema import ResponseModel, response_base

router = APIRouter()

"""
接口需求：
1、获取配置表中根据选择的产品型号得到工序名称列表，用于支持前端的级联查询
2、获取配置表中根据选择的工序名称得到物料名称(物料编码)列表，用于支持前端的级联查询
"""

@router.get('/process_name', summary='根据选定的产品型号获取对应的故障部位')
async def get_config_process_name_by_product_model(
    product_model: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    models = await configuration_service.get_process_name_by_product_model(product_model=product_model)
    return response_base.success(data=models)

@router.get('/material_name', summary='根据选定的工序名称获取对应的物料名称（物料编码）')
async def get_config_material_name_by_process_name(
    process_name: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    models = await configuration_service.get_material_name_by_process_name(process_name=process_name)
    return response_base.success(data=models)