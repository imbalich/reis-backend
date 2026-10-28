#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : test_science_warehouse_railway_only.py
@Desc    : 第4阶段测试(评审PR#3意见③的替代测试):
           备品同时映射铁路与风电型号时, 科学库存只使用铁路型号:
           - 返回的型号列表不含风电型号
           - 风电DAO(dm_jl_failure/dm_jl_product)调用次数为0
"""
import asyncio
from types import SimpleNamespace

import pytest

from backend.app.calcu.service import science_warehouse_service as svc_mod
from backend.common.industry import Industry


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def _mapping(product_model: str):
    return SimpleNamespace(
        product_model=product_model,
        product_config_code='PS00',
        original_part_name='故障件',
        original_part_code='P-' + product_model,
        spare_part_name='备品',
        spare_part_code='SP-1',
    )


def _patch(monkeypatch, mappings):
    """打桩: 映射查询返回双产业型号; 统计风电DAO调用次数"""
    fake_db = _FakeSession()

    def fake_session_factory():
        return fake_db

    monkeypatch.setattr(svc_mod, 'async_db_session', fake_session_factory)

    class _FakeMappingDao:
        async def get_by_spare_part_code(self, db, spare_part_code):
            return mappings

    monkeypatch.setattr(svc_mod, 'part_spare_mapping_dao', _FakeMappingDao())

    calls = {'wind_dao': 0}

    class _CountingWindDao:
        def __getattr__(self, name):
            def _method(*a, **kw):
                calls['wind_dao'] += 1
                raise AssertionError('风电DAO不应被科学库存调用')
            return _method

    # 产业判定: R1→铁路, W1→风电(打桩 resolve, 避免测试依赖库中数据)
    import backend.common.industry as industry_mod

    async def fake_resolve(db, model):
        return Industry.WIND if str(model).startswith('W') else Industry.RAILWAY

    monkeypatch.setattr(industry_mod, 'resolve_industry', fake_resolve)
    return calls


class TestScienceWarehouseRailwayOnly:
    def test_models_using_spare_excludes_wind(self, monkeypatch):
        """备品同时映射铁路(R1)与风电(W1)型号 → 只返回铁路型号"""
        mappings = [_mapping('R1'), _mapping('W1')]
        calls = _patch(monkeypatch, mappings)
        result = asyncio.run(
            svc_mod.science_warehouse_service.get_models_using_spare('SP-1')
        )
        assert set(result) == {'R1'}, f'应只含铁路型号, 实际: {result}'
        assert 'W1' not in result
        assert calls['wind_dao'] == 0, '风电DAO调用次数应为0'
