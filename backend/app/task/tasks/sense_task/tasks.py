#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：reis-backend 
@File    ：tasks.py.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/4/25 10:29 
'''
from backend.app.sense.schema.sense_param import CreateSenseSortInParam
from backend.app.sense.service.sense_predict_service import sense_predict_service
from backend.app.task.celery import celery_app
from backend.common.exception.errors import DataValidationError


@celery_app.task(name='sense_sort_task',time_limit=3600,max_retries=3,acks_late=True,
                 reject_on_worker_lost=True )
async def sense_sort_task(model: str, part: str, stage: str,process_name: str,
                                   check_project: str, check_bezier: str,  start_time: str,
                                   end_time: str,extra_material_names: str) -> str:
    """
    后台任务:手动触发
    单零部件级别敏感度分析任务

    :param model: 产品型号
    :param part: 零部件名称
    :param stage: 检修阶段
    :param process_name: 工序名称
    :param check_project: 检验区位
    :param check_bezier: 检验项点
    :param start_time: 计算开始时间
    :param end_time: 计算结束时间
    :param extra_material_names: 配件/原材料名称
    """
    try:
        fit_param = CreateSenseSortInParam(model=model, part=part, stage=stage,process_name=process_name,
                                           check_project=check_project, check_bezier=check_bezier,start_time=start_time,
                                           end_time=end_time,extra_material_names=extra_material_names)
        await sense_predict_service.create(obj=fit_param)

        return f"Task completed for model: {model}, part: {part}"
    except DataValidationError as e:
        return f'Error processing model {model}, part {part}: {str(e.msg)}'
    except Exception as e:
        return f'Unexpected Error processing model {model}, part {part}: {str(e)}'