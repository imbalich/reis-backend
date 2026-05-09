#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：product_distribute_service.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/8/20 09:48
"""
from typing import Any

import numpy as np
import pandas as pd
from reliability.Fitters import Fit_Everything

from backend.app.datamanage.crud.crud_overhaul import overhaul_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.common.exception.errors import DataValidationError

from backend.database.db import async_db_session
from scipy.stats import gaussian_kde


class ProductDistributeService:
    @staticmethod
    async def get_product_distribute(
        product_model: str, check_bezier: str
    ) -> dict[str, Any]:
        """
        拟合每个阶段的分布，计算峰值点列表
        :param product_model: 产品型号
        :param check_bezier: 检查项
        :return:x_peaks,y_peaks
        """
        try:
            # 1、获取基础数据
            basic_data = await ProductDistributeService.get_overhaul_date(
                product_model, check_bezier
            )

            # 检查返回的是否为错误字典
            if isinstance(basic_data, dict) and "error" in basic_data:
                raise DataValidationError(msg=basic_data["error"])

            # 检查是否为空的DataFrame
            if basic_data.empty:
                raise DataValidationError(
                    msg=f"型号为 {product_model}，检查项为 {check_bezier} 的检修数据不存在"
                )

            stage_columns = list(basic_data.columns)

            # if len(stage_columns) < 3:
            #     raise DataValidationError(
            #         msg=f"型号为 {product_model}，检查项为 {check_bezier} 的检修阶段数量不足（当前：{len(stage_columns)}个，至少需要3个）"
            #     )

            # 2、获取年运行小时并计算x_peaks
            if product_model == "测试" or product_model == "测试负值":
                repair_worktimes = 13140
                year_worktimes = 5600
            else:
                repair_worktimes, year_worktimes = (
                    await ProductDistributeService.repair_interval_times(product_model)
                )

            if "新造" in stage_columns:
                x_peaks = [0] + [
                    repair_worktimes * i for i in range(1, len(stage_columns))
                ]
            else:
                x_peaks = [
                    repair_worktimes * (i + 1) for i in range(len(stage_columns))
                ]

            # 3、拟合每个阶段的分布函数并计算峰值y_peaks
            y_peaks = []
            for category in stage_columns:
                data = np.array(basic_data[category].dropna().values, dtype=float)
                # print("data", data)
                
                # 检查过滤后的数据是否足够
                if len(data) == 0:
                    raise DataValidationError(
                        msg=f"检修阶段 {category} 的有效数据为空（所有值都小于等于0），无法进行分布拟合"
                    )
                # --- 新增逻辑：检查是否为单一重复数值 ---
                unique_vals = np.unique(data)
                if len(unique_vals) == 1:
                    # 如果数据全部相同，峰值直接就是这个唯一值，无需拟合
                    peak_y = unique_vals[0]
                    y_peaks.append(float(peak_y))
                    continue

                # 针对数据中的负值
                min_val = np.min(data)
                offset = max(-min_val + 1,0)
                # print("offset", offset)
                data = data + offset  # 所有数据转为正值
                # print("data_positive", data)
                # # 过滤掉零值和负值（Fit_Everything要求所有值必须大于0）
                # data = data[data > 0]

                if len(data) < 2:
                    raise DataValidationError(
                        msg=f"检修阶段 {category} 的有效数据不足（只有{len(data)}个有效值，至少需要2个），无法进行分布拟合"
                    )

                y = np.linspace(min(data), max(data), 200)
                # print("y", y)
                try:
                    fit = Fit_Everything(
                        failures=data,
                        show_PP_plot=False,
                        show_histogram_plot=False,
                        show_probability_plot=False,
                        show_best_distribution_probability_plot=False,
                        print_results=False,
                        exclude=[
                            "Weibull_Mixture",
                            "Weibull_CR",
                            "Weibull_DS",
                            "Weibull_3P",
                            "Gamma_3P",
                            "Lognormal_3P",
                            "Loglogistic_3P",
                            "Gamma_2P",
                        ],
                        method="MLE",
                    )
                    distribution = fit.best_distribution
                    # print("distribution", distribution)
                    pdf_values = distribution.PDF(y, show_plot=False)
                    peak_y = y[np.argmax(pdf_values)]
                    # print("peak_y", peak_y)
                    peak_y = peak_y - offset  # 还原
                    # print("peak_y_restored", peak_y)
                    y_peaks.append(peak_y.tolist())
                except ValueError as e:
                    if "greater than zero" in str(e):
                        raise DataValidationError(
                            msg=f"检修阶段 {category} 的数据包含零值或负值，无法进行分布拟合。"
                            f"请检查检查项 {check_bezier} 在 {category} 阶段的检查值是否正确"
                        ) from e
                    raise

            # 4、返回结果
            return {
                "x_peaks": x_peaks,
                "y_peaks": y_peaks,
                "year_worktimes": year_worktimes,
            }

        except DataValidationError:
            raise
        except Exception as e:
            raise DataValidationError(
                msg=f"参数退化评估进行数据处理时发生错误: {str(e)}"
            )

    @staticmethod
    async def get_overhaul_date(product_model: str, check_bezier: str):
        """
        获取检修级别以及对应的检验结果，每一个检修级别成为一列
        :param product_model: 产品型号
        :param check_bezier: 检查项
        :return: DataFrame
        """
        async with async_db_session() as db:
            try:
                # 获取检修数据并定义修程
                overhaul_date = await overhaul_dao.get_by_model_and_bezier(
                    db, product_model, check_bezier
                )
                repair_level_order = [
                    "新造",
                    "三级修",
                    "四级修",
                    "首轮三级修",
                    "首轮四级修",
                    "次轮三级修",
                    "五级修",
                    "三轮三级修",
                    "次轮四级修",
                    "四轮三级修",
                    "次轮五级修",
                    "五轮三级修",
                    "三轮四级修",
                    "六轮三级修",
                    "三轮五级修",
                    "C4",
                    "C5",
                    "2C4",
                    "C6",
                    "3C4",
                    "2C5",
                ]

                # 将数据转换为DataFrame
                df = pd.DataFrame(
                    [(x.repair_level, x.check_value) for x in overhaul_date],
                    columns=["repair_level", "check_value"],
                )

                # 将数据按repair_level进行排序
                df = df.pivot_table(
                    index=df.groupby("repair_level").cumcount(),
                    columns="repair_level",
                    values="check_value",
                    aggfunc="first",
                ).reset_index(drop=True)
                df = df.reindex(
                    columns=[col for col in repair_level_order if col in df.columns]
                )
                return df
            except Exception as e:
                return {"error": f"数据处理失败: {str(e)}"}

    @staticmethod
    async def repair_interval_times(model: str):
        """
        获取维修间隔小时
        :param model: 产品型号
        :return: 维修间隔小时
        """
        async with async_db_session() as db:
            try:
                product_date = await product_dao.get_by_model(db, model)
                if product_date is None:
                    raise DataValidationError(
                        msg=f"型号为 {model} 的产品信息不存在，请检查数据库中是否有该型号的记录"
                    )
                if (
                    product_date.repair_times is None
                    or product_date.avg_worktime is None
                    or product_date.year_days is None
                ):
                    raise DataValidationError(
                        msg=f"型号为 {model} 的产品信息不完整（repair_times、avg_worktime 或 year_days 为空）"
                    )
                repair_worktimes = product_date.repair_times * product_date.avg_worktime
                year_worktimes = 365 * product_date.avg_worktime
                return repair_worktimes, year_worktimes
            except DataValidationError:
                raise


product_distribute_service: ProductDistributeService = ProductDistributeService()
