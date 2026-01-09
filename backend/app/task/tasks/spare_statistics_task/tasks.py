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
from typing import List, Tuple

from backend.app.calcu.schema.distribute_param import DistributeType
from backend.app.calcu.service.spare_service import spare_service
from backend.app.calcu.service.spare_statistics_service import spare_statistics_service
from backend.app.calcu.crud.crud_spare_statistics_result import (
    spare_statistics_result_dao,
)
from backend.app.fit.schema.fit_param import FitMethodType, FitCheckType
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.utils.convert_model import convert_to_pydantic_model
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.fit.schema.base_param import ProductParam
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.calcu.service.distribute_service import distribute_service
from backend.app.calcu.schema.distribute_param import DistributionParams
from backend.app.task.celery import celery_app
from backend.app.task.tasks.base import TaskBase
from backend.common.exception.errors import DataValidationError
from backend.common.log import log
from backend.common.socketio.actions import task_notification
from backend.database.db import async_db_session


@celery_app.task(name="spare_prediction_batch_task", base=TaskBase)
async def spare_prediction_batch_task(
    model_part_list: List[Tuple[str, str]],
    input_date: str,
    start_date: str,
    end_date: str,
    distribution_type: str | None = None,
    method: str | None = None,
    check: str | None = None,
    source: bool | None = False,
) -> str:
    """
    预计备件数量批量计算任务
    每次计算都新增记录（保留历史），按 task_id 区分批次

    :param model_part_list: 型号+零部件组合列表 [(model, part), ...]
    :param input_date: 拟合输入日期 YYYY-MM-DD
    :param start_date: 计算开始日期 YYYY-MM-DD
    :param end_date: 计算结束日期 YYYY-MM-DD
    :param distribution_type: 分布类型（可选）
    :param method: 拟合方法（可选）
    :param check: 拟合优度检验（可选）
    :param source: 拟合来源（可选）
    :return: 任务执行摘要
    """
    task_id = spare_prediction_batch_task.request.id
    # 如果获取不到任务ID，生成一个唯一的备选ID
    if not task_id:
        import uuid

        task_id = str(uuid.uuid4())
    start_time = time.time()
    total_count = len(model_part_list)
    success_count = 0
    failed_count = 0
    error_messages = []

    # 参数转换
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
            method_enum = FitMethodType.MLE

    check_enum = FitCheckType.BIC
    if check:
        try:
            check_enum = FitCheckType(check)
        except ValueError:
            check_enum = FitCheckType.BIC

    try:
        await task_notification(
            msg=f"预计备件数量计算任务开始: 共 {total_count} 个组合需要计算"
        )

        for idx, (model, part) in enumerate(model_part_list, 1):
            try:
                # 1. 获取标签数据（无论是否使用已有拟合结果，都需要标签数据来计算备件数量）
                tags = await part_strategy_service.part_tag_process(
                    model, part, input_date_obj
                )

                # 2. 获取产品信息和拟合结果（在同一数据库会话中）
                async with async_db_session() as db:
                    product_data = convert_to_pydantic_model(
                        await product_dao.get_by_model(db, model), ProductParam
                    )

                    # 3. 先检查 fit_part 表中是否有相同型号+零部件+input_date 的拟合结果（忽略 source，查询所有 source 值）
                    existing_fit_results = (
                        await fit_part_dao.get_by_model_and_part_ignore_source(
                            db=db,
                            model=model,
                            part=part,
                            input_date=input_date_obj,
                            method=method_enum,
                            check=check_enum,
                        )
                    )

                    if existing_fit_results and len(existing_fit_results) > 0:
                        # 3.1 如果存在拟合结果，选择最优的（第一个就是按 check 类型排序的最优结果）
                        best_fit_part = existing_fit_results[0]
                        # 转换为分布对象
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
                                msg=f"型号{model}的零部件{part}的拟合结果无法转换为分布对象"
                            )
                        actual_distribution_type = best_fit_part.distribution
                        log.info(
                            f"使用已有拟合结果 - 型号:{model}, 零部件:{part}, "
                            f"分布类型:{actual_distribution_type}, "
                            f"拟合方法:{method_enum.value}, 检验方法:{check_enum.value}"
                        )
                    else:
                        # 3.2 如果没有拟合结果，执行拟合获取最优分布
                        fit_result = await part_fit_service.tag_fit(tags, method_enum)
                        best_distribution = fit_result.best_distribution
                        if best_distribution is None:
                            raise DataValidationError(
                                msg=f"型号{model}的零部件{part}拟合失败，未找到最优分布"
                            )
                        actual_distribution_type = best_distribution.name
                        log.info(
                            f"执行新拟合 - 型号:{model}, 零部件:{part}, "
                            f"分布类型:{actual_distribution_type}"
                        )

                    # 4. 使用最优分布计算备件数量（计算精确小数结果）
                    predicted_spare_num = (
                        await spare_service.get_spare_num_float_by_allotment(
                            db=db,
                            tags=tags,
                            start_date=start_date_obj,
                            end_date=end_date_obj,
                            input_date=input_date_obj,
                            product_data=product_data,
                            distribution=best_distribution,
                        )
                    )
                    # 从小数结果计算取整后的整数结果
                    predicted_spare_num_int = math.ceil(predicted_spare_num)

                    # 5. 立即保存计算结果到数据库（逐条保存）
                    # 注意：part_name 不在预测任务中设置，使用 init=False，由实际故障数量任务填充
                    result_data = {
                        "task_id": task_id,
                        "task_type": "prediction",
                        "model": model,
                        "part": part,
                        "input_date": input_date_obj,
                        "start_date": start_date_obj,
                        "end_date": end_date_obj,
                        "predicted_spare_num": predicted_spare_num,  # 精确小数结果
                        "predicted_spare_num_int": predicted_spare_num_int,  # 取整整数结果
                        "actual_failure_num": None,
                        "distribution_type": actual_distribution_type,  # 使用实际拟合得到的最优分布类型
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
                log.error(
                    f"预计备件数量计算失败 - 型号:{model}, 零部件:{part}, 错误:{error_msg}"
                )

                # 立即保存失败记录到数据库
                # 注意：part_name 不在预测任务中设置，使用 init=False
                async with async_db_session() as db:
                    result_data = {
                        "task_id": task_id,
                        "task_type": "prediction",
                        "model": model,
                        "part": part,
                        "input_date": input_date_obj,
                        "start_date": start_date_obj,
                        "end_date": end_date_obj,
                        "predicted_spare_num": None,  # 精确小数结果
                        "predicted_spare_num_int": None,  # 取整整数结果
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
                error_messages.append(f"{model}+{part}: {error_msg}")

            except Exception as e:
                error_msg = str(e)
                log.error(
                    f"预计备件数量计算异常 - 型号:{model}, 零部件:{part}, 错误:{error_msg}"
                )

                # 立即保存异常记录到数据库
                # 注意：part_name 不在预测任务中设置，使用 init=False
                async with async_db_session() as db:
                    result_data = {
                        "task_id": task_id,
                        "task_type": "prediction",
                        "model": model,
                        "part": part,
                        "input_date": input_date_obj,
                        "start_date": start_date_obj,
                        "end_date": end_date_obj,
                        "predicted_spare_num": None,  # 精确小数结果
                        "predicted_spare_num_int": None,  # 取整整数结果
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
                error_messages.append(f"{model}+{part}: {error_msg}")

            # 每处理10%或每50个推送一次进度
            if (
                idx % 50 == 0
                or idx == total_count
                or (idx * 100 // total_count) % 10 == 0
            ):
                progress = (idx * 100) // total_count
                await task_notification(
                    msg=f"预计备件数量计算进度: {idx}/{total_count} ({progress}%)"
                )

        end_time = time.time()
        execution_time = end_time - start_time

        summary = (
            f"预计备件数量计算任务完成 - 耗时: {execution_time:.2f}秒, "
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
        end_time = time.time()
        execution_time = end_time - start_time
        error_msg = (
            f"预计备件数量计算任务异常 - 耗时: {execution_time:.2f}秒, 错误: {str(e)}"
        )
        log.error(error_msg)
        await task_notification(msg=error_msg)
        return error_msg


@celery_app.task(name="failure_count_batch_task", base=TaskBase)
async def failure_count_batch_task(
    model_part_list: List[Tuple[str, str]],
    input_date: str,
    start_date: str,
    end_date: str,
) -> str:
    """
    实际故障数量批量统计任务
    相同条件覆盖更新

    :param model_part_list: 型号+零部件组合列表 [(model, part), ...]
    :param input_date: 拟合输入日期 YYYY-MM-DD
    :param start_date: 统计开始日期 YYYY-MM-DD
    :param end_date: 统计结束日期 YYYY-MM-DD
    :return: 任务执行摘要
    """
    task_id = failure_count_batch_task.request.id
    # 如果获取不到任务ID，生成一个唯一的备选ID
    if not task_id:
        import uuid

        task_id = str(uuid.uuid4())
    start_time = time.time()
    total_count = len(model_part_list)
    success_count = 0
    failed_count = 0
    error_messages = []

    # 参数转换
    input_date_obj = date.fromisoformat(input_date)
    start_date_obj = date.fromisoformat(start_date)
    end_date_obj = date.fromisoformat(end_date)

    try:
        await task_notification(
            msg=f"实际故障数量统计任务开始: 共 {total_count} 个组合需要统计"
        )

        async with async_db_session() as db:
            for idx, (model, part) in enumerate(model_part_list, 1):
                try:
                    # 统计实际故障数量
                    actual_failure_num = (
                        await spare_statistics_service.count_failures_by_model_part(
                            model=model,
                            part=part,
                            start_date=start_date_obj,
                            end_date=end_date_obj,
                        )
                    )

                    # 获取零部件名称（从故障表中获取第一个出现的名称）
                    part_name = (
                        await spare_statistics_service.get_part_name_by_model_part(
                            model=model,
                            part=part,
                            start_date=start_date_obj,
                            end_date=end_date_obj,
                        )
                    )

                    # 优先查找并更新预测记录（task_type="prediction"）
                    prediction_records = await spare_statistics_result_dao.get_all_prediction_records_by_model_part_dates(
                        db=db,
                        model=model,
                        part=part,
                        input_date=input_date_obj,
                        start_date=start_date_obj,
                        end_date=end_date_obj,
                    )

                    if prediction_records:
                        # 更新所有匹配的预测记录的 actual_failure_num 和 part_name
                        updated_count = 0
                        for pred_record in prediction_records:
                            pred_record.actual_failure_num = actual_failure_num
                            if part_name:
                                pred_record.part_name = part_name
                            pred_record.updated_time = datetime.now()
                            updated_count += 1
                        await db.commit()
                        log.info(
                            f"更新了 {updated_count} 条预测记录的 actual_failure_num 和 part_name - "
                            f"型号:{model}, 零部件:{part}, 零部件名称:{part_name}"
                        )
                    else:
                        # 如果没有找到预测记录，检查是否存在 failure_count 记录
                        existing_record = (
                            await spare_statistics_result_dao.get_by_model_part_dates(
                                db=db,
                                model=model,
                                part=part,
                                input_date=input_date_obj,
                                start_date=start_date_obj,
                                end_date=end_date_obj,
                                task_type="failure_count",
                            )
                        )

                        if existing_record:
                            # 更新现有 failure_count 记录
                            existing_record.actual_failure_num = actual_failure_num
                            if part_name:
                                existing_record.part_name = part_name
                            existing_record.calculation_status = "success"
                            existing_record.error_message = None
                            existing_record.updated_time = datetime.now()
                            await db.commit()
                            await db.refresh(existing_record)
                        else:
                            # 创建新的 failure_count 记录（没有预测记录时）
                            # 注意：part_name 使用 init=False，需要在创建后通过属性赋值设置
                            result_data = {
                                "task_id": task_id,
                                "task_type": "failure_count",
                                "model": model,
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
                            new_record = spare_statistics_result_dao.model(
                                **result_data
                            )
                            # 设置 part_name（因为使用了 init=False，需要通过属性赋值）
                            if part_name:
                                new_record.part_name = part_name
                            db.add(new_record)
                            await db.commit()
                            await db.refresh(new_record)

                    success_count += 1

                except Exception as e:
                    error_msg = str(e)
                    log.error(
                        f"实际故障数量统计失败 - 型号:{model}, 零部件:{part}, 错误:{error_msg}"
                    )

                    # 检查是否存在记录，如果存在则更新状态
                    existing_record = (
                        await spare_statistics_result_dao.get_by_model_part_dates(
                            db=db,
                            model=model,
                            part=part,
                            input_date=input_date_obj,
                            start_date=start_date_obj,
                            end_date=end_date_obj,
                            task_type="failure_count",
                        )
                    )

                    if existing_record:
                        existing_record.calculation_status = "failed"
                        existing_record.error_message = error_msg
                        existing_record.updated_time = datetime.now()
                        await db.commit()
                    else:
                        # 创建失败记录
                        # 注意：part_name 使用 init=False，不需要在创建时设置
                        result_data = {
                            "task_id": task_id,
                            "task_type": "failure_count",
                            "model": model,
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
                    error_messages.append(f"{model}+{part}: {error_msg}")

                # 每处理10%或每50个推送一次进度
                if (
                    idx % 50 == 0
                    or idx == total_count
                    or (idx * 100 // total_count) % 10 == 0
                ):
                    progress = (idx * 100) // total_count
                    await task_notification(
                        msg=f"实际故障数量统计进度: {idx}/{total_count} ({progress}%)"
                    )

        end_time = time.time()
        execution_time = end_time - start_time

        summary = (
            f"实际故障数量统计任务完成 - 耗时: {execution_time:.2f}秒, "
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
        end_time = time.time()
        execution_time = end_time - start_time
        error_msg = (
            f"实际故障数量统计任务异常 - 耗时: {execution_time:.2f}秒, 错误: {str(e)}"
        )
        log.error(error_msg)
        await task_notification(msg=error_msg)
        return error_msg
