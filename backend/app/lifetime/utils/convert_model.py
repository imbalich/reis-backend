
from typing import List, TypeVar

import json

from backend.app.lifetime.schema.lifetime_param import CreateEqualLifetimeParam
from backend.common.schema import SchemaBase
from backend.database.db import uuid4_str

T = TypeVar('T', bound=SchemaBase)


def convert_to_euqal_lifetime_params(
    results: dict, 
    model: str, 
    parts: list[str],
    target_sf: float,
    step_start: float, 
    step_end: float,
    is_all_parts: bool = False
) -> List[CreateEqualLifetimeParam]:
    """
    将等寿命点优化结果转换为数据库存储参数，只存储优化后的参数
    """
    group_id = uuid4_str()
    time_point = results.get("time_point")
    equal_lifetime_t = results.get("equal_lifetime_t")
    equal_lifetime_sf = results.get("equal_lifetime_sf")
    all_parts = results.get("parts")
    distribution_params = [
        CreateEqualLifetimeParam(
            group_id = group_id,
            model=model,
            parts=json.dumps(all_parts),
            is_all_parts=is_all_parts,
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