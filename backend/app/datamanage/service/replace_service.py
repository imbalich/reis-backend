#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend 
@File    ：replace_service.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/1/20 09:41 
'''
from typing import Sequence

from sqlalchemy import Select

from backend.app.datamanage.crud.crud_replace import replace_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


class ReplaceService:

    @staticmethod
    async def get_models() -> Sequence[str]:
        async with async_db_session() as db:
            models = await replace_dao.get_distinct_column_values(db, 'model')
            if not models:
                raise errors.NotFoundError(msg='必换件数据中未找到型号')
            return models

    @staticmethod
    async def get_select(*, model: str = None,state_now: bool = None) -> Select:
        '''
        获取数据列表
        :param model: 产品型号
        :param state_now: 状态
        :return: 查询语句
        '''
        return await replace_dao.get_list(model=model, state_now=state_now)

replace_service: ReplaceService=ReplaceService()