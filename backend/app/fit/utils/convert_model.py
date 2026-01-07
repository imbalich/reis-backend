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
from backend.app.fit.schema.fit_param import (
    CreatePartDistributionParam,
    CreateProductDistributionParam,
    FitMethodType,
)
from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.app.datamanage.model.ebom import Ebom
from backend.common.schema import SchemaBase
from backend.database.db import uuid4_str
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T", bound=SchemaBase)


def convert_to_pydantic_models(values: Sequence[Any], model: Type[T]) -> List[T]:
    """
    将数据库查询结果Sequence转换为Pydantic模型列表

    :param values: 数据库查询结果
    :param model: Pydantic模型
    :return: Pydantic模型列表
    """
    return [
        model(**value) if isinstance(value, dict) else model.model_validate(value)
        for value in values
    ]


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
    fit_results: pd.DataFrame,
    model: str,
    input_date: date,
    method: FitMethodType,
    source: bool,
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
            distribution=row["Distribution"],
            alpha=(
                float(row["Alpha"])
                if pd.notna(row["Alpha"]) and row["Alpha"] != ""
                else None
            ),
            beta=(
                float(row["Beta"])
                if pd.notna(row["Beta"]) and row["Beta"] != ""
                else None
            ),
            gamma=(
                float(row["Gamma"])
                if pd.notna(row["Gamma"]) and row["Gamma"] != ""
                else None
            ),
            alpha_1=(
                float(row["Alpha 1"])
                if pd.notna(row["Alpha 1"]) and row["Alpha 1"] != ""
                else None
            ),
            beta_1=(
                float(row["Beta 1"])
                if pd.notna(row["Beta 1"]) and row["Beta 1"] != ""
                else None
            ),
            alpha_2=(
                float(row["Alpha 2"])
                if pd.notna(row["Alpha 2"]) and row["Alpha 2"] != ""
                else None
            ),
            beta_2=(
                float(row["Beta 2"])
                if pd.notna(row["Beta 2"]) and row["Beta 2"] != ""
                else None
            ),
            proportion_1=(
                float(row["Proportion 1"])
                if pd.notna(row["Proportion 1"]) and row["Proportion 1"] != ""
                else None
            ),
            ds=float(row["DS"]) if pd.notna(row["DS"]) and row["DS"] != "" else None,
            mu=float(row["Mu"]) if pd.notna(row["Mu"]) and row["Mu"] != "" else None,
            sigma=(
                float(row["Sigma"])
                if pd.notna(row["Sigma"]) and row["Sigma"] != ""
                else None
            ),
            lambda_=(
                float(row["Lambda"])
                if pd.notna(row["Lambda"]) and row["Lambda"] != ""
                else None
            ),
            log_likelihood=(
                float(row["Log-likelihood"])
                if pd.notna(row["Log-likelihood"]) and row["Log-likelihood"] != ""
                else None
            ),
            aicc=(
                float(row["AICc"])
                if pd.notna(row["AICc"]) and not pd.isna(row["AICc"])
                else None
            ),
            bic=(
                float(row["BIC"])
                if pd.notna(row["BIC"]) and not pd.isna(row["BIC"])
                else None
            ),
            ad=(
                float(row["AD"])
                if pd.notna(row["AD"]) and not pd.isna(row["AD"])
                else None
            ),
            optimizer=(
                row["optimizer"]
                if pd.notna(row["optimizer"]) and row["optimizer"] != ""
                else None
            ),
            source=source,
        )
        distribution_params.append(param)
    return distribution_params


