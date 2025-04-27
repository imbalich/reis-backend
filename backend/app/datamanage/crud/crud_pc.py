#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：curd_pc.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/3/24 14:13
"""

from typing import Sequence

from sqlalchemy import select,or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import PC


class CRUDPC(CRUDPlus[PC]):
    async def get_by_model(self, db: AsyncSession, model: str) -> Sequence[PC]:
        """
        根据产品型号查询PC列表,仅检测使用
        :param db: 数据库会话
        :param model: 产品型号
        :return: PC列表
        """
        stmt = select(self.model).order_by(self.model.manufaucture_date)
        where_list = []
        where_list.append(self.model.prod_model == model)
        where_list.append(self.model.rela_self_value != '合格')
        where_list.append(self.model.product_serial_no is not None)
        where_list.append(self.model.self_create_by is not None)
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_batch_by_products(
            self,
            db: AsyncSession,
            model: str,
            stage: str,
            check_project: str,
            check_bezier: str,
            product_nos: set[str],
            process_names: set[str]
    ) -> Sequence[PC]:
        """
        根据产品型号、造修阶段、检修区位、检修项点、产品编号、工序名称集合查询PC列表
        :param db: 数据库会话
        :param model: 产品型号
        :param stage: 造修阶段
        :param check_project: 检修区位
        :param check_bezier: 检修项点
        :param product_nos: 产品编号集合
        :param process_names: 工序名称集合
        :return: PC列表
        """
        stage_variants = [stage, f"首轮{stage}", f"次轮{stage}", f"三轮{stage}", f"首轮{stage}修", f"次轮{stage}修",
                          f"三轮{stage}修", ]
        where_list = [
            self.model.prod_model == model,
            self.model.product_serial_no.in_(product_nos),
            self.model.repair_level.in_(stage_variants),
            self.model.rela_self_value.notin_(['合格', '/']),
            self.model.rela_self_value.isnot(None),
            self.model.check_tools_sign.notin_(['/']),
            self.model.check_tools_sign.isnot(None),
            self.model.product_serial_no.isnot(None),
            self.model.self_create_by.isnot(None),
            self.model.check_tools.notin_(['目测', '感官目测', '目测手感']),
        ]

        if process_names:
            base_process_names = {name.split("（")[0] for name in process_names}
            where_list.append(
                or_(*[self.model.process_name.startswith(base_name) for base_name in base_process_names])
            )

        if check_project:
            where_list.append(self.model.check_project == check_project)
        if check_bezier:
            where_list.append(self.model.check_bezier == check_bezier)
        stmt = select(self.model).where(*where_list).order_by(self.model.product_serial_no, self.model.process_name)
        result = await db.execute(stmt)
        return result.scalars().all()


pc_dao: CRUDPC = CRUDPC(PC)
