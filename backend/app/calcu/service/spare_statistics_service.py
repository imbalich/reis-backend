#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : spare_statistics_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : 备件统计服务
"""

from datetime import date
from typing import List, Tuple
from sqlalchemy import func, select, distinct, and_, or_

from backend.app.datamanage.crud.crud_failure import failure_dao, CRUDFailure
from backend.app.datamanage.model import FailureModel
from backend.database.db import async_db_session
from backend.common.log import log


class SpareStatisticsService:
    """备件统计服务类"""

    @staticmethod
    async def filter_model_part_combinations(
        input_date: date, min_failure_count: int = 10
    ) -> List[Tuple[str, str, int]]:
        """
        筛选符合条件的型号+零部件组合
        条件：input_date之前故障个数 >= min_failure_count

        :param input_date: 拟合输入日期
        :param min_failure_count: 最小故障数量阈值，默认10
        :return: [(model, part, failure_count), ...] 列表
        """
        async with async_db_session() as db:
            # 构建查询：统计每个型号+零部件组合在input_date之前的故障数量
            stmt = (
                select(
                    FailureModel.product_model,
                    FailureModel.fault_material_code,
                    func.count(FailureModel.pk).label("failure_count"),
                )
                .where(
                    and_(
                        FailureModel.discovery_date <= input_date.strftime("%Y-%m-%d"),
                        FailureModel.is_zero_distance == 0,
                        FailureModel.fault_material_code.isnot(None),
                        FailureModel.manufacturing_date.isnot(None),
                        CRUDFailure._non_user_responsibility_condition(FailureModel),
                    )
                )
                .group_by(FailureModel.product_model, FailureModel.fault_material_code)
                .having(func.count(FailureModel.pk) >= min_failure_count)
                .order_by(FailureModel.product_model, FailureModel.fault_material_code)
            )

            result = await db.execute(stmt)
            rows = result.all()

            # 转换为元组列表
            combinations = [
                (row.product_model, row.fault_material_code, row.failure_count)
                for row in rows
            ]

            log.info(
                f"筛选完成: input_date={input_date}, "
                f"min_failure_count={min_failure_count}, "
                f"符合条件的组合数={len(combinations)}"
            )

            return combinations

    @staticmethod
    async def count_failures_by_model_part(
        model: str,
        part: str,
        start_date: date,
        end_date: date,
    ) -> int:
        """
        统计指定型号+零部件在时间范围内的实际故障数量

        :param model: 产品型号
        :param part: 零部件物料编码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 故障数量
        """
        async with async_db_session() as db:
            stmt = select(func.count(FailureModel.pk)).where(
                and_(
                    FailureModel.product_model == model,
                    FailureModel.fault_material_code == part,
                    FailureModel.discovery_date >= start_date.strftime("%Y-%m-%d"),
                    FailureModel.discovery_date <= end_date.strftime("%Y-%m-%d"),
                    FailureModel.is_zero_distance == 0,
                    CRUDFailure._non_user_responsibility_condition(FailureModel),
                )
            )

            result = await db.execute(stmt)
            count = result.scalar()
            return count if count is not None else 0

    @staticmethod
    async def get_part_name_by_model_part(
        model: str,
        part: str,
        start_date: date,
        end_date: date,
    ) -> str | None:
        """
        获取指定型号+零部件在时间范围内的零部件名称
        使用 MIN(fault_part_name) 作为零部件名称

        :param model: 产品型号
        :param part: 零部件物料编码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 零部件名称，如果不存在则返回 None
        """
        async with async_db_session() as db:
            stmt = select(func.min(FailureModel.fault_location)).where(
                and_(
                    FailureModel.product_model == model,
                    FailureModel.fault_material_code == part,
                    FailureModel.discovery_date >= start_date.strftime("%Y-%m-%d"),
                    FailureModel.discovery_date <= end_date.strftime("%Y-%m-%d"),
                    FailureModel.is_zero_distance == 0,
                    FailureModel.fault_location.isnot(None),
                    CRUDFailure._non_user_responsibility_condition(FailureModel),
                )
            )

            result = await db.execute(stmt)
            part_name = result.scalar()
            return part_name if part_name else None


spare_statistics_service: SpareStatisticsService = SpareStatisticsService()
