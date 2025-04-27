#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：sense_predict_service.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/4/1 16:39
"""

from datetime import date, datetime
from typing import Union
import json

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.sense.utils.time_utils import dateutils
from backend.app.sense.crud.crud_sense import sense_dao
from backend.app.sense.schema.sense_param import CreateSenseSortInParam
from backend.app.sense.service.model_process_service import ModelProcessService
from backend.app.sense.service.process_service import ProcessService
from backend.app.sense.utils.convert_model import convert_to_sense_sort_params
from backend.app.sense.utils.data_check_utils import data_check_utils
from backend.database.db import async_db_session
from backend.common.exception import errors


class SensePredictService:

    @staticmethod
    async def create(*, obj: CreateSenseSortInParam) -> None:
        """
        单个产品敏感度分析预测：
        根据输入条件检查是否存在最近7天内的记录，如果存在，不再进行预测
        如果不存在，根据条件预测
        """
        # 处理 input_date 参数
        start_time = dateutils.validate_and_parse_date(obj.start_time)
        end_time = dateutils.validate_and_parse_date(obj.end_time)
        if start_time is not None and end_time is not None:
            range_time = [start_time, end_time]
        else:
            range_time = None
        async with async_db_session() as db:
            if await SensePredictService._recent_sense_exists(db, obj.model, obj.part, obj.stage, obj.process_name,
                                                              obj.check_project, obj.check_bezier,
                                                              obj.extra_material_names, start_time, end_time):
                return

        await SensePredictService.sense_predict(obj.model, obj.part, obj.stage, obj.process_name, obj.check_project,
                                                obj.check_bezier, range_time, obj.extra_material_names)

    @staticmethod
    async def _recent_sense_exists(db: AsyncSession, model: str, part: str, stage: str, process_name: str,
                                   check_project: str, check_bezier: str, extra_material_names: str, start_time: date,
                                   end_time: date) -> bool:
        sense_sort = await sense_dao.get_last(db, model, part, stage, process_name, check_project, check_bezier,
                                              extra_material_names, start_time, end_time)
        if sense_sort and sense_sort.created_time:
            days_difference = (datetime.now().date() - sense_sort.created_time).days
            return days_difference < 7
        return False

    @staticmethod
    async def sense_predict(
            model: str,
            part: str,
            stage: str,
            process_name: str,
            check_project: str,
            check_bezier: str,
            time_range: list[str],
            extra_material_names: str,
    ) -> None:
        # 1.检查故障信息Failure数量
        fault_check = await data_check_utils.check_model_and_part_in_failure(model, part)
        if not fault_check:
            raise errors.DataValidationError(msg=f"型号{model}+零部件{part}的故障信息数量不足")
        # 2.检查配置信息
        config_check = await data_check_utils.check_model_and_part_in_configuration(model, part)
        if not config_check:
            raise errors.DataValidationError(msg=f"型号{model}+零部件{part}的配置信息不存在")
        # 3.检查PC信息
        pc_check = await data_check_utils.check_model_and_part_in_pc(model)
        if not pc_check:
            raise errors.DataValidationError(msg=f"型号{model}的PC信息不存在")
        async with async_db_session() as db:
            async with db.begin():
                tags = await ProcessService.process(model, part, stage, process_name, check_project, check_bezier,
                                                    time_range, extra_material_names)
                if tags['data'] is None:
                    raise errors.DataValidationError(msg=f"型号{model}+零部件{part}的故障数据量不足")
                fit = await ModelProcessService.model_process(tags)
                sort_params = convert_to_sense_sort_params(fit, model, part, stage, process_name, check_project,
                                                           check_bezier, time_range, extra_material_names)
                await sense_dao.creates(db, sort_params)

    @staticmethod
    async def get_sense_sort_result(
            model: str,
            part: str,
            stage: str,
            process_name: str,
            check_project: str,
            check_bezier: str,
            extra_material_names: str,
            start_time: Union[str, date] = None,
            end_time: Union[str, date] = None,
    ):
        async with async_db_session() as db:

            sense_sort = await sense_dao.get_by_model_and_part(db, model, part, stage, process_name, check_project,
                                                               check_bezier, extra_material_names, start_time, end_time)
            for sense in sense_sort:
                categorical_dict = json.loads(sense.categorical_analysis)
                category_values = {}
                for category, items in categorical_dict.items():
                    raw_values = [item['value'] for item in items]
                    category_values[category] = raw_values

                sense.categorical_analysis = json.dumps(category_values, ensure_ascii=False)

            return sense_sort


sense_predict_service: SensePredictService = SensePredictService()
