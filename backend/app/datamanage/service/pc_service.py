#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：pc_service.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/5/20 17:19
"""
from typing import Sequence

from backend.app.datamanage.crud.crud_pc import pc_dao
from backend.database.db import async_db_session


class PCService:

    @staticmethod
    async def get_check_project_by_process_name(process_name:str=None)-> Sequence[str]:
        async with async_db_session() as db:
            results = await pc_dao.get_distinct_column_values(
                db, 'process_name', process_name, 'check_project'
            )
            return results

    @staticmethod
    async def get_check_bezier_by_check_project(check_project:str=None)-> Sequence[str]:
        async with async_db_session() as db:
            results = await pc_dao.get_distinct_column_values(
                db, 'check_project', check_project, 'check_bezier'
            )
            return results


pc_service: PCService=PCService()