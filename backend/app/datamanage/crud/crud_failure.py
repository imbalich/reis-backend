#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""Datamanage failure CRUD helpers."""

from datetime import date
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
        return or_(
            model.final_fault_responsibility.is_(None),
            model.final_fault_responsibility == "",
            ~model.final_fault_responsibility.contains("用户"),
        )

    async def get_distinct_column_values(
        self, db: AsyncSession, column_name: str
    ) -> Sequence[Any]:
        if not hasattr(self.model, column_name):
            raise ValueError(
                f"Column {column_name} does not exist in model {self.model.__name__}"
            )

        column = getattr(self.model, column_name)
        stmt = select(distinct(column)).order_by(column)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_distinct_columns_values(
        self, db: AsyncSession, column_names: List[str]
    ) -> Sequence[Row[tuple[Any, ...]]]:
        for col in column_names:
            if not hasattr(self.model, col):
                raise ValueError(
                    f"Column {col} does not exist in model {self.model.__name__}"
                )

        columns = [getattr(self.model, col) for col in column_names]
        stmt = select(*columns).distinct().order_by(*columns)
        result = await db.execute(stmt)
        return result.all()

    async def get_distinct_column_values_by_product_model(
        self,
        db: AsyncSession,
        product_model: str,
        column_name: str,
        product_config_code: str | None = None,
    ) -> Sequence[Any]:
        if not hasattr(self.model, column_name):
            raise ValueError(
                f"Column {column_name} does not exist in model {self.model.__name__}"
            )

        column = getattr(self.model, column_name)
        where_list = [self.model.product_model == product_model, column.isnot(None)]
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        stmt = select(distinct(column)).where(*where_list).order_by(column)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_distinct_columns_values_by_product_model(
        self,
        db: AsyncSession,
        product_model: str,
        column_names: List[str],
        product_config_code: str | None = None,
    ) -> Sequence[Row[tuple[Any, ...]]]:
        for col in column_names:
            if not hasattr(self.model, col):
                raise ValueError(
                    f"Column {col} does not exist in model {self.model.__name__}"
                )

        columns = [getattr(self.model, col) for col in column_names]
        where_list = [self.model.product_model == product_model]
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        stmt = select(*columns).distinct().where(*where_list).order_by(*columns)
        result = await db.execute(stmt)
        return result.all()

    async def get_list(
        self,
        product_model: str = None,
        product_config_code: str | None = None,
        fault_location: str = None,
        product_lifetime_stage: str = None,
        product_number: str = None,
        fault_mode: str = None,
        time_range: list[str] = None,
        is_zero_distance: int = 1,
        is_company: int = 1,
        fault_material_code: str = None,
    ) -> Select:
        stmt = select(self.model).order_by(desc(self.model.product_model))
        where_list = []
        if product_model is not None:
            where_list.append(self.model.product_model == product_model)
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        if fault_location is not None:
            where_list.append(self.model.fault_location == fault_location)
        if product_lifetime_stage is not None:
            where_list.append(self.model.product_lifetime_stage == product_lifetime_stage)
        if product_number is not None:
            where_list.append(self.model.product_number == product_number)
        if fault_mode is not None:
            where_list.append(self.model.fault_mode == fault_mode)
        if time_range:
            where_list.append(self.model.discovery_date.between(time_range[0], time_range[1]))
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
        self,
        db: AsyncSession,
        model: str,
        product_config_code: str | None = None,
    ) -> Sequence[FailureModel]:
        stmt = select(self.model).order_by(self.model.discovery_date)
        where_list = [self.model.product_model == model]
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        where_list.extend(
            [
                self.model.is_zero_distance == 0,
                CRUDFailure._non_user_responsibility_condition(self.model),
                self.model.manufacturing_date.isnot(None),
            ]
        )
        stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_models_by_part(self, part: str) -> Select:
        stmt = select(distinct(self.model.product_model))
        where_list = [
            self.model.fault_material_code == part,
            self.model.is_zero_distance == 0,
            CRUDFailure._non_user_responsibility_condition(self.model),
        ]
        stmt = stmt.where(*where_list)
        return stmt

    async def get_by_model_and_part(
        self,
        db: AsyncSession,
        model: str,
        part: str,
        input_date: date = None,
        product_config_code: str | None = None,
    ) -> Sequence[FailureModel]:
        stmt = select(self.model).order_by(self.model.discovery_date)
        where_list = []
        if input_date:
            where_list.append(self.model.discovery_date <= input_date.strftime("%Y-%m-%d"))
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        where_list.extend(
            [
                self.model.product_model == model,
                self.model.fault_material_code == part,
                self.model.is_zero_distance == 0,
                CRUDFailure._non_user_responsibility_condition(self.model),
                self.model.manufacturing_date.isnot(None),
            ]
        )
        stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_model_and_part_usesense(
        self, db: AsyncSession, model: str, part: str
    ) -> Sequence[FailureModel]:
        stmt = select(self.model).order_by(self.model.discovery_date)
        where_list = [
            self.model.product_model == model,
            self.model.fault_material_code == part,
            CRUDFailure._non_user_responsibility_condition(self.model),
        ]
        stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_number_by_model(
        self,
        db: AsyncSession,
        model: str,
        part: str,
        stage: str,
        time_range: list[str],
    ) -> Sequence[str]:
        stmt = select(distinct(self.model.product_number))
        where_list = [
            self.model.product_model == model,
            self.model.fault_material_code == part,
            self.model.product_lifetime_stage == stage,
        ]
        if time_range:
            where_list.append(self.model.manufacturing_date.between(time_range[0], time_range[1]))
        stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_parts_with_names_by_model(
        self, db: AsyncSession, model: str
    ) -> Sequence[tuple[str, str]]:
        stmt = (
            select(
                distinct(self.model.fault_location),
                self.model.fault_material_code,
            )
            .where(
                self.model.product_model == model,
                self.model.fault_material_code.isnot(None),
                self.model.fault_location.isnot(None),
                self.model.is_zero_distance == 0,
                CRUDFailure._non_user_responsibility_condition(self.model),
            )
            .order_by(self.model.fault_location, self.model.fault_material_code)
        )
        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_parts_with_names_only_by_model(
        self, db: AsyncSession, model: str
    ) -> Sequence[tuple[str, str]]:
        stmt = (
            select(
                distinct(self.model.fault_location),
                self.model.fault_material_code,
            )
            .where(
                self.model.product_model == model,
                self.model.fault_material_code.isnot(None),
                self.model.fault_location.isnot(None),
                ~self.model.fault_location.like("%电机%"),
                ~self.model.fault_location.like("%电动机%"),
                ~self.model.fault_location.like("%变流器%"),
                ~self.model.fault_location.like("%变流柜%"),
            )
            .order_by(self.model.fault_location, self.model.fault_material_code)
        )
        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_by_product_number(
        self, db: AsyncSession, product_number: str
    ) -> Sequence[FailureModel]:
        stmt = (
            select(self.model)
            .where(
                self.model.product_number == product_number,
                self.model.is_zero_distance == 0,
                CRUDFailure._non_user_responsibility_condition(self.model),
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
        stmt = select(func.count(self.model.pk)).where(
            self.model.product_model == model,
            self.model.fault_material_code == part,
            self.model.product_number.in_(products),
            self.model.discovery_date >= start_date,
            self.model.discovery_date <= end_date,
            self.model.is_zero_distance == 0,
            CRUDFailure._non_user_responsibility_condition(self.model),
        )
        result = await db.execute(stmt)
        count = result.scalar()
        return count if count is not None else 0


failure_dao: CRUDFailure = CRUDFailure(FailureModel)
