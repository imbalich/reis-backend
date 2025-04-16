#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：product_tag_process_service.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/16 17:09
"""

from datetime import date
from typing import Any

from backend.app.datamanage.model import Despatch, Failure, Product
from backend.app.fit.schema.base_param import DespatchParam, FailureParam
from backend.app.fit.service.tag_process_service import TagProcessService
from backend.app.fit.utils.time_utils import dateutils


class ProductTagProcessService(TagProcessService):
    async def process_data(
            self,
            despatch_data: list[Despatch],
            failure_data: list[Failure],
            product_data: Product,
            input_date: str | date = None,
            **kwargs: Any,
    ) -> list[list]:
        """
        处理数据，包括发运数据和故障数据，并计算标签数据。
        :param despatch_data: 发运数据列表
        :param failure_data: 故障数据列表
        :param product_data: 产品基本信息(年运行天数,天运行小时数,平均速度)
        :param input_date: 输入日期，可以是字符串格式或日期格式，默认为当前日期。
        :return :{'product_model': '产品型号', 'tags':[[标签],[标签]]}
        """
        despatch_data = await self.process_despatch_data(despatch_data, input_date)
        failure_data = await self.process_failure_data(failure_data, input_date)
        # 1.发运根据发运数据先创建基础数据结构
        container = await self.container_create(despatch_data)
        # 2.故障数据向基础结构中补充
        container = await self.container_inspect(container, failure_data)
        # 3.计算标签数据
        tags = await self.tag_create(container, product_data, input_date)

        return tags

    async def process_despatch_data(self, despatch_data: list[Despatch], input_date: date):
        """
        处理发运数据，根据产品型号和最早的发运时间保留记录
        :param despatch_data: 发运数据列表
        :param input_date: 输入日期
        :return:每一组数据中时间最晚的那一条记录列表
        """
        return await super().process_despatch_data(despatch_data, input_date)

    async def process_failure_data(self, failure_data: list[Failure], input_date: date):
        """
        处理故障数据，按时间顺序排序，降序。
        :param failure_data: 故障数据列表
        :param input_date: 输入日期
        :return: 按时间顺序排序后的故障数据列表
        """
        return await super().process_failure_data(failure_data, input_date)

    @staticmethod
    async def container_create(despatch_data: list[DespatchParam]) -> dict[str, dict[str, Any]]:
        """
        创建一个字典，其键为 Despatch 对象的 identifier，值为包含 Despatch 信息的字典。
        参数:
            despatch_data (List[Despatch]): 包含多个 Despatch 对象的列表。

        返回值:
            Dict[str, Dict[str, Any]]: 一个字典，其键为 Despatch 对象的 identifier（字符串类型），
            值为另一个字典，包含 Despatch 对象的标识符、生命周期时间、故障列表和故障部件列表。
        """
        item_dict = {}  # 初始化一个空字典，用于存储结果
        for despatch in despatch_data:  # 遍历输入的 despatch_data 列表
            cur = {  # 为当前 despatch 对象创建一个新的字典
                'identifier': despatch.identifier,  # 添加 despatch 的标识符
                'despatch_date': despatch.life_cycle_time,  # 添加 despatch 的生命周期时间
                # 假设将生命周期时间作为故障列表的一部分（可能需要根据实际情况调整）
                'fault_date_list': [
                    despatch.life_cycle_time
                ],
                'fault_part_list': [],  # 初始化一个空列表，用于存储故障部件（可能需要后续填充）
            }
            item_dict[despatch.identifier] = cur  # 将当前 despatch 的字典添加到 item_dict 中，以 identifier 为键
        return item_dict  # 返回填充好的 item_dict

    @staticmethod
    async def container_inspect(
            container: dict[str, dict[str, Any]], failure_data: list[FailureParam]
    ) -> dict[str, dict[str, Any]]:
        """
        在 container 中检查故障数据，并更新 fault_list 和 fault_part_list。
        参数:
            container (Dict[str, Dict[str, Any]]): 包含 Despatch 信息的字典。
            failure_data (List[Failure]): 包含多个故障数据对象的列表。
        返回值:
            Dict[str, Dict[str, Any]]: 更新后的 container 字典。
        """
        for failure in failure_data:
            # 确保 product_number 是字符串类型
            product_number = str(failure.product_number) if failure.product_number is not None else ''
            if not product_number:  # 跳过空的产品编号
                continue
            discovery_date = failure.discovery_date
            # 确保 fault_part_number 是有效值
            failure_part = failure.fault_part_number if failure.fault_part_number not in [None, '', '无'] else '#'

            if product_number in container:
                # 向 fault_list 中插入发现时间
                container[product_number]['fault_date_list'].append(discovery_date)
                # 向 fault_part_list 中插入故障部件
                container[product_number]['fault_part_list'].append(failure_part)
            else:
                # 如果 container 中不存在 product_number
                # 添加一个新的字典,fault_list中插入[发运时间,发现时间],fault_part_list插入故障部件
                # 加一个判断，如果发现时间大于发运时间，不插入
                # 新表利用production_date(转换后的manufacturing_date)字段来判断
                if discovery_date < failure.manufacturing_date:
                    continue
                cur = {
                    'identifier': product_number,
                    'despatch_date': failure.manufacturing_date,
                    # 初始化 fault_list，插入[发运时间,发现时间]
                    'fault_date_list': [
                        failure.manufacturing_date,
                        discovery_date,
                    ],
                    'fault_part_list': [failure_part],  # 初始化 fault_part_list，插入故障部件
                }
                # 将新字典添加到 container 中
                container[product_number] = cur
        return container

    @staticmethod
    async def tag_create(
            container: dict[str, dict[str, Any]], product_data: Product, input_date: date
    ) -> list[list[Any]]:
        """
        根据给定的容器（包含产品编号和故障日期列表）和产品数据，为每个故障日期对创建标签列表。

        Args:
            container (Dict[str, Dict[str, Any]]): 包含产品编号（键）和对应数据的字典。
            每个对应数据也是一个字典，包含'fault_date_list'键，其值为一个日期列表。
            product_data (Product): 产品数据对象，包含产品的相关信息（如年工作日数、平均工作时间等）。
            input_date (date): 当前的输入日期，用于添加到'fault_date_list'中作为最后一个故障日期。

        Returns:
            List[List[Any]]: 一个二维列表，其中每个子列表代表一个标签记录。
            每个标签记录包含以下元素：
            - 编号（产品编号）
            - 前一日期（前一个故障日期）
            - 后一日期（当前故障日期）
            - 间隔天数（前后两个故障日期之间的天数）
            - 累计运行时间（通过某个计算函数得出的累计运行时间）
            - 状态标签（'suspense' 或 'failure'）
        """
        result = []
        # 循环遍历 container 容器中的每个键和值
        for bh, context in container.items():
            context['fault_date_list'].append(input_date)
            # 再按照升序排一次
            context['fault_date_list'] = sorted(context['fault_date_list'], key=lambda x: x, reverse=False)
            for i in range(1, len(context['fault_date_list'])):
                diff = context['fault_date_list'][i] - context['fault_date_list'][i - 1]
                if diff.days == 0:
                    continue
                t = dateutils.run_time(diff.days - 90, product_data.year_days, product_data.avg_worktime)
                cur = [bh, context['fault_date_list'][i - 1], context['fault_date_list'][i], diff.days, t]
                if i == len(context['fault_date_list']) - 1:
                    cur.append('suspense')
                else:
                    cur.append('failure')
                result.append(cur)
        return result


product_tag_process_service: ProductTagProcessService = ProductTagProcessService()
