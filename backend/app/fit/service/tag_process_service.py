#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：tag_process_service.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/2 16:53
"""

from abc import ABC, abstractmethod
from datetime import date
from itertools import groupby
from operator import attrgetter

from pydantic import ValidationError

from backend.app.datamanage.model import Despatch, Failure
from backend.app.fit.schema.base_param import DespatchParam, FailureParam


class TagProcessService(ABC):
    @abstractmethod
    async def process_data(self, *args, **kwargs):
        """
        处理数据的方法。
        应在子类中实现。
        """
        raise NotImplementedError('Subclasses must implement this method')

    @abstractmethod
    async def process_despatch_data(self, despatch_data: list[Despatch], input_date: date) -> list[DespatchParam]:
        """
        处理发运数据，根据产品型号和最早的发运时间保留记录
        :param despatch_data: 发运数据列表
        :param input_date: 输入日期
        :return: 每一组数据中时间最晚的那一条记录列表
        """
        processed_data = []
        error_data = []
        for despatch in despatch_data:
            try:
                # 使用 Pydantic 模型进行验证和转换
                validated_despatch = DespatchParam.model_validate(despatch)
                # 过滤抛掉input_date之后的数据
                if validated_despatch.life_cycle_time <= input_date:
                    # 将验证后的 Pydantic 模型实例添加到处理列表中
                    processed_data.append(validated_despatch)
            except ValidationError as e:
                # 处理验证错误
                error_msg = f'数据验证失败 (ID: {getattr(despatch, "id", "Unknown")}): {str(e)}'
                # 将错误信息和原始数据添加到错误列表中
                error_data.append({'original_data': despatch, 'error_message': error_msg})
        # 发运数据取时间 LIFE_CYCLE_TIME 最近的那一条
        # 降序排序是为了确保最晚的日期在分组的第一个位置
        sorted_data = sorted(processed_data, key=lambda x: x.life_cycle_time, reverse=True)
        # 使用 groupby 分组，并保留每个组中的第一个元素（即时间最晚的）
        result = []
        for _, group in groupby(sorted_data, key=attrgetter('identifier')):
            group_list = list(group)
            # 第一个元素就是时间最晚的记录
            result.append(group_list[0])

        return result

    @abstractmethod
    async def process_failure_data(self, failure_data: list[Failure], input_date: date) -> list[FailureParam]:
        """
        处理故障数据，按时间顺序排序，降序。
        :param failure_data: 故障数据列表
        :param input_date: 输入日期
        :return: 按时间顺序排序后的故障数据列表
        """
        processed_data = []
        error_data = []
        for failure in failure_data:
            try:
                # 使用 FailureParam 模型来验证和转换数据
                processed_failure = FailureParam.model_validate(failure)
                if (
                    processed_failure.discovery_date <= input_date and processed_failure.manufacturing_date <= input_date
                ):
                    # 将验证后的 FailureParam 模型实例添加到处理列表中
                    processed_data.append(processed_failure)
            except ValidationError as e:
                # 处理验证错误
                error_msg = f'数据验证失败 (ID: {getattr(failure, "report_id", "Unknown")}): {str(e)}'
                # 将错误信息和原始数据添加到错误列表中
                error_data.append({'original_data': failure, 'error_message': error_msg})

        # 过滤掉为空的故障数据
        filtered_failure_data = [
            failure for failure in processed_data if failure.discovery_date != '' and failure.manufacturing_date != ''
        ]
        # 按故障数据中的时间属性升序排序
        sorted_failure_data = sorted(filtered_failure_data, key=lambda x: x.discovery_date, reverse=False)

        return sorted_failure_data
