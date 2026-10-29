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

class PlotLifetimeService:
    @staticmethod
    async def plot_optimize_result(model, pso_results, t, equal_points: dict, target_sf, code_to_name):
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

    @staticmethod
    def _fig_to_base64(fig):
        '''将 matplotlib 图片转换为 base64'''
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        img_base64 = base64.b64encode(buf.getvalue()).decode()
        plt.close(fig)
        return img_base64

plot_lifetime_service: PlotLifetimeService = PlotLifetimeService()
