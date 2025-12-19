#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
拟合模块测试脚本（Weibull专用版）
目的：从fit_part表中获取每组型号+零部件的最优Weibull分布（Weibull_3P和Weibull_2P中选择最优），
      计算故障率（PDF）并转换为FPMH单位
"""
import argparse
import asyncio
from datetime import date
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
from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.app.fit.utils.time_utils import dateutils
from sqlalchemy import select, and_, asc, desc
from typing import List, Dict, Any, Optional


def parse_args():
    parser = argparse.ArgumentParser(description="拟合模块测试脚本（Weibull专用版）")
    parser.add_argument(
        "--input-date",
        dest="input_date",
        help="输入时间（用于计算故障率），格式YYYY-MM-DD，默认使用当前时间",
    )
    parser.add_argument(
        "--output",
        dest="output",
        help="输出Excel路径，默认 test_fit_distribution_weibull.xlsx",
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
    """
    获取最优拟合结果
    1. 如果有Weibull_3P和Weibull_2P，选择其中BIC最小的
    2. 如果只有Exponential_1P，选择它
    """
    async with async_db_session() as db:
        # 定义排序列（BIC）
        order_column = fit_part_dao.model.bic

        # 基本查询条件（不限制分布类型）
        base_conditions = [
            fit_part_dao.model.model == model,
            fit_part_dao.model.part == part,
            fit_part_dao.model.method == FitMethodType.MLE,
            fit_part_dao.model.source == False,
        ]

        # 子查询：获取最新的group_id
        latest_group_subquery = (
            select(fit_part_dao.model.group_id)
            .where(and_(*base_conditions))
            .order_by(desc(fit_part_dao.model.created_time))
            .limit(1)
            .scalar_subquery()
        )

        # 主查询：获取最新group的所有记录
        stmt = (
            select(fit_part_dao.model)
            .where(
                and_(
                    *base_conditions,
                    fit_part_dao.model.group_id == latest_group_subquery,
                )
            )
            .order_by(asc(order_column))
        )

        result = await db.execute(stmt)
        all_results = result.scalars().all()

        if not all_results or len(all_results) == 0:
            return None

        # 筛选Weibull分布
        weibull_results = [
            r for r in all_results if r.distribution in ["Weibull_3P", "Weibull_2P"]
        ]

        # 如果有Weibull分布，返回最优的
        if weibull_results:
            # 已经按BIC排序，第一个是最优的
            return weibull_results[0]

        # 如果没有Weibull分布，检查是否有Exponential_1P
        exponential_results = [
            r for r in all_results if r.distribution == "Exponential_1P"
        ]

        # 如果有Exponential_1P，返回它
        if exponential_results:
            return exponential_results[0]

        # 如果既没有Weibull也没有Exponential_1P，返回None
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


async def get_part_name(model: str, part: str) -> Optional[str]:
    """获取零部件名称"""
    async with async_db_session() as db:
        ebom_data = await ebom_dao.get_by_model_and_part(db, model, part)
        if ebom_data and len(ebom_data) > 0:
            # 获取第一个记录的y8_matname字段
            part_name = getattr(ebom_data[0], "object_name1", None)
            return part_name
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
) -> tuple[float, float]:
    """
    计算累计运行时间（累计运行时间最长的产品的运行时间）
    返回: (运行时间（小时）, 运行时间（年）)
    """
    async with async_db_session() as db:
        # 获取产品信息
        product = await product_dao.get_by_model(db, model)
        if not product:
            return (0.0, 0.0)

        # 获取所有发运数据
        despatchs = await despatch_dao.get_despatchs_by_model(db, model)
        if not despatchs:
            return (0.0, 0.0)

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

        # 计算年数：运行时间（小时） / (年运行天数 * 日均工作小时)
        if product.year_days and product.avg_worktime:
            hours_per_year = product.year_days * product.avg_worktime
            if hours_per_year > 0:
                years = max_hours / hours_per_year
            else:
                years = 0.0
        else:
            years = 0.0

        return (max_hours, years)


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


def convert_to_fpmh(failure_rate: float) -> float:
    """将故障率转换为FPMH单位（乘以10^6）"""
    return failure_rate * 1000000.0


async def main():
    args = parse_args()

    # 解析输入日期
    input_date = date.today()
    if args.input_date:
        input_date = dateutils.validate_and_parse_date(args.input_date)

    current_date = date.today()

    print(f"开始处理拟合模块测试（Weibull专用版）...")
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
            # 1. 获取零部件名称
            part_name = await get_part_name(model, part)

            # 2. 获取最优拟合结果（优先Weibull，否则Exponential_1P）
            fit_part = await get_best_fit_part(model, part)
            if not fit_part:
                results.append(
                    {
                        "型号": model,
                        "物料编码": part,
                        "零部件": part_name,
                        "分布名称": None,
                        "alpha": None,
                        "beta": None,
                        "gamma": None,
                        "lambda_": None,
                        "产品最早发运日期": None,
                        "最早发运产品累计运行时间": None,
                        "最早发运产品累计运行时间（年）": None,
                        "故障率FPMH": None,
                        "预测计算截止日期": None,
                        "预测最早发运产品累计运行时间": None,
                        "预测最早发运产品累计运行时间（年）": None,
                        "预测故障率FPMH": None,
                        "error": "未找到拟合结果（Weibull或Exponential_1P）",
                    }
                )
                continue

            # 3. 转换为分布对象
            distribution = await convert_fit_part_to_distribution(fit_part)
            if not distribution:
                results.append(
                    {
                        "型号": model,
                        "物料编码": part,
                        "零部件": part_name,
                        "分布名称": fit_part.distribution,
                        "alpha": fit_part.alpha,
                        "beta": fit_part.beta,
                        "gamma": fit_part.gamma,
                        "lambda_": fit_part.lambda_,
                        "产品最早发运日期": None,
                        "最早发运产品累计运行时间": None,
                        "最早发运产品累计运行时间（年）": None,
                        "故障率FPMH": None,
                        "预测计算截止日期": None,
                        "预测最早发运产品累计运行时间": None,
                        "预测最早发运产品累计运行时间（年）": None,
                        "预测故障率FPMH": None,
                        "error": "分布对象转换失败",
                    }
                )
                continue

            # 4. 获取最早发运日期
            earliest_dispatch_date = await get_earliest_dispatch_date(model)
            if not earliest_dispatch_date:
                results.append(
                    {
                        "型号": model,
                        "物料编码": part,
                        "零部件": part_name,
                        "分布名称": fit_part.distribution,
                        "alpha": fit_part.alpha,
                        "beta": fit_part.beta,
                        "gamma": fit_part.gamma,
                        "lambda_": fit_part.lambda_,
                        "产品最早发运日期": None,
                        "最早发运产品累计运行时间": None,
                        "最早发运产品累计运行时间（年）": None,
                        "故障率FPMH": None,
                        "预测计算截止日期": None,
                        "预测最早发运产品累计运行时间": None,
                        "预测最早发运产品累计运行时间（年）": None,
                        "预测故障率FPMH": None,
                        "error": "未找到发运日期",
                    }
                )
                continue

            # 5. 计算累计运行时间（当前时间）
            max_run_time_current_hours, max_run_time_current_years = (
                await calculate_max_cumulative_run_time(
                    model, earliest_dispatch_date, current_date
                )
            )

            # 6. 计算累计运行时间（输入时间）
            max_run_time_input_hours, max_run_time_input_years = (
                await calculate_max_cumulative_run_time(
                    model, earliest_dispatch_date, input_date
                )
            )

            # 7. 计算当前时间的故障率（PDF）
            current_failure_rate = await calculate_failure_rate_at_time(
                distribution, max_run_time_current_hours
            )

            # 8. 计算输入时间的故障率（PDF）
            input_date_failure_rate = await calculate_failure_rate_at_time(
                distribution, max_run_time_input_hours
            )

            # 9. 转换为FPMH单位
            current_failure_rate_fpmh = convert_to_fpmh(current_failure_rate)
            input_date_failure_rate_fpmh = convert_to_fpmh(input_date_failure_rate)

            results.append(
                {
                    "型号": model,
                    "物料编码": part,
                    "零部件": part_name,
                    "分布名称": fit_part.distribution,
                    "alpha": fit_part.alpha,
                    "beta": fit_part.beta,
                    "gamma": fit_part.gamma,
                    "lambda_": fit_part.lambda_,
                    "产品最早发运日期": earliest_dispatch_date,
                    "最早发运产品累计运行时间": round(max_run_time_current_hours, 2),
                    "最早发运产品累计运行时间（年）": round(
                        max_run_time_current_years, 4
                    ),
                    "故障率FPMH": round(current_failure_rate_fpmh, 4),
                    "预测计算截止日期": input_date,
                    "预测最早发运产品累计运行时间": round(max_run_time_input_hours, 2),
                    "预测最早发运产品累计运行时间（年）": round(
                        max_run_time_input_years, 4
                    ),
                    "预测故障率FPMH": round(input_date_failure_rate_fpmh, 4),
                    "error": None,
                }
            )

        except Exception as e:
            # 即使出错也尝试获取零部件名称
            part_name = None
            try:
                part_name = await get_part_name(model, part)
            except:
                pass

            results.append(
                {
                    "型号": model,
                    "物料编码": part,
                    "零部件": part_name,
                    "分布名称": None,
                    "alpha": None,
                    "beta": None,
                    "gamma": None,
                    "lambda_": None,
                    "产品最早发运日期": None,
                    "最早发运产品累计运行时间": None,
                    "最早发运产品累计运行时间（年）": None,
                    "故障率FPMH": None,
                    "预测计算截止日期": None,
                    "预测最早发运产品累计运行时间": None,
                    "预测最早发运产品累计运行时间（年）": None,
                    "预测故障率FPMH": None,
                    "error": str(e),
                }
            )

    # 输出到Excel
    output_path = Path(args.output or "test_fit_distribution_weibull.xlsx")
    df = pd.DataFrame(results)
    df.to_excel(output_path, index=False, engine="openpyxl")

    print(f"\n处理完成！")
    print(f"成功处理: {len([r for r in results if r.get('error') is None])} 条")
    print(f"失败: {len([r for r in results if r.get('error') is not None])} 条")
    print(f"结果已保存到: {output_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
