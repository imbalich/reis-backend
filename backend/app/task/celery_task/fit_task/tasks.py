#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：tasks.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/6 15:39
"""

import time

from anyio import sleep

from backend.app.datamanage.service.failure_service import failure_service
from backend.app.fit.schema.fit_param import CreateFitPartInParam, CreateFitProductInParam, FitMethodType
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.service.product_fit_service import product_fit_service
from backend.app.task.celery import celery_app
from backend.common.exception.errors import DataValidationError
from backend.common.log import log


@celery_app.task(name='cleanup_redis_keys')
async def cleanup_redis_keys() -> str:
    """定期清除 Celery 管理的 Redis 键,转移到 db_log 下"""
    await sleep(5)
    result = 'cleanup_redis_keys done!'
    return result


@celery_app.task(name='product_fit_task')
async def product_fit_task(model: str, input_date: str, method: FitMethodType = FitMethodType.MLE) -> str:
    """
    后台任务:手动触发
    单型号产品级别拟合任务

    :param model: 产品型号
    :param input_date: 输入日期 YYYY-MM-DD
    :param method: 拟合方法
    """
    try:
        fit_param = CreateFitProductInParam(model=model, input_date=input_date, method=method)
        await product_fit_service.create(obj=fit_param)
        return f'Task completed for model: {model}'
    except DataValidationError as e:
        return f'Error processing model {model}: {str(e.msg)}'
    except Exception as e:
        return f'Unexpected Error processing model {model}: {str(e)}'


@celery_app.task(name='part_fit_task')
async def part_fit_task(model: str, part: str, input_date: str, method: FitMethodType = FitMethodType.MLE) -> str:
    """
    后台任务:手动触发
    单零部件级别拟合任务

    :param model: 产品型号
    :param part: 零部件名称
    :param input_date: 输入日期 YYYY-MM-DD
    :param method: 拟合方法
    """
    try:
        fit_param = CreateFitPartInParam(model=model, part=part, input_date=input_date, method=method)
        await part_fit_service.create(obj=fit_param)

        return f'Task completed for model: {model}, part: {part}'
    except DataValidationError as e:
        return f'Error processing model {model}, part {part}: {str(e.msg)}'
    except Exception as e:
        return f'Unexpected Error processing model {model}, part {part}: {str(e)}'


@celery_app.task(name='product_fit_all_task')
async def product_fit_all_task(input_date: str | None = None, method: FitMethodType = FitMethodType.MLE) -> str:
    """
    后台任务:手动触发/自动执行
    :return:
    """
    start_time = time.time()
    problematic_models: list[str] = []
    total_models = 0
    successful_models = 0

    try:
        # 1. 先查出所有型号
        models = await failure_service.get_product_model()
        total_models = len(models)

        # 2. 挨个进行打标拟合
        for model in models:
            try:
                fit_param = CreateFitProductInParam(model=model, input_date=input_date, method=method)
                await product_fit_service.create(obj=fit_param)
                successful_models += 1
            except DataValidationError as e:
                log.error(f'Error processing model {model}: {str(e.msg)}')
                problematic_models.append(model)
            except Exception as e:
                log.error(f'Unexpected Error processing model {model}: {str(e)}')
                problematic_models.append(model)

    except Exception as e:
        log.error(f'Unexpected Error in product_fit_all_task: {str(e)}')

    end_time = time.time()
    execution_time = end_time - start_time

    result_summary = (
        f'Task completed in {execution_time:.2f} seconds. '
        f'Processed {total_models} models, '
        f'{successful_models} successful, '
        f'{len(problematic_models)} problematic.'
    )

    if problematic_models:
        result_summary += f' Problematic models: {", ".join(problematic_models)}'

    return result_summary


@celery_app.task(name='part_fit_all_task')
async def part_fit_all_task(input_date: str | None = None, method: FitMethodType = FitMethodType.MLE) -> str:
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
        models = await failure_service.get_product_model()
        total_models = len(models)

        # 2. 每个型号的零部件拟合
        for model in models:
            try:
                # 2.1 查出该型号下的所有零部件
                parts = await failure_service.get_parts_by_model(model)
                total_parts = len(parts)
                successful_parts = 0
                problematic_parts: list[str] = []
                for part in parts:
                    try:
                        fit_param = CreateFitPartInParam(model=model, part=part, input_date=input_date, method=method)
                        await part_fit_service.create(obj=fit_param)
                        successful_parts += 1
                    except DataValidationError as e:
                        log.error(f'Error processing model {model}, part {part}: {str(e.msg)}')
                        problematic_parts.append(f'{model} + {part}')
                    except Exception as e:
                        log.error(f'Unexpected Error processing model {model}, part {part}: {str(e)}')
                        problematic_parts.append(f'{model} + {part}')

                result_part_summary = (
                    f'Processed {model} parts, '
                    f'{total_parts} total, '
                    f'{successful_parts} successful, '
                    f'{len(problematic_parts)} problematic.'
                )

                if problematic_parts:
                    result_part_summary += f' Problematic parts: {", ".join(problematic_parts)}'

                final_results.append(result_part_summary)

                log.info(result_part_summary)
            except Exception as e:
                log.error(f'Unexpected Error processing model {model}: {str(e)}')
                problematic_models.append(model)

            successful_models += 1

    except Exception as e:
        log.error(f'Unexpected Error in product_fit_all_task: {str(e)}')

    end_time = time.time()
    execution_time = end_time - start_time

    result_summary = (
        f'Task completed in {execution_time:.2f} seconds. '
        f'Processed {total_models} models, '
        f'{successful_models} successful, '
        f'{len(problematic_models)} problematic.'
    )

    if problematic_models:
        result_summary += f' Problematic models: {", ".join(problematic_models)}'

    if final_results:
        result_summary += f' Final results: {", ".join(final_results)}'

    return result_summary
