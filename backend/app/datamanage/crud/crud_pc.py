#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend 
@File    ：curd_pc.py.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/3/24 14:13 
'''
from typing import Sequence, Any

from sqlalchemy import Select, select, distinct, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import PC

class CRUDPC(CRUDPlus[PC]):

    ## 根据产品信号获取PC列表，要求工具编号(check_tools_sign)不为空,自检结果(rela_self_value)不为合格,
    async def get_by_model(self, db: AsyncSession, model: str,product_no,process_name) -> Sequence[PC]:
        stmt = select(self.model).order_by(self.model.manufaucture_date)
        where_list = []
        where_list.append(self.model.prod_model == model)
        where_list.append(self.model.process_name == process_name)
        where_list.append(self.model.product_serial_no == product_no)
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
            product_nos: set[str],
            process_names: set[str]
    ) -> Sequence[PC]:
        stmt = select(self.model).where(
            self.model.prod_model == model,
            self.model.product_serial_no.in_(product_nos),
            self.model.process_name.in_(process_names),
            self.model.rela_self_value.notin_(['合格', '/']),
            self.model.rela_self_value.isnot(None),
            self.model.check_tools_sign.notin_(['/']),
            self.model.check_tools_sign.isnot(None),
            self.model.product_serial_no.isnot(None),
            self.model.self_create_by.isnot(None),
            self.model.check_tools.notin_(['目测', '感官目测','目测手感']),
            # self.model.check_tools_sign != self.model.rela_self_value
        ).order_by(
            self.model.product_serial_no,
            self.model.process_name
        )
        result = await db.execute(stmt)
        return result.scalars().all()

pc_dao: CRUDPC = CRUDPC(PC)
