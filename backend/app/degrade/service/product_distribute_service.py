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
    async def get_product_distribute(product_model: str, check_bezier: str) -> dict[str, Any]:
        '''
        拟合每个阶段的分布，计算峰值点列表
        :param product_model: 产品型号
        :param check_bezier: 检查项
        :return:x_peaks,y_peaks
        '''
        try:
            # 1、获取基础数据
            basic_data = await ProductDistributeService.get_overhaul_date(product_model, check_bezier)
            stage_columns = list(basic_data.columns)

            if len(stage_columns) < 3:
                raise DataValidationError(
                    msg=f"型号为 {product_model} 的检修阶段数量不足"
                )
            
            # 2、获取年运行小时并计算x_peaks
            if product_model == '测试':
                year_worktimes = 13140
            else:
                year_worktimes = await ProductDistributeService.repair_interval_times(product_model)

            if '新造' in stage_columns:
                x_peaks = [0] + [year_worktimes * i for i in range(1, len(stage_columns))]
            else:
                x_peaks = [year_worktimes * (i + 1) for i in range(len(stage_columns))]

            # 3、拟合每个阶段的分布函数并计算峰值y_peaks
            y_peaks = []
            for category in stage_columns:
                data = np.array(basic_data[category].dropna().values, dtype=float)
                y = np.linspace(min(data), max(data), 200)
                fit = Fit_Everything(
                    failures=data,
                    show_PP_plot=False,
                    show_histogram_plot=False,
                    show_probability_plot=False,
                    show_best_distribution_probability_plot=False,
                    print_results=False,
                    exclude=['Weibull_Mixture', 'Weibull_CR', 'Weibull_DS', 'Weibull_3P', 'Gamma_3P',
                             'Lognormal_3P', 'Loglogistic_3P','Gamma_2P'],
                    method='MLE',
                )
                distribution = fit.best_distribution
                pdf_values = distribution.PDF(y, show_plot=False)
                peak_y = y[np.argmax(pdf_values)]
                y_peaks.append(peak_y.tolist())

            # 4、返回结果
            return {'x_peaks': x_peaks, 'y_peaks': y_peaks}

        except DataValidationError:
            raise
        except Exception as e:
            raise DataValidationError(msg=f"参数退化评估进行数据处理时发生错误: {str(e)}")

    @staticmethod
    async def get_overhaul_date(product_model: str, check_bezier: str):
        '''
        获取检修级别以及对应的检验结果，每一个检修级别成为一列
        :param product_model: 产品型号
        :param check_bezier: 检查项
        :return: DataFrame
        '''
        async with async_db_session() as db:
            try:
                # 获取检修数据并定义修程
                overhaul_date = await overhaul_dao.get_by_model_and_bezier(db, product_model, check_bezier)
                repair_level_order = ['新造', '三级修', '四级修', '次轮三级修', '五级修', '三轮三级修', '次轮四级修',
                                      '四轮三级修', '次轮五级修','五轮三级修','三轮四级修','六轮三级修','三轮五级修',
                                      'C4', 'C5', '2C4','C6','3C4','2C5']
                
                # 将数据转换为DataFrame
                df = pd.DataFrame([(x.repair_level, x.check_value) for x in overhaul_date],
                                  columns=['repair_level', 'check_value'])
                
                # 将数据按repair_level进行排序
                df = df.pivot_table(
                    index=df.groupby('repair_level').cumcount(),
                    columns='repair_level',
                    values='check_value',
                    aggfunc='first'
                ).reset_index(drop=True)
                df = df.reindex(columns=[col for col in repair_level_order if col in df.columns])
                return df
            except Exception as e:
                return {'error': f'数据处理失败: {str(e)}'}

    @staticmethod
    async def repair_interval_times(model:str):
        '''
        获取维修间隔小时
        :param model: 产品型号
        :return: 维修间隔小时
        '''
        async with async_db_session() as db:
            try:
                product_date = await product_dao.get_by_model(db, model)
                if product_date is None:
                    raise DataValidationError(
                        msg=f"型号为 {model} 的产品信息不存在"
                    )
                year_worktimes = product_date.repair_times * product_date.avg_worktime
                return year_worktimes
            except DataValidationError:
                raise



product_distribute_service: ProductDistributeService = ProductDistributeService()