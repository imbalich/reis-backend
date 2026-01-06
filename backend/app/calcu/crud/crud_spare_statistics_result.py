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
from typing import List, Sequence, Any, Optional
from sqlalchemy import Select, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.calcu.model.spare_statistics_result import SpareStatisticsResult


class CRUDSpareStatisticsResult(CRUDPlus[SpareStatisticsResult]):
    """备件统计计算结果数据库操作类"""

    async def get_select(
        self,
        task_id: str | None = None,
        task_type: str | None = None,
        model: str | None = None,
        part: str | None = None,
        input_date: date | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        calculation_status: str | None = None,
    ) -> Select:
        """
        获取备件统计计算结果查询语句

        :param task_id: 任务ID
        :param task_type: 任务类型
        :param model: 产品型号
        :param part: 零部件物料编码
        :param input_date: 拟合输入日期
        :param start_date: 计算开始日期
        :param end_date: 计算结束日期
        :param calculation_status: 计算状态
        :return: 查询语句
        """
        query = select(self.model)
        conditions = []

        if task_id:
            conditions.append(self.model.task_id == task_id)
        if task_type:
            conditions.append(self.model.task_type == task_type)
        if model:
            conditions.append(self.model.model == model)
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
    ) -> Optional[SpareStatisticsResult]:
        """
        根据型号+零部件+日期条件查询记录（用于实际故障数量的覆盖更新）

        :param db: 数据库会话
        :param model: 产品型号
        :param part: 零部件物料编码
        :param input_date: 拟合输入日期
        :param start_date: 计算开始日期
        :param end_date: 计算结束日期
        :param task_type: 任务类型
        :return: 查询结果或None
        """
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.model == model,
                    self.model.part == part,
                    self.model.input_date == input_date,
                    self.model.start_date == start_date,
                    self.model.end_date == end_date,
                    self.model.task_type == task_type,
                )
            )
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
    ) -> Sequence[SpareStatisticsResult]:
        """
        根据型号+零部件+日期条件查询所有预测记录（task_type="prediction"）
        用于实际故障数量任务更新预测记录的 actual_failure_num

        :param db: 数据库会话
        :param model: 产品型号
        :param part: 零部件物料编码
        :param input_date: 拟合输入日期
        :param start_date: 计算开始日期
        :param end_date: 计算结束日期
        :return: 预测记录列表
        """
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.model == model,
                    self.model.part == part,
                    self.model.input_date == input_date,
                    self.model.start_date == start_date,
                    self.model.end_date == end_date,
                    self.model.task_type == "prediction",
                )
            )
            .order_by(self.model.created_time.desc())
        )

        result = await db.execute(stmt)
        return result.scalars().all()

    async def bulk_create(
        self, db: AsyncSession, result_data: List[dict[str, Any]]
    ) -> List[SpareStatisticsResult]:
        """
        批量创建备件统计计算结果

        :param db: 数据库会话
        :param result_data: 结果数据列表
        :return: 创建的结果列表
        """
        # 确保每个数据字典都包含 part_name 字段（如果缺失则设置为 None）
        for data in result_data:
            data.setdefault("part_name", None)
        results = [SpareStatisticsResult(**data) for data in result_data]
        db.add_all(results)
        await db.commit()
        for result in results:
            await db.refresh(result)
        return results

    async def get_distinct_task_ids(
        self, db: AsyncSession, task_type: str | None = None
    ) -> Sequence[str]:
        """
        获取所有唯一的任务ID列表

        :param db: 数据库会话
        :param task_type: 任务类型（可选，用于过滤）
        :return: 任务ID列表
        """
        from sqlalchemy import distinct

        stmt = select(distinct(self.model.task_id))
        if task_type:
            stmt = stmt.where(self.model.task_type == task_type)
        stmt = stmt.order_by(self.model.task_id.desc())

        result = await db.execute(stmt)
        return result.scalars().all()


spare_statistics_result_dao: CRUDSpareStatisticsResult = CRUDSpareStatisticsResult(
    SpareStatisticsResult
)
