#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : test_convert_industry.py
@Desc    : 评审B2/S4验收测试:
           convert_to_* 系列(本模块)接受 industry 参数并透传到结果对象,
           调用方以关键字传参, 避免位置错位(B2 的 TypeError 根因)。
"""
from datetime import date

import pandas as pd

from backend.app.fit.utils.convert_model import (
    convert_to_part_distribution_params,
    convert_to_part_exponential_distribution_params,
    convert_to_product_distribution_params,
    convert_to_product_exponential_distribution_params,
)
from backend.app.fit.schema.fit_param import FitMethodType


def _fit_results() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Distribution": "Weibull_2P",
                "Alpha": 1200.0,
                "Beta": 1.8,
                "Gamma": None,
                "Alpha 1": None,
                "Beta 1": None,
                "Alpha 2": None,
                "Beta 2": None,
                "Proportion 1": None,
                "DS": None,
                "Mu": None,
                "Sigma": None,
                "Lambda": None,
                "Log-likelihood": -100.0,
                "AICc": 204.0,
                "BIC": 206.0,
                "AD": 0.5,
                "optimizer": "scipy",
            }
        ]
    )


def test_part_distribution_params_industry_wind():
    params = convert_to_part_distribution_params(
        _fit_results(),
        "YJ376B3",
        "M000001784211",
        "轴承",
        date(2025, 12, 30),
        FitMethodType.MLE,
        False,
        industry="wind",
    )
    assert len(params) == 1
    assert params[0].industry == "wind"


def test_part_distribution_params_default_railway():
    params = convert_to_part_distribution_params(
        _fit_results(),
        "CR400AF",
        "Z500000183465",
        "齿轮",
        date(2025, 12, 30),
        FitMethodType.MLE,
        False,
    )
    assert params[0].industry == "railway"


def test_product_distribution_params_industry_keyword():
    params = convert_to_product_distribution_params(
        _fit_results(),
        "YJ328A1",
        None,
        date(2025, 12, 30),
        FitMethodType.MLE,
        False,
        industry="wind",
    )
    assert params[0].industry == "wind"


def test_part_exponential_params_industry_keyword():
    param = convert_to_part_exponential_distribution_params(
        "YJ93A",
        None,
        "叶片",
        date(2025, 12, 30),
        FitMethodType.MLE,
        False,
        1e-5,
        industry="wind",
    )
    assert param.industry == "wind"


def test_product_exponential_params_industry_keyword():
    param = convert_to_product_exponential_distribution_params(
        "YGZN2Q271",
        "Z500000183465",
        date(2025, 12, 30),
        FitMethodType.MLE,
        False,
        1e-5,
        industry="railway",
    )
    assert param.industry == "railway"
