#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : tasks.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : 备件统计后台任务
"""

import math
import time
from datetime import date, datetime
from typing import List, Sequence, Tuple

from backend.app.calcu.schema.distribute_param import DistributionParams, DistributeType
from backend.app.calcu.service.distribute_service import distribute_service
from backend.app.calcu.service.spare_service import spare_service
from backend.app.calcu.service.spare_statistics_service import spare_statistics_service
from backend.app.calcu.crud.crud_spare_statistics_result import (
    spare_statistics_result_dao,
)
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.fit.schema.base_param import ProductParam
from backend.app.fit.schema.fit_param import FitCheckType, FitMethodType
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.fit.utils.convert_model import (
    convert_to_pydantic_model,
)
from backend.app.task.celery import celery_app
from backend.app.task.tasks.base import TaskBase
from backend.common.exception.errors import DataValidationError
from backend.common.log import log
from backend.common.socketio.actions import task_notification
from backend.database.db import async_db_session


def _normalize_model_part_item(
    item: Sequence[str | None],
) -> Tuple[str, str | None, str]:
    if len(item) == 2:
        model, part = item
        return str(model), None, str(part)
    model, product_config_code, part = item
    return str(model), product_config_code, str(part)


@celery_app.task(name="spare_prediction_batch_task", base=TaskBase)
async def spare_prediction_batch_task(
    model_part_list: List[Tuple[str, str | None, str]],
    input_date: str,
    start_date: str,
    end_date: str,
    distribution_type: str | None = None,
    method: str | None = None,
    check: str | None = None,
    source: bool | None = False,
) -> str:
    task_id = spare_prediction_batch_task.request.id
    if not task_id:
        import uuid

        task_id = str(uuid.uuid4())

    start_time = time.time()
    total_count = len(model_part_list)
    success_count = 0
    failed_count = 0
    error_messages = []

    input_date_obj = date.fromisoformat(input_date)
    start_date_obj = date.fromisoformat(start_date)
    end_date_obj = date.fromisoformat(end_date)

    distribution_enum = None
    if distribution_type:
        try:
            distribution_enum = DistributeType(distribution_type)
        except ValueError:
            distribution_enum = None

    method_enum = FitMethodType.MLE
    if method:
        try:
            method_enum = FitMethodType(method)
        except ValueError:
            pass

    check_enum = FitCheckType.BIC
    if check:
        try:
            check_enum = FitCheckType(check)
        except ValueError:
            pass

    try:
        await task_notification(
            msg=f"预计备件数量计算任务开始，共 {total_count} 个组合需要计算"
        )

        for idx, raw_item in enumerate(model_part_list, 1):
            model, product_config_code, part = _normalize_model_part_item(raw_item)
            dimension_desc = (
                f"{model}/{product_config_code}/{part}"
                if product_config_code is not None
                else f"{model}/{part}"
            )

            try:
                tags = await part_strategy_service.part_tag_process(
                    model,
                    part,
                    input_date_obj,
                    product_config_code=product_config_code,
                )

                async with async_db_session() as db:
                    product_data = convert_to_pydantic_model(
                        await product_dao.get_by_model(
                            db,
                            model,
                            product_config_code=product_config_code,
                        ),
                        ProductParam,
                    )

                    existing_fit_results = (
                        await fit_part_dao.get_by_model_and_part_ignore_source(
                            db=db,
                            model=model,
                            part=part,
                            product_config_code=product_config_code,
                            input_date=input_date_obj,
                            method=method_enum,
                            check=check_enum,
                        )
                    )

                    if existing_fit_results:
                        best_fit_part = existing_fit_results[0]
                        distribution_params = convert_to_pydantic_model(
                            best_fit_part, DistributionParams
                        )
                        best_distribution = (
                            await distribute_service.get_distribution_by_params(
                                distribution_params
                            )
                        )
                        if best_distribution is None:
                            raise DataValidationError(
                                msg=f"{dimension_desc} 的拟合结果无法转换为分布对象"
                            )
                        actual_distribution_type = best_fit_part.distribution
                    else:
                        fit_result = await part_fit_service.tag_fit(tags, method_enum)
                        best_distribution = fit_result.best_distribution
                        if best_distribution is None:
                            raise DataValidationError(
                                msg=f"{dimension_desc} 拟合失败，未找到最优分布"
                            )
                        actual_distribution_type = best_distribution.name

                    predicted_spare_num = (
                        await spare_service.get_spare_num_float_by_allotment(
                            db=db,
                            tags=tags,
                            start_date=start_date_obj,
                            end_date=end_date_obj,
                            input_date=input_date_obj,
                            product_data=product_data,
                            distribution=best_distribution,
                            product_config_code=product_config_code,
                        )
                    )
                    predicted_spare_num_int = math.ceil(predicted_spare_num)

                    result_data = {
                        "task_id": task_id,
                        "task_type": "prediction",
                        "model": model,
                        "product_config_code": product_config_code,
                        "part": part,
                        "input_date": input_date_obj,
                        "start_date": start_date_obj,
                        "end_date": end_date_obj,
                        "predicted_spare_num": predicted_spare_num,
                        "predicted_spare_num_int": predicted_spare_num_int,
                        "actual_failure_num": None,
                        "distribution_type": actual_distribution_type,
                        "method": method or FitMethodType.MLE.value,
                        "check": check or FitCheckType.BIC.value,
                        "source": source,
                        "calculation_status": "success",
                        "error_message": None,
                    }

                    new_record = spare_statistics_result_dao.model(**result_data)
                    db.add(new_record)
                    await db.commit()
                    await db.refresh(new_record)

                success_count += 1
            except DataValidationError as e:
                error_msg = getattr(e, "msg", None) or str(e)
                log.error("预计备件数量计算失败 - %s - %s", dimension_desc, error_msg)
                async with async_db_session() as db:
                    result_data = {
                        "task_id": task_id,
                        "task_type": "prediction",
                        "model": model,
                        "product_config_code": product_config_code,
                        "part": part,
                        "input_date": input_date_obj,
                        "start_date": start_date_obj,
                        "end_date": end_date_obj,
                        "predicted_spare_num": None,
                        "predicted_spare_num_int": None,
                        "actual_failure_num": None,
                        "distribution_type": distribution_type,
                        "method": method or FitMethodType.MLE.value,
                        "check": check or FitCheckType.BIC.value,
                        "source": source,
                        "calculation_status": "failed",
                        "error_message": error_msg,
                    }
                    new_record = spare_statistics_result_dao.model(**result_data)
                    db.add(new_record)
                    await db.commit()

                failed_count += 1
                error_messages.append(f"{dimension_desc}: {error_msg}")
            except Exception as e:
                error_msg = str(e)
                log.error("预计备件数量计算异常 - %s - %s", dimension_desc, error_msg)
                async with async_db_session() as db:
                    result_data = {
                        "task_id": task_id,
                        "task_type": "prediction",
                        "model": model,
                        "product_config_code": product_config_code,
                        "part": part,
                        "input_date": input_date_obj,
                        "start_date": start_date_obj,
                        "end_date": end_date_obj,
                        "predicted_spare_num": None,
                        "predicted_spare_num_int": None,
                        "actual_failure_num": None,
                        "distribution_type": distribution_type,
                        "method": method or FitMethodType.MLE.value,
                        "check": check or FitCheckType.BIC.value,
                        "source": source,
                        "calculation_status": "failed",
                        "error_message": error_msg,
                    }
                    new_record = spare_statistics_result_dao.model(**result_data)
                    db.add(new_record)
                    await db.commit()

                failed_count += 1
                error_messages.append(f"{dimension_desc}: {error_msg}")

            if (
                idx % 50 == 0
                or idx == total_count
                or (idx * 100 // max(total_count, 1)) % 10 == 0
            ):
                progress = (idx * 100) // max(total_count, 1)
                await task_notification(
                    msg=f"预计备件数量计算进度: {idx}/{total_count} ({progress}%)"
                )

        execution_time = time.time() - start_time
        summary = (
            f"预计备件数量计算任务完成 - 耗时: {execution_time:.2f}秒 "
            f"总数: {total_count}, 成功: {success_count}, 失败: {failed_count}"
        )
        if error_messages:
            summary += f"\n失败详情（前10条）: {'; '.join(error_messages[:10])}"
            if len(error_messages) > 10:
                summary += f" ... 还有 {len(error_messages) - 10} 条错误"

        log.info(summary)
        await task_notification(msg=summary)
        return summary
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"预计备件数量计算任务异常 - 耗时: {execution_time:.2f}秒 错误: {str(e)}"
        log.error(error_msg)
        await task_notification(msg=error_msg)
        return error_msg


@celery_app.task(name="failure_count_batch_task", base=TaskBase)
async def failure_count_batch_task(
    model_part_list: List[Tuple[str, str | None, str]],
    input_date: str,
    start_date: str,
    end_date: str,
) -> str:
    task_id = failure_count_batch_task.request.id
    if not task_id:
        import uuid

        task_id = str(uuid.uuid4())

    start_time = time.time()
    total_count = len(model_part_list)
    success_count = 0
    failed_count = 0
    error_messages = []

    input_date_obj = date.fromisoformat(input_date)
    start_date_obj = date.fromisoformat(start_date)
    end_date_obj = date.fromisoformat(end_date)

    try:
        await task_notification(
            msg=f"实际故障数量统计任务开始，共 {total_count} 个组合需要统计"
        )

        async with async_db_session() as db:
            for idx, raw_item in enumerate(model_part_list, 1):
                model, product_config_code, part = _normalize_model_part_item(raw_item)
                dimension_desc = (
                    f"{model}/{product_config_code}/{part}"
                    if product_config_code is not None
                    else f"{model}/{part}"
                )
                try:
                    actual_failure_num = (
                        await spare_statistics_service.count_failures_by_model_part(
                            model=model,
                            product_config_code=product_config_code,
                            part=part,
                            start_date=start_date_obj,
                            end_date=end_date_obj,
                        )
                    )
                    part_name = await spare_statistics_service.get_part_name_by_model_part(
                        model=model,
                        product_config_code=product_config_code,
                        part=part,
                        start_date=start_date_obj,
                        end_date=end_date_obj,
                    )

                    prediction_records = await spare_statistics_result_dao.get_all_prediction_records_by_model_part_dates(
                        db=db,
                        model=model,
                        product_config_code=product_config_code,
                        part=part,
                        input_date=input_date_obj,
                        start_date=start_date_obj,
                        end_date=end_date_obj,
                    )

                    if prediction_records:
                        for pred_record in prediction_records:
                            pred_record.actual_failure_num = actual_failure_num
                            if part_name:
                                pred_record.part_name = part_name
                            pred_record.updated_time = datetime.now()
                        await db.commit()
                    else:
                        existing_record = (
                            await spare_statistics_result_dao.get_by_model_part_dates(
                                db=db,
                                model=model,
                                product_config_code=product_config_code,
                                part=part,
                                input_date=input_date_obj,
                                start_date=start_date_obj,
                                end_date=end_date_obj,
                                task_type="failure_count",
                            )
                        )
                        if existing_record:
                            existing_record.actual_failure_num = actual_failure_num
                            if part_name:
                                existing_record.part_name = part_name
                            existing_record.calculation_status = "success"
                            existing_record.error_message = None
                            existing_record.updated_time = datetime.now()
                            await db.commit()
                            await db.refresh(existing_record)
                        else:
                            result_data = {
                                "task_id": task_id,
                                "task_type": "failure_count",
                                "model": model,
                                "product_config_code": product_config_code,
                                "part": part,
                                "input_date": input_date_obj,
                                "start_date": start_date_obj,
                                "end_date": end_date_obj,
                                "predicted_spare_num": None,
                                "actual_failure_num": actual_failure_num,
                                "distribution_type": None,
                                "method": None,
                                "check": None,
                                "source": None,
                                "calculation_status": "success",
                                "error_message": None,
                            }
                            new_record = spare_statistics_result_dao.model(**result_data)
                            if part_name:
                                new_record.part_name = part_name
                            db.add(new_record)
                            await db.commit()
                            await db.refresh(new_record)

                    success_count += 1
                except Exception as e:
                    error_msg = str(e)
                    log.error("实际故障数量统计失败 - %s - %s", dimension_desc, error_msg)
                    existing_record = await spare_statistics_result_dao.get_by_model_part_dates(
                        db=db,
                        model=model,
                        product_config_code=product_config_code,
                        part=part,
                        input_date=input_date_obj,
                        start_date=start_date_obj,
                        end_date=end_date_obj,
                        task_type="failure_count",
                    )

                    if existing_record:
                        existing_record.calculation_status = "failed"
                        existing_record.error_message = error_msg
                        existing_record.updated_time = datetime.now()
                        await db.commit()
                    else:
                        result_data = {
                            "task_id": task_id,
                            "task_type": "failure_count",
                            "model": model,
                            "product_config_code": product_config_code,
                            "part": part,
                            "input_date": input_date_obj,
                            "start_date": start_date_obj,
                            "end_date": end_date_obj,
                            "predicted_spare_num": None,
                            "actual_failure_num": None,
                            "distribution_type": None,
                            "method": None,
                            "check": None,
                            "source": None,
                            "calculation_status": "failed",
                            "error_message": error_msg,
                        }
                        new_record = spare_statistics_result_dao.model(**result_data)
                        db.add(new_record)
                        await db.commit()

                    failed_count += 1
                    error_messages.append(f"{dimension_desc}: {error_msg}")

                if (
                    idx % 50 == 0
                    or idx == total_count
                    or (idx * 100 // max(total_count, 1)) % 10 == 0
                ):
                    progress = (idx * 100) // max(total_count, 1)
                    await task_notification(
                        msg=f"实际故障数量统计进度: {idx}/{total_count} ({progress}%)"
                    )

        execution_time = time.time() - start_time
        summary = (
            f"实际故障数量统计任务完成 - 耗时: {execution_time:.2f}秒 "
            f"总数: {total_count}, 成功: {success_count}, 失败: {failed_count}"
        )
        if error_messages:
            summary += f"\n失败详情（前10条）: {'; '.join(error_messages[:10])}"
            if len(error_messages) > 10:
                summary += f" ... 还有 {len(error_messages) - 10} 条错误"

        log.info(summary)
        await task_notification(msg=summary)
        return summary
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"实际故障数量统计任务异常 - 耗时: {execution_time:.2f}秒 错误: {str(e)}"
        log.error(error_msg)
        await task_notification(msg=error_msg)
        return error_msg
