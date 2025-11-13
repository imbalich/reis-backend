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


repair_interval_dao: CRUDRepairInterval = CRUDRepairInterval(RepairInterval)
