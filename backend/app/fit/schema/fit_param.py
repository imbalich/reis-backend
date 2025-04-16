#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : fastapi-base-backend
@File    : fit_param.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/2/28 下午3:49
'''
from datetime import date

from pydantic import ConfigDict

from backend.common.enums import StrEnum
from backend.common.schema import SchemaBase


class FitMethodType(StrEnum):
    """拟合方法"""
    MLE = "MLE"  # 极大似然估计
    LS = "LS"  # 最小二乘估计
    RRX = "RRX"  # x轴回归
    RRY = "RRY"  # y轴回归


class FitCheckType(StrEnum):
    # 拟合优度检验方法
    BIC = "BIC"
    AICc = "AICc"
    AD = "AD"
    Log = "Log-likelihood"


class CreateFitProductInParam(SchemaBase):
    # 创建产品级别拟合信息入参
    model: str
    input_date: str | None = None
    method: FitMethodType = FitMethodType.MLE


class CreateFitPartInParam(SchemaBase):
    # 创建产品级别拟合信息入参
    model: str
    part: str
    input_date: str | None = None
    method: FitMethodType | None = FitMethodType.MLE


class CreateFitAllProductInParam(SchemaBase):
    # 创建多型号产品级别拟合信息入参
    input_date: str | None = None
    method: FitMethodType = FitMethodType.MLE


class CreateFitAllPartInParam(SchemaBase):
    # 创建多型号零部件级别拟合信息入参
    input_date: str | None = None
    method: FitMethodType = FitMethodType.MLE


class CreateProductDistributionParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    group_id: str
    model: str
    input_date: date
    method: FitMethodType

    distribution: str
    alpha: float | None = None
    beta: float | None = None
    gamma: float | None = None
    alpha_1: float | None = None
    beta_1: float | None = None
    alpha_2: float | None = None
    beta_2: float | None = None
    proportion_1: float | None = None
    ds: float | None = None
    mu: float | None = None
    sigma: float | None = None
    lambda_: float | None = None  # lambda
    log_likelihood: float | None = None
    aicc: float
    bic: float
    ad: float
    optimizer: str | None = None

    source: bool


class CreatePartDistributionParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    group_id: str
    model: str
    part: str
    input_date: date
    method: FitMethodType

    distribution: str
    alpha: float | None = None
    beta: float | None = None
    gamma: float | None = None
    alpha_1: float | None = None
    beta_1: float | None = None
    alpha_2: float | None = None
    beta_2: float | None = None
    proportion_1: float | None = None
    ds: float | None = None
    mu: float | None = None
    sigma: float | None = None
    lambda_: float | None = None  # lambda
    log_likelihood: float | None = None
    aicc: float
    bic: float
    ad: float
    optimizer: str | None = None

    source: bool
