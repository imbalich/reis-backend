# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : test_science_warehouse_industry_defense.py
@Desc    : 第4阶段测试——科学库存 ESB 推送三道防线(评审PR#3意见#7)
          1. 产业聚合: 混合型号批次 → mixed
          2. 兜底: 批次混入风电行 → 拒绝推送且不发起任何 ESB 请求
          3. 纯铁路批次 → ESB 收到的报文只含铁路行
"""
import asyncio
from types import SimpleNamespace

import pytest

from backend.common.industry import Industry, aggregate_industry
from backend.app.calcu.service import science_warehouse_push_service as push_mod


def _row(spare_part_code: str, industry: str):
    return SimpleNamespace(
        calculation_id='CALC-1',
        warehouse_code='WH01',
        warehouse_name='一号库',
        spare_part_code=spare_part_code,
        spare_part_name='备品' + spare_part_code,
        max_failure_count=3,
        required_quantity=2,
        industry=industry,
    )


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    """最小异步会话替身: 满足 async with / begin 用法"""

    def __init__(self):
        self.begun = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def begin(self):
        return self

    async def __aenter2__(self):
        pass

    # context manager for begin()
    class _Tx:
        async def __aenter__(self_inner):
            return self_inner

        async def __aexit__(self_inner, *a):
            return False

    def begin(self):
        return self._Tx()


def _patch(monkeypatch, rows):
    fake_db = _FakeSession()

    def fake_session_factory():
        return fake_db

    monkeypatch.setattr(push_mod, 'async_db_session', fake_session_factory)

    class _FakePushDao:
        async def get_by_calculation_id(self, db, calculation_id):
            return rows

    monkeypatch.setattr(push_mod, 'science_warehouse_push_result_dao', _FakePushDao())

    calls = {'posts': []}

    class _FakeEsbClient:
        @staticmethod
        def build_headers(source_system, service_name):
            return {'requestId': 'R1', 'trackId': 'T1', 'serviceName': service_name}

        @staticmethod
        async def post_json(url, headers, payload, timeout_seconds):
            calls['posts'].append(payload)
            return SimpleNamespace(success=True, headers={}, body_text='ok',
                                   http_status=200)

    monkeypatch.setattr(push_mod, 'science_warehouse_esb_client', _FakeEsbClient)

    class _FakeLogDao:
        async def create_log(self, db, data):
            return SimpleNamespace(id=1)

        async def update_log(self, db, log, data):
            return None

    monkeypatch.setattr(push_mod, 'science_warehouse_push_log_dao', _FakeLogDao())
    return calls


class TestAggregateIndustry:
    def test_all_wind(self):
        assert aggregate_industry({Industry.WIND}) == 'wind'

    def test_all_railway(self):
        assert aggregate_industry({Industry.RAILWAY}) == 'railway'

    def test_mixed(self):
        assert aggregate_industry({Industry.WIND, Industry.RAILWAY}) == 'mixed'

    def test_empty_defaults_railway(self):
        assert aggregate_industry(set()) == 'railway'


class TestPushDefense:
    def test_mixed_batch_rejected_without_esb_request(self, monkeypatch):
        """兜底防线: 批次混入风电行 → 拒绝推送, ESB 零请求"""
        rows = [_row('SP-RAIL-1', 'railway'), _row('SP-WIND-1', 'wind')]
        calls = _patch(monkeypatch, rows)
        with pytest.raises(Exception) as exc:
            asyncio.run(push_mod.science_warehouse_push_service.push_by_calculation_id(
                calculation_id='CALC-1', push_reason='测试'
            ))
        msg = getattr(exc.value, 'msg', '') or str(exc.value)
        assert '非铁路' in msg or '拒绝' in msg, f'异常信息不含兜底标识: {msg!r}'
        assert calls['posts'] == [], '兜底触发时不得发起任何ESB请求'

    def test_railway_only_batch_pushes_railway_rows(self, monkeypatch):
        """纯铁路批次 → ESB 正常推送, 报文只含铁路行"""
        rows = [_row('SP-RAIL-1', 'railway'), _row('SP-RAIL-2', 'railway')]
        calls = _patch(monkeypatch, rows)
        result = asyncio.run(push_mod.science_warehouse_push_service.push_by_calculation_id(
            calculation_id='CALC-1', push_reason='测试'
        ))
        assert result['status'] == 'success'
        assert len(calls['posts']) >= 1
        pushed_codes = [r['spare_part_code']
                        for p in calls['posts'] for r in p['results']]
        assert set(pushed_codes) == {'SP-RAIL-1', 'SP-RAIL-2'}
        assert all(not c.startswith('SP-WIND') for c in pushed_codes)
