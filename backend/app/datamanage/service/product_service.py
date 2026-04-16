#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project 锛歠astapi-base-backend
@File    锛歱roduct_service.py
@IDE     锛歅yCharm
@Author  锛歩mbalich
@Date    锛?025/1/16 16:52
"""

from typing import Any, List, Sequence

from sqlalchemy import Select

from backend.app.datamanage.crud.crud_product import product_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


def _extract_model_config_pair(row: Any) -> tuple[str | None, str | None]:
    mapping = getattr(row, "_mapping", None)
    if mapping is not None and "model" in mapping and "product_config_code" in mapping:
        return mapping["model"], mapping["product_config_code"]

    if hasattr(row, "model") or hasattr(row, "product_config_code"):
        return getattr(row, "model", None), getattr(row, "product_config_code", None)

    return row[0], row[1]


def _deduplicate_dimension_pairs(rows: Sequence[Any]) -> list[list[str | None]]:
    seen: set[tuple[str | None, str | None]] = set()
    pairs: list[list[str | None]] = []
    for row in rows:
        pair = _extract_model_config_pair(row)
        if pair in seen:
            continue
        seen.add(pair)
        pairs.append([pair[0], pair[1]])
    return pairs


class ProductService:
    @staticmethod
    async def get_models() -> Sequence[str]:
        async with async_db_session() as db:
            models = await product_dao.get_distinct_column_values(db, "model")
            if not models:
                raise errors.NotFoundError(msg="浜у搧鏁版嵁涓湭鎵惧埌鍨嬪彿")
            return models

    @staticmethod
    async def get_product_dimension_pairs() -> Sequence[list[str | None]]:
        async with async_db_session() as db:
            rows = await product_dao.get_distinct_columns_values(
                db, ["model", "product_config_code"]
            )
            return _deduplicate_dimension_pairs(rows)

    @staticmethod
    async def get_run_time_parameters(
        model: str, product_config_code: str | None = None
    ) -> List[int | None]:
        async with async_db_session() as db:
            product = await product_dao.get_by_model(
                db, model=model, product_config_code=product_config_code
            )
            if product is None:
                raise errors.NotFoundError(msg=f"鏈壘鍒板瀷鍙蜂负 {model} 鐨勪骇鍝佷俊鎭?")

            return [product.year_days, product.avg_worktime, product.avg_speed]

    @staticmethod
    async def get_select(
        *, model: str = None, product_config_code: str | None = None
    ) -> Select:
        return await product_dao.get_list(model=model, product_config_code=product_config_code)


product_service: ProductService = ProductService()
