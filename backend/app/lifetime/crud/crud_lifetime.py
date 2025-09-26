#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：crud_equal_lifetime_optimization.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/15 14:03
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_,desc
from sqlalchemy import delete as sa_delete

from backend.app.lifetime.model.equal_lifetime import EqualLifetime
from sqlalchemy_crud_plus import CRUDPlus



class CRUDEqualLifetime(CRUDPlus[EqualLifetime]):
    """等寿命点优化结果CRUD操作类"""
    
    async def creates(self, db: AsyncSession, objs) -> None:
        """
        创建单型号多条分布信息
        :param db:
        :param objs:
        :return:
        """
        await self.create_models(db, objs)
    

    async def get_by_model(
            self, db: AsyncSession,
            model: str,
            target_sf: float,
            step_start: float,
            step_end: float
            ):
        """
        根据产品型号获取等寿命点优化结果
        :param db:
        :param model:
        :return:
        """

        stmt = select(self.model).order_by(desc(self.model.created_time))
        where_list = []
        where_list.append(self.model.model == model)
        where_list.append(self.model.target_sf.between(target_sf-1e-6, target_sf+1e-6))
        where_list.append(self.model.step_start.between(step_start-1e-6, step_start+1e-6))
        where_list.append(self.model.step_end.between(step_end-1e-6, step_end+1e-6))
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()
    

    @staticmethod
    async def delete_all(db: AsyncSession) -> None:
        """
        删除所有等寿命结果

        :param db: 数据库会话
        :return:
        """
        await db.execute(sa_delete(EqualLifetime))



equal_lifetime_dao: CRUDEqualLifetime= CRUDEqualLifetime(EqualLifetime)