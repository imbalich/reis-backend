#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : test_wind_models.py
@Desc    : 风电直连模型的口径与转换纯函数测试(评审PR#3意见#6固化)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backend.app.datamanage.model.dm_jl_failure import cn_yes_no_to_int
from backend.app.datamanage.model.dm_jl_product import calc_repair_times_days


class TestCalcRepairTimesDays:
    """repair_times(删失阈值)口径: PROD_REPAIR年 × 365 天(业务确认后固化)"""

    def test_typical_design_life_20y(self):
        assert calc_repair_times_days(20.0) == 7300

    def test_25y(self):
        assert calc_repair_times_days(25.0) == 9125

    def test_zero_life(self):
        assert calc_repair_times_days(0.0) == 0

    def test_none(self):
        assert calc_repair_times_days(None) is None

    def test_string_number_coerced(self):
        assert calc_repair_times_days('20') == 7300


class TestCnYesNoToInt:
    """中文'是/否'转数值: 与铁路 is_zero/is_company 语义一致"""

    def test_yes(self):
        assert cn_yes_no_to_int('是') == 1

    def test_no(self):
        assert cn_yes_no_to_int('否') == 0

    def test_none(self):
        assert cn_yes_no_to_int(None) is None

    def test_other_value(self):
        assert cn_yes_no_to_int('其他') is None
