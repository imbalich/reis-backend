#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : fit_param.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/2/28 涓嬪崍3:49
"""

from datetime import date

from pydantic import ConfigDict

from backend.common.enums import StrEnum
from backend.common.schema import SchemaBase


class FitMethodType(StrEnum):
    """拟合方法"""

    MLE = "MLE"
    LS = "LS"
    RRX = "RRX"
    RRY = "RRY"


class FitCheckType(StrEnum):
    BIC = "BIC"
    AICc = "AICc"
    AD = "AD"
    Log = "Log-likelihood"


class CreateFitProductInParam(SchemaBase):
    model: str
    product_config_code: str
    input_date: str | None = None
    method: FitMethodType = FitMethodType.MLE


class CreateFitPartInParam(SchemaBase):
    model: str
    product_config_code: str
    part: str
    input_date: str | None = None
    method: FitMethodType | None = FitMethodType.MLE


class CreateFitAllProductInParam(SchemaBase):
    input_date: str | None = None
    method: FitMethodType = FitMethodType.MLE


class CreateFitAllPartInParam(SchemaBase):
    input_date: str | None = None
    method: FitMethodType = FitMethodType.MLE


class CreateFitModelAllPartInParam(SchemaBase):
    model: str
    product_config_code: str | None = None
    input_date: str | None = None
    method: FitMethodType = FitMethodType.MLE


class CreateProductDistributionParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    group_id: str
    model: str
    product_config_code: str | None = None
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
    lambda_: float | None = None
    log_likelihood: float | None = None
    aicc: float | None = None
    bic: float | None = None
    ad: float | None = None
    optimizer: str | None = None

    source: bool


class CreatePartDistributionParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    group_id: str
    model: str
    product_config_code: str | None = None
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
    lambda_: float | None = None
    log_likelihood: float | None = None
    aicc: float | None = None
    bic: float | None = None
    ad: float | None = None
    optimizer: str | None = None

    source: bool
