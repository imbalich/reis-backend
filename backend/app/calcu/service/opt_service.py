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
import re
from contextlib import contextmanager
from typing import List, Dict, Any

from reliability.Repairable_systems import optimal_replacement_time
from backend.app.calcu.schema.opt_param import OptPartParam
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.common.exception.errors import DataValidationError
from backend.database.db import async_db_session

# 设置中文字体支持
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False


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
    def _translate_plot_to_chinese(figure):
        """
        将图表中的英文标签翻译为中文并统一图片大小

        Args:
            figure: matplotlib figure 对象
        """
        # 统一设置图片大小
        figure.set_size_inches(8, 6)

        # 翻译映射表（按长度从长到短排序，优先匹配长文本）
        translation_map = [
            # 标题匹配（处理换行符）
            (
                "Optimal replacement interval across a range of CM costs",
                "不同CM成本下的最佳更换间隔",
            ),
            (
                "Optimal replacement interval\nacross a range of CM costs",
                "不同CM成本下的最佳更换间隔",
            ),
            ("Optimal replacement time estimation", "最佳更换时间估算"),
            ("Minimum cost per unit time is", "最小单位时间成本为"),
            ("Optimal replacement time is", "最佳更换时间为"),
            ("Cost per unit time", "单位时间成本"),
            ("Replacement Interval", "更换间隔"),
            ("Replacement time", "更换时间"),
            # X轴标签匹配（处理 LaTeX 格式）
            ("Cost ratio (CM/PM)", "成本比 (CM/PM)"),
            # 匹配 LaTeX 格式：Cost ratio $\left(\frac{CM}{PM}\right)$
            # 注意：需要转义所有反斜杠，因为 \left 和 \frac 中的 \l 和 \f 不是有效转义
            (
                r"Cost ratio.*CM.*PM",
                "成本比 (CM/PM)",
            ),  # 通用匹配（匹配所有包含 Cost ratio、CM 和 PM 的文本）
            # LaTeX 格式匹配（文本注释）
            # 注意：在文本中实际是 $cost_{CM} = $，需要转义 $ 和 { }
            (r"\$cost_\{CM\}\s*=\s*\$", "成本CM ="),
            (r"\$cost_\{PM\}\s*=\s*\$", "成本PM ="),
            (r"\$cost_\{CM\}\$", "成本CM"),
            (r"\$cost_\{PM\}\$", "成本PM"),
            # 普通格式匹配
            ("cost_CM =", "成本CM ="),
            ("costCM =", "成本CM ="),
            ("cost_PM =", "成本PM ="),
            ("costPM =", "成本PM ="),
            ("Interval =", "间隔 ="),
            ("cost_CM", "成本CM"),
            ("costCM", "成本CM"),
            ("cost_PM", "成本PM"),
            ("costPM", "成本PM"),
            ("Interval", "间隔"),
        ]

        # 遍历所有 axes
        for ax in figure.get_axes():
            # 翻译标题
            title = ax.get_title()
            if title:
                # 标准化标题（将换行符替换为空格，便于匹配）
                normalized_title = title.replace("\n", " ").replace("\r", " ")
                translated_title = title
                for en, zh in translation_map:
                    # 标准化匹配文本
                    normalized_en = en.replace("\n", " ").replace("\r", " ")
                    # 判断是否使用正则表达式（包含特殊字符或转义序列）
                    use_regex = (
                        "$" in en or "\\" in en or ".*" in en or "(" in en or ")" in en
                    )

                    if use_regex:
                        # 使用正则表达式匹配
                        pattern = en.replace("$", r"\$") if "$" in en else en
                        try:
                            if re.search(pattern, normalized_title, re.DOTALL):
                                translated_title = re.sub(
                                    pattern, zh, normalized_title, flags=re.DOTALL
                                )
                                break
                        except re.error:
                            continue
                    else:
                        # 字符串匹配（处理换行符）
                        if normalized_en in normalized_title:
                            translated_title = normalized_title.replace(
                                normalized_en, zh
                            )
                            break
                if translated_title != title:
                    ax.set_title(translated_title, fontsize=12)

            # 翻译 x 轴标签
            xlabel = ax.get_xlabel()
            if xlabel:
                translated_xlabel = xlabel

                # 特殊处理：如果包含 "Cost ratio" 和 LaTeX 符号，直接替换整个标签
                if "Cost ratio" in xlabel and "$" in xlabel:
                    translated_xlabel = "成本比（CM/PM）"
                else:
                    for en, zh in translation_map:
                        # 判断是否使用正则表达式
                        use_regex = (
                            "$" in en
                            or "\\" in en
                            or ".*" in en
                            or "(" in en
                            or ")" in en
                        )

                        if use_regex:
                            # 使用正则表达式匹配
                            pattern = en.replace("$", r"\$") if "$" in en else en
                            try:
                                if re.search(pattern, translated_xlabel):
                                    # 如果匹配到 "Cost ratio.*CM.*PM"，直接替换整个标签
                                    if "Cost ratio" in en and ".*" in en:
                                        translated_xlabel = zh
                                    else:
                                        translated_xlabel = re.sub(
                                            pattern, zh, translated_xlabel
                                        )
                                    break
                            except re.error:
                                continue
                        else:
                            if en in translated_xlabel:
                                translated_xlabel = translated_xlabel.replace(en, zh)
                                break

                if translated_xlabel != xlabel:
                    ax.set_xlabel(translated_xlabel, fontsize=11)

            # 翻译 y 轴标签
            ylabel = ax.get_ylabel()
            if ylabel:
                translated_ylabel = ylabel
                for en, zh in translation_map:
                    if "$" in en:
                        pattern = en.replace("$", r"\$")
                        if re.search(pattern, translated_ylabel):
                            translated_ylabel = re.sub(pattern, zh, translated_ylabel)
                    else:
                        if en in translated_ylabel:
                            translated_ylabel = translated_ylabel.replace(en, zh)
                            break
                if translated_ylabel != ylabel:
                    ax.set_ylabel(translated_ylabel, fontsize=11)

            # 获取坐标轴范围，用于调整注释位置
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]

            # 翻译文本注释并调整位置到坐标系内部
            texts_to_remove = []
            texts_to_add = []  # 存储需要添加的新文本

            for text in ax.texts:
                text_str = text.get_text()
                if not text_str:
                    continue

                pos = text.get_position()
                transform = text.get_transform()

                # 翻译文本（支持正则表达式匹配 LaTeX 格式）
                translated = text_str
                for en, zh in translation_map:
                    # 判断是否使用正则表达式（包含 $、\、.* 等特殊字符）
                    use_regex = (
                        "$" in en
                        or "\\" in en
                        or ".*" in en
                        or "(" in en
                        or ")" in en
                        or "{" in en
                    )

                    if use_regex:
                        # 使用正则表达式匹配
                        pattern = en
                        try:
                            if re.search(pattern, translated):
                                translated = re.sub(pattern, zh, translated)
                        except re.error:
                            pass
                    else:
                        if en in translated:
                            translated = translated.replace(en, zh)

                # 获取文本位置（用于判断是否在坐标系外部）
                x_pos, y_pos = pos

                # 判断文本是否在坐标系外部
                # 改进策略：考虑边界情况，如果位置太靠近边界（95%以上），也认为在外部
                is_outside = False
                boundary_threshold = 0.95  # 边界阈值

                if transform == ax.transData:
                    # 数据坐标：检查是否超出范围或太靠近边界
                    x_range = xlim[1] - xlim[0]
                    y_range = ylim[1] - ylim[0]
                    # 如果位置超出范围，或者太靠近右边界或上边界（可能显示在外部）
                    is_outside = (
                        x_pos > xlim[1]
                        or x_pos < xlim[0]
                        or y_pos > ylim[1]
                        or y_pos < ylim[0]
                        or (
                            x_range > 0
                            and (x_pos - xlim[0]) / x_range > boundary_threshold
                        )
                        or (
                            y_range > 0
                            and (y_pos - ylim[0]) / y_range > boundary_threshold
                        )
                    )
                elif transform == ax.transAxes:
                    # axes 坐标（0-1范围）：超出 0-1 范围说明在外部
                    is_outside = x_pos < 0 or x_pos > 1 or y_pos < 0 or y_pos > 1
                else:
                    # 对于其他坐标系统，使用启发式方法
                    # 如果位置值明显超出数据范围，认为在外部
                    max_x = max(abs(xlim[0]), abs(xlim[1]))
                    max_y = max(abs(ylim[0]), abs(ylim[1]))
                    # 如果位置值超过数据范围的 1.5 倍，认为在外部
                    is_outside = abs(x_pos) > max_x * 1.5 or abs(y_pos) > max_y * 1.5

                if is_outside:
                    # 标记为需要移除和重新添加
                    texts_to_remove.append((text, translated))
                else:
                    # 如果已经在内部，只更新文本
                    text.set_text(translated)

            # 处理需要重新定位的文本
            if texts_to_remove:
                # 计算新位置（右上角内部，垂直堆叠）
                new_x = xlim[0] + x_range * 0.65
                base_y = ylim[0] + y_range * 0.95
                line_height = y_range * 0.08  # 每行文本的高度

                for idx, (text, translated) in enumerate(texts_to_remove):
                    new_y = base_y - idx * line_height
                    texts_to_add.append((new_x, new_y, translated))
                    text.remove()

                # 添加新文本在坐标系内部（垂直堆叠）
                for new_x, new_y, translated in texts_to_add:
                    ax.text(
                        new_x,
                        new_y,
                        translated,
                        transform=ax.transData,
                        fontsize=9,
                        verticalalignment="top",
                        horizontalalignment="left",
                        bbox=dict(
                            boxstyle="round", facecolor="wheat", alpha=0.6, pad=0.5
                        ),
                    )

        # 翻译 figure 标题（如果有）
        suptitle = figure._suptitle
        if suptitle:
            title_text = suptitle.get_text()
            if title_text:
                for en, zh in translation_map:
                    if en in title_text:
                        figure.suptitle(title_text.replace(en, zh), fontsize=13)
                        break

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

                # 设置全局图片大小（reliability 库可能会使用这个设置）
                plt.rcParams["figure.figsize"] = [8, 6]

                # 直接调用函数，然后手动获取图片
                opt = optimal_replacement_time(
                    cost_PM=obj.pm_price,
                    cost_CM=obj.cm_price,
                    weibull_alpha=fix_part.alpha,
                    weibull_beta=fix_part.beta,
                    q=0,
                )

                # 手动获取所有图片并中文化处理
                plots = []
                for fig_num in plt.get_fignums():
                    figure = plt.figure(fig_num)

                    # 将图表中的英文标签翻译为中文并统一大小
                    OptService._translate_plot_to_chinese(figure)

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
        返回格式: [("零部件名称", "零部件物料编码"), ...]
        """
        try:
            async with async_db_session() as db:
                # 1. 获取该型号下所有有Weibull_2P分布的零部件编码
                opt_parts = await fit_part_dao.get_parts_for_opt_by_model(db, model)

                # 2. 获取故障表中该型号的所有零部件名称和编码映射
                failure_parts = await failure_dao.get_parts_with_names_by_model(
                    db, model
                )

                # 3. 创建编码到名称的映射字典
                code_to_name = {code: name for name, code in failure_parts}

                # 4. 筛选出既有分布数据又有名称的零部件，返回二元组
                result = []
                for part_code in opt_parts:
                    if part_code in code_to_name:
                        result.append((code_to_name[part_code], part_code))

                return result

        except Exception as e:
            raise DataValidationError(msg=f"获取所有零部件时发生错误: {str(e)}")


opt_service: OptService = OptService()
