
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

def convert_to_equal_lifetime_params_with_classification(
        results: dict,
        model: str,
        target_sf: float,
        step_start: float,
        step_end: float,
        is_all_parts: bool = False
) -> List[CreateEqualLifetimeParam]:
    """
    将分类后的等寿命点结果转换为数据库参数
    results 结构：
    {
        'A': {...},
        'B': {...},
        'C': {...}
    }
    
    返回三条记录（每个分类一条）
    """
    group_id = uuid4_str()
    time_point = results.get('D',results.get('B', results.get('C', results.get('A', {})))).get('time_point')

    distribution_params = []

    for category in ['A', 'B', 'C','D']:
        if category not in results:
            continue

        category_result = results[category]

        param = CreateEqualLifetimeParam(
            group_id=group_id,
            model=model,
            category=category,
            parts=json.dumps(category_result['parts']),
            part_count=category_result['part_count'],
            sf_at_time_point=float(category_result['sf_at_time_point']) if category_result['sf_at_time_point'] else None,
            is_all_parts=is_all_parts,
            target_sf=float(target_sf),
            step_start=float(step_start),
            step_end=float(step_end),
            time_point=int(time_point),
            equal_lifetime_t=category_result.get('equal_lifetime_t'),
            equal_lifetime_sf=category_result.get('equal_lifetime_sf'),
            equal_lifetime_t_year = category_result.get('equal_lifetime_t_year'),
            status=category_result.get('status', 'completed'),
            reason=category_result.get('reason', None)
        )
        distribution_params.append(param)

    return distribution_params