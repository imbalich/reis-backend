#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RCM计算后台任务
"""

import time
from datetime import datetime

from backend.app.rcm.service.rcm_calculation_service import rcm_calculation_service
from backend.app.task.tasks.base import TaskBase
from backend.app.task.celery import celery_app
from backend.common.log import log


@celery_app.task(name="rcm_batch_calculation_task", base=TaskBase)
async def rcm_batch_calculation_task() -> str:
    """
    RCM
    后台任务:RCM批量计算

    计算所有RCM基础数据并保存结果到数据库
    :return: 任务执行结果
    """
    start_time = time.time()

    try:
        log.info("开始执行RCM批量计算任务")

        # 执行批量计算
        result = await rcm_calculation_service.calculate_batch_rcm()

        end_time = time.time()
        execution_time = end_time - start_time

        if result["status"] == "success":
            summary = (
                f"RCM批量计算完成 - 耗时: {execution_time:.2f}秒, "
                f"总计算数: {result['total']}, "
                f"成功: {result['success']}, "
                f"失败: {result['failed']}"
            )
            log.info(summary)
            return summary
        else:
            error_msg = f"RCM批量计算失败: {result.get('error', '未知错误')}"
            log.error(error_msg)
            return error_msg

    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        error_msg = f"RCM批量计算异常 - 耗时: {execution_time:.2f}秒, 错误: {str(e)}"
        log.error(error_msg)
        return error_msg
