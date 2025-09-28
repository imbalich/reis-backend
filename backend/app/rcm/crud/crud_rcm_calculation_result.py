#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : crud_rcm_calculation_result.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : RCM计算结果CRUD操作
"""

from typing import List, Sequence, Any
from datetime import datetime

from sqlalchemy import Select, delete, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.rcm.model.rcm_calculation_result import RcmCalculationResult


class CRUDRcmCalculationResult(CRUDPlus[RcmCalculationResult]):
    """RCM计算结果数据库操作类"""

    async def get_by_base_data_id(
        self, db: AsyncSession, base_data_id: int
    ) -> RcmCalculationResult | None:
        """
        根据基础数据ID获取计算结果

        :param db: 数据库会话
        :param base_data_id: 基础数据ID
        :return: 计算结果
        """
        stmt = select(self.model).where(self.model.base_data_id == base_data_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def clear_by_base_data_id(self, db: AsyncSession, base_data_id: int) -> None:
        """
        清除指定基础数据ID的计算结果

        :param db: 数据库会话
        :param base_data_id: 基础数据ID
        """
        await db.execute(
            delete(self.model).where(self.model.base_data_id == base_data_id)
        )
        await db.commit()

    async def bulk_create_results(
        self, db: AsyncSession, results: List[dict[str, Any]]
    ) -> List[RcmCalculationResult]:
        """
        批量创建计算结果

        :param db: 数据库会话
        :param results: 计算结果列表
        :return: 创建的计算结果列表
        """
        result_records = [RcmCalculationResult(**data) for data in results]
        db.add_all(result_records)
        await db.commit()
        for record in result_records:
            await db.refresh(record)
        return result_records

    async def create(
        self, db: AsyncSession, obj_in: dict[str, Any]
    ) -> RcmCalculationResult:
        """
        创建单个计算结果记录

        :param db: 数据库会话
        :param obj_in: 计算结果数据
        :return: 创建的计算结果记录
        """
        result_record = RcmCalculationResult(**obj_in)
        db.add(result_record)
        await db.commit()
        await db.refresh(result_record)
        return result_record

    async def get_calculation_history(
        self, db: AsyncSession, limit: int = 100
    ) -> Sequence[RcmCalculationResult]:
        """
        获取计算历史记录

        :param db: 数据库会话
        :param limit: 限制数量
        :return: 计算历史记录列表
        """
        stmt = (
            select(self.model).order_by(self.model.calculation_time.desc()).limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_results_with_filters(
        self,
        db: AsyncSession,
        product_model: str = None,
        component_name: str = None,
        component_material_code: str = None,
        final_result: str = None,
    ) -> Select:
        """
        根据过滤条件获取查询语句

        :param db: 数据库会话
        :param product_model: 产品型号
        :param component_name: 部件名称
        :param component_material_code: 零部件物料编码
        :param final_result: 最终计算结果
        :return: 查询语句
        """
        from backend.app.rcm.model.rcm_base_data import RcmBaseData

        # 构建查询语句，关联基础数据表，选择需要的字段
        stmt = select(
            self.model,
            RcmBaseData.product_model,
            RcmBaseData.component_name,
            RcmBaseData.component_material_code,
            RcmBaseData.failure_mode,
        ).join(RcmBaseData, self.model.base_data_id == RcmBaseData.id)

        # 添加过滤条件
        if product_model:
            stmt = stmt.where(RcmBaseData.product_model.like(f"%{product_model}%"))
        if component_name:
            stmt = stmt.where(RcmBaseData.component_name.like(f"%{component_name}%"))
        if component_material_code:
            stmt = stmt.where(
                RcmBaseData.component_material_code.like(f"%{component_material_code}%")
            )
        if final_result:
            stmt = stmt.where(self.model.final_result.like(f"%{final_result}%"))

        # 按计算时间倒序排列
        stmt = stmt.order_by(self.model.calculation_time.desc())

        return stmt


rcm_calculation_result_dao: CRUDRcmCalculationResult = CRUDRcmCalculationResult(
    RcmCalculationResult
)
