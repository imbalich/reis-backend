#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：tasks.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/23 11:35
"""
import time

from backend.app.lifetime.service.find_point_service import find_point_service
from backend.common.exception.errors import DataValidationError

from backend.app.lifetime.schema.lifetime_param import CreateEuqalLifetimeInParam
from backend.app.task.celery import celery_app
from backend.common.log import log
from backend.app.lifetime.service.equal_lifetime_service import equal_lifetime_service

@celery_app.task(name="equal_lifetime_task")
async def equal_lifetime_task(
    model: str, 
    parts: list[str],
    target_sf: float,
    step_start: float,
    step_end: float,
) -> str:
    """
    后台任务:手动触发
    单零部件级别拟合任务

    :param model: 产品型号
    :param parts: 零部件名称
    :param target_sf: 目标Failure_rate
    :param step_start: 步长开始
    :param step_end: 步长结束
    """
    try:
        lifetime_param = CreateEuqalLifetimeInParam(
            model=model, parts=parts, target_sf=target_sf, step_start=step_start, step_end=step_end
        )
        await equal_lifetime_service.create(obj=lifetime_param)

        return f"Task completed for model: {model}, part: {parts}"
    except DataValidationError as e:
        return f"Error processing model {model}, part {parts}: {str(e.msg)}"
    except Exception as e:
        return f"Unexpected Error processing model {model}, part {parts}: {str(e)}"
    


@celery_app.task()
async def equal_lifetime_all_task(
    target_sf: float,
    step_start: float,
    step_end: float,
) -> str:
    """
    后台任务:手动触发/自动执行
    :return:
    """
    start_time = time.time()
    problematic_models: list[str] = []
    total_models = 0
    successful_models = 0
    final_results: list[str] = []
    try:
        # 1. 先查出所有型号
        models = await equal_lifetime_service.get_all_models()
        total_models = len(models)

        # 2. 每个型号的零部件拟合
        for model in models:
            try:
                # 2.1 查出该型号下的所有零部件
                parts = await find_point_service.get_part_by_model(model)
                successful_parts = 0
                try:
                    lifetime_param = CreateEuqalLifetimeInParam(
                        model=model, parts=parts, target_sf=target_sf, step_start=step_start, step_end=step_end
                    )
                    await equal_lifetime_service.create(obj=lifetime_param)
                    successful_parts += 1
                except DataValidationError as e:
                    log.error(
                        f"Error processing model {model}, part {parts}: {str(e.msg)}"
                    )
                except Exception as e:
                    log.error(
                        f"Unexpected Error processing model {model}, part {parts}: {str(e)}"
                    )
                result_part_summary = (
                    f"Processed {model} parts, "
                    f"{successful_parts} successful, "
                )

                final_results.append(result_part_summary)

                log.info(result_part_summary)
            except Exception as e:
                log.error(f"Unexpected Error processing model {model}: {str(e)}")
                problematic_models.append(model)

            successful_models += 1

    except Exception as e:
        log.error(f"Unexpected Error in product_fit_all_task: {str(e)}")

    end_time = time.time()
    execution_time = end_time - start_time

    result_summary = (
        f"Task completed in {execution_time:.2f} seconds. "
        f"Processed {total_models} models, "
        f"{successful_models} successful, "
        f"{len(problematic_models)} problematic."
    )

    if problematic_models:
        result_summary += f' Problematic models: {", ".join(problematic_models)}'

    if final_results:
        result_summary += f' Final results: {", ".join(final_results)}'

    return result_summary