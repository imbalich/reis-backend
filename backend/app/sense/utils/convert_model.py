#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：reis-backend 
@File    ：convert_model.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/4/25 10:12 
'''
import copy
import json
import re
from typing import Any, List, TypeVar

from backend.app.sense.schema.sense_param import CreateSenseSortParam
from backend.common.schema import SchemaBase
from backend.database.db import uuid4_str

T = TypeVar('T', bound=SchemaBase)


def convert_to_sense_sort_params(
        sense_results: dict[str, Any],
        model: str,
        part: str,
        stage:str,
        process_name:str,
        check_project:str,
        check_bezier:str,
        time_range:list[str],
        extra_material_names:str,
) -> List[CreateSenseSortParam]:
    sort_params = []
    # 计算group_id
    group_id = uuid4_str()
    # 提取 results 列表
    model_results = sense_results['results']

    for model_result in model_results:
        # 将 feature_importance 转换为字典方便提取
        feature_importance = {
            item["feature"]: item["shap_value"].item()
            for item in model_result["feature_importance"]
        }
        processed_ca = copy.deepcopy(model_result.get("categorical_analysis", {}))
        # 遍历每个子类别下的条目
        check_tools_sign = processed_ca["check_tools_sign"]
        if isinstance(check_tools_sign, list):  # 确保是列表
            for item in check_tools_sign:  # 直接遍历列表
                if "value" in item:
                    item["value"] = re.sub(r'-\d+$', '', item["value"])
        # 构建参数对象
        param = CreateSenseSortParam(
            group_id=group_id,
            model=model,
            part=part,
            stage=stage,
            process_name=process_name,
            check_project=check_project,
            check_bezier=check_bezier,
            start_time=time_range[0] if time_range else None,
            end_time=time_range[1] if time_range else None,
            extra_material_names=extra_material_names,
            model_type=model_result["model_type"],
            rela_self_value=feature_importance.get("rela_self_value", 0.0),
            check_tools_sign=feature_importance.get("check_tools_sign", 0.0),
            self_create_by=feature_importance.get("self_create_by", 0.0),
            extra_source_code=feature_importance.get("extra_source_code", 0.0),
            extra_supplier=feature_importance.get("extra_supplier", 0.0),
            categorical_analysis=json.dumps(processed_ca, ensure_ascii=False),
        )
        sort_params.append(param)
    return sort_params