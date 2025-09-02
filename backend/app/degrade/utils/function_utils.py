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

    # 1. 线性回归 (sklearn)
    try:
        linear_model = LinearRegression()
        linear_model.fit(x_peaks.reshape(-1, 1), y_peaks)
        y_pred_linear = linear_model.predict(x_peaks.reshape(-1, 1))
        mse_linear = mean_squared_error(y_peaks, y_pred_linear)

        fits['linear'] = {
            'func': lambda x: linear_model.predict(np.array(x).reshape(-1, 1)).flatten(),
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
            'func': lambda x: best_poly_model.predict(np.array(x).reshape(-1, 1)).flatten(),
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
        def exp_func(x, a, b, c):
            return a * np.exp(b * x) + c

        p0_exp = [np.max(y_peaks), 0.01, np.min(y_peaks)]
        popt_exp, _ = curve_fit(exp_func, x_1d, y_peaks, p0=p0_exp, maxfev=5000)
        y_pred_exp = exp_func(x_1d, *popt_exp)
        mse_exp = mean_squared_error(y_peaks, y_pred_exp)

        fits['exponential'] = {
            'func': lambda x: exp_func(np.array(x), *popt_exp),
            'name': 'exponential',
            'params': [float(popt_exp[0]), float(popt_exp[1]), float(popt_exp[2])],
            'mse': mse_exp
        }
    except:
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
        def sigmoid_func(x, a, b, c, d):
            return a / (1 + np.exp(-b * (x - c))) + d

        p0_sigmoid = [np.max(y_peaks) - np.min(y_peaks), 0.1, np.mean(x_1d), np.min(y_peaks)]
        popt_sigmoid, _ = curve_fit(sigmoid_func, x_1d, y_peaks, p0=p0_sigmoid, maxfev=5000)
        y_pred_sigmoid = sigmoid_func(x_1d, *popt_sigmoid)
        mse_sigmoid = mean_squared_error(y_peaks, y_pred_sigmoid)

        fits['sigmoid'] = {
            'func': lambda x: sigmoid_func(np.array(x), *popt_sigmoid),
            'name': 'sigmoid',
            'params': [float(popt_sigmoid[0]), float(popt_sigmoid[1]), float(popt_sigmoid[2]), float(popt_sigmoid[3])],
            'mse': mse_sigmoid
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



