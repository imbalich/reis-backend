#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project 锛歠astapi-base-backend
@File    锛歞espatch_service.py
@IDE     锛歅yCharm
@Author  锛歩mbalich
@Date    锛?024/12/26 16:52
"""

from typing import Any, Sequence

from sqlalchemy import Select

from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


def _extract_product_dimension_pair(row: Any) -> tuple[str | None, str | None]:
    mapping = getattr(row, "_mapping", None)
    if mapping is not None and "product_model" in mapping and "product_config_code" in mapping:
        return mapping["product_model"], mapping["product_config_code"]

    if hasattr(row, "product_model") or hasattr(row, "product_config_code"):
        return getattr(row, "product_model", None), getattr(row, "product_config_code", None)

    return row[0], row[1]


def _deduplicate_dimension_pairs(rows: Sequence[Any]) -> list[list[str | None]]:
    seen: set[tuple[str | None, str | None]] = set()
    pairs: list[list[str | None]] = []
    for row in rows:
        pair = _extract_product_dimension_pair(row)
        if pair in seen:
            continue
        seen.add(pair)
        pairs.append([pair[0], pair[1]])
    return pairs


class FailureService:
    @staticmethod
    async def get_product_lifetime_stage() -> Sequence[str]:
        async with async_db_session() as db:
            models = await failure_dao.get_distinct_column_values(
                db, "product_lifetime_stage"
            )
            if not models:
                raise errors.NotFoundError(msg="鏁呴殰鏁版嵁涓湭鎵惧埌浜у搧瀵垮懡闃舵")
            return models

    @staticmethod
    async def get_fault_mode() -> Sequence[str]:
        async with async_db_session() as db:
            models = await failure_dao.get_distinct_column_values(db, "fault_mode")
            if not models:
                raise errors.NotFoundError(msg="鏁呴殰鏁版嵁涓湭鎵惧埌缁堝垽鏁呴殰妯″紡")
            return models

    @staticmethod
    async def get_product_model() -> Sequence[str]:
        async with async_db_session() as db:
            models = await failure_dao.get_distinct_column_values(db, "product_model")
            if not models:
                raise errors.NotFoundError(msg="鏁呴殰鏁版嵁涓湭鎵惧埌浜у搧鍨嬪彿")
            return models

    @staticmethod
    async def get_product_dimension_pairs() -> Sequence[list[str | None]]:
        async with async_db_session() as db:
            rows = await failure_dao.get_distinct_columns_values(
                db, ["product_model", "product_config_code"]
            )
            return _deduplicate_dimension_pairs(rows)

    @staticmethod
    async def get_fault_location_by_product_model(
        product_model: str = None,
        product_config_code: str | None = None,
    ) -> Sequence[list[str]]:
        async with async_db_session() as db:
            if not product_model:
                raise errors.NotFoundError(msg="璇疯緭鍏ヤ骇鍝佸瀷鍙?")

            results = await failure_dao.get_distinct_columns_values_by_product_model(
                db,
                product_model,
                ["fault_location", "fault_material_code"],
                product_config_code=product_config_code,
            )

            unique_models: dict[str, str] = {}
            for fl, mc in results:
                if mc and mc[0] in ["C", "M", "Z"] and mc not in unique_models:
                    unique_models[mc] = fl
            return [[fl, mc] for mc, fl in unique_models.items()]

    @staticmethod
    async def get_select(
        *,
        product_model: str = None,
        product_config_code: str | None = None,
        fault_location: str = None,
        product_lifetime_stage: str = None,
        product_number: str = None,
        fault_mode: str = None,
        time_range: list[str] = None,
        is_zero_distance: int = 1,
        is_company: int = None,
        fault_material_code: str = None,
    ) -> Select:
        return await failure_dao.get_list(
            product_model=product_model,
            product_config_code=product_config_code,
            fault_location=fault_location,
            product_lifetime_stage=product_lifetime_stage,
            product_number=product_number,
            fault_mode=fault_mode,
            time_range=time_range,
            is_zero_distance=is_zero_distance,
            is_company=is_company,
            fault_material_code=fault_material_code,
        )

    @staticmethod
    async def get_parts_by_model(
        product_model: str = None, product_config_code: str | None = None
    ) -> Sequence[str]:
        async with async_db_session() as db:
            return await failure_dao.get_distinct_column_values_by_product_model(
                db,
                product_model,
                "fault_material_code",
                product_config_code=product_config_code,
            )

    @staticmethod
    async def get_parts_by_model_and_config(
        product_model: str, product_config_code: str | None
    ) -> Sequence[str]:
        return await FailureService.get_parts_by_model(
            product_model=product_model, product_config_code=product_config_code
        )


failure_service: FailureService = FailureService()
