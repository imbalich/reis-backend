#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：crud_unqualify.py
@IDE     ：PyCharm
@Author  ：seven
@Date    ：2025/10/13 11:36
"""

from typing import Any,Tuple,Sequence

from sqlalchemy import Select, desc, distinct, select,asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Unqualify


class CRUDUnqualify(CRUDPlus[Unqualify]):
    
    async def get_by_model_and_part(self, db: AsyncSession, model: str, part:str) -> Sequence[Unqualify]:
        """
        根据产品型号修程级别
        :param db: 数据库会话
        :param model: 产品型号
        :return: 修成级别表
        """
        # stmt = select(self.model)
        stmt = select(self.model).order_by(asc(self.model.occurrence_rate))
        where_list = []
        where_list.append(self.model.product_model == model)
        where_list.append(self.model.ncr_material_code == part)
        where_list.append(self.model.is_new == '检修')
        where_list.append(self.model.repair_levels != '')
        if where_list:
            stmt = stmt.where(*where_list)
        stmt = stmt.distinct() 
        results = await db.execute(stmt)
        return results.scalars().all()


unqualify_dao: CRUDUnqualify = CRUDUnqualify(Unqualify)
