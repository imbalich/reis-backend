#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : rcm_calculation.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : RCM计算API接口
"""

from typing import Optional, Annotated
from datetime import datetime

from fastapi import APIRouter, Query, Depends

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.database.db import CurrentSession
from backend.app.rcm.service.rcm_calculation_service import rcm_calculation_service
from backend.app.rcm.schema.rcm_calculation_result import RcmCalculationListDetails

router = APIRouter()


@router.get("", summary="分页获取RCM计算结果", dependencies=[DependsPagination])
async def get_pagination_rcm_calculation_results(
    db: CurrentSession,
    product_model: Annotated[str | None, Query()] = None,
    component_name: Annotated[str | None, Query()] = None,
    component_material_code: Annotated[str | None, Query()] = None,
    final_result: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[RcmCalculationListDetails]]:
    """分页获取RCM计算结果，支持多条件模糊查询"""
    # 获取分页数据
    rcm_select = await rcm_calculation_service.get_select(
        product_model=product_model,
        component_name=component_name,
        component_material_code=component_material_code,
        final_result=final_result,
    )
    page_data = await paging_data(db, rcm_select)

    # 转换数据格式以匹配Schema
    if page_data.get("items"):
        converted_items = []
        for item in page_data["items"]:
            # item是元组：(RcmCalculationResult, product_model, component_name, component_material_code, failure_mode)
            result_obj = item[0]  # RcmCalculationResult对象
            converted_item = {
                "id": result_obj.id,
                "base_data_id": result_obj.base_data_id,
                "product_model": item[1],  # product_model
                "component_name": item[2],  # component_name
                "component_material_code": item[3],  # component_material_code
                "failure_mode": item[4],  # failure_mode
                "final_result": result_obj.final_result,
                "calculation_status": result_obj.calculation_status,
                "calculation_process": result_obj.calculation_process,
                "error_message": result_obj.error_message,
                "calculation_time": result_obj.calculation_time,
                "created_time": result_obj.created_time,
                "updated_time": result_obj.updated_time
                or result_obj.created_time,  # 处理None值
            }
            converted_items.append(converted_item)
        page_data["items"] = converted_items

    return response_base.success(data=page_data)


@router.post("/batch-calculate", summary="提交RCM批量计算任务")
async def submit_rcm_batch_calculation_task() -> ResponseSchemaModel[dict]:
    """
    提交RCM批量计算任务到后台执行

    防重复提交机制：
    1. 检查是否有正在执行的任务
    2. 如果有正在执行的任务，返回当前任务状态
    3. 如果没有，提交新任务并返回任务ID
    """
    try:
        from backend.app.task.tasks.rcm_task.tasks import rcm_batch_calculation_task
        from backend.app.task.celery import celery_app

        # 检查是否有正在执行的RCM计算任务
        active_tasks = celery_app.control.inspect().active()
        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    if task.get("name") == "rcm_batch_calculation_task":
                        return response_base.success(
                            data={
                                "task_id": task.get("id"),
                                "task_name": task.get("name"),
                                "message": "RCM批量计算任务正在执行中，请勿重复提交",
                                "status": "running",
                                "is_duplicate": True,
                            }
                        )

        # 检查是否有待执行的任务
        scheduled_tasks = celery_app.control.inspect().scheduled()
        if scheduled_tasks:
            for worker, tasks in scheduled_tasks.items():
                for task in tasks:
                    if task.get("name") == "rcm_batch_calculation_task":
                        return response_base.success(
                            data={
                                "task_id": task.get("id"),
                                "task_name": task.get("name"),
                                "message": "RCM批量计算任务已排队等待执行",
                                "status": "pending",
                                "is_duplicate": True,
                            }
                        )

        # 提交新的后台任务
        task = rcm_batch_calculation_task.delay()

        return response_base.success(
            data={
                "task_id": task.id,
                "task_name": rcm_batch_calculation_task.name,
                "message": "RCM批量计算任务已提交到后台执行",
                "status": "submitted",
                "is_duplicate": False,
            }
        )
    except Exception as e:
        return response_base.fail(msg=f"提交计算任务失败: {str(e)}")


@router.get("/task-status/{task_id}", summary="查询RCM计算任务状态")
async def get_rcm_calculation_task_status(task_id: str) -> ResponseSchemaModel[dict]:
    """
    查询RCM计算任务的执行状态

    :param task_id: 任务ID
    :return: 任务状态信息
    """
    try:
        from backend.app.task.celery import celery_app

        # 获取任务状态
        task_result = celery_app.AsyncResult(task_id)

        status_info = {
            "task_id": task_id,
            "status": task_result.status,
            "ready": task_result.ready(),
        }

        if task_result.ready():
            # 检查任务状态字符串而不是successful()方法
            if task_result.status == "SUCCESS":
                status_info["result"] = task_result.result
                status_info["message"] = "任务执行成功"
            else:
                status_info["error"] = str(task_result.result)
                status_info["message"] = f"任务执行失败，状态: {task_result.status}"
        else:
            status_info["message"] = "任务正在执行中"

        return response_base.success(data=status_info)
    except Exception as e:
        return response_base.fail(msg=f"查询任务状态失败: {str(e)}")


@router.get("/calculation-status", summary="检查RCM计算任务全局状态")
async def get_rcm_calculation_global_status() -> ResponseSchemaModel[dict]:
    """
    检查RCM计算任务的全局状态

    用于前端判断是否可以提交新的计算任务
    返回当前是否有任务在执行或排队
    """
    try:
        from backend.app.task.celery import celery_app

        # 检查正在执行的任务
        active_tasks = celery_app.control.inspect().active()
        running_task = None
        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    if task.get("name") == "rcm_batch_calculation_task":
                        running_task = {
                            "task_id": task.get("id"),
                            "status": "running",
                            "worker": worker,
                        }
                        break
                if running_task:
                    break

        # 检查排队的任务
        scheduled_tasks = celery_app.control.inspect().scheduled()
        pending_task = None
        if scheduled_tasks and not running_task:
            for worker, tasks in scheduled_tasks.items():
                for task in tasks:
                    if task.get("name") == "rcm_batch_calculation_task":
                        pending_task = {
                            "task_id": task.get("id"),
                            "status": "pending",
                            "worker": worker,
                        }
                        break
                if pending_task:
                    break

        # 确定当前状态
        if running_task:
            current_task = running_task
            can_submit = False
            message = "RCM计算任务正在执行中，请等待完成"
        elif pending_task:
            current_task = pending_task
            can_submit = False
            message = "RCM计算任务已排队等待执行"
        else:
            current_task = None
            can_submit = True
            message = "可以提交新的RCM计算任务"

        return response_base.success(
            data={
                "can_submit": can_submit,
                "current_task": current_task,
                "message": message,
            }
        )
    except Exception as e:
        return response_base.fail(msg=f"检查任务状态失败: {str(e)}")
