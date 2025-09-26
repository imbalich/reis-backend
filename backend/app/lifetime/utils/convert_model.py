
from datetime import date
from typing import Any, List, Sequence, Type, TypeVar

import pandas as pd
import json

from backend.app.fit.schema.base_param import EbomParam
from backend.app.lifetime.schema.lifetime_param import CreateEqualLifetimeParam, CreateEqualLifetimeParam1
from backend.common.schema import SchemaBase
from backend.database.db import uuid4_str

T = TypeVar('T', bound=SchemaBase)

def convert_to_euqal_lifetime_params(
    results: dict, 
    model: str, 
    target_sf: float,
    step_start: float, 
    step_end: float
) -> List[CreateEqualLifetimeParam]:
    """
    将等寿命点优化结果转换为数据库存储参数，只存储优化后的参数
    """
    group_id = uuid4_str()
    distribution_params = []
    time_point = results.get("time_point")
    # equal_lifetime_point = results.get("equal_lifetime_point")
    equal_lifetime_t = results.get("equal_lifetime_t")
    equal_lifetime_sf = results.get("equal_lifetime_sf")
    parts_results = results.get("parts_results", {})

    for part, part_result in parts_results.items():
        params = part_result.copy()
        param = CreateEqualLifetimeParam(
            group_id = group_id,
            model=model,
            part=part,
            step_start=float(step_start),
            step_end=float(step_end),
            time_point=float(time_point),
            target_sf=float(target_sf),
            need_optimization = params.get('need_optimization'),
            # equal_lifetime_point = equal_lifetime_point,
            equal_lifetime_t= equal_lifetime_t,
            equal_lifetime_sf= equal_lifetime_sf,
            distribution = params.get('distribution_type') if params.get('distribution_type') is not None else None,
            original_sf = params.get('original_sf'),
            optimized_sf =  params.get('optimized_sf') if params.get('optimized_sf') is not None else params.get('original_sf'),
            original_pdf = params.get('original_pdf'),
            optimized_pdf = params.get('optimized_pdf') if params.get('optimized_pdf') is not None else None,
            original_equal_point_pdf = params.get('original_equal_point_pdf') if params.get('original_equal_point_pdf') is not None else None,
            optimized_equal_point_pdf = params.get('optimized_equal_point_pdf') if params.get('optimized_equal_point_pdf') is not None else None,
            alpha=float(params.get("alpha")) if "alpha" in params else None,
            beta=float(params.get("beta")) if "beta" in params else None,
            gamma=float(params.get("gamma")) if "gamma" in params else None,
            alpha_1=float(params.get("alpha_1")) if "alpha_1" in params else None,
            beta_1=float(params.get("beta_1")) if "beta_1" in params else None,
            alpha_2=float(params.get("alpha_2")) if "alpha_2" in params else None,
            beta_2=float(params.get("beta_2")) if "beta_2" in params else None,
            proportion_1=float(params.get("proportion_1")) if "proportion_1" in params else None,
            ds=float(params.get("ds")) if "ds" in params else None,
            mu=float(params.get("mu")) if "mu" in params else None,
            sigma=float(params.get("sigma")) if "sigma" in params else None,
            lambda_=float(params.get("Lambda")) if "Lambda" in params else None,
        )
        distribution_params.append(param)
    return distribution_params


def convert_to_euqal_lifetime_params1(
    results: dict, 
    model: str, 
    parts: list[str],
    target_sf: float,
    step_start: float, 
    step_end: float
) -> List[CreateEqualLifetimeParam1]:
    """
    将等寿命点优化结果转换为数据库存储参数，只存储优化后的参数
    """
    group_id = uuid4_str()
    time_point = results.get("time_point")
    equal_lifetime_t = results.get("equal_lifetime_t")
    equal_lifetime_sf = results.get("equal_lifetime_sf")
    all_parts = results.get("parts")
    distribution_params = [
        CreateEqualLifetimeParam1(
            group_id = group_id,
            model=model,
            parts=json.dumps(all_parts),
            step_start=float(step_start),
            step_end=float(step_end),
            time_point=float(time_point),
            target_sf=float(target_sf),
            equal_lifetime_t = equal_lifetime_t if equal_lifetime_t else None,
            equal_lifetime_sf= equal_lifetime_sf if equal_lifetime_sf else None,
            # equal_lifetime_point = equal_lifetime_point,
        )
    ]
    return distribution_params