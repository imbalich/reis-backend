#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：repair_service.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/20 09:40
"""

from typing import Sequence

from sqlalchemy import Select

from backend.app.datamanage.crud.crud_repair import repair_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


class RepairService:
    @staticmethod
    async def get_models() -> Sequence[str]:
        async with async_db_session() as db:
            models = await repair_dao.get_distinct_column_values(db, 'model')
            if not models:
                raise errors.NotFoundError(msg='造修阶段数据中未找到型号')
            return models

    @staticmethod
    async def get_select(*, model: str = None, state_now: bool = None) -> Select:
        """
        获取数据列表
        :param model: 产品型号
        :param state_now: 当前状态
        :return: 查询语句
        """
        return await repair_dao.get_list(model=model, state_now=state_now)


repair_service: RepairService = RepairService()
