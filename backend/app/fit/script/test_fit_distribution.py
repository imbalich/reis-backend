#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
拟合模块测试脚本
目的：将fit_part表中的每组型号+零部件的最优曲线拿出，计算故障率（PDF）
"""
import argparse
import asyncio
from datetime import date, timedelta
from pathlib import Path
import sys

import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.db import async_db_session
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.fit.schema.fit_param import FitMethodType, FitCheckType
from backend.app.calcu.service.distribute_service import DistributeService
from backend.app.calcu.schema.distribute_param import DistributeType, DistributionParams
from backend.app.fit.utils.convert_model import convert_to_pydantic_model
from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.fit.utils.data_check_utils import DataCheckUtils
from backend.app.fit.utils.time_utils import dateutils
from sqlalchemy import select, func
from typing import List, Dict, Any, Optional


def parse_args():
    parser = argparse.ArgumentParser(description="拟合模块测试脚本")
    parser.add_argument(
        "--input-date",
        dest="input_date",
        help="输入时间（用于计算故障率），格式YYYY-MM-DD，默认使用当前时间",
    )
    parser.add_argument(
        "--output", dest="output", help="输出Excel路径，默认 test_fit_distribution.xlsx"
    )
    return parser.parse_args()


async def get_all_model_part_combinations() -> List[tuple[str, str]]:
    """获取fit_part表中所有唯一的型号+零部件组合"""
    async with async_db_session() as db:
        stmt = select(fit_part_dao.model.model, fit_part_dao.model.part).distinct()
        result = await db.execute(stmt)
        rows = result.all()
        return [(row[0], row[1]) for row in rows if row[0] and row[1]]


async def get_best_fit_part(model: str, part: str) -> Optional[Any]:
    """获取最优拟合结果（BIC最小）"""
    async with async_db_session() as db:
        results = await fit_part_dao.get_by_model_and_part(
            db,
            model=model,
            part=part,
            method=FitMethodType.MLE,
            check=FitCheckType.BIC,
            source=False,
        )
        if results and len(results) > 0:
            return results[0]  # 已经按BIC排序，第一个是最优的
        return None


async def convert_fit_part_to_distribution(fit_part: Any) -> Optional[Any]:
    """将fit_part模型转换为分布对象"""
    try:
        # 转换为DistributionParams
        distribution_params = convert_to_pydantic_model(fit_part, DistributionParams)

        # 使用DistributeService的方法创建分布对象
        distribution = await DistributeService.get_distribution_by_params(
            distribution_params
        )
        return distribution
    except Exception as e:
        model = fit_part.model if hasattr(fit_part, "model") else "Unknown"
        part = fit_part.part if hasattr(fit_part, "part") else "Unknown"
        print(f"转换分布对象失败: {model}+{part}, 错误: {e}")
        return None


async def get_earliest_dispatch_date(model: str) -> Optional[date]:
    """获取型号的最早发运日期"""
    async with async_db_session() as db:
        despatchs = await despatch_dao.get_despatchs_by_model(db, model)
        if not despatchs:
            return None

        earliest_date = None
        for despatch in despatchs:
            dispatch_date = despatch.life_cycle_time
            if dispatch_date:
                if isinstance(dispatch_date, str):
                    dispatch_date = dateutils.validate_and_parse_date(dispatch_date)
                if earliest_date is None or dispatch_date < earliest_date:
                    earliest_date = dispatch_date

        return earliest_date


async def calculate_max_cumulative_run_time(
    model: str, earliest_dispatch_date: date, current_date: date
) -> float:
    """计算累计运行时间（累计运行时间最长的产品的运行时间）"""
    async with async_db_session() as db:
        # 获取产品信息
        product = await product_dao.get_by_model(db, model)
        if not product:
            return 0.0

        # 获取所有发运数据
        despatchs = await despatch_dao.get_despatchs_by_model(db, model)
        if not despatchs:
            return 0.0

        max_hours = 0.0
        for despatch in despatchs:
            dispatch_date = despatch.life_cycle_time
            if dispatch_date:
                if isinstance(dispatch_date, str):
                    dispatch_date = dateutils.validate_and_parse_date(dispatch_date)
                # 计算日期差
                date_diff = (current_date - dispatch_date).days
                hours = dateutils.run_time(
                    date_diff, product.year_days, product.avg_worktime
                )
                if hours > max_hours:
                    max_hours = hours

        return max_hours


async def calculate_failure_rate_at_time(distribution: Any, run_time: float) -> float:
    """计算指定运行时间的故障率（PDF）"""
    try:
        if distribution is None:
            return 0.0
        pdf_value = distribution.PDF(xvals=[run_time], show_plot=False)
        if isinstance(pdf_value, (list, tuple)):
            return float(pdf_value[0]) if len(pdf_value) > 0 else 0.0
        return float(pdf_value)
    except Exception as e:
        print(f"计算PDF失败，运行时间={run_time}, 错误: {e}")
        return 0.0


async def main():
    args = parse_args()

    # 解析输入日期
    input_date = date.today()
    if args.input_date:
        input_date = dateutils.validate_and_parse_date(args.input_date)

    current_date = date.today()

    print(f"开始处理拟合模块测试...")
    print(f"当前日期: {current_date}")
    print(f"输入日期: {input_date}")

    # 获取所有型号+零部件组合
    model_part_combinations = await get_all_model_part_combinations()
    print(f"共找到 {len(model_part_combinations)} 个型号+零部件组合")

    results = []

    for idx, (model, part) in enumerate(model_part_combinations, 1):
        if idx % 100 == 0:
            print(f"处理进度: {idx}/{len(model_part_combinations)}")

        try:
            # 1. 获取最优拟合结果
            fit_part = await get_best_fit_part(model, part)
            if not fit_part:
                results.append(
                    {
                        "model": model,
                        "part": part,
                        "distribution": None,
                        "earliest_dispatch_date": None,
                        "max_cumulative_run_time": None,
                        "current_failure_rate": None,
                        "input_date_failure_rate": None,
                        "error": "未找到拟合结果",
                    }
                )
                continue

            # 2. 转换为分布对象
            distribution = await convert_fit_part_to_distribution(fit_part)
            if not distribution:
                results.append(
                    {
                        "model": model,
                        "part": part,
                        "distribution": fit_part.distribution,
                        "earliest_dispatch_date": None,
                        "max_cumulative_run_time": None,
                        "current_failure_rate": None,
                        "input_date_failure_rate": None,
                        "error": "分布对象转换失败",
                    }
                )
                continue

            # 3. 获取最早发运日期
            earliest_dispatch_date = await get_earliest_dispatch_date(model)
            if not earliest_dispatch_date:
                results.append(
                    {
                        "model": model,
                        "part": part,
                        "distribution": fit_part.distribution,
                        "earliest_dispatch_date": None,
                        "max_cumulative_run_time": None,
                        "current_failure_rate": None,
                        "input_date_failure_rate": None,
                        "error": "未找到发运日期",
                    }
                )
                continue

            # 4. 计算累计运行时间（当前时间）
            max_run_time_current = await calculate_max_cumulative_run_time(
                model, earliest_dispatch_date, current_date
            )

            # 5. 计算累计运行时间（输入时间）
            max_run_time_input = await calculate_max_cumulative_run_time(
                model, earliest_dispatch_date, input_date
            )

            # 6. 计算当前时间的故障率（PDF）
            current_failure_rate = await calculate_failure_rate_at_time(
                distribution, max_run_time_current
            )

            # 7. 计算输入时间的故障率（PDF）
            input_date_failure_rate = await calculate_failure_rate_at_time(
                distribution, max_run_time_input
            )

            results.append(
                {
                    "model": model,
                    "part": part,
                    "distribution": fit_part.distribution,
                    "earliest_dispatch_date": earliest_dispatch_date,
                    "max_cumulative_run_time": round(max_run_time_current, 2),
                    "current_failure_rate": round(current_failure_rate, 8),
                    "input_date": input_date,
                    "max_cumulative_run_time_at_input": round(max_run_time_input, 2),
                    "input_date_failure_rate": round(input_date_failure_rate, 8),
                    "error": None,
                }
            )

        except Exception as e:
            results.append(
                {
                    "model": model,
                    "part": part,
                    "distribution": None,
                    "earliest_dispatch_date": None,
                    "max_cumulative_run_time": None,
                    "current_failure_rate": None,
                    "input_date_failure_rate": None,
                    "error": str(e),
                }
            )

    # 输出到Excel
    output_path = Path(args.output or "test_fit_distribution.xlsx")
    df = pd.DataFrame(results)
    df.to_excel(output_path, index=False, engine="openpyxl")

    print(f"\n处理完成！")
    print(f"成功处理: {len([r for r in results if r.get('error') is None])} 条")
    print(f"失败: {len([r for r in results if r.get('error') is not None])} 条")
    print(f"结果已保存到: {output_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
