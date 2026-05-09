#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : crud_spare_statistics_result.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : 备件统计计算结果CRUD操作
"""

from datetime import date
from typing import Any, List, Optional, Sequence

from sqlalchemy import Select, and_, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.calcu.model.spare_statistics_result import SpareStatisticsResult


class CRUDSpareStatisticsResult(CRUDPlus[SpareStatisticsResult]):
    """备件统计计算结果数据库操作类。"""

    async def get_select(
        self,
        task_id: str | None = None,
        task_type: str | None = None,
        model: str | None = None,
        product_config_code: str | None = None,
        part: str | None = None,
        input_date: date | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        calculation_status: str | None = None,
    ) -> Select:
        query = select(self.model)
        conditions = []

        if task_id:
            conditions.append(self.model.task_id == task_id)
        if task_type:
            conditions.append(self.model.task_type == task_type)
        if model:
            conditions.append(self.model.model == model)
        if product_config_code is not None:
            conditions.append(self.model.product_config_code == product_config_code)
        if part:
            conditions.append(self.model.part == part)
        if input_date:
            conditions.append(self.model.input_date == input_date)
        if start_date:
            conditions.append(self.model.start_date == start_date)
        if end_date:
            conditions.append(self.model.end_date == end_date)
        if calculation_status:
            conditions.append(self.model.calculation_status == calculation_status)

        if conditions:
            query = query.where(and_(*conditions))

        return query.order_by(self.model.created_time.desc())

    async def get_by_model_part_dates(
        self,
        db: AsyncSession,
        model: str,
        part: str,
        input_date: date,
        start_date: date,
        end_date: date,
        task_type: str,
        product_config_code: str | None = None,
    ) -> Optional[SpareStatisticsResult]:
        conditions = [
            self.model.model == model,
            self.model.part == part,
            self.model.input_date == input_date,
            self.model.start_date == start_date,
            self.model.end_date == end_date,
            self.model.task_type == task_type,
        ]
        if product_config_code is not None:
            conditions.append(self.model.product_config_code == product_config_code)
        else:
            conditions.append(self.model.product_config_code.is_(None))

        stmt = (
            select(self.model)
            .where(and_(*conditions))
            .order_by(self.model.created_time.desc())
            .limit(1)
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_prediction_records_by_model_part_dates(
        self,
        db: AsyncSession,
        model: str,
        part: str,
        input_date: date,
        start_date: date,
        end_date: date,
        product_config_code: str | None = None,
    ) -> Sequence[SpareStatisticsResult]:
        conditions = [
            self.model.model == model,
            self.model.part == part,
            self.model.input_date == input_date,
            self.model.start_date == start_date,
            self.model.end_date == end_date,
            self.model.task_type == "prediction",
        ]
        if product_config_code is not None:
            conditions.append(self.model.product_config_code == product_config_code)
        else:
            conditions.append(self.model.product_config_code.is_(None))

        stmt = select(self.model).where(and_(*conditions)).order_by(
            self.model.created_time.desc()
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def bulk_create(
        self, db: AsyncSession, result_data: List[dict[str, Any]]
    ) -> List[SpareStatisticsResult]:
        for data in result_data:
            data.setdefault("part_name", None)
            data.setdefault("product_config_code", None)
        results = [SpareStatisticsResult(**data) for data in result_data]
        db.add_all(results)
        await db.commit()
        for result in results:
            await db.refresh(result)
        return results

    async def get_distinct_task_ids(
        self, db: AsyncSession, task_type: str | None = None
    ) -> Sequence[str]:
        stmt = select(distinct(self.model.task_id))
        if task_type:
            stmt = stmt.where(self.model.task_type == task_type)
        stmt = stmt.order_by(self.model.task_id.desc())

        result = await db.execute(stmt)
        return result.scalars().all()


spare_statistics_result_dao: CRUDSpareStatisticsResult = CRUDSpareStatisticsResult(
    SpareStatisticsResult
)
