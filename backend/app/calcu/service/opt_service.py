#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : opt_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/5/7 16:38
"""
import matplotlib

matplotlib.use("Agg")  # 设置非交互式后端
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from contextlib import contextmanager
from typing import List, Dict, Any

from reliability.Repairable_systems import optimal_replacement_time
from backend.app.calcu.schema.opt_param import OptPartParam
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.common.exception.errors import DataValidationError
from backend.database.db import async_db_session


@contextmanager
def capture_plots():
    """捕获 matplotlib 图片的 context manager"""
    figures = []
    try:
        # 保存原始的 plt.show 函数
        original_show = plt.show

        def custom_show():
            """自定义的 plt.show 函数，用于捕获图片"""
            # 获取当前所有图片
            for fig_num in plt.get_fignums():
                figure = plt.figure(fig_num)
                # 保存图片到内存
                buffer = BytesIO()
                figure.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
                buffer.seek(0)
                # 转换为 base64
                img_base64 = base64.b64encode(buffer.getvalue()).decode()
                figures.append(img_base64)
                plt.close(figure)  # 关闭图片释放内存

        # 替换 plt.show 为自定义函数
        plt.show = custom_show
        yield figures
    finally:
        # 恢复原始的 plt.show 函数
        plt.show = original_show


class OptService:

    @staticmethod
    async def get_opt_part(*, obj: OptPartParam) -> tuple[float, float]:
        try:
            async with async_db_session() as db:
                fix_part = await fit_part_dao.get_by_model_and_part_and_distribution(
                    db, obj.model, obj.part, "Weibull_2P"
                )
                if fix_part is None:
                    raise DataValidationError(
                        msg=f"找不到型号为 {obj.model} 且部件为 {obj.part} 的Weibull_2P分布数据"
                    )

                opt = optimal_replacement_time(
                    cost_PM=obj.pm_price,
                    cost_CM=obj.cm_price,
                    weibull_alpha=fix_part.alpha,
                    weibull_beta=fix_part.beta,
                    q=0,
                )
                return opt.ORT, opt.min_cost
        except DataValidationError:
            raise
        except Exception as e:
            raise DataValidationError(msg=f"计算最佳更换周期时发生错误: {str(e)}")

    @staticmethod
    async def get_opt_part_with_plots(*, obj: OptPartParam) -> Dict[str, Any]:
        """
        获取最佳更换周期并捕获生成的图片

        Returns:
            Dict 包含:
            - data: tuple[float, float] - (ORT, min_cost)
            - plots: List[str] - base64 编码的图片列表
        """
        try:
            async with async_db_session() as db:
                fix_part = await fit_part_dao.get_by_model_and_part_and_distribution(
                    db, obj.model, obj.part, "Weibull_2P"
                )
                if fix_part is None:
                    raise DataValidationError(
                        msg=f"找不到型号为 {obj.model} 且部件为 {obj.part} 的Weibull_2P分布数据"
                    )

                # 直接调用函数，然后手动获取图片
                opt = optimal_replacement_time(
                    cost_PM=obj.pm_price,
                    cost_CM=obj.cm_price,
                    weibull_alpha=fix_part.alpha,
                    weibull_beta=fix_part.beta,
                    q=0,
                )

                # 手动获取所有图片（reliability 库不会调用 plt.show()）
                plots = []
                for fig_num in plt.get_fignums():
                    figure = plt.figure(fig_num)
                    buffer = BytesIO()
                    figure.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
                    buffer.seek(0)
                    img_base64 = base64.b64encode(buffer.getvalue()).decode()
                    plots.append(img_base64)
                    plt.close(figure)  # 关闭图片释放内存

                return {"data": (opt.ORT, opt.min_cost), "plots": plots}

        except DataValidationError:
            raise
        except Exception as e:
            raise DataValidationError(msg=f"计算最佳更换周期时发生错误: {str(e)}")
        
        
    @staticmethod
    async def get_all_models():
        """
        获取所有型号:获取所有能够计算opt的型号,级联筛选获取所有能满足opt计算的型号
        """
        try:
            async with async_db_session() as db:
                models = await fit_part_dao.get_all_models_for_opt(db)
                return models
        except Exception as e:
            raise DataValidationError(msg=f"获取所有型号时发生错误: {str(e)}")
        
    @staticmethod
    async def get_all_parts(model: str):
        """
        获取所有零部件:获取所有能够计算opt的零部件,级联筛选获取所有能满足opt计算的零部件
        """
        try:
            async with async_db_session() as db:
                parts = await fit_part_dao.get_all_parts_for_opt(db, model)
                return parts
        except Exception as e:
            raise DataValidationError(msg=f"获取所有零部件时发生错误: {str(e)}")


opt_service: OptService = OptService()
