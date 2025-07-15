#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：pc.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/5/20 11:32
"""
from typing import Annotated

from fastapi import APIRouter,Query

from backend.app.datamanage.service.pc_service import pc_service
from backend.common.response.response_schema import ResponseModel, response_base

router = APIRouter()

"""
接口需求：
1、获取pc表中根据选择的检验工序得到相应的检验区位列表，用于支持前端级联查询
2、获取pc表中根据选择的检验区位得到相应的检验项点列表，用于支持前端级联查询
"""

@router.get('/check_project',summary='根据选定的检验工序获取对应的检验区位')
async def get_pc_check_project_by_process_name(
        process_name:Annotated[str | None, Query()] = None,
) -> ResponseModel:
    models = await pc_service.get_check_project_by_process_name(process_name=process_name)
    return response_base.success(data=models)

@router.get('/check_bezier',summary='根据选定的检验工序获取对应的检验区位')
async def get_pc_check_bezier_by_check_project(
        check_project:Annotated[str | None, Query()] = None,
) -> ResponseModel:
    models = await pc_service.get_check_bezier_by_check_project(check_project=check_project)
    return response_base.success(data=models)















