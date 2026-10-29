#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : test_aaron_part_fit_industry.py
@Desc    : fit_aaron 零部件拟合写库时按型号判定产业, 风电型号结果标记为 wind。
"""
import asyncio

from datetime import date

import pytest

from backend.app.fit.schema.fit_param import FitMethodType
from backend.app.fit_aaron.service import part_fit_service as svc_mod
from backend.common.exception.errors import FailureCheckError
from backend.common.industry import Industry


class _FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def begin(self):
        return _FakeTransaction()


class _FakeSessionContext:
    async def __aenter__(self):
        return _FakeSession()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeFit:
    results = object()


def _patch_common(monkeypatch, industry: Industry) -> dict:
    captured: dict = {}

    async def fake_resolve(db, model):
        return industry

    async def fake_creates(db, params):
        captured['saved'] = params

    async def fake_create(db, param):
        captured['saved'] = param

    monkeypatch.setattr(svc_mod, 'async_db_session', lambda: _FakeSessionContext())
    monkeypatch.setattr(svc_mod, 'resolve_industry', fake_resolve)
    monkeypatch.setattr(svc_mod.fit_part_dao, 'creates', fake_creates)
    monkeypatch.setattr(svc_mod.fit_part_dao, 'create', fake_create)
    return captured


@pytest.mark.parametrize('industry', [Industry.WIND, Industry.RAILWAY])
def test_distribution_fit_saves_industry(monkeypatch, industry):
    captured = _patch_common(monkeypatch, industry)

    async def fake_tags(*args, **kwargs):
        return [['p1', 100.0, 'failure']]

    async def fake_tag_fit(tags, method):
        return _FakeFit()

    def fake_convert(*args, **kwargs):
        captured['industry'] = kwargs.get('industry')
        return ['row']

    monkeypatch.setattr(svc_mod.part_strategy_service, 'part_tag_process', fake_tags)
    monkeypatch.setattr(svc_mod.PartFitService, 'tag_fit', staticmethod(fake_tag_fit))
    monkeypatch.setattr(svc_mod, 'convert_to_part_distribution_params', fake_convert)

    asyncio.run(
        svc_mod.PartFitService._perform_and_save_fit(
            'YJ376B3', 'M000001784211', date(2026, 10, 29), FitMethodType.MLE, False, product_config_code='PS02'
        )
    )

    assert captured['industry'] == industry.value
    assert captured['saved'] == ['row']


@pytest.mark.parametrize('industry', [Industry.WIND, Industry.RAILWAY])
def test_exponential_fallback_saves_industry(monkeypatch, industry):
    captured = _patch_common(monkeypatch, industry)

    async def fake_tags(*args, **kwargs):
        raise FailureCheckError(msg='故障数不足')

    async def fake_none_tag_fit(*args, **kwargs):
        return 0.001

    def fake_convert(*args, **kwargs):
        captured['industry'] = kwargs.get('industry')
        return 'row'

    monkeypatch.setattr(svc_mod.part_strategy_service, 'part_tag_process', fake_tags)
    monkeypatch.setattr(svc_mod.PartFitService, 'none_tag_fit', staticmethod(fake_none_tag_fit))
    monkeypatch.setattr(svc_mod, 'convert_to_part_exponential_distribution_params', fake_convert)

    asyncio.run(
        svc_mod.PartFitService._perform_and_save_fit(
            'YJ376B3', 'M000001784211', date(2026, 10, 29), FitMethodType.MLE, False, product_config_code='PS02'
        )
    )

    assert captured['industry'] == industry.value
    assert captured['saved'] == 'row'
