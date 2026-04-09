#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：product_fit_service.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/8/20 09:48
"""
import numpy as np
from typing import Any

from scipy import stats
from backend.database.db import async_db_session
from backend.app.datamanage.crud.crud_overhaul import overhaul_dao

from backend.app.degrade.service.product_distribute_service import ProductDistributeService
from backend.app.degrade.utils.function_utils import fit_functions, is_monotonic

class ProductFitService:

    @staticmethod
    async def product_fit(
        product_model:str, 
        check_bezier:str,
        failure_threshold:float = None,
        product_no:str=None)-> dict[str, Any]:
        '''
        根据峰值点拟合最优函数,计算置信宽度，供前端计算置信区间
        :product_model: 产品型号
        :check_bezier: 检查曲
        :return:最优函数参数、置信宽度
        '''

        # 1、获取峰值点列表
        peaks_time = await ProductDistributeService.get_product_distribute(product_model, check_bezier)
        # print("峰值点列表:",peaks_time)
        curret_value = await  ProductFitService.get_current_check_value(product_model, product_no)

        # 2、函数拟合并寻找最优模型
        # 时间数据标准化 - 将小时转换为千小时单位
        scale_factor = 10000.0
        x_peaks = [x / scale_factor for x in peaks_time['x_peaks']]
        y_peaks = peaks_time['y_peaks']
        year_worktimes = peaks_time['year_worktimes']
        fits = fit_functions(x_peaks, y_peaks)
        all_negative = np.all(np.array(y_peaks) < 0)
        # print("是否为负数:",all_negative)
        best_fit_model = await ProductFitService.get_best_fit_model(fits,all_negative=all_negative)

        # 3、计算置信区间（假设残差服从正态分布），后端仅计算置信宽度，供前端计算置信区间
        results = []
        y_pred = best_fit_model['func'](x_peaks)
        residuals = y_peaks - y_pred
        dof = max(1, len(y_peaks) - 2)
        s_err = np.sqrt(np.sum(residuals ** 2) / dof)
        # t_val = stats.t.ppf(0.975, dof)  # 95%置信区间
        t_val = stats.t.ppf(0.8, dof)
        ci = (t_val * s_err)

        # 4、计算失效阈值对应的运行时间以及置信区间
        x_smooth = np.linspace(min(x_peaks), 40, 1000)
        # x_smooth = np.linspace(1, 40, 1000)
        y_smooth = best_fit_model['func'](x_smooth)
        y_upper_smooth = y_smooth + ci
        y_lower_smooth = y_smooth - ci

        if failure_threshold is not None and failure_threshold.strip() != "":
            y_failure = float(failure_threshold)
            x_failure, failure_interval = await ProductFitService.find_failure_threshold_x(
                x_smooth, y_smooth, y_upper_smooth, y_lower_smooth, y_failure, year_worktimes
            )
        else:
            x_failure = None
            failure_interval = None
        
        # 
        if curret_value is not None:
            y_curret = float(curret_value)
            x_current, current_interval= await ProductFitService.find_failure_threshold_x(
                x_smooth, y_smooth, y_upper_smooth, y_lower_smooth, y_curret, year_worktimes
            )
        else:
            x_current = None
            current_interval = None

        # 5、返回结果
        results.append({
            'product_model': product_model,
            'check_bezier': check_bezier,
            'product_no': product_no,
            'all_negative': bool(all_negative),
            'x_peaks': x_peaks,
            'y_peaks':y_peaks,
            'name': best_fit_model['name'],
            'params': best_fit_model['params'],
            'ci': ci,
            'failure_threshold': failure_threshold,
            't_failure':x_failure,
            'failure_interval': failure_interval,
            'current_threshold': curret_value,
            'x_current': x_current,
            'current_interval': current_interval,
            'difference': int((x_failure - x_current)) if x_current is not None and x_failure is not None else None
        })
        return results
    
    @staticmethod
    async def get_current_check_value(product_model: str, product_no: str):
        async with async_db_session() as db:
            if product_no is not None:
                current_value = await overhaul_dao.get_by_model_and_no(db, product_model, product_no)
            else:
                current_value = None
            return current_value


    # @staticmethod
    # async def get_best_fit_model(fits,all_negative=False):
    #     """
    #     从拟合结果中选出单调且mse最小的函数
    #     :param fits: 拟合结果字典
    #     :return: 最优拟合函数信息字典
    #     """
    #     best_fit = None
    #     min_mse = float('inf')
        
    #     # 减少测试点数量，提高性能
    #     x_test = np.linspace(0, 50, 100) 
        
    #     # 首先按MSE排序，优先检查MSE较小的模型
    #     sorted_fits = sorted(
    #         [(name, info) for name, info in fits.items() if info is not None and 'func' in info and 'mse' in info],
    #         key=lambda x: x[1]['mse']
    #     )
        
    #     # 检查前3个MSE最小的模型是否单调
    #     for fit_name, fit_info in sorted_fits[:3]:
    #         try:
    #             y_test = fit_info['func'](x_test)
    #             print("测试模型:", fit_name)
    #             print("检查模型:", y_test)
    #             if all_negative and np.max(y_test) > 0:
    #                 continue
    #             if is_monotonic(fit_info['func'], x_test):
    #                 # 找到第一个单调的模型就返回
    #                 return fit_info
    #         except Exception:
    #             continue
        
    #     # 如果前3个都不单调，再检查其他模型
    #     for fit_name, fit_info in sorted_fits[3:]:
    #         try:
    #             y_test = fit_info['func'](x_test)
    #             if all_negative and np.max(y_test) > 0:
    #                 continue
    #             if is_monotonic(fit_info['func'], x_test):
    #                 if fit_info['mse'] < min_mse:
    #                     min_mse = fit_info['mse']
    #                     best_fit = fit_info
    #         except Exception:
    #             continue

    #     # 如果没有找到单调模型，返回MSE最小的模型
    #     if best_fit is None and sorted_fits:
    #         best_fit = sorted_fits[0][1]
            
    #     return best_fit

    @staticmethod
    async def get_best_fit_model(fits, all_negative=False):
        valid_fits = []
        # 测试一段较长的时间跨度，确保远期不越界
        x_future_test = np.linspace(0, 100, 100) 
        
        for name, info in fits.items():
            if info is None: continue
            try:
                y_future = info['func'](x_future_test)
                
                # 核心约束：如果是负值模式，预测值绝不能超过 0
                # if all_negative and np.any(y_future > 0.001):
                #     continue 
                
                # 核心约束：必须满足单调性
                if is_monotonic(info['func'], x_future_test):
                    valid_fits.append(info)
            except:
                continue

        if valid_fits:
            # 返回满足约束且 MSE 最小的模型
            return min(valid_fits, key=lambda x: x['mse'])
        
        # 兜底：如果都越界了，返回 MSE 最小的原始模型
        sorted_fits = [v for v in fits.values() if v is not None]
        return min(sorted_fits, key=lambda x: x['mse']) if sorted_fits else None
    
    @staticmethod
    async def find_failure_threshold_x(x_smooth, y_smooth, y_upper_smooth, y_lower_smooth, failure_value,year_worktimes):
        '''
        查找失效阈值对应的x值及其置信范围
        :x_smooth: 平滑的x值数组
        :y_smooth: 拟合函数在x_smooth上的y值
        :y_upper_smooth: 上置信边界在x_smooth上的y值
        :y_lower_smooth: 下置信边界在x_smooth上的y值
        :failure_value: 失效阈值
        '''
        # 确定曲线的单调性
        is_increasing = y_smooth[-1] > y_smooth[0]

        x_failure = None
        x_failure_lower = None
        x_failure_upper = None
    
        # 根据曲线单调性选择查找条件
        if is_increasing:
            # 对于递增曲线：查找第一个超过失效阈值的点
            above_threshold_indices = np.where(y_smooth >= failure_value)[0]
            if len(above_threshold_indices) > 0:
                x_failure = min(round((x_smooth[above_threshold_indices[0]] * 10000)/year_worktimes,2),30)
        
            above_threshold_upper_indices = np.where(y_upper_smooth >= failure_value)[0]
            if len(above_threshold_upper_indices) > 0:
                x_failure_upper = min(round((x_smooth[above_threshold_upper_indices[0]] * 10000)/year_worktimes,2),30)
        
            above_threshold_lower_indices = np.where(y_lower_smooth >= failure_value)[0]
            if len(above_threshold_lower_indices) > 0:
                x_failure_lower = min(round((x_smooth[above_threshold_lower_indices[0]] * 10000)/year_worktimes,2),30)
            failure_interval = [x_failure_upper,x_failure_lower]
        else:
            # 对于递减曲线：查找第一个低于失效阈值的点
            below_threshold_indices = np.where(y_smooth <= failure_value)[0]
            if len(below_threshold_indices) > 0:
                x_failure = min(round((x_smooth[below_threshold_indices[0]] * 10000)/year_worktimes,2),30)
        
            below_threshold_upper_indices = np.where(y_upper_smooth <= failure_value)[0]
            if len(below_threshold_upper_indices) > 0:
                x_failure_upper = min(round((x_smooth[below_threshold_upper_indices[0]] * 10000)/year_worktimes,2),30)
        
            below_threshold_lower_indices = np.where(y_lower_smooth <= failure_value)[0]
            if len(below_threshold_lower_indices) > 0:
                x_failure_lower = min(round((x_smooth[below_threshold_lower_indices[0]] * 10000)/year_worktimes,2),30)
            failure_interval = [x_failure_lower,x_failure_upper]
        return x_failure, failure_interval

product_fit_service: ProductFitService = ProductFitService()