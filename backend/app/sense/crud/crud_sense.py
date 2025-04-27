#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：reis-backend 
@File    ：crud_sense.py.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/4/25 10:20 
'''
from datetime import date
from typing import Sequence, Optional

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.sense.model.sense_sort import SenseSort
from backend.database import db


class CRUDSensePart(CRUDPlus[SenseSort]):
    async def creates(self, db: AsyncSession, objs) -> None:
        """
        创建单型号单零部件多条分布信息
        :param db:
        :param objs:
        :return:
        """
        await self.create_models(db, objs)

    async def get_last(
            self,
            db: AsyncSession,
            model: str,
            part: str,
            stage: str,
            process_name: str,
            check_project: str,
            check_bezier: str,
            extra_material_names: str,
            start_time: Optional[date] = None,
            end_time: Optional[date] = None
    ) -> SenseSort | None:
        """
        获取单条型号单零部件最后的一条分布信息
        :param db:
        :param model: 产品型号
        :param part: 零部件
        :param stage: 阶段
        :param process_name: 工序名称
        :param check_project: 检验区位
        :param check_bezier: 检验项点
        :param extra_material_names: 配件/原材料名称
        :param start_time: 计算开始时间
        :param end_time: 计算结束时间
        :return: 单条数据
        """
        stmt = (
            select(self.model)
            .where(self.model.model == model)
            .where(self.model.part == part)
            .where(self.model.stage == stage)
            .where(self.model.process_name == process_name)
            .where(self.model.check_project == check_project)
            .where(self.model.check_bezier == check_bezier)
            .where(self.model.extra_material_names == extra_material_names)
            .where(self.model.start_time == start_time)
            .where(self.model.end_time == end_time)
            .order_by(desc(self.model.created_time))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_model_and_part(
            self,
            db: AsyncSession,
            model: str,
            part: str,
            stage: str,
            process_name: str,
            check_project: str,
            check_bezier: str,
            extra_material_names: str,
            start_time: str,
            end_time: str,
    ) -> Sequence[SenseSort]:
        '''
        获取单个产品型号+零部件的敏感度分析排序结果
        :param db:
        :param model: 产品型号
        :param part: 零部件
        :param stage: 阶段
        :param process_name: 工序名称
        :param check_project: 检验区位
        :param check_bezier: 检验项点
        :param extra_material_names: 配件/原材料名称
        :param start_time: 计算开始时间
        :param end_time: 计算结束时间
        :return: 排序结果
        '''
        # 基本查询条件
        base_conditions = [
            self.model.model == model,
            self.model.part == part,
            self.model.stage == stage,
        ]

        if process_name:
            base_conditions.append(self.model.process_name == process_name)
        if check_project:
            base_conditions.append(self.model.check_project == check_project)
        if check_bezier:
            base_conditions.append(self.model.check_bezier == check_bezier)
        if start_time:
            base_conditions.append(self.model.start_time == start_time)
        if end_time:
            base_conditions.append(self.model.end_time == end_time)
        if extra_material_names:
            base_conditions.append(self.model.extra_material_names == extra_material_names)
        # 子查询：获取最新的group_id
        latest_group_subquery = (
            select(self.model.group_id)
            .where(and_(*base_conditions))
            .order_by(desc(self.model.created_time))
            .limit(1)
            .scalar_subquery()
        )

        # 主查询：获取最新group的所有记录并排序
        stmt = (
            select(self.model)
            .where(and_(*base_conditions, self.model.group_id == latest_group_subquery))
        )

        result = await db.execute(stmt)
        return result.scalars().all()

sense_dao: CRUDSensePart = CRUDSensePart(SenseSort)