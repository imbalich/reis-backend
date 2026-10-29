#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : test_plot_lifetime.py
@Desc    : 评审B3验收测试: 等寿命设计画图函数必须可调用
           (@staticmethod + async + _fig_to_base64 完整),
           用空的 pso_results 断言返回长度为1的 base64 列表。
"""
import asyncio

import matplotlib

matplotlib.use("Agg")

from backend.app.lifetime.service.plot_lifetime_service import plot_lifetime_service


class _FakeDistribution:
    @staticmethod
    def SF(x):
        import numpy as np
        return np.full_like(np.asarray(x, dtype=float), 0.99)


def test_plot_optimize_result_returns_base64():
    result = asyncio.run(
        plot_lifetime_service.plot_optimize_result(
            model="CR400AF",
            pso_results={},
            t=100000,
            equal_points={},
            target_sf=0.9,
            code_to_name={},
        )
    )
    assert len(result) == 1
    assert isinstance(result[0], str) and len(result[0]) > 100  # base64 内容


def test_plot_original_result_returns_base64():
    result = asyncio.run(
        plot_lifetime_service.plot_original_result(
            model="CR400AF",
            pso_results={
                "P-001": {
                    "original_distribution": _FakeDistribution(),
                }
            },
            t=100000,
            target_sf=0.9,
            code_to_name={"P-001": "齿轮"},
            year_worktimes=3000,
        )
    )
    assert len(result) == 1
    assert isinstance(result[0], str) and len(result[0]) > 100
