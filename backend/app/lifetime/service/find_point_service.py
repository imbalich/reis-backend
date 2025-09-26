#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：equal_lifetime.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/15 14:03
"""

import numpy as np
from typing import Any
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.lcc.service.cycle_life_service import cycle_life_service
from backend.app.calcu.service.reliability_index_service import reliability_index_service
from backend.database.db import async_db_session
class FindPointService:

    @staticmethod
    async def get_part_by_model(model:str) -> dict[str, Any]:
         async with async_db_session() as db:
              parts = await fit_part_dao.get_by_model(db, model)
              return parts

    @staticmethod
    async def find_equal_lifetime_point(model:str,parts:list[str],step_start:float,step_end:float):
        """
        通过滑动窗口法寻找等寿点
        """

        if parts is None or len(parts) == 0:
            parts = await FindPointService.get_part_by_model(model)
        sf_list = []
        year_worktimes = await cycle_life_service.year_worktimes(model)
        time_point = year_worktimes * 15
        for part in parts:
            best_distribution = await reliability_index_service._get_best_distribution(model, part)
            x = np.linspace(0, time_point, 50000)
            sf = best_distribution.SF(x)
            sf_list.append(sf)
        # 滑动窗口参数
        window_length = year_worktimes
        step = int(window_length/10)
        x_min, x_max = 1000, time_point
        y_min ,y_max = step_start,step_end

        # 初始化最佳结果
        best_score = -np.inf # 负无穷大
        best_window = (0, 0)
        best_intersections = []

        for x_start in range(x_min, x_max - window_length + 1, step):
            x_end = x_start + window_length

            # 提取窗口内的x和曲线数据
            mask = (x >= x_start) & (x <= x_end)
            x_window = x[mask]
            sf_window = [sf[mask] for sf in sf_list]

            # 检测交点
            intersections = []
            for i in range(len(sf_list)):
                for j in range(i + 1, len(sf_list)):
                    F_i = sf_window[i]
                    F_j = sf_window[j]

                    # 逐点比较，检测交叉
                    for k in range(len(x_window) - 1):
                        if (y_min <= F_i[k] <= y_max) and (y_min <= F_j[k] <= y_max):
                            # 线性插值计算精确交点
                            if (F_i[k] - F_j[k]) * (F_i[k + 1] - F_j[k + 1]) < 0:
                                # 线性插值计算精确交点
                                x0, x1 = x_window[k], x_window[k + 1]
                                y0_i, y1_i = F_i[k], F_i[k + 1]
                                y0_j, y1_j = F_j[k], F_j[k + 1]

                                # 解方程 (y_i - y_j) = 0
                                t = (y0_j - y0_i) / ((y1_i - y0_i) - (y1_j - y0_j) + 1e-9)
                                x_intersect = x0 + t * (x1 - x0)
                                y_intersect = y0_i + t * (y1_i - y0_i)
                                intersections.append((x_intersect, y_intersect))

            # 统计评分
            num_intersections = len(intersections)
            if num_intersections == 0:
                continue

            # 计算密度（单位面积交点数）
            window_area = window_length * (y_max - y_min) 
            density = num_intersections / window_area
            score = num_intersections * density  # 自定义评分公式

            # 更新最佳结果
            if score > best_score:
                best_score = score
                best_window = (x_start, x_end)
                best_intersections = intersections
        
        x_center = (best_window[0] + best_window[1]) / 2
        y_center = (y_max+y_min)/2 

        # 计算每个交点到中心的平方距离
        min_sq_distance = np.inf
        closest_point = None
        for point in best_intersections:
            x_p, y_p = point
            sq_dist = (x_p - x_center)**2 + (y_p - y_center)**2
            if sq_dist < min_sq_distance:
                min_sq_distance = sq_dist
                closest_point = point
        return {
            "parts": parts,
            "equal_lifetime_t": int(closest_point[0]) if closest_point else None,
            "equal_lifetime_sf": closest_point[1] if closest_point else None,
            "time_point": time_point
            }

    
find_point_service: FindPointService = FindPointService()