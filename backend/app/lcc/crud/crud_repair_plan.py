#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：crud_repair_plan.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/15 14:03
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_,desc
from sqlalchemy import delete as sa_delete
from typing import Sequence, Any, Optional,List

from backend.app.lcc.model.repair_plan import RepairPlan
from sqlalchemy_crud_plus import CRUDPlus



class CRUDRepairPlan(CRUDPlus[RepairPlan]):
    """等寿命点优化结果CRUD操作类"""
    
    async def creates(self, db: AsyncSession, objs) -> None:
        """
        创建单型号多条分布信息
        :param db:
        :param objs:
        :return:
        """
        await self.create_models(db, objs)

    
    async def get_lcc_parts_with_names_only_by_model(
        self, db: AsyncSession, model: str,parts: list[str]
    ) -> List[tuple[str, str]]:
        """
        根据型号获取零部件物料编码和名称的二元组列表
        :param db: 数据库会话
        :param model: 产品型号
        :return: (零部件名称, 零部件物料编码) 的二元组列表
        """
        # 如果 parts 为空，直接返回空列表，避免构造 SQL IN ()
        if not parts:
            return []

        stmt = (
            select(
                self.model.part,    # 零部件物料编码
                self.model.level_new,  # 推荐修程周期
            )
            .where(
                self.model.model == model,
                self.model.part.in_(parts),
            )
            # 按 id 降序，确保最新记录排在前面（调用方可按需要取第一个）
            .order_by(desc(self.model.created_time))
        )

        res = await db.execute(stmt)
        result = res.all()  # List[Tuple[part, year_new]]
        return result
        


    


    



repair_plan_dao: CRUDRepairPlan= CRUDRepairPlan(RepairPlan)