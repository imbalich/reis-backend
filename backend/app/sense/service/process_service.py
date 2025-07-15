#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：process_service.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/3/27 14:48
"""

import re

from itertools import groupby
from typing import Any, Dict, List

from backend.app.datamanage.crud.crud_configuration import configuration_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_pc import pc_dao
from backend.app.sense.utils.format_process_utils import (
    process_sub_value,
    split_part_into_sub_values,
    split_rela_self_value,
    standard_data,
    self_create_by,
)
from backend.database.db import async_db_session


class ProcessService:
    @staticmethod
    async def process(model: str, part: str,stage:str,process_names:str,check_project: str,check_bezier: str,time_range:list[str],extra_material_names:str) -> dict[str, Any]:
        async with async_db_session() as db:
            try:
                # 1. 并行获取基础数据
                figure_data = await failure_dao.get_number_by_model(db, model, part, stage, time_range)
                config_data = await configuration_dao.get_by_model_and_part(db, model, part, stage, process_names,
                                                                            extra_material_names)

                # config_data中的product_no去重
                seen = set()
                filtered_config_data = []
                for row in config_data:
                    key = (row.product_no, row.extra_source_code)
                    if key not in seen:
                        seen.add(key)
                        filtered_config_data.append(row)
                config_data = filtered_config_data

                figure_product_numbers = set(figure_data) if figure_data else set()

                # 2. 提前获取所有PC数据并建立内存索引
                pc_groups = await ProcessService._get_pc_groups(db, model, stage,config_data,check_project,check_bezier)

                # 3. 构建响应数据
                processed_data = []
                for config in config_data:
                    group_key = (config.product_no, config.process_name)
                    pcs = pc_groups.get(group_key, [])

                    for pc in pcs:
                        pc_item = {
                            "extra_material_name": config.extra_material_name,
                            "extra_source_code": config.extra_source_code,
                            "extra_supplier": config.extra_supplier,
                            "check_tools": pc.check_tools,
                            "check_tools_sign": pc.check_tools_sign,
                            "rela_self_value": pc.rela_self_value,
                            "self_create_by": pc.self_create_by,
                            "check_project": pc.check_project,
                            "check_bezier": pc.check_bezier,
                            "manufaucture_date": pc.manufaucture_date,
                            'is_figure': 1 if config.product_no in figure_product_numbers else 0,
                        }
                        processed_pc_item = ProcessService.process_pc_item(pc_item)
                        processed_data.extend(processed_pc_item)
                is_figure_count = sum(item["is_figure"] for item in processed_data)
                if is_figure_count <= 5:
                    return {
                        "data": None,
                    }

                return {'model': model, 'part': part, 'count': len(processed_data), 'data': processed_data}

            except Exception as e:
                return {'error': f'处理失败: {str(e)}'}


    @staticmethod
    async def _get_pc_groups(db, model, stage, config_data,check_project,check_bezier):
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
            stage=stage,
            check_project=check_project,
            check_bezier=check_bezier,
            process_names=process_names,
            product_nos=product_nos,
        )

        # 使用内存分组建立快速索引
        sorted_pcs = sorted(all_pcs, key=lambda x: (x.product_serial_no, x.process_name))
        return {
            (key[0], key[1]): list(group)
            for key, group in groupby(sorted_pcs, key=lambda x: (x.product_serial_no, x.process_name))
        }

    @staticmethod
    def process_pc_item(pc_item: Dict) -> List[Dict]:
        base_data = {
            'extra_material_name': standard_data(pc_item['extra_material_name']),
            'extra_source_code': standard_data(pc_item['extra_source_code']),
            'extra_supplier': pc_item['extra_supplier'].replace(' ', ''),
            'check_tools': pc_item['check_tools'],
            'self_create_by': self_create_by(pc_item['self_create_by']),
            'is_figure': pc_item['is_figure'],
            'check_project': pc_item['check_project'],
            'check_bezier': pc_item['check_bezier'],
            'manufaucture_date': pc_item['manufaucture_date'],
        }
        tools = standard_data(pc_item['check_tools_sign']).split('\n')
        parts = split_rela_self_value(pc_item['rela_self_value'])
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

                # 生成当前条目
                item = base_data.copy()
                item['check_tools_sign'] = f'{tool}-{tool_counters[tool]}'
                item['rela_self_value'] = num_val
                processed_items.append(item)
        return processed_items




process_service: ProcessService = ProcessService()
