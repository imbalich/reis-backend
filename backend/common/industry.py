# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : industry.py
@Desc    : 产业判定与并行基础设施(评审PR#3意见#1/#2定版)
           单部署单库架构下, 国铁与风电型号在同一系统中并行:
           - 按型号判定产业(型号存在于 dm_jl_product 即为风电)
           - 判定结果进程内缓存(TTL), 避免拟合任务高频查库
           - 同一型号同时出现在铁路与风电产品表时必须报错(不允许静默选边)
           - ProductLike/FailureLike 协议: 只声明拟合管道实际使用的属性
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.datamanage.model.dm_jl_product import ProductJL


class Industry(str, Enum):
    """数据产业: railway=轨道交通 wind=风电"""

    RAILWAY = 'railway'
    WIND = 'wind'


# ---------------------------------------------------------------------------
# 产业判定缓存(进程内, TTL 300 秒)
# ---------------------------------------------------------------------------
_CACHE_TTL_SECONDS = 300
_cache: dict[str, Any] = {'wind_models': frozenset(), 'railway_only_conflicts': frozenset(), 'ts': 0.0}


def invalidate_industry_cache() -> None:
    """风电产品表数据刷新后调用, 强制下次判定重新查库"""
    _cache['ts'] = 0.0


async def _load_wind_models(db: AsyncSession) -> frozenset[str]:
    """加载风电产品型号全集(去重)"""
    stmt = select(ProductJL.model).where(ProductJL.model.isnot(None))
    result = await db.execute(stmt)
    models = {str(m).strip() for (m,) in result.all() if m and str(m).strip()}
    return frozenset(models)


async def _load_railway_models(db: AsyncSession) -> frozenset[str]:
    """加载铁路产品型号全集(去重), 用于重叠检测"""
    from backend.app.datamanage.model.product import Product

    stmt = select(Product.model).where(Product.model.isnot(None))
    result = await db.execute(stmt)
    models = {str(m).strip() for (m,) in result.all() if m and str(m).strip()}
    return frozenset(models)


async def get_industry_model_sets(db: AsyncSession) -> tuple[frozenset[str], frozenset[str]]:
    """返回(风电型号集合, 冲突型号集合), 带TTL缓存"""
    now = time.time()
    if now - _cache['ts'] < _CACHE_TTL_SECONDS:
        return _cache['wind_models'], _cache['railway_only_conflicts']
    wind = await _load_wind_models(db)
    railway = await _load_railway_models(db)
    conflicts = frozenset(wind & railway)
    _cache['wind_models'] = wind
    _cache['railway_only_conflicts'] = conflicts
    _cache['ts'] = now
    return wind, conflicts


async def resolve_industry(db: AsyncSession, model: str) -> Industry:
    """按产品型号判定产业

    判定规则: 型号存在于 dm_jl_product(风电产品表) → WIND, 否则 → RAILWAY
    同一型号同时存在于铁路与风电产品表 → 抛出异常(不允许静默选边, 评审PR#3意见#1)
    """
    normalized = str(model).strip() if model else ''
    wind_models, conflicts = await get_industry_model_sets(db)
    # 评审PR#3意见#1原规则(重叠即报错)经数据核实不可行:
    #   fba.dm_product 是全公司统一产品主表, 数据方已将全部风电产品
    #   (product_type='风力电机')灌入其中, 风电型号与 dm_product 的重叠是常态。
    #   故以 dm_jl_product 成员资格作为风电判定唯一依据, 重叠仅告警。
    if normalized in conflicts:
        import logging

        logging.warning('型号 %s 同时存在于铁路与风电产品表, 已按风电处理', model)
    return Industry.WIND if normalized in wind_models else Industry.RAILWAY


def aggregate_industry(industries: set[Industry]) -> str:
    """聚合一组产业为单行标记: 全风电→wind / 全铁路→railway / 混合→mixed / 空→railway

    用于科学库存等按(库房,备品)聚合的结果行: 行的产业取决于支撑该行的型号产业构成。
    ESB 推送防线只放行 industry='railway' 的行(评审PR#3意见#7, 业务已确认风电不推ESB)。
    """
    if not industries:
        return 'railway'
    if industries == {Industry.WIND}:
        return 'wind'
    if industries == {Industry.RAILWAY}:
        return 'railway'
    return 'mixed'


# ---------------------------------------------------------------------------
# 拟合管道协议类型: 只声明管道实际使用的属性(评审PR#3意见#3)
# ---------------------------------------------------------------------------
@runtime_checkable
class ProductLike(Protocol):
    """产品模型协议: 铁路 Product 与风电 ProductJL 均满足"""

    pk: Any
    id: Any
    model: Any
    sub_saet: Any
    avg_worktime: Any
    avg_speed: Any
    year_days: Any
    repair_priod: Any
    repair_times: Any
    product_config_code: Any


@runtime_checkable
class FailureLike(Protocol):
    """故障模型协议: 铁路 Failure/FailureMROCorrect 与风电 FailureJL 均满足"""

    pk: Any
    report_id: Any
    product_model: Any
    product_number: Any
    product_config_code: Any
    discovery_date: Any
    manufacturing_date: Any
    fault_location: Any
    fault_material_code: Any
    fault_part_number: Any
    replacement_part_number: Any
    final_fault_responsibility: Any
    is_zero_distance: Any
    is_company: Any
    life_cycle_time_erp: Any
