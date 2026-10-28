#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : fastapi-base-backend
@File    : crud_product.py
@Author  : imbalich
@Date    : 2025/1/14 14:24
@Desc    : 产品数据访问: 铁路/风电分流代理(评审PR#3意见#2)
           带型号的方法按型号判定产业后转发; 跨产业列表方法返回合并结果;
           分页列表(get_list)支持可选产业参数, 不带时默认铁路
           (全产业合并分页随第5阶段前端产业标识一起实现)
"""
from typing import Any, List, Sequence

from sqlalchemy import Row, Select, desc, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Product
from backend.app.datamanage.model.dm_jl_product import ProductJL
from backend.app.datamanage.model.dm_jl_product import ProductJL
from backend.common.industry import Industry, resolve_industry
from backend.common.product_config import apply_product_config_code_filter


class CRUDProduct(CRUDPlus[Product]):
    async def get_list(
        self, model: str = None, product_config_code: str | None = None
    ) -> Select:
        """
        获取数据列表
        """
        stmt = select(self.model).order_by(desc(self.model.model))
        where_list = []
        if model:
            where_list.append(self.model.model == model)
        apply_product_config_code_filter(
            where_list, self.model.product_config_code, product_config_code
        )
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_distinct_column_values(self, db: AsyncSession, column_name: str) -> Sequence[Any]:
        """
        获取指定列的所有唯一值
        """
        if not hasattr(self.model, column_name):
            raise ValueError(f'Column {column_name} does not exist in model {self.model.__name__}')

        column = getattr(self.model, column_name)
        stmt = select(distinct(column)).order_by(column)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_distinct_columns_values(
        self, db: AsyncSession, column_names: List[str]
    ) -> Sequence[Row[tuple[Any, ...]]]:
        for col in column_names:
            if not hasattr(self.model, col):
                raise ValueError(f'Column {col} does not exist in model {self.model.__name__}')

        columns = [getattr(self.model, col) for col in column_names]
        stmt = select(*columns).distinct().order_by(*columns)
        result = await db.execute(stmt)
        return result.all()

    async def get_models_by_product(self, db: AsyncSession) -> Sequence[str]:
        stmt = select(distinct(self.model.model)).order_by(self.model.model)
        where_list = [
            self.model.avg_worktime.is_not(None),
            self.model.avg_speed.is_not(None),
            self.model.year_days.is_not(None),
            self.model.avg_worktime != 0,
            self.model.avg_speed != 0,
            self.model.year_days != 0,
        ]
        stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_model(
        self, db: AsyncSession, model: str, product_config_code: str | None = None
    ) -> Product:
        stmt = select(self.model).order_by(desc(self.model.year_days))
        where_list = []
        if model:
            where_list.append(self.model.model == model)
        apply_product_config_code_filter(
            where_list, self.model.product_config_code, product_config_code
        )
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().first()


class ProductDaoProxy:
    """产品数据访问分流代理(评审PR#3意见#2)

    - 带型号的方法: 先按型号判定产业(Industry), 再转发到对应DAO
    - 跨产业枚举方法: 铁路与风电结果合并去重
    - 分页列表(get_list): 带型号时自动分流; 不带型号时默认铁路,
      全产业合并分页随第5阶段(前端产业标识)实现
    """

    def __init__(self, railway: CRUDProduct, wind: CRUDProduct, wind_model: type):
        self._railway = railway
        self._wind = wind
        self._wind_model = wind_model

    async def _dao_for(self, db: AsyncSession, model: str | None) -> CRUDProduct:
        if not model:
            return self._railway
        industry = await resolve_industry(db, model)
        return self._wind if industry == Industry.WIND else self._railway

    async def get_list(
        self, db: AsyncSession, model: str = None, product_config_code: str | None = None
    ) -> Select:
        dao = await self._dao_for(db, model)
        return await dao.get_list(model, product_config_code=product_config_code)

    async def get_distinct_column_values(
        self, db: AsyncSession, column_name: str
    ) -> Sequence[Any]:
        railway = await self._railway.get_distinct_column_values(db, column_name)
        # 风电侧: 仅物理列可参与查询(计算属性/property 不入SQL)
        if column_name in self._wind_model.__table__.columns:
            col = getattr(self._wind_model, column_name)
            stmt = select(distinct(col)).order_by(col)
            result = await db.execute(stmt)
            wind = [v for v in result.scalars().all() if v is not None]
            return sorted(set(railway) | set(wind), key=str)
        return railway

    async def get_distinct_columns_values(
        self, db: AsyncSession, column_names: List[str]
    ) -> Sequence[Row[tuple[Any, ...]]]:
        railway = await self._railway.get_distinct_columns_values(db, column_names)
        usable = [c for c in column_names if c in self._wind_model.__table__.columns]
        wind: list[tuple] = []
        if usable:
            cols = [getattr(self._wind_model, c) for c in usable]
            stmt = select(*cols).distinct().order_by(*cols)
            result = await db.execute(stmt)
            wind = [tuple(r) for r in result.all()]
        merged = sorted(set(map(tuple, railway)) | set(wind), key=lambda t: tuple(str(x) for x in t))
        return merged

    async def get_models_by_product(self, db: AsyncSession) -> Sequence[str]:
        """产业判定基础数据: 铁路与风电可用型号并集"""
        railway = await self._railway.get_models_by_product(db)
        m = self._wind_model
        stmt = select(distinct(m.model)).where(
            m.avg_worktime.is_not(None),
            m.year_days.is_not(None),
            m.avg_worktime != 0,
            m.year_days != 0,
        )
        result = await db.execute(stmt)
        wind = result.scalars().all()
        return sorted(set(railway) | set(wind))

    async def get_by_model(
        self, db: AsyncSession, model: str, product_config_code: str | None = None
    ):
        dao = await self._dao_for(db, model)
        return await dao.get_by_model(db, model, product_config_code=product_config_code)


product_dao: ProductDaoProxy = ProductDaoProxy(
    railway=CRUDProduct(Product),      # 铁路: dm_product
    wind=CRUDProduct(ProductJL),       # 风电: dm_jl_product
    wind_model=ProductJL,
)
