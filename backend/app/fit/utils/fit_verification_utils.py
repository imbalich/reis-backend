#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
拟合验证工具类

功能：
1. 读取Excel文件（包含产品型号、零部件物料编码、input_date）
2. 执行拟合
3. 计算多个时间区间的预测值
"""

import pandas as pd
from datetime import date
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.fit.schema.fit_param import FitMethodType
from backend.app.fit.schema.base_param import ProductParam
from backend.app.fit.utils.time_utils import dateutils
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.fit.utils.convert_model import convert_to_pydantic_model
from backend.database.db import async_db_session
from backend.common.exception.errors import DataValidationError
from backend.app.calcu.service.science_warehouse_service import parse_discovery_date


class FitVerificationUtils:
    """拟合验证工具类"""

    @staticmethod
    async def read_excel_input(excel_path: str | Path) -> List[Dict[str, Any]]:
        """
        读取Excel输入文件

        Excel文件应包含以下列：
        - 产品型号 (model)
        - 零部件物料编码 (part)
        - input_date (计算截止日期，格式：YYYY-MM-DD)

        :param excel_path: Excel文件路径
        :return: 输入数据列表
        """
        excel_path = Path(excel_path)
        if not excel_path.exists():
            raise FileNotFoundError(f"Excel文件不存在: {excel_path}")

        df = pd.read_excel(excel_path)

        # 检查必需的列
        required_columns = ["产品型号", "零部件物料编码", "input_date"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Excel文件缺少必需的列: {missing_columns}")

        # 转换为列表
        input_data = []
        for _, row in df.iterrows():
            model = str(row["产品型号"]).strip()
            part = str(row["零部件物料编码"]).strip()
            input_date_value = row["input_date"]

            # 解析日期
            try:
                # 先检查是否是 pd.Timestamp 对象
                if isinstance(input_date_value, pd.Timestamp):
                    input_date = input_date_value.date()
                elif isinstance(input_date_value, date):
                    input_date = input_date_value
                else:
                    # 转换为字符串并解析
                    input_date_str = str(input_date_value).strip()
                    # 处理 pandas 读取的日期格式（如 "2020-01-01 00:00:00"）
                    if " " in input_date_str:
                        input_date_str = input_date_str.split(" ")[0]  # 只取日期部分
                    input_date = dateutils.validate_and_parse_date(input_date_str)
            except Exception as e:
                raise ValueError(
                    f"第{len(input_data)+1}行: input_date格式错误: {input_date_value}, 错误: {e}"
                )

            input_data.append(
                {
                    "model": model,
                    "part": part,
                    "input_date": input_date,
                }
            )

        return input_data

    @staticmethod
    async def perform_fit(
        model: str,
        part: str,
        input_date: date,
        method: FitMethodType = FitMethodType.MLE,
    ) -> Tuple[Any, List[List], ProductParam]:
        """
        执行拟合

        :param model: 产品型号
        :param part: 零部件物料编码
        :param input_date: 计算截止日期
        :param method: 拟合方法
        :return: (最佳分布对象, 标签数据, 产品参数)
        """
        # 1. 获取标签数据
        tags = await part_strategy_service.part_tag_process(model, part, input_date)

        # 2. 执行拟合
        fit_result = await part_fit_service.tag_fit(tags, method)

        # 3. 获取最佳分布
        best_distribution = fit_result.best_distribution

        # 4. 获取产品参数
        async with async_db_session() as db:
            product_data = convert_to_pydantic_model(
                await product_dao.get_by_model(db, model), ProductParam
            )

        return best_distribution, tags, product_data

    @staticmethod
    def extract_product_despatch_dates(tags: List[List]) -> Dict[Any, date]:
        """
        从标签数据中提取每个产品/虚拟件的最早发运日期
        兼容整机级和零部件级两种标签结构

        :param tags: 标签数据列表
        :return: 发运日期字典
            - 整机级: {产品编号: 发运日期}
            - 零部件级: {(产品编号, 虚拟物料编码): 发运日期}
        """
        if not tags:
            return {}

        # 兼容整机级（product_tag）和零部件级（part_tag）两种标签结构
        # - 整机级: [产品编号, 开始日期, 结束日期, 天数差, 运行时间, 类型]  -> len == 6
        # - 零部件级: [产品编号, 虚拟物料编码, 开始日期, 结束日期, 天数差, 运行时间, 类型] -> len == 7
        tag_len = len(tags[0])

        despatch_map = {}
        for tag in tags:
            # 防止混合结构，长度不一致时退化为按产品编号
            if len(tag) != tag_len:
                key = tag[0]
            else:
                if tag_len >= 7:
                    # 零部件级：产品编号 + 虚拟键
                    key = (tag[0], tag[1])
                else:
                    # 整机级：只有产品编号
                    key = tag[0]

            start_tag = tag[-5]  # 开始日期（统一使用 tag[-5]）
            if key not in despatch_map or start_tag < despatch_map[key]:
                despatch_map[key] = start_tag

        return despatch_map

    @staticmethod
    async def get_actual_failure_count(
        model: str,
        part: str,
        start_date: date,
        end_date: date,
    ) -> int:
        """
        查询时间范围内的实际故障数量

        :param model: 产品型号
        :param part: 零部件物料编码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 实际故障数量
        """
        async with async_db_session() as db:
            # 使用和 get_by_model_and_part 相同的筛选条件
            failures = await failure_dao.get_by_model_and_part(db, model, part)

            # 过滤时间范围
            actual_count = 0
            for failure in failures:
                # 解析 discovery_date
                parsed_date = parse_discovery_date(failure.discovery_date)
                if parsed_date is None:
                    continue

                # 检查是否在时间范围内
                if start_date <= parsed_date <= end_date:
                    actual_count += 1

            return actual_count

    @staticmethod
    def calculate_prediction_for_interval(
        distribution: Any,
        product_despatch: Dict[Any, date],
        product_data: ProductParam,
        start_date: date,
        end_date: date,
    ) -> float:
        """
        计算指定时间区间的预测值
        兼容整机级和零部件级两种标签结构

        :param distribution: 分布对象
        :param product_despatch: 发运日期字典
            - 整机级: {产品编号: 发运日期}
            - 零部件级: {(产品编号, 虚拟物料编码): 发运日期}
        :param product_data: 产品参数
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 预测值（所有产品/虚拟件的CDF差值之和）
        """
        total_prediction = 0.0

        for key, despatch_date in product_despatch.items():
            # 计算运行时间（小时）
            start_x = (
                ((start_date - despatch_date).days + 365)
                * product_data.year_days
                * product_data.avg_worktime
                / 365
            )
            end_x = (
                ((end_date - despatch_date).days + 365)
                * product_data.year_days
                * product_data.avg_worktime
                / 365
            )

            # 确保运行时间为非负数
            start_x = max(0, start_x)
            end_x = max(0, end_x)

            # 如果开始时间大于结束时间，跳过
            if start_x >= end_x:
                continue

            # 计算CDF差值
            try:
                yvals = distribution.CDF(xvals=[start_x, end_x], show_plot=False)
                prediction = yvals[1] - yvals[0]
                total_prediction += max(0.0, prediction)  # 确保不为负数
            except Exception as e:
                # 如果计算失败，记录错误但继续
                key_str = f"{key[0]}-{key[1]}" if isinstance(key, tuple) else str(key)
                print(f"警告: {key_str} 计算失败: {e}")
                continue

        return total_prediction

    @staticmethod
    async def calculate_predictions_for_intervals(
        model: str,
        part: str,
        input_date: date,
        time_intervals: List[Tuple[date, date]],
        method: FitMethodType = FitMethodType.MLE,
    ) -> List[Dict[str, Any]]:
        """
        计算多个时间区间的预测值

        :param model: 产品型号
        :param part: 零部件物料编码
        :param input_date: 计算截止日期
        :param time_intervals: 时间区间列表，每个元素为 (start_date, end_date)
        :param method: 拟合方法
        :return: 预测结果列表
        """
        results = []

        try:
            # 1. 执行拟合
            distribution, tags, product_data = await FitVerificationUtils.perform_fit(
                model, part, input_date, method
            )

            # 2. 提取产品发运日期
            product_despatch = FitVerificationUtils.extract_product_despatch_dates(tags)

            # 3. 计算每个时间区间的预测值和实际值
            for start_date, end_date in time_intervals:
                prediction = FitVerificationUtils.calculate_prediction_for_interval(
                    distribution,
                    product_despatch,
                    product_data,
                    start_date,
                    end_date,
                )

                # 查询实际故障数量
                actual_count = await FitVerificationUtils.get_actual_failure_count(
                    model, part, start_date, end_date
                )

                results.append(
                    {
                        "model": model,
                        "part": part,
                        "input_date": input_date,
                        "start_date": start_date,
                        "end_date": end_date,
                        "prediction": prediction,
                        "actual_count": actual_count,
                        "difference": (
                            prediction - actual_count
                            if prediction is not None
                            else None
                        ),
                        "distribution": (
                            distribution.name
                            if hasattr(distribution, "name")
                            else str(type(distribution).__name__)
                        ),
                        "product_count": len(
                            set(
                                k[0] if isinstance(k, tuple) else k
                                for k in product_despatch.keys()
                            )
                        ),  # 统计产品编号数量（去重）
                    }
                )

        except Exception as e:
            # 如果拟合失败，记录错误
            error_msg = str(e)
            for start_date, end_date in time_intervals:
                # 即使拟合失败，也尝试查询实际故障数量
                try:
                    actual_count = await FitVerificationUtils.get_actual_failure_count(
                        model, part, start_date, end_date
                    )
                except Exception:
                    actual_count = None

                results.append(
                    {
                        "model": model,
                        "part": part,
                        "input_date": input_date,
                        "start_date": start_date,
                        "end_date": end_date,
                        "prediction": None,
                        "actual_count": actual_count,
                        "difference": None,
                        "distribution": None,
                        "product_count": None,
                        "error": error_msg,
                    }
                )

        return results

    @staticmethod
    def export_to_csv(
        results: List[Dict[str, Any]],
        output_path: str | Path,
    ) -> None:
        """
        导出结果到CSV文件

        :param results: 预测结果列表
        :param output_path: 输出文件路径
        """
        output_path = Path(output_path)

        # 转换为DataFrame
        df = pd.DataFrame(results)

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 导出CSV
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

        print(f"结果已导出到: {output_path}")
