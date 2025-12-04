#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：crud_failure.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/26 16:51
"""

from typing import Any, List, Sequence, TypeVar

from sqlalchemy import Row, Select, desc, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import FailureModel

T = TypeVar("T")


class CRUDFailure(CRUDPlus[T]):

    def __init__(self, model: type[T]):
        super().__init__(model=model)

    @staticmethod
    def _non_user_responsibility_condition(model):
        """
        生成非用户责任的条件
        包含：NULL值、空字符串、不包含"用户"的值

        Args:
            model: Failure 模型类

        Returns:
            SQLAlchemy 条件表达式
        """
        return or_(
            model.final_fault_responsibility.is_(None),  # NULL 值
            model.final_fault_responsibility == "",  # 空字符串
            ~model.final_fault_responsibility.contains("用户"),  # 不包含"用户"
        )

    async def get_distinct_column_values(
        self, db: AsyncSession, column_name: str
    ) -> Sequence[Any]:
        """
        获取指定列的所有唯一值
        :param db: 数据库会话
        :param column_name: 列名
        :return: 唯一值列表
        """
        # 确保列名存在于模型中
        if not hasattr(self.model, column_name):
            raise ValueError(
                f"Column {column_name} does not exist in model {self.model.__name__}"
            )

        # 构建查询
        column = getattr(self.model, column_name)
        stmt = select(distinct(column)).order_by(column)
        # 执行查询
        result = await db.execute(stmt)

        # 返回结果
        return result.scalars().all()

    async def get_distinct_column_values_by_product_model(
        self, db: AsyncSession, product_model: str, column_name: str
    ) -> Sequence[Any]:
        """
        获取指定列的所有唯一值，根据产品型号
        :param db: 数据库会话
        :param product_model: 产品型号
        :param column_name: '故障部位‘
        :return: 产品型号下故障部位的唯一列表
        """
        # 确保列名存在于模型中
        if not hasattr(self.model, column_name):
            raise ValueError(
                f"Column {column_name} does not exist in model {self.model.__name__}"
            )

        # 构建查询
        column = getattr(self.model, column_name)
        # 先查产品型号==column下的所有product_model，然后针对product_model去重
        stmt = (
            select(distinct(column))
            .where(
                self.model.product_model == product_model,
                column.isnot(None),  # 过滤掉 NULL 值
            )
            .order_by(column)
        )
        # 执行查询
        result = await db.execute(stmt)

        # 返回结果
        return result.scalars().all()

    async def get_distinct_columns_values_by_product_model(
        self, db: AsyncSession, product_model: str, column_names: List[str]
    ) -> Sequence[Row[tuple[Any, ...]]]:
        """
        获取指定两列的所有唯一值，根据产品型号
        :param db: 数据库会话
        :param product_model: 产品型号
        :param column_names: '故障部位‘
        :return: 产品型号下故障部位的唯一列表
        """
        for col in column_names:
            if not hasattr(self.model, col):
                raise ValueError(
                    f"Column {col} does not exist in model {self.model.__name__}"
                )
        columns = [getattr(self.model, col) for col in column_names]
        # 构建查询，按列排序
        stmt = (
            select(*columns)
            .distinct()
            .where(self.model.product_model == product_model)
            .order_by(*columns)
        )
        result = await db.execute(stmt)
        return result.all()

    async def get_list(
        self,
        product_model: str = None,
        fault_location: str = None,
        product_lifetime_stage: str = None,
        product_number: str = None,
        fault_mode: str = None,
        time_range: list[str] = None,
        is_zero_distance: int = 1,
        is_company: int = 1,
        fault_material_code: str = None,
    ) -> Select:
        """
        获取数据列表
        :param product_model:
        :param fault_location:
        :param product_lifetime_stage:
        :param product_number:
        :param fault_mode:
        :param time_range:
        :param is_zero_distance:
        :param is_company:
        :param fault_material_code:
        :return: 查询语句
        """
        stmt = select(self.model).order_by(desc(self.model.product_model))
        where_list = []
        if product_model is not None:
            where_list.append(self.model.product_model == product_model)
        if fault_location is not None:
            where_list.append(self.model.fault_location == fault_location)
        if product_lifetime_stage is not None:
            where_list.append(
                self.model.product_lifetime_stage == product_lifetime_stage
            )
        if product_number is not None:
            where_list.append(self.model.product_number == product_number)
        if fault_mode is not None:
            where_list.append(self.model.fault_mode == fault_mode)
        if time_range:
            where_list.append(
                self.model.discovery_date.between(time_range[0], time_range[1])
            )
        if is_zero_distance is not None:
            where_list.append(self.model.is_zero_distance == is_zero_distance)
        if is_company is not None:
            where_list.append(self.model.is_company == is_company)
        if fault_material_code is not None:
            where_list.append(self.model.fault_material_code == fault_material_code)
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_by_model(
        self, db: AsyncSession, model: str
    ) -> Sequence[FailureModel]:
        """
        根据产品型号获取故障列表
        :param db: 数据库会话
        :param model: 产品型号
        :return: 故障列表
        """
        stmt = select(self.model).order_by(self.model.discovery_date)
        where_list = []
        where_list.append(self.model.product_model == model)
        where_list.append(self.model.is_zero_distance == 0)
        where_list.append(CRUDFailure._non_user_responsibility_condition(self.model))
        where_list.append(self.model.manufacturing_date.isnot(None))  # 添加这个条件
        # where_list.append(self.model.is_company == 1)  # 添加这个条件2025-11-13
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_models_by_part(self, part: str) -> Select:
        """
        根据零部件在故障清单中获取产品型号，主要用于校验检验零部件是否在故障单中
        :param part: 零部件
        :return: 产品型号
        """
        stmt = select(distinct(self.model.product_model))
        where_list = []
        where_list.append(self.model.fault_material_code == part)
        where_list.append(self.model.is_zero_distance == 0)
        where_list.append(CRUDFailure._non_user_responsibility_condition(self.model))
        # where_list.append(self.model.is_company == 1)  # 添加这个条件2025-11-13
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_by_model_and_part(
        self, db: AsyncSession, model: str, part: str
    ) -> Sequence[FailureModel]:
        """
        查询单型号单零部件故障信息:做检测用，不用考虑是否新造
        :param db: 数据库会话
        :param model: 产品型号
        :param part: 零部件
        :return: 故障列表
        """
        stmt = select(self.model).order_by(self.model.discovery_date)
        where_list = []
        where_list.append(self.model.product_model == model)
        where_list.append(self.model.fault_material_code == part)
        where_list.append(self.model.is_zero_distance == 0)
        where_list.append(CRUDFailure._non_user_responsibility_condition(self.model))
        where_list.append(self.model.manufacturing_date.isnot(None))  # 添加这个条件
        # where_list.append(self.model.is_company == 1)  # 添加这个条件2025-11-13
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_model_and_part_usesense(
        self, db: AsyncSession, model: str, part: str
    ) -> Sequence[FailureModel]:
        """
        查询单型号单零部件故障信息:做检测用，不用考虑是否新造
        :param db: 数据库会话
        :param model: 产品型号
        :param part: 零部件
        :return: 故障列表
        """
        stmt = select(self.model).order_by(self.model.discovery_date)
        where_list = []
        where_list.append(self.model.product_model == model)
        where_list.append(self.model.fault_material_code == part)
        where_list.append(CRUDFailure._non_user_responsibility_condition(self.model))
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_number_by_model(
        self, db: AsyncSession, model: str, part: str, stage: str, time_range: list[str]
    ) -> Sequence[str]:
        """
        查询单型号零部件下的故障件编号
        :param db: 数据库会话
        :param model: 产品型号
        :param part: 零部件
        :param stage: 造修阶段
        :param time_range: 时间范围
        :return: 故障件编号列表
        """
        stmt = select(distinct(self.model.product_number))
        where_list = []
        where_list.append(self.model.product_model == model)
        where_list.append(self.model.fault_material_code == part)
        where_list.append(self.model.product_lifetime_stage == stage)
        if time_range:
            where_list.append(
                self.model.manufacturing_date.between(time_range[0], time_range[1])
            )
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_parts_with_names_by_model(
        self, db: AsyncSession, model: str
    ) -> Sequence[tuple[str, str]]:
        """
        根据型号获取零部件物料编码和名称的二元组列表
        :param db: 数据库会话
        :param model: 产品型号
        :return: (零部件名称, 零部件物料编码) 的二元组列表
        """
        stmt = (
            select(
                distinct(self.model.fault_location),  # 零部件名称
                self.model.fault_material_code,  # 零部件物料编码
            )
            .where(
                self.model.product_model == model,
                self.model.fault_material_code.isnot(None),  # 物料编码不为空
                self.model.fault_location.isnot(None),  # 部位名称不为空
                self.model.is_zero_distance == 0,  # 非零公里故障
                CRUDFailure._non_user_responsibility_condition(
                    self.model
                ),  # 非用户责任（包含NULL和空字符串）
                # self.model.is_company == 1,  # 添加这个条件2025-11-13
            )
            .order_by(self.model.fault_location, self.model.fault_material_code)
        )

        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_parts_with_names_only_by_model(
        self, db: AsyncSession, model: str
    ) -> Sequence[tuple[str, str]]:
        """
        根据型号获取零部件物料编码和名称的二元组列表
        :param db: 数据库会话
        :param model: 产品型号
        :return: (零部件名称, 零部件物料编码) 的二元组列表
        """
        stmt = (
            select(
                distinct(self.model.fault_location),  # 零部件名称
                self.model.fault_material_code,  # 零部件物料编码
            )
            .where(
                self.model.product_model == model,
                self.model.fault_material_code.isnot(None),  # 物料编码不为空
                self.model.fault_location.isnot(None),  # 部位名称不为空
                ~self.model.fault_location.like("%电机%"),  # 排除包含"电机"字眼的数据
                ~self.model.fault_location.like("%电动机%"),
                ~self.model.fault_location.like(
                    "%变流器%"
                ),  # 排除包含"变流器"字眼的数据
                ~self.model.fault_location.like("%变流柜%"),
            )
            .order_by(self.model.fault_location, self.model.fault_material_code)
        )

        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_by_product_number(
        self, db: AsyncSession, product_number: str
    ) -> Sequence[FailureModel]:
        """
        根据产品编号获取故障数据
        :param db: 数据库会话
        :param product_number: 产品编号
        :return: 故障数据列表
        """
        stmt = (
            select(self.model)
            .where(
                self.model.product_number == product_number,
                self.model.is_zero_distance == 0,
                CRUDFailure._non_user_responsibility_condition(self.model),
                # self.model.is_company == 1,  # 添加这个条件2025-11-13
            )
            .order_by(self.model.discovery_date)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_job_loss_by_model_and_part(
        self, db: AsyncSession, model: str, part: str
    ) -> Sequence[FailureModel]:
        stmt = (
            select(self.model)
            .where(
                self.model.product_model == model,
                self.model.fault_material_code == part,
                self.model.is_zero_distance == 0,
                self.model.loss_accounting.isnot(None),
                self.model.loss_accounting != "/",
                self.model.job_duration.isnot(None),
            )
            .order_by(self.model.discovery_date)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_failure_count_by_model_and_part_in_products(
        self,
        db: AsyncSession,
        model: str,
        part: str,
        start_date: str,
        end_date: str,
        products: list,
    ):
        """
        获取型号+故障件在指定时间范围内的故障次数
        :param db: 数据库会话
        :param model: 产品型号
        :param part: 故障件
        :param start_date: 开始日期（字符串格式 "YYYY-MM-DD"）
        :param end_date: 结束日期（字符串格式 "YYYY-MM-DD"）
        :param products: 需要被管理的产品编号列表
        :return: 故障次数（整数）
        """
        stmt = select(func.count(self.model.pk)).where(
            self.model.product_model == model,
            self.model.fault_material_code == part,
            self.model.product_number.in_(products),
            # 使用字符串比较，因为discovery_date是String类型，格式为"YYYY-MM-DD"
            # "YYYY-MM-DD"格式的字符串按字典序比较也能得到正确结果
            self.model.discovery_date >= start_date,
            self.model.discovery_date <= end_date,
            self.model.is_zero_distance == 0,
            CRUDFailure._non_user_responsibility_condition(self.model),
        )
        result = await db.execute(stmt)
        count = result.scalar()
        return count if count is not None else 0


failure_dao: CRUDFailure = CRUDFailure(FailureModel)
