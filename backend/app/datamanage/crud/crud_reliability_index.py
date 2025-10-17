#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：crud_reliability_index.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/10/11 16:47
"""

from typing import Any

from sqlalchemy import Select, Sequence, desc, distinct, select,asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import ReliabilityIndex


class CRUDReliabilityIndex(CRUDPlus[ReliabilityIndex]):
    
    async def get_pre_value_by_model_and_part(self, db: AsyncSession, model: str, part:str) -> Sequence[ReliabilityIndex]:
        """
        根据产品型号+物料编码获取预计值
        :param db: 数据库会话
        :param model: 产品型号
        :return: 修成级别表
        """
        stmt = select(self.model.pre_value)
        where_list = []
        where_list.append(self.model.model == model)
        where_list.append(self.model.part == part)
        if where_list:
            stmt = stmt.where(*where_list)
        results = await db.execute(stmt)
        return results.scalars().first()


reliability_index_dao: CRUDReliabilityIndex = CRUDReliabilityIndex(ReliabilityIndex)
