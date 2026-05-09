#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : fastapi-base-backend
@File    : tasks.py
@IDE     : PyCharm
@Author  : imbalich
@Date    : 2025/1/6 15:39
"""

import time
from collections.abc import Sequence

from backend.app.datamanage.service.failure_service import failure_service
from backend.app.fit.schema.fit_param import (
    CreateFitPartInParam,
    CreateFitProductInParam,
    FitMethodType,
)
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.service.product_fit_service import product_fit_service
from backend.app.task.celery import celery_app
from backend.common.exception.errors import DataValidationError
from backend.common.log import log


def _format_dimension_label(model: str, product_config_code: str | None) -> str:
    return f"{model} + {product_config_code}" if product_config_code else model


def _filter_dimension_pairs_for_model(
    pairs: Sequence[list[str | None]],
    model: str,
    product_config_code: str | None = None,
) -> list[tuple[str, str | None]]:
    matched_pairs: list[tuple[str, str | None]] = []
    for pair_model, pair_config in pairs:
        if pair_model != model:
            continue
        if product_config_code is not None and pair_config != product_config_code:
            continue
        matched_pairs.append((pair_model, pair_config))
    return matched_pairs


def _get_valid_dimension_pairs(
    pairs: Sequence[list[str | None]],
) -> list[tuple[str, str]]:
    valid_pairs: list[tuple[str, str]] = []
    for model, product_config_code in pairs:
        if not model or not product_config_code:
            continue
        valid_pairs.append((model, product_config_code))
    return valid_pairs


@celery_app.task(name="product_fit_task")
async def product_fit_task(
    model: str,
    input_date: str,
    method: FitMethodType = FitMethodType.MLE,
    product_config_code: str | None = None,
) -> str:
    """后台单型号产品级拟合任务。"""
    try:
        fit_param = CreateFitProductInParam(
            model=model,
            product_config_code=product_config_code,
            input_date=input_date,
            method=method,
        )
        await product_fit_service.create(obj=fit_param)
        return f"Task completed for model: {model}"
    except DataValidationError as exc:
        return f"Error processing model {model}: {exc.msg}"
    except Exception as exc:
        return f"Unexpected Error processing model {model}: {exc}"


@celery_app.task(name="part_fit_task")
async def part_fit_task(
    model: str,
    part: str,
    input_date: str,
    method: FitMethodType = FitMethodType.MLE,
    product_config_code: str | None = None,
) -> str:
    """后台单型号单零部件拟合任务。"""
    try:
        fit_param = CreateFitPartInParam(
            model=model,
            product_config_code=product_config_code,
            part=part,
            input_date=input_date,
            method=method,
        )
        await part_fit_service.create(obj=fit_param)
        return f"Task completed for model: {model}, part: {part}"
    except DataValidationError as exc:
        return f"Error processing model {model}, part {part}: {exc.msg}"
    except Exception as exc:
        return f"Unexpected Error processing model {model}, part {part}: {exc}"


@celery_app.task()
async def product_fit_all_task(
    input_date: str | None = None,
    method: FitMethodType = FitMethodType.MLE,
) -> str:
    """后台全量产品级拟合任务，按型号+派生码粒度执行。"""
    start_time = time.time()
    problematic_dimensions: list[str] = []
    total_dimensions = 0
    successful_dimensions = 0

    try:
        dimension_pairs = _get_valid_dimension_pairs(
            await failure_service.get_product_dimension_pairs()
        )
        total_dimensions = len(dimension_pairs)

        for model, product_config_code in dimension_pairs:
            label = _format_dimension_label(model, product_config_code)
            try:
                fit_param = CreateFitProductInParam(
                    model=model,
                    product_config_code=product_config_code,
                    input_date=input_date,
                    method=method,
                )
                await product_fit_service.create(obj=fit_param)
                successful_dimensions += 1
            except DataValidationError as exc:
                log.error(f"Error processing model-config {label}: {exc.msg}")
                problematic_dimensions.append(label)
            except Exception as exc:
                log.error(f"Unexpected Error processing model-config {label}: {exc}")
                problematic_dimensions.append(label)
    except Exception as exc:
        log.error(f"Unexpected Error in product_fit_all_task: {exc}")

    execution_time = time.time() - start_time
    result_summary = (
        f"Task completed in {execution_time:.2f} seconds. "
        f"Processed {total_dimensions} model-config pairs, "
        f"{successful_dimensions} successful, "
        f"{len(problematic_dimensions)} problematic."
    )
    if problematic_dimensions:
        result_summary += f' Problematic pairs: {", ".join(problematic_dimensions)}'
    return result_summary


@celery_app.task()
async def part_fit_all_task(
    input_date: str | None = None,
    method: FitMethodType = FitMethodType.MLE,
) -> str:
    """后台全量零部件拟合任务，按型号+派生码+零部件粒度执行。"""
    start_time = time.time()
    problematic_dimensions: list[str] = []
    total_dimensions = 0
    successful_dimensions = 0
    final_results: list[str] = []

    try:
        dimension_pairs = _get_valid_dimension_pairs(
            await failure_service.get_product_dimension_pairs()
        )
        total_dimensions = len(dimension_pairs)

        for model, product_config_code in dimension_pairs:
            label = _format_dimension_label(model, product_config_code)
            try:
                parts = await failure_service.get_parts_by_model(
                    model, product_config_code=product_config_code
                )
                total_parts = len(parts)
                successful_parts = 0
                problematic_parts: list[str] = []

                for part in parts:
                    try:
                        fit_param = CreateFitPartInParam(
                            model=model,
                            product_config_code=product_config_code,
                            part=part,
                            input_date=input_date,
                            method=method,
                        )
                        await part_fit_service.create(obj=fit_param)
                        successful_parts += 1
                    except DataValidationError as exc:
                        log.error(f"Error processing {label}, part {part}: {exc.msg}")
                        problematic_parts.append(f"{label} + {part}")
                    except Exception as exc:
                        log.error(f"Unexpected Error processing {label}, part {part}: {exc}")
                        problematic_parts.append(f"{label} + {part}")

                result_part_summary = (
                    f"Processed {label} parts, "
                    f"{total_parts} total, "
                    f"{successful_parts} successful, "
                    f"{len(problematic_parts)} problematic."
                )
                if problematic_parts:
                    result_part_summary += f' Problematic parts: {", ".join(problematic_parts)}'
                final_results.append(result_part_summary)
                log.info(result_part_summary)
            except Exception as exc:
                log.error(f"Unexpected Error processing model-config {label}: {exc}")
                problematic_dimensions.append(label)

            successful_dimensions += 1
    except Exception as exc:
        log.error(f"Unexpected Error in part_fit_all_task: {exc}")

    execution_time = time.time() - start_time
    result_summary = (
        f"Task completed in {execution_time:.2f} seconds. "
        f"Processed {total_dimensions} model-config pairs, "
        f"{successful_dimensions} successful, "
        f"{len(problematic_dimensions)} problematic."
    )
    if problematic_dimensions:
        result_summary += f' Problematic pairs: {", ".join(problematic_dimensions)}'
    if final_results:
        result_summary += f' Final results: {", ".join(final_results)}'
    return result_summary


@celery_app.task(name="part_fit_model_all_task")
async def part_fit_model_all_task(
    model: str,
    input_date: str | None = None,
    method: FitMethodType = FitMethodType.MLE,
    product_config_code: str | None = None,
) -> str:
    """后台单型号全零部件拟合任务，可按指定派生码或自动遍历该型号全部派生码。"""
    start_time = time.time()
    total_parts = 0
    successful_parts = 0
    problematic_parts: list[str] = []
    label = _format_dimension_label(model, product_config_code)

    try:
        dimension_pairs = _get_valid_dimension_pairs(
            await failure_service.get_product_dimension_pairs()
        )
        matched_pairs = _filter_dimension_pairs_for_model(
            dimension_pairs, model, product_config_code
        )
        if not matched_pairs:
            return f"Task failed for model {label}: no matched model-config pair found"

        for pair_model, pair_config in matched_pairs:
            pair_label = _format_dimension_label(pair_model, pair_config)
            parts = await failure_service.get_parts_by_model(
                pair_model, product_config_code=pair_config
            )
            total_parts += len(parts)

            for part in parts:
                try:
                    fit_param = CreateFitPartInParam(
                        model=pair_model,
                        product_config_code=pair_config,
                        part=part,
                        input_date=input_date,
                        method=method,
                    )
                    await part_fit_service.create(obj=fit_param)
                    successful_parts += 1
                except DataValidationError as exc:
                    log.error(f"Error processing {pair_label}, part {part}: {exc.msg}")
                    problematic_parts.append(f"{pair_label} + {part}")
                except Exception as exc:
                    log.error(f"Unexpected Error processing {pair_label}, part {part}: {exc}")
                    problematic_parts.append(f"{pair_label} + {part}")
    except Exception as exc:
        log.error(f"Unexpected Error in part_fit_model_all_task for model {label}: {exc}")
        return f"Task failed for model {label}: {exc}"

    execution_time = time.time() - start_time
    result_summary = (
        f"Task completed in {execution_time:.2f} seconds. "
        f"Processed model {label}, "
        f"{total_parts} total parts, "
        f"{successful_parts} successful, "
        f"{len(problematic_parts)} problematic."
    )
    if problematic_parts:
        result_summary += f' Problematic parts: {", ".join(problematic_parts[:10])}'
        if len(problematic_parts) > 10:
            result_summary += f" ... and {len(problematic_parts) - 10} more"
    return result_summary
