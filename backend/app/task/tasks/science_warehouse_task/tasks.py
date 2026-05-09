#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科学库存计算后台任务。
"""

from datetime import date

from backend.app.calcu.service.science_warehouse_service import (
    science_warehouse_service,
)
from backend.app.task.celery import celery_app
from backend.app.task.tasks.base import TaskBase
from backend.common.exception.errors import DataValidationError


@celery_app.task(name="science_warehouse_calculation_task", base=TaskBase)
async def science_warehouse_calculation_task(
    time_interval_days: int = 180,
    input_date: str = None,
    product_model: str | None = None,
    product_config_code: str | None = None,
) -> str:
    """
    后台任务: 科学库存需求计算。
    """
    try:
        parsed_input_date = None
        if input_date:
            parsed_input_date = date.fromisoformat(input_date)

        result = await science_warehouse_service.calculate_science_warehouse_requirements(
            time_interval_days=time_interval_days,
            input_date=parsed_input_date,
            product_model=product_model,
            product_config_code=product_config_code,
        )

        if product_model is not None or product_config_code is not None:
            return (
                f"科学库存计算完成（新维度过滤走主服务）- "
                f"计算批次ID: {result.calculation_id}, "
                f"总备品数量: {result.statistics.get('total_warehouse_spares', 0)}"
            )

        return (
            f"科学库存计算完成 - 计算批次ID: {result.calculation_id}, "
            f"总备品数量: {result.statistics.get('total_warehouse_spares', 0)}"
        )

    except DataValidationError as e:
        return f"数据验证错误: {str(e.msg)}"
    except Exception as e:
        return f"科学库存计算失败: {str(e)}"
