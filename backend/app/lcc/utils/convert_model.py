#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：reis-backend 
@File    ：convert_model.py
@IDE     ：PyCharm 
@Author  ：seven
@Date    ：2025/11/26 10:02
'''
import copy
import json
import re
from typing import Any, List, TypeVar

from backend.app.lcc.schema.lcc_param import CreateRepairPlanParam
from backend.common.schema import SchemaBase
from backend.database.db import uuid4_str

T = TypeVar('T', bound=SchemaBase)


def convert_to_repair_plan_params(
    results: dict, 
    model: str, 
    parts: list[str],
    life: int,
    is_ai: bool = False,
    is_all_parts: bool = False
) -> List[CreateRepairPlanParam]:
    """
    将等寿命点优化结果转换为数据库存储参数，只存储优化后的参数
    """
    group_id = uuid4_str()

    # 这里假定 caller 已经提取了 results 列表（即 result = result.get('results')），
    # 如果传入的是列表则直接使用，否则尝试包装为列表。
    items = results.get('result')
    print('items',items)

    params: List[CreateRepairPlanParam] = []
    for itm in items:
        param = CreateRepairPlanParam(
            group_id=group_id,
            model=model,
            life=life,
            is_ai=is_ai,
            is_all_parts=is_all_parts,
            part=itm.get('part'),
            part_name=itm.get('part_name') ,
            level_old=itm.get('level_old') ,
            year_new=itm.get('year_new'),
            level_new=itm.get('level_new'),
            lcc_min=itm.get('lcc_min'),
            sf=itm.get('sf'),
            lcc_old=itm.get('lcc_old') ,
            lcc_result= itm.get('lcc_result')  or None,
            lcc_result_tag= itm.get('lcc_result_tag')  or None,
        )
        params.append(param)

    return params