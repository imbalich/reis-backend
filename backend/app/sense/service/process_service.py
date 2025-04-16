#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend 
@File    ：process_service.py.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/3/27 14:48 
'''
import re
from itertools import groupby
from typing import List, Dict, Any
from collections import defaultdict

from backend.app.datamanage.crud.crud_configuration import configuration_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_pc import pc_dao
from backend.app.sense.utils.data_check_utils import datacheckutils
from backend.app.sense.utils.format_format_utils import split_rela_self_value, split_part_into_sub_values, \
    process_sub_value, standard_data
from backend.database.db import async_db_session

class ProcessService:
    @staticmethod
    async def process(model: str, part: str) -> dict[str, Any]:
        async with async_db_session() as db:
            try:
                # 1. 并行获取基础数据
                figure_data, config_data = await ProcessService._get_base_data(db, model, part)
                figure_product_numbers = set(figure_data) if figure_data else set()

                # 2. 提前获取所有PC数据并建立内存索引
                pc_groups = await ProcessService._get_pc_groups(db, model, config_data)

                # 3. 构建响应数据
                processed_data = []
                for config in config_data:
                    group_key = (config.product_no, config.process_name)
                    pcs = pc_groups.get(group_key, [])

                    for pc in pcs:
                        pc_item = {
                            # "product_no": config.product_no,
                            # "process_name": config.process_name,
                            "extra_source_code": config.extra_source_code,
                            "check_tools_sign": pc.check_tools_sign,
                            "rela_self_value": pc.rela_self_value,
                            "self_create_by": pc.self_create_by,
                            # "check_project": pc.check_project,
                            # "check_bezier": pc.check_bezier,
                            # "check_tools": pc.check_tools,
                            # "repair_level": pc.repair_level,
                            # "manufaucture_date": pc.manufaucture_date,
                            "is_figure": 1 if config.product_no in figure_product_numbers else 0,
                        }
                        # print(pc_item)
                        processed_pc_item = ProcessService.process_pc_item(pc_item)
                        processed_data.extend(processed_pc_item)
                # # 4. 频次编码和格式转换
                # formatted_data = []
                # if processed_data:
                #     freq_encoded_data = ProcessService._apply_frequency_encoding(processed_data)
                #     formatted_data = ProcessService._format_to_table(freq_encoded_data)

                return {
                    "model": model,
                    "part": part,
                    "count": len(processed_data),
                    "data": processed_data
                }

            except Exception as e:
                return {"error": f"处理失败: {str(e)}"}

    @staticmethod
    async def _get_base_data(db, model, part):
        """并行获取基础数据集"""
        figure_data = await failure_dao.get_number_by_model(db, model, part)
        config_data = await configuration_dao.get_by_model_and_part(db, model, part)
        return figure_data, config_data

    @staticmethod
    async def _get_pc_groups(db, model, config_data):
        """获取并分组PC数据"""
        # 获取所有需要查询的product_no
        product_nos = {config.product_no for config in config_data if config.product_no}
        process_names = {config.process_name for config in config_data if config.process_name}

        if not product_nos:
            return {}
        if not process_names:
            return {}
        # 批量获取所有相关PC记录
        all_pcs = await pc_dao.get_batch_by_products(
            db,
            model=model,
            process_names=process_names,
            product_nos=product_nos
        )

        # 使用内存分组建立快速索引
        sorted_pcs = sorted(all_pcs, key=lambda x: (x.product_serial_no, x.process_name))
        return {
            (key[0], key[1]): list(group)
            for key, group in groupby(
                sorted_pcs,
                key=lambda x: (x.product_serial_no, x.process_name)
            )
        }

    @staticmethod
    def process_pc_item(pc_item: Dict) -> List[Dict]:
        base_data = {
            # 'product_no': pc_item['product_no'],
            # 'process_name': pc_item['process_name'],
            'extra_source_code': standard_data(pc_item['extra_source_code']),
            'self_create_by': pc_item['self_create_by'],
            'is_figure': pc_item['is_figure'],
            # "check_project": pc_item['check_project'],
            # "check_bezier": pc_item['check_bezier'],
            # "check_tools": pc_item['check_tools'],
            # "repair_level": pc_item['repair_level'],
            # "manufaucture_date": pc_item['manufaucture_date'],
        }
        tools = standard_data(pc_item['check_tools_sign']).split('\n')
        # print(tools)
        parts = split_rela_self_value(pc_item['rela_self_value'])
        # print(parts)
        if len(tools) < len(parts):
            tools = tools + [tools[-1]] * (len(parts) - len(tools))  # 扩展tools到与parts相同长度
        processed_items = []
        tool_counters = {}  # 记录每个tool的计数器

        for tool, part in zip(tools, parts):
            # 初始化或获取当前tool的计数器
            if tool not in tool_counters:
                tool_counters[tool] = 1
            else:
                tool_counters[tool] += 1

            # 处理每个子值
            sub_values = split_part_into_sub_values(part)
            for sub_val in sub_values:
                processed_val = process_sub_value(sub_val)
                if not re.match(r'^-?\d+\.?\d*$', processed_val):
                    continue
                num_val = float(processed_val) if processed_val else None
                # print(num_val)

                # 生成当前条目
                item = base_data.copy()
                item['check_tools_sign'] = f"{tool}-{tool_counters[tool]}"
                item['rela_self_value'] = num_val
                processed_items.append(item)
        # print(processed_items)
        return processed_items

    # @staticmethod
    # def _apply_frequency_encoding(data: List[Dict]) -> List[Dict]:
    #     """对指定字段进行频次编码"""
    #     if not data:
    #         return data
    #     # 计算每个字段的频率
    #     freq_maps = {
    #         'extra_source_code': defaultdict(int),
    #         'check_tools_sign': defaultdict(int),
    #         'self_create_by': defaultdict(int)
    #     }
    #
    #     # 第一次遍历：计算频率
    #     for item in data:
    #         for field in freq_maps:
    #             value = item.get(field, '')
    #             freq_maps[field][value] += 1
    #     total_items = len(data)
    #
    #     # 第二次遍历：应用频次编码
    #     encoded_data = []
    #     for item in data:
    #         encoded_item = item.copy()
    #         for field in freq_maps:
    #             value = item.get(field, '')
    #             # 计算频率并保留4位小数
    #             frequency = freq_maps[field][value] / total_items
    #             encoded_item[f"{field}_freq"] = round(frequency, 4)
    #         encoded_data.append(encoded_item)
    #
    #     return encoded_data
    #
    # @staticmethod
    # def _format_to_table(data: List[Dict]) -> List[List[Any]]:
    #     """将字典列表转换为二维表格形式"""
    #     if not data:
    #         return []
    #
    #     # 定义列顺序
    #     columns = [
    #         'self_create_by_freq',
    #         'extra_source_code_freq',
    #         'check_tools_sign_freq',
    #         'rela_self_value',
    #         'is_figure'
    #     ]
    #
    #     table_data = []
    #     for item in data:
    #         row = []
    #         for col in columns:
    #             # 确保所有列都存在，不存在则填充0或适当默认值
    #             value = item.get(col, 0 if col.endswith('_freq') else '')
    #             row.append(value)
    #         table_data.append(row)
    #
    #     return table_data

process_service: ProcessService = ProcessService()