#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional

from sqlalchemy import Select

from backend.app.datamanage.crud.crud_allotment import allotment_dao


class AllotmentService:
    """产品配属服务类"""

    @staticmethod
    async def get_select(
        vehicle_type: Optional[str] = None,
        vehicle_number: Optional[str] = None,
        product_model: Optional[str] = None,
        ps_code: Optional[str] = None,
        product_number: Optional[str] = None,
        allotment_one: Optional[str] = None,
        allotment_two: Optional[str] = None,
    ) -> Select:
        """
        获取产品配属查询语句

        :param vehicle_type: 车型
        :param vehicle_number: 车号
        :param product_model: 产品型号
        :param ps_code: 派生码
        :param product_number: 产品编号
        :param allotment_one: 一级配属
        :param allotment_two: 二级配属
        :return: 查询语句
        """
        return await allotment_dao.get_select(
            vehicle_type=vehicle_type,
            vehicle_number=vehicle_number,
            product_model=product_model,
            ps_code=ps_code,
            product_number=product_number,
            allotment_one=allotment_one,
            allotment_two=allotment_two,
        )


allotment_service = AllotmentService()