def convert_to_part_distribution_params(
    fit_results: pd.DataFrame,
    model: str,
    part: str,
    input_date: date,
    method: FitMethodType,
    source: bool,
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
            distribution=row["Distribution"],
            alpha=(
                float(row["Alpha"])
                if pd.notna(row["Alpha"]) and row["Alpha"] != ""
                else None
            ),
            beta=(
                float(row["Beta"])
                if pd.notna(row["Beta"]) and row["Beta"] != ""
                else None
            ),
            gamma=(
                float(row["Gamma"])
                if pd.notna(row["Gamma"]) and row["Gamma"] != ""
                else None
            ),
            alpha_1=(
                float(row["Alpha 1"])
                if pd.notna(row["Alpha 1"]) and row["Alpha 1"] != ""
                else None
            ),
            beta_1=(
                float(row["Beta 1"])
                if pd.notna(row["Beta 1"]) and row["Beta 1"] != ""
                else None
            ),
            alpha_2=(
                float(row["Alpha 2"])
                if pd.notna(row["Alpha 2"]) and row["Alpha 2"] != ""
                else None
            ),
            beta_2=(
                float(row["Beta 2"])
                if pd.notna(row["Beta 2"]) and row["Beta 2"] != ""
                else None
            ),
            proportion_1=(
                float(row["Proportion 1"])
                if pd.notna(row["Proportion 1"]) and row["Proportion 1"] != ""
                else None
            ),
            ds=float(row["DS"]) if pd.notna(row["DS"]) and row["DS"] != "" else None,
            mu=float(row["Mu"]) if pd.notna(row["Mu"]) and row["Mu"] != "" else None,
            sigma=(
                float(row["Sigma"])
                if pd.notna(row["Sigma"]) and row["Sigma"] != ""
                else None
            ),
            lambda_=(
                float(row["Lambda"])
                if pd.notna(row["Lambda"]) and row["Lambda"] != ""
                else None
            ),
            log_likelihood=(
                float(row["Log-likelihood"])
                if pd.notna(row["Log-likelihood"]) and row["Log-likelihood"] != ""
                else None
            ),
            aicc=(
                float(row["AICc"])
                if pd.notna(row["AICc"]) and not pd.isna(row["AICc"])
                else None
            ),
            bic=(
                float(row["BIC"])
                if pd.notna(row["BIC"]) and not pd.isna(row["BIC"])
                else None
            ),
            ad=(
                float(row["AD"])
                if pd.notna(row["AD"]) and not pd.isna(row["AD"])
                else None
            ),
            optimizer=(
                row["optimizer"]
                if pd.notna(row["optimizer"]) and row["optimizer"] != ""
                else None
            ),
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
        distribution="Exponential_1P",
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
    model: str,
    part: str,
    input_date: date,
    method: FitMethodType,
    source: bool,
    lambda_: float,
) -> CreatePartDistributionParam:
    group_id = uuid4_str()
    param = CreatePartDistributionParam(
        group_id=group_id,
        model=model,
        part=part,
        input_date=input_date,  # 注意：这里移除了 .today()
        method=method,
        distribution="Exponential_1P",
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


async def get_ebom_tree_with_parents(
    db: AsyncSession, model: str, part: str
) -> list[Ebom]:
    """
    递归获取完整的BOM树（包括所有父级节点）

    :param db: 数据库会话
    :param model: 产品型号
    :param part: 零部件物料编码
    :return: 完整的BOM数据列表（包括当前节点和所有父级节点）
    """
    # 1. 查询当前零部件的数据
    current_items = await ebom_dao.get_by_model_and_part(db, model, part)
    if not current_items:
        return []

    # 2. 收集所有需要查询的partid（父节点ID）
    all_items = list(current_items)  # 复制列表
    id_to_item = {item.id: item for item in all_items}  # 构建id映射
    partids_to_fetch = set()  # 需要查询的partid集合

    # 从当前节点收集所有partid
    for item in current_items:
        partid = getattr(item, "partid", None)
        if partid and partid not in id_to_item:
            partids_to_fetch.add(partid)

    # 3. 递归查询所有父级节点
    visited_partids = set()  # 防止重复查询和循环引用
    while partids_to_fetch:
        current_partid = partids_to_fetch.pop()

        # 防止循环引用和重复查询
        if current_partid in visited_partids:
            continue
        visited_partids.add(current_partid)

        # 查询父节点
        parent_item = await ebom_dao.get_by_id(db, current_partid)
        if parent_item:
            all_items.append(parent_item)
            id_to_item[parent_item.id] = parent_item

            # 如果父节点还有父节点，继续查询
            parent_partid = getattr(parent_item, "partid", None)
            if parent_partid and parent_partid not in id_to_item:
                partids_to_fetch.add(parent_partid)

    return all_items


def convert_to_total_quantity(ebom_data: list, part: str = None) -> int:
    """
    计算BOM总数量（考虑层级结构）

    对于每条BOM数据，需要向上查找所有父级，将当前条目的bl_quantity与所有父级的bl_quantity相乘，
    然后将所有最终结果相加。

    :param ebom_data: BOM数据列表（可以是Ebom对象或EbomParam对象，必须包含完整的父子关系）
    :param part: 零部件物料编码（可选，如果提供则只处理匹配的节点）
    :return: 总数量
    """
    if not ebom_data:
        return 0

    # 构建id到对象的映射（用于快速查找父级）
    id_to_item = {}
    for item in ebom_data:
        item_id = getattr(item, "id", None)
        if item_id:
            id_to_item[item_id] = item

    total_bl_quantity = 0

    # 如果提供了part参数，只处理匹配的节点；否则处理所有节点
    items_to_process = ebom_data
    if part:
        items_to_process = [
            item for item in ebom_data if getattr(item, "y8_matbnum1", None) == part
        ]

    for item in items_to_process:
        # 处理bl_quantity字段
        bl_quantity_str = getattr(item, "bl_quantity", "0") or "0"
        try:
            # 尝试将字符串转换为浮点数
            bl_quantity_float = float(bl_quantity_str)

            # 检查是否为整数
            if bl_quantity_float.is_integer():
                # 如果是整数，保持原值
                current_quantity = int(bl_quantity_float)
            else:
                # 如果是浮点数，视为1
                current_quantity = 1
        except (ValueError, TypeError):
            # 如果转换失败，默认为1（而不是0，因为0会导致整个链为0）
            current_quantity = 1

        # 如果当前数量为0，跳过
        if current_quantity == 0:
            continue

        # 向上遍历父级，计算连乘结果
        multiplied_quantity = current_quantity
        current_item = item
        visited_ids = set()  # 防止循环引用

        while True:
            # 获取父节点ID
            partid = getattr(current_item, "partid", None)
            level1 = getattr(current_item, "level1", 0)

            # 如果没有父节点（顶层），或者partid为空/None，停止
            if not partid or partid == "" or level1 == 0:
                break

            # 防止循环引用
            if partid in visited_ids:
                break
            visited_ids.add(partid)

            # 查找父节点
            parent_item = id_to_item.get(partid)
            if not parent_item:
                # 如果找不到父节点，停止（可能父节点不在当前查询结果中）
                break

            # 获取父节点的bl_quantity
            parent_quantity_str = getattr(parent_item, "bl_quantity", "0") or "0"
            try:
                parent_quantity_float = float(parent_quantity_str)
                if parent_quantity_float.is_integer():
                    parent_quantity = int(parent_quantity_float)
                else:
                    parent_quantity = 1
            except (ValueError, TypeError):
                parent_quantity = 1

            # 如果父节点数量为0，整个链为0
            if parent_quantity == 0:
                multiplied_quantity = 0
                break

            # 乘以父节点数量
            multiplied_quantity *= parent_quantity

            # 继续向上查找
            current_item = parent_item

        # 累加到总数
        total_bl_quantity += multiplied_quantity

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
