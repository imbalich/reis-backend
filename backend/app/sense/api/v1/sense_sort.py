#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : sense.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/26 15:08
"""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.sense.schema.sense_param import CreateSenseSortInParam
from backend.app.sense.service.process_service import process_service
from backend.common.response.response_schema import response_base
from backend.app.sense.service.sense_predict_service import sense_predict_service
from backend.app.task.celery_task.sense_task.tasks import sense_sort_task

router = APIRouter()

"""
接口需求：
1、根据故障表、配置表和PC表三个表按需求整理的数据处理标签
2、计算产品故障的关键影响要素及其敏感度，仅调试使用
3、计算产品故障的关键影响要素及其敏感度，后台任务执行
4、获取计算出的敏感因素排序结果
"""

@router.get("/sense/tag",summary="数据处理标签")
async def sense_tag(
        model: str = Query(..., description="产品型号"),
        part: str = Query(..., description="零部件名称"),
        stage: Annotated[str | None, Query(description="造修阶段")] = '新造',
        process_name: Annotated[str | None, Query(description="工序名称")] = None,
        check_project: Annotated[str | None, Query(description="检修区位")] = None,
        check_bezier: Annotated[str | None, Query(description="检验项点")] = None,
        time_range: Annotated[list[str] | None, Query(description="时间范围")] = None,
        extra_material_names: Annotated[str | None, Query(description="配件/原材料名称")] = None,
):
    tags = await process_service.process(model, part, stage, process_name, check_project, check_bezier,
                                        time_range, extra_material_names)
    return response_base.success(data=tags)

@router.post("/sense/swagger", summary="识别故障关键影响要素及其敏感度-->仅调试使用")
async def sense_sort(obj: CreateSenseSortInParam):
    await sense_predict_service.create(obj=obj)
    return response_base.success()


@router.post('/sense', summary='识别故障关键影响要素及其敏感度-->后台任务执行')
async def sort_create_sense_task(obj: CreateSenseSortInParam):
    # 移除了 await 关键字delay() 方法会立即返回一个 AsyncResult 对象，而不会阻塞当前的异步函数。
    # 任务会在后台异步执行，而 API 会立即返回任务 ID 和其他相关信息
    task = sense_sort_task.delay(obj.model, obj.part, obj.stage, obj.process_name, obj.check_project,
                                 obj.check_bezier,obj.start_time, obj.end_time,obj.extra_material_names)
    return response_base.success(data={'task_id': task.id, 'task_name': sense_sort_task.name, 'message': '任务已提交'})


@router.get('/sense', summary='识别故障关键影响要素及其敏感度')
async def sort_get_senses(
        model: str = Query(..., description="产品型号"),
        part: str = Query(..., description="零部件名称"),
        stage: Annotated[str | None, Query(description="造修阶段")] = '新造',
        process_name: Annotated[str | None, Query(description="工序名称")] = None,
        check_project: Annotated[str | None, Query(description="检修区位")] = None,
        check_bezier: Annotated[str | None, Query(description="检验项点")] = None,
        start_time: Annotated[str | None, Query(description="计算开始时间")] = None,
        end_time: Annotated[str | None, Query(description="计算结束时间")] = None,
        extra_material_names: Annotated[str | None, Query(description="配件/原材料名称")] = None,
):
    """
    获取单个产品型号下单个零部件的敏感度排序结果
    """
    results = await sense_predict_service.get_sense_sort_result(
        model,
        part,
        stage,
        process_name,
        check_project,
        check_bezier,
        extra_material_names,
        start_time,
        end_time
    )
    return response_base.success(data=results)
