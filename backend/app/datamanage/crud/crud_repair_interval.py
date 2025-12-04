#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：crud_repair_interval.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/10/11 16:47
"""

from typing import Any

from sqlalchemy import Select, Sequence, desc, distinct, select,asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import RepairInterval


class CRUDRepairInterval(CRUDPlus[RepairInterval]):
    
    async def get_repair_levels_by_model(self, db: AsyncSession, model: str) -> Sequence[RepairInterval]:
        """
        根据产品型号修程级别
        :param db: 数据库会话
        :param model: 产品型号
        :return: 修成级别表
        """
        stmt = select(self.model).order_by(asc(self.model.repair_years))
        where_list = []
        where_list.append(self.model.model == model)
        where_list.append(self.model.repair_levels != '新造')
        if where_list:
            stmt = stmt.where(*where_list)
        results = await db.execute(stmt)
        return results.scalars().all()

    async def get_repair_parts_with_names_only_by_model(
        self, db: AsyncSession, model: str
    ) -> Sequence[tuple[str, str]]:
        """
        根据型号获取零部件物料编码和名称的二元组列表
        :param db: 数据库会话
        :param model: 产品型号
        :return: (零部件名称, 零部件物料编码) 的二元组列表
        """
        stmt = (
            select(
                distinct(self.model.repair_years),  # 零部件名称
                self.model.repair_levels,  # 零部件物料编码
            )
            .where(
                self.model.model == model,
                self.model.repair_levels.isnot(None),  # 物料编码不为空
                self.model.repair_years.isnot(None),  # 部位名称不为空
                self.model.repair_levels.in_(['C5', 'C6', '首轮三级修', '首轮四级修', '首轮五级修','D5','D6'])
            )
            .order_by(self.model.repair_years ,self.model.repair_years)
        )

        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]


repair_interval_dao: CRUDRepairInterval = CRUDRepairInterval(RepairInterval)
