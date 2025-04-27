#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：data_check_utils.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/3/28 08:53
"""

from backend.app.datamanage.crud.crud_configuration import configuration_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_pc import pc_dao
from backend.database.db import async_db_session


class DataCheckUtils:
    @staticmethod
    async def check_model_and_part_in_failure(model: str, part: str) -> bool:
        """
        检查型号和零部件是否在Failure表中,检查下顺序 1
        :param model: 产品型号
        :param part: 零部件
        :return:布尔类型
        """
        async with async_db_session() as db:
            failures = await failure_dao.get_by_model_and_part(db, model, part)
            if failures and len(failures) > 4:
                return True
            return False

    @staticmethod
    async def check_model_and_part_in_configuration(model: str, part: str) -> bool:
        """
        检查型号和零部件是否在Configuration表中,检查下顺序 1
        :param model: 产品型号
        :param part: 零部件
        :return:布尔类型
        """
        async with async_db_session() as db:
            configurations = await configuration_dao.get_by_model_and_part_check(db, model, part)
            if configurations:
                return True
            return False

    @staticmethod
    async def check_model_and_part_in_pc(model: str) -> bool:
        """
        检查型号是否在PC表中,检查下顺序 1
        :param model: 产品型号
        :return:布尔类型
        """
        async with async_db_session() as db:
            pcs = await pc_dao.get_by_model(db, model)
            if pcs:
                return True
            return False


data_check_utils: DataCheckUtils = DataCheckUtils()
