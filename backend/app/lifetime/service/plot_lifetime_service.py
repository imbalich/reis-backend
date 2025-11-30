#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：plot_lifetime_service.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/20 14:03
"""
import io
import base64
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm  # 正确导入FontProperties
from backend.app.calcu.service.distribute_service import distribute_service
import os

# 同样，构建字体路径
base_dir = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.join(base_dir,'..', '..', '..',  'static', 'msyh.ttc')

# 验证字体文件是否存在
if not os.path.exists(font_path):
    print(f"警告：字体文件不存在于 {font_path}")
    # 可以添加备用方案
else:
    # print(f"使用字体文件: {font_path}")
    pass


# 设置中文字体支持
font_prop = fm.FontProperties(fname=font_path)
# plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
# plt.rcParams['font.family'] = ['sans-serif'] # 设置字体家族
# plt.rcParams['font.sans-serif'] = [plt.FontProperties(fname=font_path).get_name()] # 指定中文字体
# plt.rcParams['axes.unicode_minus'] = False

class PlotLifetimeService:
    @staticmethod
    async def plot_optimize_result(model,pso_results,t,target_sf,code_to_name,equal_lifetime_t,equal_lifetime_sf,year_worktimes):
        '''绘制优化结果'''
        fig, ax = plt.subplots(figsize=(8, 6))
        x = np.linspace(0, t, 1000)
        for part,pso_result in pso_results.items():
            if 'optimized_distribution' in pso_result:
                if pso_result['original_equal_point_pdf'] is not None and pso_result['optimized_equal_point_pdf']-pso_result['original_equal_point_pdf'] < 0:
                    distribution = pso_result['optimized_distribution']
                    y = distribution.SF(x)
                    ax.plot(x, y, label=code_to_name[part])
                elif pso_result['original_equal_point_pdf'] is None and pso_result['optimized_pdf']-pso_result['original_pdf'] < 0:
                    distribution = pso_result['optimized_distribution']
                    y = distribution.SF(x)
                    ax.plot(x, y, label=code_to_name[part])
        if equal_lifetime_t is not None:
            ax.plot(equal_lifetime_t, equal_lifetime_sf, 'ro', markersize=4, label=f'等寿命点: (t={round(equal_lifetime_t/year_worktimes,2)}, sf={equal_lifetime_sf:.4f})')
        ax.set_title(f"优化寿命曲线-{model}(时间截止点t0 = {round(t/year_worktimes,2)}(年))",fontproperties=font_prop)
        ax.set_xlabel("时间", fontproperties=font_prop)
        ax.set_ylabel("SF", fontproperties=font_prop)
        ax.set_xlim(0, t)
        ax.set_ylim(target_sf, 1)
        ax.legend(prop=font_prop)
        img_base64 = PlotLifetimeService._fig_to_base64(fig)
        return [img_base64]  
                    

    @staticmethod
    async def plot_original_result(model,parts,t,target_sf,pso_results,year_worktimes):
        '''绘制原始结果'''
        fig, ax = plt.subplots(figsize=(8, 6))
        x = np.linspace(0, t+10000, 1000)
        for part,pso_result in pso_results.items():
            original_distribution = pso_result['original_distribution']
            y = original_distribution.SF(x)
            ax.plot(x, y)
        ax.set_title(f"原始寿命曲线-{model}(时间截止点t0 = {round(t/year_worktimes,2)}(年))", fontproperties=font_prop)
        ax.set_xlabel("时间",fontproperties=font_prop)
        ax.set_ylabel("SF")
        ax.set_xlim(0, t)
        ax.set_ylim(0.7, 1)
        img_base64 = PlotLifetimeService._fig_to_base64(fig)
        return [img_base64]
            
    
    @staticmethod
    def _fig_to_base64(fig):
        '''将 matplotlib 图片转换为 base64'''
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        img_base64 = base64.b64encode(buf.getvalue()).decode()
        plt.close(fig)
        return img_base64
    

    @staticmethod
    async def plot_optimize_result(model, pso_results, t, equal_points: dict, target_sf, code_to_name):
        """
        绘制优化结果
        pso_results: dict keyed by part, 包含 optimized_distribution / optimized_pdf 等字段
        equal_points: dict, e.g. {'B': (t_b, sf_b), 'C': (t_c, sf_c)}
        """
        fig, ax = plt.subplots(figsize=(12, 10))
        # 安全计算绘图 x 轴上限：优先使用 equal_points 中的时间点（取最大）
        # if equal_points:
        #     # 期望 equal_points.values() 中每项为 (t_point, sf_point)
        #     t_candidates = [pair[0] for pair in equal_points.values() if pair and pair[0] is not None]
        #     x_max = max(t_candidates) if t_candidates else 1
        # else:
        #     x_max = 1

        # # 保证上限至少为 1，避免 np.linspace 参数异常
        # x_max = max(1, int(x_max))
        # x = np.linspace(0, x_max, 1000)
        x = np.linspace(0, t+10000, 1000)
        for part, pso_result in pso_results.items():
            # 只绘制优化后生成的分布
            if 'optimized_distribution' in pso_result:
                distribution = pso_result['optimized_distribution']
                y = distribution.SF(x)
                label = code_to_name.get(part, part)
                ax.plot(x, y, label=label)

        # 绘制所有 category 的等寿命点（如果存在）
        for cat_label, (repair_level,t_point, sf_point) in equal_points.items():
            if t_point is not None:
                ax.plot(t_point, sf_point, marker='o', label=f'等寿命点 {cat_label}: (t={repair_level}, sf={sf_point:.4f})')

        ax.set_title(f"优化寿命曲线-{model}", fontproperties=font_prop)
        ax.set_xlabel("时间", fontproperties=font_prop)
        ax.set_ylabel("SF", fontproperties=font_prop)
        # y 轴下限为 target_sf，便于显示优化上效果
        ax.set_xlim(0, t+10000)
        ax.set_ylim(target_sf-0.01, 1)
        ax.legend(prop=font_prop)
        img_base64 = PlotLifetimeService._fig_to_base64(fig)
        return [img_base64]

    # @staticmethod
    # async def plot_original_result(model, parts, t, target_sf, pso_results, year_worktimes):
    #     """
    #     绘制原始结果，并按分类用不同颜色/标注显示 A/B/C
    #     pso_results：包含每个 part 的 'original_distribution' 和 'category' 字段
    #     """
    #     fig, ax = plt.subplots(figsize=(12, 10))
    #     x = np.linspace(0, t, 1000)

    #     # 颜色映射
    #     category_colors = {
    #         'A': 'green',
    #         'B': 'orange',
    #         'C': 'red',
    #         'unknown': 'gray'
    #     }
    #     # 为 legend 准备 handle
    #     plotted_categories = set()

    #     for part in parts:
    #         part_key = part
    #         pso_result = pso_results.get(part_key)
    #         if not pso_result:
    #             # 如果没有预先计算的记录，则画原始分布（灰色）
    #             try:
    #                 dist = await distribute_service.get_part_distribution(model, part_key)
    #             except Exception:
    #                 continue
    #             y = dist.SF(x)
    #             ax.plot(x, y, color='gray', alpha=0.6)
    #             if 'unknown' not in plotted_categories:
    #                 ax.plot([], [], color='gray', label='unknown')
    #                 plotted_categories.add('unknown')
    #             continue

    #         original_distribution = pso_result.get('original_distribution')
    #         category = pso_result.get('category', 'unknown')
    #         color = category_colors.get(category, category_colors['unknown'])
    #         y = original_distribution.SF(x)
    #         ax.plot(x, y, color=color, alpha=0.8)
    #         if category not in plotted_categories:
    #             ax.plot([], [], color=color, label=f'Category {category}')
    #             plotted_categories.add(category)

    #     ax.set_title(f"原始寿命曲线-{model}(时间截止点t0 = {round(t / year_worktimes, 2)}(年))", fontproperties=font_prop)
    #     ax.set_xlabel("时间", fontproperties=font_prop)
    #     ax.set_ylabel("SF", fontproperties=font_prop)
    #     ax.set_xlim(0, t)
    #     ax.set_ylim(0.7, 1)
    #     ax.legend(prop=font_prop)
    #     img_base64 = PlotLifetimeService._fig_to_base64(fig)
    #     return [img_base64]
    
    @staticmethod
    async def plot_original_result(model, pso_results, t, target_sf, code_to_name, year_worktimes):
        """
        绘制优化结果
        pso_results: dict keyed by part, 包含 optimized_distribution / optimized_pdf 等字段
        equal_points: dict, e.g. {'B': (t_b, sf_b), 'C': (t_c, sf_c)}
        """
        fig, ax = plt.subplots(figsize=(12, 10))
        # 安全计算绘图 x 轴上限：优先使用 equal_points 中的时间点（取最大）
        x = np.linspace(0, t+10000, 1000)
        for part, pso_result in pso_results.items():
            # 只绘制优化后生成的分布
            # if 'optimized_distribution' in pso_result:
            #     distribution = pso_result['original_distribution']
            #     y = distribution.SF(x)
            #     label = code_to_name.get(part, part)
            #     ax.plot(x, y, label=label)
            distribution = pso_result['original_distribution']
            y = distribution.SF(x)
            label = code_to_name.get(part, part)
            ax.plot(x, y, label=label)

        ax.set_title(f"原始寿命曲线-{model}(时间截止点t0 = {round(t / year_worktimes, 2)}(年))", fontproperties=font_prop)
        ax.set_xlabel("时间", fontproperties=font_prop)
        ax.set_ylabel("SF", fontproperties=font_prop)
        ax.set_xlim(0, t+10000)
        # y 轴下限为 target_sf，便于显示优化上效果
        ax.set_ylim(0.85, 1)
        ax.legend(prop=font_prop)
        img_base64 = PlotLifetimeService._fig_to_base64(fig)
        return [img_base64]
    

plot_lifetime_service: PlotLifetimeService = PlotLifetimeService()