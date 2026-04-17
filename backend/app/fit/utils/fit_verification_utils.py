#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
拟合校验工具类。

功能：
1. 读取 Excel 输入数据；
2. 执行零部件级拟合；
3. 计算多个时间区间内的预测值，并和实际故障数对比。
"""

from __future__ import annotations

import inspect
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from backend.app.calcu.service.science_warehouse_service import parse_discovery_date
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.fit.schema.base_param import ProductParam
from backend.app.fit.schema.fit_param import FitMethodType
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.fit.utils.convert_model import convert_to_pydantic_model
from backend.app.fit.utils.time_utils import dateutils
from backend.database.db import async_db_session


def _filter_supported_kwargs(func: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    signature = inspect.signature(func)
    return {key: value for key, value in kwargs.items() if key in signature.parameters}


class FitVerificationUtils:
    """拟合校验工具类。"""

    @staticmethod
    async def read_excel_input(excel_path: str | Path) -> List[Dict[str, Any]]:
        """
        读取 Excel 输入文件。

        必填列：
        - 产品型号
        - 零部件物料编码
        - input_date

        可选列：
        - 派生码
        - product_config_code
        """
        excel_path = Path(excel_path)
        if not excel_path.exists():
            raise FileNotFoundError(f"Excel 文件不存在: {excel_path}")

        df = pd.read_excel(excel_path)
        required_columns = ["产品型号", "零部件物料编码", "input_date"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Excel 文件缺少必填列: {missing_columns}")

        input_data: List[Dict[str, Any]] = []
        for index, row in df.iterrows():
            model = str(row["产品型号"]).strip()
            part = str(row["零部件物料编码"]).strip()
            input_date_value = row["input_date"]
            product_config_code = row.get("派生码", row.get("product_config_code"))

            try:
                if isinstance(input_date_value, pd.Timestamp):
                    parsed_input_date = input_date_value.date()
                elif isinstance(input_date_value, date):
                    parsed_input_date = input_date_value
                else:
                    input_date_str = str(input_date_value).strip()
                    if " " in input_date_str:
                        input_date_str = input_date_str.split(" ")[0]
                    parsed_input_date = dateutils.validate_and_parse_date(input_date_str)
            except Exception as exc:
                raise ValueError(
                    f"第 {index + 2} 行 input_date 格式错误: {input_date_value}, 错误: {exc}"
                ) from exc

            row_payload: Dict[str, Any] = {
                "model": model,
                "part": part,
                "input_date": parsed_input_date,
            }
            if pd.notna(product_config_code):
                row_payload["product_config_code"] = str(product_config_code).strip()
            input_data.append(row_payload)

        return input_data

    @staticmethod
    async def perform_fit(
        model: str,
        part: str,
        input_date: date,
        method: FitMethodType = FitMethodType.MLE,
        product_config_code: str | None = None,
    ) -> Tuple[Any, List[List], ProductParam]:
        """执行一次零部件拟合。"""
        strategy_kwargs = _filter_supported_kwargs(
            part_strategy_service.part_tag_process,
            {"product_config_code": product_config_code},
        )
        tags = await part_strategy_service.part_tag_process(
            model, part, input_date, **strategy_kwargs
        )

        fit_result = await part_fit_service.tag_fit(tags, method)
        best_distribution = fit_result.best_distribution

        async with async_db_session() as db:
            product_kwargs = _filter_supported_kwargs(
                product_dao.get_by_model,
                {"product_config_code": product_config_code},
            )
            product = await product_dao.get_by_model(db, model, **product_kwargs)
            product_data = convert_to_pydantic_model(product, ProductParam)

        return best_distribution, tags, product_data

    @staticmethod
    def extract_product_despatch_dates(tags: List[List]) -> Dict[Any, date]:
        """
        从标签数据中提取每个产品或产品+虚拟件的最早发运日期。

        兼容两种结构：
        - 整机级: [产品编号, 开始日期, 结束日期, 天数差, 运行时间, 类型]
        - 零部件级: [产品编号, 虚拟件编码, 开始日期, 结束日期, 天数差, 运行时间, 类型]
        """
        if not tags:
            return {}

        tag_len = len(tags[0])
        despatch_map: Dict[Any, date] = {}

        for tag in tags:
            if len(tag) != tag_len:
                key = tag[0]
            elif tag_len >= 7:
                key = (tag[0], tag[1])
            else:
                key = tag[0]

            start_tag = tag[-5]
            if key not in despatch_map or start_tag < despatch_map[key]:
                despatch_map[key] = start_tag

        return despatch_map

    @staticmethod
    async def get_actual_failure_count(
        model: str,
        part: str,
        start_date: date,
        end_date: date,
        product_config_code: str | None = None,
    ) -> int:
        """查询指定时间区间内的实际故障数量。"""
        async with async_db_session() as db:
            failure_kwargs = _filter_supported_kwargs(
                failure_dao.get_by_model_and_part,
                {"product_config_code": product_config_code},
            )
            failures = await failure_dao.get_by_model_and_part(
                db, model, part, **failure_kwargs
            )

        actual_count = 0
        for failure in failures:
            parsed_date = parse_discovery_date(failure.discovery_date)
            if parsed_date is not None and start_date <= parsed_date <= end_date:
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
        """计算指定时间区间的累计预测值。"""
        total_prediction = 0.0

        for key, despatch_date in product_despatch.items():
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

            start_x = max(0, start_x)
            end_x = max(0, end_x)
            if start_x >= end_x:
                continue

            try:
                yvals = distribution.CDF(xvals=[start_x, end_x], show_plot=False)
                prediction = yvals[1] - yvals[0]
                total_prediction += max(0.0, prediction)
            except Exception as exc:
                key_str = f"{key[0]}-{key[1]}" if isinstance(key, tuple) else str(key)
                print(f"警告: {key_str} 预测计算失败: {exc}")

        return total_prediction

    @staticmethod
    async def calculate_predictions_for_intervals(
        model: str,
        part: str,
        input_date: date,
        time_intervals: List[Tuple[date, date]],
        method: FitMethodType = FitMethodType.MLE,
        product_config_code: str | None = None,
    ) -> List[Dict[str, Any]]:
        """计算多个时间区间的预测结果。"""
        results: List[Dict[str, Any]] = []

        try:
            distribution, tags, product_data = await FitVerificationUtils.perform_fit(
                model=model,
                part=part,
                input_date=input_date,
                method=method,
                product_config_code=product_config_code,
            )
            product_despatch = FitVerificationUtils.extract_product_despatch_dates(tags)

            for start_date, end_date in time_intervals:
                prediction = FitVerificationUtils.calculate_prediction_for_interval(
                    distribution=distribution,
                    product_despatch=product_despatch,
                    product_data=product_data,
                    start_date=start_date,
                    end_date=end_date,
                )
                actual_count = await FitVerificationUtils.get_actual_failure_count(
                    model=model,
                    part=part,
                    start_date=start_date,
                    end_date=end_date,
                    product_config_code=product_config_code,
                )

                result: Dict[str, Any] = {
                    "model": model,
                    "part": part,
                    "input_date": input_date,
                    "start_date": start_date,
                    "end_date": end_date,
                    "prediction": prediction,
                    "actual_count": actual_count,
                    "difference": prediction - actual_count,
                    "distribution": (
                        distribution.name
                        if hasattr(distribution, "name")
                        else type(distribution).__name__
                    ),
                    "product_count": len(
                        {
                            key[0] if isinstance(key, tuple) else key
                            for key in product_despatch.keys()
                        }
                    ),
                }
                if product_config_code is not None:
                    result["product_config_code"] = product_config_code
                results.append(result)

        except Exception as exc:
            error_msg = str(exc)
            for start_date, end_date in time_intervals:
                try:
                    actual_count = await FitVerificationUtils.get_actual_failure_count(
                        model=model,
                        part=part,
                        start_date=start_date,
                        end_date=end_date,
                        product_config_code=product_config_code,
                    )
                except Exception:
                    actual_count = None

                result = {
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
                if product_config_code is not None:
                    result["product_config_code"] = product_config_code
                results.append(result)

        return results

    @staticmethod
    def export_to_csv(results: List[Dict[str, Any]], output_path: str | Path) -> None:
        """导出结果到 CSV。"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(results).to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"结果已导出到: {output_path}")
