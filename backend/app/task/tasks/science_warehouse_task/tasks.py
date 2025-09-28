#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科学库存计算后台任务
"""

from datetime import date

from backend.app.calcu.service.science_warehouse_service import (
    science_warehouse_service,
)
from backend.app.task.tasks.base import TaskBase
from backend.common.exception.errors import DataValidationError
from backend.app.task.celery import celery_app


@celery_app.task(name="science_warehouse_calculation_task", base=TaskBase)
async def science_warehouse_calculation_task(
    time_interval_days: int = 180, input_date: str = None
) -> str:
    """
    后台任务:科学库存需求计算

    :param time_interval_days: 需求预测时间间隔（天数）,默认180天
    :param input_date: 计算截止日期，格式为 YYYY-MM-DD 的字符串，默认为当前日期
    :return: 任务执行结果
    """
    try:
        # 处理 input_date 参数
        parsed_input_date = None
        if input_date:
            parsed_input_date = date.fromisoformat(input_date)

        # 执行科学库存计算
        result = (
            await science_warehouse_service.calculate_science_warehouse_requirements(
                time_interval_days=time_interval_days,
                input_date=parsed_input_date,
            )
        )

        return f"科学库存计算完成 - 计算批次ID: {result.calculation_id}, 总备品数量: {result.statistics.get('total_warehouse_spares', 0)}"

    except DataValidationError as e:
        return f"数据验证错误: {str(e.msg)}"
    except Exception as e:
        return f"科学库存计算失败: {str(e)}"


@celery_app.task(name="science_warehouse_calculation_and_api_task", base=TaskBase)
async def science_warehouse_calculation_and_api_task(
    time_interval_days: int = 180, input_date: str = None
) -> str:
    """
    后台任务:科学库存需求计算并返回API格式结果

    :param time_interval_days: 需求预测时间间隔（天数）,默认180天
    :param input_date: 计算截止日期，格式为 YYYY-MM-DD 的字符串，默认为当前日期
    :return: 任务执行结果
    """
    try:
        # 处理 input_date 参数
        parsed_input_date = None
        if input_date:
            parsed_input_date = date.fromisoformat(input_date)

        # 1. 执行科学库存计算
        result = (
            await science_warehouse_service.calculate_science_warehouse_requirements(
                time_interval_days=time_interval_days,
                input_date=parsed_input_date,
            )
        )

        # 2. 获取API格式数据
        api_data = await science_warehouse_service.get_calculation_results_for_api(
            result.calculation_id
        )

        return f"科学库存计算并生成API数据完成 - 计算批次ID: {result.calculation_id}, API数据条数: {len(api_data) if api_data else 0}"

    except DataValidationError as e:
        return f"数据验证错误: {str(e.msg)}"
    except Exception as e:
        return f"科学库存计算失败: {str(e)}"
