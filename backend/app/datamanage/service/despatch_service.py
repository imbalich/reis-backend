#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：despatch_service.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/26 16:52
"""

from typing import Sequence

from sqlalchemy import Select

from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


class DespatchService:
    @staticmethod
    async def get_models() -> Sequence[str]:
        async with async_db_session() as db:
            models = await despatch_dao.get_distinct_column_values(db, 'model')
            if not models:
                raise errors.NotFoundError(msg='发运数据中未找到型号')
            return models

    @staticmethod
    async def get_repair_levels() -> Sequence[str]:
        async with async_db_session() as db:
            repair_levels = await despatch_dao.get_distinct_column_values(db, 'repair_level')
            if not repair_levels:
                raise errors.NotFoundError(msg='发运数据中未找到修理级别')
            return repair_levels

    @staticmethod
    async def get_select(
        *, model: str = None, identifier: str = None, repair_level: str = None, time_range: list[str] = None
    ) -> Select:
        # 时间范围
        return await despatch_dao.get_list(
            model=model, identifier=identifier, repair_level=repair_level, time_range=time_range
        )


despatch_service: DespatchService = DespatchService()
