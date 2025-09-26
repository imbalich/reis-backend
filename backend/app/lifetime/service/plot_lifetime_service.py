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

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class PlotLifetimeService:
    @staticmethod
    async def plot_optimize_result(model,pso_results,t,target_sf,code_to_name,equal_lifetime_t,equal_lifetime_sf):
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
            ax.plot(equal_lifetime_t, equal_lifetime_sf, 'ro', markersize=4, label=f'等寿命点: (t={equal_lifetime_t}, sf={equal_lifetime_sf:.4f})')
        else:
            ax.plot([], [], ' ', label='没有找到等寿命点')
        ax.set_title(f"优化寿命曲线-{model}(时间截止点t0 = {t})")
        ax.set_xlabel("时间")
        ax.set_ylabel("SF")
        ax.set_xlim(0, t)
        ax.set_ylim(target_sf, 1)
        ax.legend()
        img_base64 = PlotLifetimeService._fig_to_base64(fig)
        return [img_base64]  
                    

    @staticmethod
    async def plot_original_result(model,parts,t,target_sf,pso_results):
        fig, ax = plt.subplots(figsize=(8, 6))
        x = np.linspace(0, t, 1000)
        for part,pso_result in pso_results.items():
            original_distribution = pso_result['original_distribution']
            y = original_distribution.SF(x)
            ax.plot(x, y)
        ax.set_title(f"原始寿命曲线-{model}(时间截止点t0 = {int(t)})")
        ax.set_xlabel("时间")
        ax.set_ylabel("SF")
        ax.set_xlim(0, t)
        ax.set_ylim(0.7, 1)
        img_base64 = PlotLifetimeService._fig_to_base64(fig)
        return [img_base64]
            
    
    @staticmethod
    def _fig_to_base64(fig):
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        img_base64 = base64.b64encode(buf.getvalue()).decode()
        plt.close(fig)
        return img_base64

plot_lifetime_service: PlotLifetimeService = PlotLifetimeService()