#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : convert_model.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/2/25 下午1:57
"""

from datetime import date
from typing import Any, List, Sequence, Type, TypeVar

import pandas as pd

from backend.app.fit.schema.base_param import EbomParam
from backend.app.fit.schema.fit_param import CreatePartDistributionParam, CreateProductDistributionParam, FitMethodType
from backend.common.schema import SchemaBase
from backend.database.db import uuid4_str

T = TypeVar('T', bound=SchemaBase)


def convert_to_pydantic_models(values: Sequence[Any], model: Type[T]) -> List[T]:
    """
    将数据库查询结果Sequence转换为Pydantic模型列表

    :param values: 数据库查询结果
    :param model: Pydantic模型
    :return: Pydantic模型列表
    """
    return [model(**value) if isinstance(value, dict) else model.model_validate(value) for value in values]


def convert_to_pydantic_model(value: Any, model: Type[T]) -> T:
    """
    将数据库查询结果转换为Pydantic模型

    :param value: 数据库查询结果
    :param model: Pydantic模型
    :return: Pydantic模型
    """
    return model(**value) if isinstance(value, dict) else model.model_validate(value)


def convert_dict_to_pydantic_model(value: dict, model: Type[T]) -> T:
    """
    将字典转换为Pydantic模型

    :param value: 字典
    :param model: Pydantic模型
    :return: Pydantic模型
    """
    return model(**value)


def convert_to_product_distribution_params(
    fit_results: pd.DataFrame, model: str, input_date: date, method: FitMethodType, source: bool
) -> List[CreateProductDistributionParam]:
    distribution_params = []
    # 计算group_id
    group_id = uuid4_str()
    for _, row in fit_results.iterrows():
        param = CreateProductDistributionParam(
            group_id=group_id,
            model=model,
            input_date=input_date,  # 注意：这里移除了 .today()
            method=method,
            distribution=row['Distribution'],
            alpha=float(row['Alpha']) if pd.notna(row['Alpha']) and row['Alpha'] != '' else None,
            beta=float(row['Beta']) if pd.notna(row['Beta']) and row['Beta'] != '' else None,
            gamma=float(row['Gamma']) if pd.notna(row['Gamma']) and row['Gamma'] != '' else None,
            alpha_1=float(row['Alpha 1']) if pd.notna(row['Alpha 1']) and row['Alpha 1'] != '' else None,
            beta_1=float(row['Beta 1']) if pd.notna(row['Beta 1']) and row['Beta 1'] != '' else None,
            alpha_2=float(row['Alpha 2']) if pd.notna(row['Alpha 2']) and row['Alpha 2'] != '' else None,
            beta_2=float(row['Beta 2']) if pd.notna(row['Beta 2']) and row['Beta 2'] != '' else None,
            proportion_1=float(row['Proportion 1'])
            if pd.notna(row['Proportion 1']) and row['Proportion 1'] != ''
            else None,
            ds=float(row['DS']) if pd.notna(row['DS']) and row['DS'] != '' else None,
            mu=float(row['Mu']) if pd.notna(row['Mu']) and row['Mu'] != '' else None,
            sigma=float(row['Sigma']) if pd.notna(row['Sigma']) and row['Sigma'] != '' else None,
            lambda_=float(row['Lambda']) if pd.notna(row['Lambda']) and row['Lambda'] != '' else None,
            log_likelihood=float(row['Log-likelihood'])
            if pd.notna(row['Log-likelihood']) and row['Log-likelihood'] != ''
            else None,
            aicc=float(row['AICc']) if pd.notna(row['AICc']) and not pd.isna(row['AICc']) else None,
            bic=float(row['BIC']) if pd.notna(row['BIC']) and not pd.isna(row['BIC']) else None,
            ad=float(row['AD']) if pd.notna(row['AD']) and not pd.isna(row['AD']) else None,
            optimizer=row['optimizer'] if pd.notna(row['optimizer']) and row['optimizer'] != '' else None,
            source=source,
        )
        distribution_params.append(param)
    return distribution_params


def convert_to_part_distribution_params(
    fit_results: pd.DataFrame, model: str, part: str, input_date: date, method: FitMethodType, source: bool
) -> List[CreatePartDistributionParam]:
    distribution_params = []
    # 计算group_id
    group_id = uuid4_str()
    for _, row in fit_results.iterrows():
        param = CreatePartDistributionParam(
            group_id=group_id,
            model=model,
            part=part,
            input_date=input_date,  # 注意：这里移除了 .today()
            method=method,
            distribution=row['Distribution'],
            alpha=float(row['Alpha']) if pd.notna(row['Alpha']) and row['Alpha'] != '' else None,
            beta=float(row['Beta']) if pd.notna(row['Beta']) and row['Beta'] != '' else None,
            gamma=float(row['Gamma']) if pd.notna(row['Gamma']) and row['Gamma'] != '' else None,
            alpha_1=float(row['Alpha 1']) if pd.notna(row['Alpha 1']) and row['Alpha 1'] != '' else None,
            beta_1=float(row['Beta 1']) if pd.notna(row['Beta 1']) and row['Beta 1'] != '' else None,
            alpha_2=float(row['Alpha 2']) if pd.notna(row['Alpha 2']) and row['Alpha 2'] != '' else None,
            beta_2=float(row['Beta 2']) if pd.notna(row['Beta 2']) and row['Beta 2'] != '' else None,
            proportion_1=float(row['Proportion 1'])
            if pd.notna(row['Proportion 1']) and row['Proportion 1'] != ''
            else None,
            ds=float(row['DS']) if pd.notna(row['DS']) and row['DS'] != '' else None,
            mu=float(row['Mu']) if pd.notna(row['Mu']) and row['Mu'] != '' else None,
            sigma=float(row['Sigma']) if pd.notna(row['Sigma']) and row['Sigma'] != '' else None,
            lambda_=float(row['Lambda']) if pd.notna(row['Lambda']) and row['Lambda'] != '' else None,
            log_likelihood=float(row['Log-likelihood'])
            if pd.notna(row['Log-likelihood']) and row['Log-likelihood'] != ''
            else None,
            aicc=float(row['AICc']) if pd.notna(row['AICc']) and not pd.isna(row['AICc']) else None,
            bic=float(row['BIC']) if pd.notna(row['BIC']) and not pd.isna(row['BIC']) else None,
            ad=float(row['AD']) if pd.notna(row['AD']) and not pd.isna(row['AD']) else None,
            optimizer=row['optimizer'] if pd.notna(row['optimizer']) and row['optimizer'] != '' else None,
            source=source,
        )
        distribution_params.append(param)
    return distribution_params


def convert_to_product_exponential_distribution_params(
    model: str, input_date: date, method: FitMethodType, source: bool, lambda_: float
) -> CreateProductDistributionParam:
    group_id = uuid4_str()
    param = CreateProductDistributionParam(
        group_id=group_id,
        model=model,
        input_date=input_date,  # 注意：这里移除了 .today()
        method=method,
        distribution='Exponential_1P',
        alpha=None,
        beta=None,
        gamma=None,
        alpha_1=None,
        beta_1=None,
        alpha_2=None,
        beta_2=None,
        proportion_1=None,
        ds=None,
        mu=None,
        sigma=None,
        lambda_=lambda_,
        log_likelihood=None,
        aicc=None,
        bic=None,
        ad=None,
        optimizer=None,
        source=source,
    )
    return param


def convert_to_part_exponential_distribution_params(
    model: str, part: str, input_date: date, method: FitMethodType, source: bool, lambda_: float
) -> CreatePartDistributionParam:
    group_id = uuid4_str()
    param = CreatePartDistributionParam(
        group_id=group_id,
        model=model,
        part=part,
        input_date=input_date,  # 注意：这里移除了 .today()
        method=method,
        distribution='Exponential_1P',
        alpha=None,
        beta=None,
        gamma=None,
        alpha_1=None,
        beta_1=None,
        alpha_2=None,
        beta_2=None,
        proportion_1=None,
        ds=None,
        mu=None,
        sigma=None,
        lambda_=lambda_,
        log_likelihood=None,
        aicc=None,
        bic=None,
        ad=None,
        optimizer=None,
        source=source,
    )
    return param


def convert_to_total_quantity(ebom_data: list[EbomParam]) -> int:
    # 获取bl_quantity
    total_bl_quantity = 0
    for item in ebom_data:
        # 处理bl_quantity字段
        bl_quantity_str = item.bl_quantity if hasattr(item, 'bl_quantity') else '0'
        try:
            # 尝试将字符串转换为浮点数
            bl_quantity_float = float(bl_quantity_str)

            # 检查是否为整数
            if bl_quantity_float.is_integer():
                # 如果是整数，保持原值
                bl_quantity = int(bl_quantity_float)
            else:
                # 如果是浮点数，视为1
                bl_quantity = 1
        except (ValueError, TypeError):
            # 如果转换失败，默认为0
            bl_quantity = 0

        # 累加到总数
        total_bl_quantity += bl_quantity

    return total_bl_quantity


def convert_method_to_str(method: FitMethodType | str | None) -> str:
    """将各种类型的method参数统一转换为字符串"""
    if method is None:
        return FitMethodType.MLE.value
    elif isinstance(method, FitMethodType):
        return method.value
    elif isinstance(method, str):
        # 可以添加验证确保字符串是有效的方法
        valid_methods = [e.value for e in FitMethodType]
        return method if method in valid_methods else FitMethodType.MLE.value
