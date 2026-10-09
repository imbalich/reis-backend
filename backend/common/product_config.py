#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""派生码查询约定：PS00 同时匹配空派生码，其它派生码精确匹配。"""

from sqlalchemy import ColumnElement, or_

DEFAULT_PRODUCT_CONFIG_CODE = "PS00"


def build_product_config_code_filter(
    column,
    product_config_code: str | None,
) -> ColumnElement | None:
    """构建派生码过滤条件。未指定派生码时返回 None，表示不加该条件。"""
    if product_config_code is None:
        return None
    code = str(product_config_code).strip()
    if not code:
        return None
    if code == DEFAULT_PRODUCT_CONFIG_CODE:
        return or_(column == code, column.is_(None), column == "")
    return column == code


def apply_product_config_code_filter(
    where_list: list,
    column,
    product_config_code: str | None,
) -> None:
    condition = build_product_config_code_filter(column, product_config_code)
    if condition is not None:
        where_list.append(condition)
