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
from backend.app.datamanage.crud.crud_repair_interval import repair_interval_dao
from backend.app.lcc.service.cycle_life_service import cycle_life_service
from backend.app.calcu.service.reliability_index_service import reliability_index_service
from backend.app.datamanage.crud.crud_replace import replace_dao
from backend.database.db import async_db_session
from backend.common.exception.errors import DataValidationError
class FindPointService:

    @staticmethod
    async def get_part_by_model(model:str) -> dict[str, Any]:
         async with async_db_session() as db:
              parts = await fit_part_dao.get_by_model(db, model)
              return parts

    # @staticmethod
    # async def find_equal_lifetime_point(model:str,parts:list[str],step_start:float,step_end:float):
    #     """
    #     通过滑动窗口法寻找等寿点
    #     """
    #     # 1、获取所有零部件
    #     if parts is None or len(parts) == 0:
    #         parts = await FindPointService.get_part_by_model(model)
    #     sf_list = []

    #     # 2、获取所有零部件的分布
    #     year_worktimes = await cycle_life_service.year_worktimes(model)
    #     time_point = year_worktimes * 15
    #     for part in parts:
    #         best_distribution = await reliability_index_service._get_best_distribution(model, part)
    #         x = np.linspace(0, time_point, 50000)
    #         sf = best_distribution.SF(x)
    #         sf_list.append(sf)
        
    #     # 3、执行滑动窗口
    #     window_length = year_worktimes
    #     step = int(window_length/10)
    #     x_min, x_max = 1000, time_point
    #     y_min ,y_max = step_start,step_end

    #     # 初始化最佳结果
    #     best_score = -np.inf # 负无穷大
    #     best_window = (0, 0)
    #     best_intersections = []

    #     for x_start in range(x_min, x_max - window_length + 1, step):
    #         x_end = x_start + window_length

    #         # 提取窗口内的x和曲线数据
    #         mask = (x >= x_start) & (x <= x_end)
    #         x_window = x[mask]
    #         sf_window = [sf[mask] for sf in sf_list]

    #         # 检测交点
    #         intersections = []
    #         for i in range(len(sf_list)):
    #             for j in range(i + 1, len(sf_list)):
    #                 F_i = sf_window[i]
    #                 F_j = sf_window[j]

    #                 # 逐点比较，检测交叉
    #                 for k in range(len(x_window) - 1):
    #                     if (y_min <= F_i[k] <= y_max) and (y_min <= F_j[k] <= y_max):
    #                         # 线性插值计算精确交点
    #                         if (F_i[k] - F_j[k]) * (F_i[k + 1] - F_j[k + 1]) < 0:
    #                             # 线性插值计算精确交点
    #                             x0, x1 = x_window[k], x_window[k + 1]
    #                             y0_i, y1_i = F_i[k], F_i[k + 1]
    #                             y0_j, y1_j = F_j[k], F_j[k + 1]

    #                             # 解方程 (y_i - y_j) = 0
    #                             t = (y0_j - y0_i) / ((y1_i - y0_i) - (y1_j - y0_j) + 1e-9)
    #                             x_intersect = x0 + t * (x1 - x0)
    #                             y_intersect = y0_i + t * (y1_i - y0_i)
    #                             intersections.append((x_intersect, y_intersect))

    #         # 统计评分
    #         num_intersections = len(intersections)
    #         if num_intersections == 0:
    #             continue

    #         # 计算密度（单位面积交点数）
    #         window_area = window_length * (y_max - y_min) 
    #         density = num_intersections / window_area
    #         score = num_intersections * density  # 自定义评分公式

    #         # 更新最佳结果
    #         if score > best_score:
    #             best_score = score
    #             best_window = (x_start, x_end)
    #             best_intersections = intersections
        
    #     x_center = (best_window[0] + best_window[1]) / 2
    #     y_center = (y_max+y_min)/2 

    #     # 计算每个交点到中心的平方距离
    #     min_sq_distance = np.inf
    #     closest_point = None
    #     for point in best_intersections:
    #         x_p, y_p = point
    #         sq_dist = (x_p - x_center)**2 + (y_p - y_center)**2
    #         if sq_dist < min_sq_distance:
    #             min_sq_distance = sq_dist
    #             closest_point = point
    #     return {
    #         "parts": parts,
    #         "equal_lifetime_t": int(closest_point[0]) if closest_point else None,
    #         "equal_lifetime_sf": closest_point[1] if closest_point else None,
    #         "time_point": time_point
    #         }

    # @staticmethod
    # async def find_equal_lifetime_point(model: str, parts: list[str], step_start: float, step_end: float):
    #     """
    #     通过滑动窗口法，寻找SF曲线穿过目标SF范围 [SF_min, SF_max] 条数最多的窗口中心作为等寿命点。

    #     :param model: 设备型号
    #     :param parts: 部件列表
    #     :param step_start: SF值下限 (y_min)
    #     :param step_end: SF值上限 (y_max)
    #     :return: 包含等寿命点信息的字典
    #     """
    #     y_min, y_max = step_start, step_end

    #     # 1. 获取所有零部件和SF曲线数据
    #     sf_list = []
    #     year_worktimes = await cycle_life_service.year_worktimes(model)
    #     time_point = year_worktimes * 15 # 总时间范围

    #     # 生成足够密集的时间点 x 轴
    #     num_points = 50000
    #     x = np.linspace(1000, time_point, num_points)
    #     step_size = x[1] - x[0] # 每个时间点的间隔
    
    #     for part in parts:
    #         best_distribution = await reliability_index_service._get_best_distribution(model, part)
    #         sf = best_distribution.SF(x)
    #         sf_list.append(sf)

    #     sf_matrix = np.array(sf_list) 
    
    #     # 2. 定义滑动窗口参数
    #     window_length = year_worktimes # 窗口长度
    
    #     # 滑动步长：使用 x 轴的固定步长（或更稀疏的步长）
    #     # 为了简化计算，我们以 x 轴的索引步进，步长设为与 year_worktimes 对应的索引数 (例如 1/10)
    #     window_size_idx = int(window_length / step_size) 
    #     step_idx = max(1, int(window_size_idx / 10)) # 滑动步长，至少为 1

    #     # 初始化最佳结果
    #     best_crossing_count = -1 
    #     best_window_indices = (0, 0)

    #     # 3. 执行滑动窗口和统计
    
    #     # 预计算：哪些 SF 值在目标范围内 (部件数 x 时间点数)
    #     in_range_mask = (sf_matrix >= y_min) & (sf_matrix <= y_max)

    #     for start_idx in range(0, num_points - window_size_idx + 1, step_idx):
    #         end_idx = start_idx + window_size_idx

    #         # 提取窗口内的布尔掩码 (部件数 x window_size_idx)
    #         window_mask = in_range_mask[:, start_idx:end_idx]
        
    #         # 统计每条 SF 曲线是否在窗口内至少有一个点落在 [y_min, y_max] 范围内
    #         # axis=1: 检查每一行（每条SF曲线）在窗口时间范围内是否有 True
    #         # crossing_parts 是一个布尔数组，形状为 (部件数,)
    #         crossing_parts = np.any(window_mask, axis=1)
        
    #         # 穿过 SF 范围的部件总数
    #         current_crossing_count = np.sum(crossing_parts)

    #         # 更新最佳结果
    #         if current_crossing_count > best_crossing_count:
    #             best_crossing_count = current_crossing_count
    #             best_window_indices = (start_idx, end_idx)

    #     # 4. 确定等寿命点
    #     if best_crossing_count <= 0:
    #         # 没有一条曲线在任何窗口内穿过目标SF范围
    #         return {
    #             "parts": parts, "equal_lifetime_t": None, "equal_lifetime_sf": None, "time_point": time_point
    #         }

    #     # 最佳窗口中心时间 t*
    #     start_idx, end_idx = best_window_indices
    #     center_idx = (start_idx + end_idx) // 2
    #     equal_lifetime_t = x[center_idx]

    #     # 等寿命 SF 值：计算 t* 处所有 SF 值的平均值（或中位数）
    #     sf_at_best_t = sf_matrix[:, center_idx]
    
    #     # 确定哪些部件在 t* 处的 SF 值落在目标范围内，用于计算平均值
    #     valid_sf_mask = (sf_at_best_t >= y_min) & (sf_at_best_t <= y_max)
    
    #     if np.sum(valid_sf_mask) > 0:
    #         # 只对落在目标范围内的有效 SF 值取平均，作为等寿命 SF 值
    #         equal_lifetime_sf = np.mean(sf_at_best_t[valid_sf_mask])
    #     else:
    #         # 如果中心点 t* 没有 SF 值落在 [y_min, y_max] 内，则取所有 SF 值的平均值
    #         # 或者使用 y_min 和 y_max 的平均值作为默认值，这里取所有 SF 平均值作为 fallback
    #         equal_lifetime_sf = np.mean(sf_at_best_t) 
        
    #     # 5. 返回结果
    #     return {
    #         "parts": parts,
    #         "equal_lifetime_t": int(equal_lifetime_t),
    #         "equal_lifetime_sf": float(equal_lifetime_sf),
    #         "time_point": time_point
    #     }

    @staticmethod
    async def _find_replace_part(model: str, part: str):
        async with async_db_session() as db:
            # 检查必换件数据
            replace_data = await replace_dao.get_all_by_model_and_part(db, model, part)
            if replace_data:
                return True
    

    @staticmethod
    async def find_equal_lifetime_point_with_classification(
        model: str, 
        parts: list[str], 
        step_start: float, 
        step_end: float,
        year_worktimes: int,
        repair_result: list[tuple],
        
    ):
        """
        改进版：支持SF分类的等寿命点查找
        """
        y_min, y_max = step_start, step_end
    
        # 1. 获取所有零部件和SF曲线数据
        sf_list = []
        # result = await repair_interval_dao.get_repair_parts_with_names_only_by_model(db, model)
        repair_year = [float(t[0]) for t in repair_result if t[1] == 'C6' or t[1] == '首轮五级修'or t[1] == 'D6']
        if not repair_year:
            raise DataValidationError(
                msg=f"型号{model}的repair_result中未找到'C6'、'首轮五级修'或'D6'修程记录，无法计算time_point。"
                f"当前repair_result: {repair_result}"
            )
        time_point = year_worktimes * repair_year[0] # 总时间范围
        replace_parts =[]

        # 生成足够密集的时间点 x 轴
        num_points = 500000
        x = np.linspace(5000, time_point, num_points)
        step_size = x[1] - x[0] # 每个时间点的间隔
    
        for part in parts:
            best_distribution = await reliability_index_service._get_best_distribution(model, part)
            print("best_distribution",best_distribution)
            sf = best_distribution.SF(x)
            sf_list.append(sf)
            replace = await FindPointService._find_replace_part(model, part)
            if replace is True:
                replace_parts.append(part)

        sf_matrix = np.array(sf_list)
        
        # filtered_replace_parts = [part for part in parts if part not in replace_parts]



    
        # 【新增第1步】在 time_point 处获取 SF 值并分类
        time_point_idx = num_points - 1  # time_point 对应的索引
        sf_at_time_point = sf_matrix[:, time_point_idx]
    
        # 分类逻辑
        classifications = {
            'A': {'indices': [], 'parts': [], 'sf_values': []},
            'B': {'indices': [], 'parts': [], 'sf_values': []},
            'C': {'indices': [], 'parts': [], 'sf_values': []},
            'D': {'indices': [], 'parts': [], 'sf_values': []}
        }
    
        for i, (part, sf_val) in enumerate(zip(parts, sf_at_time_point)):
            print("part",part)
            print("sf_val",sf_val)
            if sf_val >= 0.99 and part not in replace_parts:
                classifications['A']['indices'].append(i)
                classifications['A']['parts'].append(part)
                classifications['A']['sf_values'].append(sf_val)
            elif sf_val >= 0.95 and part not in replace_parts:
                classifications['B']['indices'].append(i)
                classifications['B']['parts'].append(part)
                classifications['B']['sf_values'].append(sf_val)
            elif sf_val < 0.95 and part not in replace_parts:
                classifications['C']['indices'].append(i)
                classifications['C']['parts'].append(part)
                classifications['C']['sf_values'].append(sf_val)
            else:
                classifications['D']['indices'].append(i)
                classifications['D']['parts'].append(part)
                classifications['D']['sf_values'].append(sf_val)
        
        # for part in replace_parts:
        #     classifications['D']['parts'].append(part)

    
        # 【新增第2步】对每个分类分别处理
        results = {}

        # D类：跳过处理
        if classifications['D']['parts']:
            results['D'] = {
                'parts': classifications['D']['parts'],
                'part_count': len(classifications['D']['parts']),
                'sf_at_time_point': None,
                'status': 'skipped',
                'reason': 'Replace parts',
                'equal_lifetime_t': None,
                'equal_lifetime_sf': None,
                "equal_lifetime_t_year": None,
                'time_point': time_point
            }
    
        # A类：跳过处理
        if classifications['A']['parts']:
            results['A'] = {
                'parts': classifications['A']['parts'],
                'part_count': len(classifications['A']['parts']),
                'sf_at_time_point': np.mean(classifications['A']['sf_values']),
                'status': 'skipped',
                'reason': 'High reliability (SF >= 0.99)',
                'equal_lifetime_t': None,
                'equal_lifetime_sf': None,
                "equal_lifetime_t_year": None,
                'time_point': time_point
            }
    
        # B类和C类：调用滑动窗口
        for category in ['B', 'C']:
            parts_in_category = classifications[category]['parts']
            if parts_in_category:
                if len(parts_in_category) == 1:
                    # 只有一个部件，直接返回 None
                    results[category] = {
                        'parts': parts_in_category,
                        'part_count': 1,
                        'sf_at_time_point': classifications[category]['sf_values'][0],
                        'status': 'skipped',
                        'reason': 'Only one part in category',
                        'equal_lifetime_t': None,
                        'equal_lifetime_sf': None,
                        'equal_lifetime_t_year': '偶换',
                        'time_point': time_point,
                        'category': category
                    }
                else:
                    # 只取该分类的 SF 曲线
                    category_indices = classifications[category]['indices']
                    category_sf_matrix = sf_matrix[category_indices, :]
                
                    # 调用原有的滑动窗口逻辑（需要提取为单独函数）
                    result = await FindPointService._sliding_window_search(
                        category_sf_matrix,
                        x,
                        parts_in_category,
                        y_min,
                        y_max,
                        year_worktimes,
                        repair_result
                    )
                    result['category'] = category
                    result['sf_at_time_point'] = np.mean(classifications[category]['sf_values'])
                    result['time_point'] = time_point
                    results[category] = result
        return results
    
    @staticmethod
    async def _sliding_window_search(
            sf_matrix: np.ndarray,
            x: np.ndarray,
            parts: list[str],
            y_min: float,
            y_max: float,
            year_worktimes: float,
            repair_result: list[tuple],
    ):
        """
        滑动窗口搜索逻辑（从原方法提取）
        用于分类后的部件集合进行等寿命点查找

        :param sf_matrix: 分类后的 SF 矩阵 (部件数 x 时间点数)
        :param x: 时间轴数据
        :param parts: 该分类的部件列表
        :param y_min: SF 下限
        :param y_max: SF 上限
        :param year_worktimes: 每年工作时间
        :return: 该分类的等寿命点结果
        """
        # 获取矩阵维度
        num_parts, num_points = sf_matrix.shape

        # 定义滑动窗口参数
        window_length = year_worktimes
        step_size = x[1] - x[0]
        window_size_idx = int(window_length / step_size)
        step_idx = max(1, int(window_size_idx / 20))

        # 
        y_mid = (y_min + y_max) / 2

        # 初始化最佳结果
        # best_crossing_count = -1
        # best_window_indices = (0, 0)
        best_crossing_score = (-1, -1) 
        best_window_indices = (0, 0)

        # 预计算：哪些 SF 值在目标范围内
        # in_range_mask = (sf_matrix >= y_min) & (sf_matrix <= y_max)
        # 区间1：可靠性较低，优先关注 [y_min, y_mid]
        in_range_mask_lower = (sf_matrix >= y_min) & (sf_matrix <= y_mid)
        # 区间2：可靠性较高 [y_mid, y_max]
        in_range_mask_upper = (sf_matrix > y_mid) & (sf_matrix <= y_max)

        # 执行滑动窗口
        for start_idx in range(0, num_points - window_size_idx + 1, step_idx):
            end_idx = start_idx + window_size_idx

            # 提取窗口内的布尔掩码
            # window_mask = in_range_mask[:, start_idx:end_idx]
            window_mask_lower = in_range_mask_lower[:, start_idx:end_idx]
            window_mask_upper = in_range_mask_upper[:, start_idx:end_idx]

            # 统计穿过目标范围的部件
            # crossing_parts = np.any(window_mask, axis=1)
            # current_crossing_count = np.sum(crossing_parts)

            crossing_parts_lower = np.any(window_mask_lower, axis=1)
            current_crossing_count_lower = np.sum(crossing_parts_lower)
            
            crossing_parts_upper = np.any(window_mask_upper, axis=1)
            current_crossing_count_upper = np.sum(crossing_parts_upper)

            current_crossing_score = (current_crossing_count_lower, current_crossing_count_upper)


            # 更新最佳结果
            # if current_crossing_count > best_crossing_count:
            #     best_crossing_count = current_crossing_count
            #     best_window_indices = (start_idx, end_idx)
            # 更新最佳结果：优先保证低可靠性部件（Lower Count）最多，其次是总数最多
            # Python 元组比较 (a, b) > (c, d) 会先比较 a 和 c，再比较 b 和 d
            if current_crossing_score > best_crossing_score:
                best_crossing_score = current_crossing_score
                best_window_indices = (start_idx, end_idx)            

        best_crossing_count = best_crossing_score[0] + best_crossing_score[1]
        # 确定等寿命点
        if best_crossing_count <= 0:
            return {
                "parts": parts,
                "part_count": len(parts),
                "equal_lifetime_t": None,
                "equal_lifetime_sf": None,
                "equal_lifetime_t_year": None,
                "status": "pending"
            }

        # 最佳窗口中心时间
        start_idx, end_idx = best_window_indices
        center_idx = (start_idx + end_idx) // 2
        equal_lifetime_t = x[center_idx]
        # print('equal_lifetime_t',equal_lifetime_t)


        # 计算等寿命 SF 值
        sf_at_best_t = sf_matrix[:, center_idx]
        valid_sf_mask = (sf_at_best_t >= y_min) & (sf_at_best_t <= y_max)

        if np.sum(valid_sf_mask) > 0:
            equal_lifetime_sf = np.mean(sf_at_best_t[valid_sf_mask])
        else:
            equal_lifetime_sf = np.mean(sf_at_best_t)
            
            if equal_lifetime_sf < y_min:
                equal_lifetime_sf = y_min

        repair_levels = [item[0] for item in repair_result if item[0] != 0.0]
        equal_lifetime_t_time = min(repair_levels, key=lambda point: (abs(equal_lifetime_t/year_worktimes - point), -point))
        repair_result_dict = dict(repair_result)
        equal_lifetime_t_year = repair_result_dict.get(equal_lifetime_t_time)
        # equal_lifetime_t_year = next((result[0] for result in repair_result if result[1] == equal_lifetime_t_time))
        equal_lifetime_t = equal_lifetime_t_time*year_worktimes
        print('year_worktimes',year_worktimes)
        print('equal_lifetime_t_year',equal_lifetime_t)

        

        return {
            "parts": parts,
            "part_count": len(parts),
            "equal_lifetime_t": int(equal_lifetime_t),
            "equal_lifetime_sf": float(equal_lifetime_sf),
            "equal_lifetime_t_year": equal_lifetime_t_year,
            "status": "completed"
        }
    

    
find_point_service: FindPointService = FindPointService()