#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend
@File    ：ebom_service.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/13 16:52
'''
from typing import Sequence

from sqlalchemy import Select

from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


class EbomService:

    @staticmethod
    async def get_models() -> Sequence[str]:
        async with async_db_session() as db:
            models = await ebom_dao.get_distinct_column_values(db, 'prd_no')
            if not models:
                raise errors.NotFoundError(msg='ebom数据中未找到型号')
            return models


    @staticmethod
    async def get_select(*,prd_no: str = None,partid: str=None,level1: int=0) -> Select:
        '''
        获取ebom查询
        :param prd_no: 产品型号
        :param partid: 父节点
        :param level1: 层级序号
        :return: ebom查询
        '''
        async with async_db_session() as db:
            if level1 == 0:
                return await ebom_dao.get_root_list(level1=level1,prd_no=prd_no)
            else:
                return await ebom_dao.get_node_list(partid=partid, level1=level1)

ebom_service: EbomService = EbomService()