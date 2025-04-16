#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : distribute_param.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/28 10:59
"""

from typing import Optional

from pydantic import ConfigDict, Field

from backend.app.fit.schema.fit_param import FitCheckType, FitMethodType
from backend.common.enums import StrEnum
from backend.common.schema import SchemaBase


class DistributeType(StrEnum):
    Weibull_2P = 'Weibull_2P'  # 威布尔
    Weibull_3P = 'Weibull_3P'
    Normal_2P = 'Normal_2P'  # 正态
    Gamma_2P = 'Gamma_2P'  # 次正态Gamma
    Gamma_3P = 'Gamma_3P'
    Loglogistic_2P = 'Loglogistic_2P'  # Loglogistic
    Loglogistic_3P = 'Loglogistic_3P'
    Lognormal_2P = 'Lognormal_2P'  # Lognormal
    Lognormal_3P = 'Lognormal_3P'
    Exponential_1P = 'Exponential_1P'  # 指数
    Exponential_2P = 'Exponential_2P'
    Gumbel_2P = 'Gumbel_2P'  # Gumbel


class DistributionParams(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

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


class ProductPredictInParams(SchemaBase):
    model: str = Field(..., description='产品型号')
    distribution: Optional[DistributeType] = Field(None, description='分布类型')
    method: Optional[FitMethodType] = Field(FitMethodType.MLE, description='拟合方法')
    check: Optional[FitCheckType] = Field(FitCheckType.BIC, description='拟合优度检验方法')
    input_date: Optional[str] = Field(None, description='计算日期')
    start_date: Optional[str] = Field(None, description='计算起始日期')
    end_date: Optional[str] = Field(None, description='计算截止日期')


class PartPredictInParams(SchemaBase):
    model: str = Field(..., description='产品型号')
    part: str = Field(..., description='零部件物料编码')
    distribution: Optional[DistributeType] = Field(None, description='分布类型')
    method: Optional[FitMethodType] = Field(FitMethodType.MLE, description='拟合方法')
    check: Optional[FitCheckType] = Field(FitCheckType.BIC, description='拟合优度检验方法')
    input_date: Optional[str] = Field(None, description='计算日期')
    start_date: Optional[str] = Field(None, description='计算起始日期')
    end_date: Optional[str] = Field(None, description='计算截止日期')
