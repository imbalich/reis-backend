#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : fastapi-base-backend
@File    : data_check_utils.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/2/25 下午3:06
'''
from datetime import date

from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.fit.utils.time_utils import dateutils
from backend.database.db import async_db_session


class DataCheckUtils:

    @staticmethod
    async def check_model_in_product(model: str) -> bool:
        """
        检查型号是否在Product表中,检查下顺序 1
        :param model: 产品型号
        :return:布尔类型
        """
        async with async_db_session() as db:
            products = await product_dao.get_models_by_product(db)
            if products and model in products:
                return True
            return False

    @staticmethod
    async def check_model_in_failure(model: str) -> bool:
        """
        检查型号是否在Failure表中,故障数量大于4个才能参与运算
        :param model: 产品型号
        :return:布尔类型
        """
        async with async_db_session() as db:
            failures = await failure_dao.get_by_model(db, model)
            if failures and len(failures) > 4:
                return True
            return False

    @staticmethod
    async def check_model_and_part_in_failure(model: str, part: str) -> bool:
        """
        检查型号是否在Failure表中,故障数量大于4个才能参与运算
        :param model: 产品型号
        :param part: 零件
        :return:布尔类型
        """
        async with async_db_session() as db:
            failures = await failure_dao.get_by_model_and_part(db, model, part)
            if failures and len(failures) > 4:
                return True
            return False

    @staticmethod
    async def check_model_in_despatch(model: str) -> bool:
        """
        检查型号是否在Despatch表中,累计运行时间小于10w就不参与计算
        :param model: 产品型号
        :return:布尔类型
        """
        async with async_db_session() as db:
            despatchs = await despatch_dao.get_despatchs_by_model(db, model)
            product = await product_dao.get_by_model(db, model)
            if despatchs:
                # 当前日期
                now = date.today()
                total_hours = 0
                for despatch in despatchs:
                    dispatch_date = despatch.life_cycle_time
                    if isinstance(dispatch_date, str):
                        dispatch_date = dateutils.validate_and_parse_date(dispatch_date)
                    # 计算日期差
                    date_diff = (now - dispatch_date).days
                    hours = dateutils.run_time(date_diff, product.year_days, product.avg_worktime)
                    total_hours += hours

                # 检查总运行时间是否达到或超过10万小时
                return total_hours >= 100000
            return False

    @staticmethod
    async def check_model_and_part_in_ebom(model: str, part: str) -> bool:
        """
        检查型号&零部件是否在零部件信息表中
        :param model: 产品型号
        :param part: 零部件物料编码
        :return:布尔类型
        """
        async with async_db_session() as db:
            bom_data = await ebom_dao.get_by_model_and_part(db, model, part)
            if bom_data:
                return True
            return False


datacheckutils: DataCheckUtils = DataCheckUtils()
