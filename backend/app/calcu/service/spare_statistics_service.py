#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : spare_statistics_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : 备件统计服务
"""

from datetime import date
from typing import List, Tuple

from sqlalchemy import and_, func, select

from backend.app.datamanage.crud.crud_failure import CRUDFailure
from backend.app.datamanage.model import FailureModel
from backend.common.log import log
from backend.database.db import async_db_session


class SpareStatisticsService:
    """备件统计服务类。"""

    @staticmethod
    async def filter_model_part_combinations(
        input_date: date, min_failure_count: int = 10
    ) -> List[Tuple[str, str | None, str, int]]:
        """筛选符合条件的产品+派生码+零部件组合。"""
        async with async_db_session() as db:
            stmt = (
                select(
                    FailureModel.product_model,
                    FailureModel.product_config_code,
                    FailureModel.fault_material_code,
                    func.count(FailureModel.pk).label("failure_count"),
                )
                .where(
                    and_(
                        FailureModel.discovery_date <= input_date.strftime("%Y-%m-%d"),
                        FailureModel.is_zero_distance == 0,
                        FailureModel.fault_material_code.isnot(None),
                        FailureModel.manufacturing_date.isnot(None),
                        CRUDFailure._non_user_responsibility_condition(FailureModel),
                    )
                )
                .group_by(
                    FailureModel.product_model,
                    FailureModel.product_config_code,
                    FailureModel.fault_material_code,
                )
                .having(func.count(FailureModel.pk) >= min_failure_count)
                .order_by(
                    FailureModel.product_model,
                    FailureModel.product_config_code,
                    FailureModel.fault_material_code,
                )
            )

            rows = (await db.execute(stmt)).all()
            combinations = [
                (
                    row.product_model,
                    row.product_config_code,
                    row.fault_material_code,
                    row.failure_count,
                )
                for row in rows
            ]

            log.info(
                "筛选完成 input_date=%s min_failure_count=%s 组合数=%s",
                input_date,
                min_failure_count,
                len(combinations),
            )
            return combinations

    @staticmethod
    async def count_failures_by_model_part(
        model: str,
        part: str,
        start_date: date,
        end_date: date,
        product_config_code: str | None = None,
    ) -> int:
        """统计指定产品+派生码+零部件在时间范围内的实际故障数量。"""
        async with async_db_session() as db:
            conditions = [
                FailureModel.product_model == model,
                FailureModel.fault_material_code == part,
                FailureModel.discovery_date >= start_date.strftime("%Y-%m-%d"),
                FailureModel.discovery_date <= end_date.strftime("%Y-%m-%d"),
                FailureModel.is_zero_distance == 0,
                CRUDFailure._non_user_responsibility_condition(FailureModel),
            ]
            if product_config_code is not None:
                conditions.append(
                    FailureModel.product_config_code == product_config_code
                )

            stmt = select(func.count(FailureModel.pk)).where(and_(*conditions))
            count = (await db.execute(stmt)).scalar()
            return count if count is not None else 0

    @staticmethod
    async def get_part_name_by_model_part(
        model: str,
        part: str,
        start_date: date,
        end_date: date,
        product_config_code: str | None = None,
    ) -> str | None:
        """获取指定产品+派生码+零部件在时间范围内的零部件名称。"""
        async with async_db_session() as db:
            conditions = [
                FailureModel.product_model == model,
                FailureModel.fault_material_code == part,
                FailureModel.discovery_date >= start_date.strftime("%Y-%m-%d"),
                FailureModel.discovery_date <= end_date.strftime("%Y-%m-%d"),
                FailureModel.is_zero_distance == 0,
                FailureModel.fault_location.isnot(None),
                CRUDFailure._non_user_responsibility_condition(FailureModel),
            ]
            if product_config_code is not None:
                conditions.append(
                    FailureModel.product_config_code == product_config_code
                )

            stmt = select(func.min(FailureModel.fault_location)).where(and_(*conditions))
            part_name = (await db.execute(stmt)).scalar()
            return part_name if part_name else None


spare_statistics_service: SpareStatisticsService = SpareStatisticsService()
