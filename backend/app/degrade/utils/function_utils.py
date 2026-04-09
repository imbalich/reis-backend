#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：function_utils.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/8/20 15:57
"""
import numpy as np
from scipy.optimize import curve_fit
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error

def fit_functions(x_peaks, y_peaks):
    """
    使用多种函数拟合峰值点，优先使用库函数
    :param x_peaks: x轴峰值点
    :param y_peaks: y轴峰值点
    :return: 包含各种拟合结果的字典
    """
    fits = {}
    x_peaks = np.array(x_peaks).reshape(-1, 1) if len(np.array(x_peaks).shape) == 1 else np.array(x_peaks)
    # print('x_peaks', x_peaks)
    y_peaks = np.array(y_peaks)
    x_1d = x_peaks.flatten()

    all_negative = np.all(y_peaks < 0)


    # 1. 线性回归 (sklearn)
    try:
        linear_model = LinearRegression()
        linear_model.fit(x_peaks.reshape(-1, 1), y_peaks)
        y_pred_linear = linear_model.predict(x_peaks.reshape(-1, 1))
        mse_linear = mean_squared_error(y_peaks, y_pred_linear)

        fits['linear'] = {
            'func':  lambda x: linear_model.predict(np.array(x).reshape(-1, 1)).flatten(),
            'name': 'linear',
            'params': [float(linear_model.coef_[0]), float(linear_model.intercept_)],
            'mse': mse_linear,
        }
    except:
        fits['linear'] = None

    # 2. 多项式回归 (sklearn Pipeline)
    try:
        best_poly_degree = 2
        best_poly_mse = float('inf')
        best_poly_model = None

        max_degree = min(len(x_peaks) - 1, 3)
        for degree in range(2, max_degree + 1):
            poly_model = Pipeline([
                ('poly', PolynomialFeatures(degree=degree)),
                ('ridge', Ridge(alpha=0.1))
            ])
            poly_model.fit(x_peaks.reshape(-1, 1), y_peaks)
            y_pred = poly_model.predict(x_peaks.reshape(-1, 1))
            mse = mean_squared_error(y_peaks, y_pred)

            if mse < best_poly_mse:
                best_poly_mse = mse
                best_poly_degree = degree
                best_poly_model = poly_model
        coefs = best_poly_model.named_steps['ridge'].coef_
        intercept = best_poly_model.named_steps['ridge'].intercept_
        params = [float(c) for c in coefs] + [float(intercept)]

        fits['polynomial'] = {
            'func':  lambda x: best_poly_model.predict(np.array(x).reshape(-1, 1)).flatten(),
            'name': f'polynomial_{best_poly_degree}',
            'params': params,
            'mse': best_poly_mse
        }
    except:
        fits['polynomial'] = None

    # 3. 岭回归 (sklearn)
    try:
        ridge_model = Ridge(alpha=1.0)
        ridge_model.fit(x_peaks.reshape(-1, 1), y_peaks)
        y_pred_ridge = ridge_model.predict(x_peaks.reshape(-1, 1))
        mse_ridge = mean_squared_error(y_peaks, y_pred_ridge)

        fits['ridge'] = {
            'func': lambda x: ridge_model.predict(np.array(x).reshape(-1, 1)).flatten(),
            'name': 'ridge',
            'params': [float(ridge_model.coef_[0]), float(ridge_model.intercept_)],
            'mse': mse_ridge,
        }
    except:
        fits['ridge'] = None

    # 6. 对数函数拟合 (scipy curve_fit)
    try:
        def log_func(x, a, b):
            return a * np.log(x + 1) + b

        popt_log, _ = curve_fit(log_func, x_1d, y_peaks)
        y_pred_log = log_func(x_1d, *popt_log)
        mse_log = mean_squared_error(y_peaks, y_pred_log)

        fits['logarithmic'] = {
            'func': lambda x: log_func(np.array(x), *popt_log),
            'name': 'logarithmic',
            'params': [float(popt_log[0]), float(popt_log[1])],
            'mse': mse_log
        }
    except:
        fits['logarithmic'] = None

    # 7. 指数函数拟合 (scipy curve_fit)
    try:
        def exp_generic(x, a, b, c):
            # 使用 clip 防止 b * x 过大导致溢出
            return a * np.exp(np.clip(b * x, -20, 20)) + c

        if all_negative:
            # 初始猜测
            # 对于全负数，通常 c 是渐近线，a 是偏离量
            c_guess = np.max(y_peaks)
            a_guess = np.min(y_peaks) - c_guess
            p0_exp = [a_guess, 0.01, c_guess]
            
            # 约束条件：
            # 1. 如果递增趋于0，b 应该 > 0 且 a 为负，或者 b < 0 且 c 接近0
            # 2. 核心约束：无论如何，在远期（比如 x=100）结果不能 > 0
            # 这里我们限制 c (渐近线) 必须小于等于 0
            # 同时限制 a，如果 b > 0，a 必须小于 0 才能保证不往正数跑
            bounds = ([-np.inf, -np.inf, -np.inf], [np.inf, np.inf, 1e-9])
            
            popt_exp, _ = curve_fit(exp_generic, x_1d, y_peaks, p0=p0_exp, bounds=bounds, maxfev=5000)
            
            # 额外物理校验：如果远期预测值 > 0，则强制压低 c
            if exp_generic(100, *popt_exp) > 0:
                popt_exp[2] = -np.abs(popt_exp[0]) if popt_exp[1] > 0 else -1e-9
        else:
            # 常规正值逻辑
            p0_exp = [1.0, 0.01, np.min(y_peaks)]
            popt_exp, _ = curve_fit(exp_generic, x_1d, y_peaks, p0=p0_exp, maxfev=5000)

        fits['exponential'] = {
            'func': lambda x: exp_generic(np.array(x), *popt_exp),
            'name': 'exponential',
            'params': [float(p) for p in popt_exp], # 始终返回 [a, b, c]
            'mse': mean_squared_error(y_peaks, exp_generic(x_1d, *popt_exp))
        }
    except Exception as e:
        fits['exponential'] = None

    # 8. 幂函数拟合 (scipy curve_fit)
    try:
        def power_func(x, a, b, c):
            return a * np.power(x + 1e-8, b) + c

        p0_power = [np.max(y_peaks), 1.0, np.min(y_peaks)]
        popt_power, _ = curve_fit(power_func, x_1d, y_peaks, p0=p0_power)
        y_pred_power = power_func(x_1d, *popt_power)
        mse_power = mean_squared_error(y_peaks, y_pred_power)

        fits['power_law'] = {
            'func': lambda x: power_func(np.array(x), *popt_power),
            'name': 'power_law',
            'params': [float(popt_power[0]), float(popt_power[1]), float(popt_power[2])],
            'mse': mse_power
        }
    except:
        fits['power_law'] = None

        # 9. Sigmoid函数拟合 (scipy curve_fit)
    try:
        # 统一函数定义
        def sigmoid_generic(x, a, b, c, d):
            return a / (1 + np.exp(-b * (x - c))) + d
        if all_negative:
            # 策略：限制 a + d <= 0 (即渐近线最大值不超过0)
            # 初始猜测：
            # d (底部) 设为最小值, a (幅值) 设为 y 的跨度, c 设为 x 中点
            d_init = np.min(y_peaks)
            a_init = np.max(y_peaks) - d_init
            p0_sigmoid = [a_init, 0.1, np.mean(x_1d), d_init]
            
            # 设置边界：a > 0 (正向摆幅), b > 0 (保证单调性方向由 a 决定)
            # 关键约束：d 必须在负数区，且 a + d (上限) 也要在负数区
            # bounds = ([min_a, min_b, min_c, min_d], [max_a, max_b, max_c, max_d])
            bounds = (
                [0, 0, -np.inf, -np.inf], 
                [np.inf, np.inf, np.inf, 1e-9] # d 最大接近 0
            )
            
            popt_sigmoid, _ = curve_fit(sigmoid_generic, x_1d, y_peaks, p0=p0_sigmoid, bounds=bounds, maxfev=5000)
            
            # 再次检查：如果拟合出来的上限仍然 > 0，则手动调整 d
            if popt_sigmoid[0] + popt_sigmoid[3] > 0:
                popt_sigmoid[3] = -popt_sigmoid[0] - 1e-9
        else:

            p0_sigmoid = [np.max(y_peaks) - np.min(y_peaks), 0.1, np.mean(x_1d), np.min(y_peaks)]
            popt_sigmoid, _ = curve_fit(sigmoid_generic, x_1d, y_peaks, p0=p0_sigmoid, maxfev=5000)
            # y_pred_sigmoid = sigmoid_generic(x_1d, *popt_sigmoid)
            # mse_sigmoid = mean_squared_error(y_peaks, y_pred_sigmoid)

        fits['sigmoid'] = {
            'func': lambda x: sigmoid_generic(np.array(x), *popt_sigmoid),
            'name': 'sigmoid',
            'params': [float(popt_sigmoid[0]), float(popt_sigmoid[1]), float(popt_sigmoid[2]), float(popt_sigmoid[3])],
            'mse': mean_squared_error(y_peaks, sigmoid_generic(x_1d, *popt_sigmoid))
        }
    except:
        fits['sigmoid'] = None

    return fits


def is_monotonic(func, x_range):
    '''
    判断函数是否单调
    :param func: 函数
    :param x_range: 函数的输入范围
    :return: 是否单调
    '''
    y = func(x_range)
    return np.all(np.diff(y) >= 0) or np.all(np.diff(y) <= 0)



