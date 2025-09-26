#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：pso_service.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/20 14:03
"""
import numpy as np
from pyswarms.single.global_best import GlobalBestPSO


class PS0Service:

    @staticmethod
    async def pso_optimize_params(param_names, original_params, distribution_class, t, target_sf, equal_lifetime_t,equal_lifetime_sf):
        """
        使用pyswarms进行分布参数优化，满足两个约束条件：
        1. sf(t) >= target_sf
        2. SF(equal_t) ≈ equal_sf
        """

        # 1. 构造优化参数列表和原始参数
        fixed_params = {k: v for k, v in original_params.items() if k.lower() == 'gamma'}

        # 2、参数边界
        bounds_lower = []
        bounds_upper = []
        for param in param_names:
            v = original_params[param]
            if "lambda" in param.lower():
                bounds_lower.append(1e-8)
                bounds_upper.append(1e-5)
            else:
                bounds_lower.append(v * 0.1)
                bounds_upper.append(v * 10.0)
        bounds = (np.array(bounds_lower), np.array(bounds_upper))

        # 3、适应度函数
        def fitness_func(x):
            fitness = []
            for params in x:
                param_dict = {k: v for k, v in zip(param_names, params)}
                param_dict.update(fixed_params) # 固定gamma参数
                try:
                    dist = distribution_class(**param_dict)
                    sf_t = dist.SF(t)
                    if equal_lifetime_t is not None:
                        sf_equal = dist.SF(int(equal_lifetime_t))
                        # 约束2：等寿命点误差
                        equal_constraint = abs(sf_equal - equal_lifetime_sf)
                    else:
                        equal_constraint = 0
                    # 约束1：可靠度
                    sf_constraint = max(0, target_sf - sf_t)
                    # 约束3：超过目标值的部分（权重较低）
                    penalty_over = max(sf_t - target_sf, 0) * 0.1  # 调整权重控制过优化
                    # 总损失：可靠度不达标+等寿命点误差
                    loss = sf_constraint + equal_constraint + penalty_over
                except Exception:
                    loss = 1e6  # 参数无效时惩罚
                fitness.append(loss)
            return np.array(fitness)
        options = {'c1': 0.5, 'c2': 0.3, 'w': 0.9}
        optimizer = GlobalBestPSO(n_particles=8, dimensions=len(param_names), options=options, bounds=bounds)
        best_cost, best_pos = optimizer.optimize(fitness_func, iters=30, verbose=False)

        #5、构造结果
        optimized_params = {k: v for k, v in zip(param_names, best_pos)}
        optimized_params.update(fixed_params)
        optimized_dist = distribution_class(**optimized_params)
        original_dist = distribution_class(**original_params)
        result = {
            "optimized_distribution": optimized_dist,
            "original_pdf": round(original_dist.PDF(t)*1000000,4),
            "optimized_pdf": round(optimized_dist.PDF(t)*1000000,4),
            "original_equal_point_pdf" : round(original_dist.PDF(equal_lifetime_t)*1000000,4) if equal_lifetime_t is not None else None,
            "optimized_equal_point_pdf": round(optimized_dist.PDF(equal_lifetime_t)*1000000,4) if equal_lifetime_t is not None else None
        }
        return result

pso_service: PS0Service = PS0Service()