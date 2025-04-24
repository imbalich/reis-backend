#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : part_tag_process_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/18 11:45
"""

from datetime import date
from typing import Any

from backend.app.datamanage.model import Despatch, Ebom, Failure, Product
from backend.app.fit.schema.base_param import DespatchParam, EbomParam, FailureParam, RepairParam, ReplaceParam
from backend.app.fit.service.tag_process_service import TagProcessService
from backend.app.fit.utils.time_utils import dateutils


class PartTagProcessService(TagProcessService):
    async def process_data(
        self,
        despatch_data: list[Despatch],
        failure_data: list[Failure],
        product_data: Product,
        bom_data: Ebom,
        input_date: str | date = None,
        **kwargs: Any,
    ) -> list[list]:
        if 'replace_data' not in kwargs:
            # 非必换件
            return await self._process_non_essential(despatch_data, failure_data, product_data, bom_data, input_date)
        else:
            # 必换件
            return await self._process_essential(
                despatch_data,
                failure_data,
                product_data,
                bom_data,
                kwargs['replace_data'],
                kwargs['repair_data'],
                kwargs['repair_despatch_data'],
                input_date,
            )

    async def _process_non_essential(
        self,
        despatch_data: list[Despatch],
        failure_data: list[Failure],
        product_data: Product,
        bom_data: Ebom,
        input_date: str | date = None,
    ) -> list[list]:
        # 处理基础数据
        despatch_data = await self.process_despatch_data(despatch_data, input_date)
        failure_data = await self.process_failure_data(failure_data, input_date)
        bom_data = EbomParam.model_validate(bom_data) if not isinstance(bom_data, EbomParam) else bom_data
        # 1.发运根据发运数据先创建基础数据结构
        container = await self.container_create(despatch_data, bom_data)
        # 2.故障数据根据容器进行补充
        container = await self.container_inspect(container, failure_data, bom_data)
        # 3.故障数据填充
        container, error_info_list = await self.container_insert_non_essential(container, failure_data)
        tags = await self.tag_create_non_essential(container, product_data, input_date)
        data = {'tags': tags}
        if error_info_list:
            data['error_info_list'] = error_info_list
        return data['tags']

    async def _process_essential(
        self,
        despatch_data: list[Despatch],
        failure_data: list[Failure],
        product_data: Product,
        bom_data: Ebom,
        replace_data: list[ReplaceParam],
        repair_data: list[RepairParam],
        repair_despatch_data: list[Despatch],
        input_date: str | date = None,
    ) -> list[list]:
        # 1.发运根据发运数据先创建基础数据结构
        despatch_data = await self.process_despatch_data(despatch_data, input_date)
        failure_data = await self.process_failure_data(failure_data, input_date)
        bom_data = EbomParam.model_validate(bom_data) if not isinstance(bom_data, EbomParam) else bom_data
        repair_despatch_data = await self.process_despatch_data(repair_despatch_data, input_date)
        # 1.发运根据发运数据先创建基础数据结构
        container = await self.container_create(despatch_data, bom_data)
        # 2.故障数据根据容器进行补充
        container = await self.container_inspect(container, failure_data, bom_data)
        # 3.等级修发运填充
        container, error_info_list_repair = await self.container_insert_essential_repair(
            container, repair_despatch_data
        )
        # 4.故障数据插入
        container, error_info_list_failure = self.container_insert_non_essential(container, failure_data)
        tags = await self.tag_create_essential(container, product_data, input_date)
        results = {'tags': tags}
        if error_info_list_repair:
            results['error_info_list_repair'] = error_info_list_repair
        if error_info_list_failure:
            results['error_info_list_failure'] = error_info_list_failure
        return results['tags']

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
    async def container_create(despatch_data: list[DespatchParam], bom_data: EbomParam) -> dict[str, Any]:
        # 1.发运根据发运数据先创建基础数据结构
        result = {
            'model': bom_data.prd_no,  # 产品型号
            'part_name': bom_data.y8_matname,  # 零部件名称
            'part_code': bom_data.y8_matbnum1,  # 零部件物料编码
            'part_container': {},  # 零部件的集合
        }
        for despatch in despatch_data:
            product = {
                'source': 'despatch_data',
                'despatch_date': despatch.life_cycle_time,  # 该产品发运时间
                'sub_container': {},  # 子容器，所有零部件信息
            }
            for i in range(int(bom_data.bl_quantity)):
                material_code_virtual = f'{bom_data.y8_matbnum1}-{i + 1}'
                product['sub_container'][material_code_virtual] = {
                    'fault_date_list': [(despatch.life_cycle_time, 'despatch', 1)],  # 故障日期列表
                    'fault_part_list': [],  # 故障件列表
                }
            result['part_container'][despatch.identifier] = product
        return result

    @staticmethod
    async def container_inspect(
        container: dict[str, Any], failure_data: list[FailureParam], bom_data: EbomParam
    ) -> dict[str, Any]:
        # 故障数据补充容器
        for failure in failure_data:
            if failure.product_number not in container['part_container']:
                # 向container内追加
                product = {
                    'source': 'failure_data',
                    'despatch_date': failure.manufacturing_date,  # 该产品发运时间
                    'sub_container': {},  # 子容器，所有零部件信息
                }
                for i in range(int(bom_data.bl_quantity)):
                    material_code_virtual = f'{bom_data.y8_matbnum1}-{i + 1}'
                    product['sub_container'][material_code_virtual] = {
                        'fault_date_list': [(failure.manufacturing_date, 'despatch', 1)],  # 故障日期列表
                        'fault_part_list': [],  # 故障件列表
                    }
                container['part_container'][failure.product_number] = product
        return container

    @staticmethod
    async def container_insert_non_essential(
        container: dict[str, Any], failure_data: list[FailureParam]
    ) -> tuple[dict, list]:
        """
        非必换件故障数据插入
        :param container: 容器
        :param failure_data: 故障数据
        :return: 容器，错误信息列表
        """
        # 非必换件:不管是否出质保,直接从头算到尾
        error_info_list = []  # 失败信息
        for failure in failure_data:
            # 检查产品编号是否存在
            # if failure.product_number not in container['part_container']:
            #     error_info_message = (
            #         f'型号 {failure.product_model} 部件 {failure.fault_location} '
            #         f'物料编码 {failure.fault_material_code} 故障报告ID {failure.report_id} '
            #         f'故障插入失败,产品编号 {failure.product_number} 不存在'
            #     )
            #     error_info_list.append(error_info_message)
            #     continue
            # # 检查是否有sub_container
            # if 'sub_container' not in container['part_container'][failure.product_number]:
            #     container['part_container'][failure.product_number]['sub_container'] = {}

            # 故障匹配:在产品编号container['part_container'][product_number],寻找虚拟件编号
            is_used = False  # 故障部件是否被插入
            for vmc, pt in container['part_container'][failure.product_number]['sub_container'].items():
                # 优先去找fault_part_list中最后一个是否匹配当前故障件编号
                if (
                    len(pt['fault_part_list']) > 0
                    and pt['fault_part_list'][-1] == failure.fault_part_number
                    and not is_used
                ):
                    pt['fault_part_list'].append(failure.replacement_part_number)
                    pt['fault_date_list'].append((failure.discovery_date, 'failure', 0))
                    is_used = True
                    break
                # 如果没有匹配，优先插入空的虚拟件
                if len(pt['fault_part_list']) == 0 and not is_used:
                    pt['fault_part_list'].append(failure.replacement_part_number)
                    pt['fault_date_list'].append((failure.discovery_date, 'failure', 0))
                    is_used = True
                    break
            # 如果没有空的虚拟件可供插入,也都不匹配,先检查是否能在过去的任意一个虚拟件中找到匹配插入
            if not is_used:
                for vmc, pt in container['part_container'][failure.product_number]['sub_container'].items():
                    if failure.fault_part_number in pt['fault_part_list']:
                        pt['fault_part_list'].append(failure.replacement_part_number)
                        pt['fault_date_list'].append((failure.discovery_date, 'failure', 0))
                        is_used = True
                        break
            # 如果不能，直接插入第一个虚拟件
            if not is_used:
                container['part_container'][failure.product_number]['sub_container'][
                    failure.fault_material_code + '-1'
                ]['fault_part_list'].append(failure.replacement_part_number)
                container['part_container'][failure.product_number]['sub_container'][
                    failure.fault_material_code + '-1'
                ]['fault_date_list'].append((failure.discovery_date, 'failure', 0))
                is_used = True
            if not is_used:
                # 插入失败
                error_info_message = (
                    f'型号 {failure.product_model} 部件 {failure.fault_location} '
                    f'物料编码 {failure.fault_material_code} 故障报告ID {failure.report_id} '
                    f'故障插入失败,请联系数字化管理部大数据室查询该故障信息完整性'
                )
                error_info_list.append(error_info_message)
        return container, error_info_list

    @staticmethod
    async def tag_create_non_essential(
        container: dict[str, Any], product_data: Product, input_date: date
    ) -> list[list[Any]]:
        result = []
        # 循环遍历 container 容器中的每个键和值
        for bh, part in container['part_container'].items():
            for vt, context in part['sub_container'].items():
                context['fault_date_list'].append((input_date, 'end', 99))
                for i in range(1, len(context['fault_date_list'])):
                    diff = context['fault_date_list'][i][0] - context['fault_date_list'][i - 1][0]
                    t = dateutils.run_time(diff.days - 90, product_data.year_days, product_data.avg_worktime)
                    cur = [bh, vt, context['fault_date_list'][i - 1][0], context['fault_date_list'][i][0], diff.days, t]
                    if i == len(context['fault_date_list']) - 1:
                        cur.append('suspense')
                    else:
                        cur.append('failure')
                    result.append(cur)
        return result

    @staticmethod
    async def container_insert_essential_repair(
        container: dict[str, Any],
        repair_despatch_data: list[DespatchParam],
    ) -> tuple[dict, list]:
        error_info_list = []  # 失败信息
        # 必换件:先考虑插入发运信息，查询该型号所有发运信息
        for despatch in repair_despatch_data:
            # 如果有这个产品编号:以前有新造发运
            if despatch.identifier in container['part_container']:
                for vmc, pt in container['part_container'][despatch.identifier]['sub_container'].items():
                    # 给产品中零部件每一个虚拟件做一次判断，向pt['fault_date_list']中插入
                    # (despatch.life_cycle_time,'repair', despatch.repair_level_num)
                    if despatch.life_cycle_time <= pt['fault_date_list'][-1][0]:
                        # 判断条件:despatch.life_cycle_time不能超过前一个的值，不然认为时间有问题
                        error_info_message = (
                            f'产品 {despatch.model} 编号 {despatch.identifier} '
                            f'等级修 {despatch.repair_level} 插入失败,'
                            f'时间 {despatch.life_cycle_time} '
                            f'小于前值 {pt["fault_date_list"][-1][0]}'
                        )
                        error_info_list.append(error_info_message)
                        break
                    pt['fault_date_list'].append((despatch.life_cycle_time, 'repair', despatch.repair_level_num))
        return container, error_info_list

    @staticmethod
    async def tag_create_essential(
        container: dict[str, Any], product_data: Product, input_date: date
    ) -> list[list[Any]]:
        result = []
        # 循环遍历 container 容器中的每个键和值
        for bh, part in container['part_container'].items():
            for vt, context in part['sub_container'].items():
                # 时间顺序排列
                context['fault_date_list'] = sorted(context['fault_date_list'], key=lambda x: x[0])
                context['fault_date_list'].append((input_date, 'end', 99))
                for i in range(1, len(context['fault_date_list'])):
                    diff = context['fault_date_list'][i][0] - context['fault_date_list'][i - 1][0]
                    if context['fault_date_list'][i][1] in ['repair', 'end']:
                        cur = [bh, vt, context['fault_date_list'][i - 1][0], context['fault_date_list'][i][0]]
                        if (diff.days - 90) <= product_data.repair_times:
                            cur.append(diff.days)
                            t = dateutils.run_time(diff.days - 90, product_data.year_days, product_data.avg_worktime)
                            cur.append(t)
                            cur.append('suspense')
                        else:
                            cur.append(product_data.repair_times)
                            t = dateutils.run_time(
                                product_data.repair_times - 90, product_data.year_days, product_data.avg_worktime
                            )
                            cur.append(t)
                            cur.append('suspense')
                        result.append(cur)
                    if context['fault_date_list'][i][1] == 'failure':
                        # 故障时间如果没有超过必换件周期则，正常标记一条故障
                        if (diff.days - 90) <= product_data.repair_times:
                            t = dateutils.run_time(diff.days - 90, product_data.year_days, product_data.avg_worktime)
                            cur = [
                                bh,
                                vt,
                                context['fault_date_list'][i - 1][0],
                                context['fault_date_list'][i][0],
                                diff.days,
                                t,
                                'failure',
                            ]
                            result.append(cur)
                        else:
                            # 如果超出了product_data.repair_times，看超出了多少倍数，超出几倍打几个删失,最后一个打故障
                            quotient, remainder = divmod(diff.days, product_data.repair_times)
                            # 只插入一次删失
                            t = dateutils.run_time(
                                product_data.repair_times - 90, product_data.year_days, product_data.avg_worktime
                            )
                            cur = [
                                bh,
                                vt,
                                context['fault_date_list'][i - 1][0],
                                context['fault_date_list'][i][0],
                                product_data.repair_times,
                                t,
                                'suspense',
                            ]
                            result.append(cur)
                            # 再插入一次故障
                            t = dateutils.run_time(remainder, product_data.year_days, product_data.avg_worktime)
                            cur = [
                                bh,
                                vt,
                                context['fault_date_list'][i - 1][0],
                                context['fault_date_list'][i][0],
                                remainder,
                                t,
                                'failure',
                            ]
                            result.append(cur)
        return result


part_tag_process_service: PartTagProcessService = PartTagProcessService()
