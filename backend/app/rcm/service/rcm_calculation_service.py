#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : rcm_calculation_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : RCM计算服务类
"""

from typing import List, Dict, Any
from datetime import datetime
import math

from backend.database.db import async_db_session
from backend.common.log import log
from backend.app.rcm.crud.crud_rcm_base_data import rcm_base_data_dao
from backend.app.rcm.crud.crud_rcm_calculation_result import rcm_calculation_result_dao


class RCMCalculationService:
    """RCM计算服务类"""

    async def calculate_single_rcm(self, base_data_id: int) -> Dict[str, Any]:
        """计算单条RCM数据"""
        try:
            # 获取基础数据
            async with async_db_session() as db:
                base_data = await rcm_base_data_dao.select_model(db, base_data_id)
                if not base_data:
                    return {
                        "status": "failed",
                        "error": f"基础数据不存在: {base_data_id}",
                        "base_data_id": base_data_id,
                    }

            # 执行计算
            result = await self._execute_rcm_logic(base_data)

            # 保存结果
            await self._save_calculation_result(base_data_id, result)

            return {"status": "success", "base_data_id": base_data_id, "result": result}

        except Exception as e:
            return {"status": "failed", "error": str(e), "base_data_id": base_data_id}

    async def calculate_batch_rcm(
        self, base_data_ids: List[int] = None
    ) -> Dict[str, Any]:
        """批量计算RCM数据"""
        try:
            if base_data_ids is None:
                # 获取所有基础数据ID
                async with async_db_session() as db:
                    from sqlalchemy import select

                    query = select(rcm_base_data_dao.model.id)
                    result = await db.execute(query)
                    base_data_ids = [row[0] for row in result.fetchall()]

            results = []
            for base_data_id in base_data_ids:
                result = await self.calculate_single_rcm(base_data_id)
                results.append(result)

            success_count = len([r for r in results if r["status"] == "success"])
            failed_count = len([r for r in results if r["status"] == "failed"])

            log.info(f"批量计算RCM数据结果: {results}")

            return {
                "status": "success",
                "total": len(results),
                "success": success_count,
                "failed": failed_count,
                "results": results,
            }

        except Exception as e:
            log.error(f"批量计算RCM数据异常: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "total": 0,
                "success": 0,
                "failed": 0,
            }

    async def _execute_rcm_logic(self, base_data) -> Dict[str, Any]:
        """执行RCM计算逻辑"""
        calculation_process = []

        try:
            # 步骤1：判断是否关键故障
            if base_data.is_key_component is None:
                return {
                    "final_result": "非关键部件不参与计算",
                    "calculation_process": "步骤1：is_key_component为空",
                    "calculation_status": "success",
                }

            calculation_process.append(
                f"步骤1：is_key_component={base_data.is_key_component}"
            )

            if base_data.is_key_component:  # 是关键故障
                # 步骤2：判断是否损耗型故障
                if base_data.is_consumable_part is None:
                    return {
                        "final_result": "缺少损耗型故障字段",
                        "calculation_process": "; ".join(calculation_process)
                        + "; 步骤2：is_consumable_part为空",
                        "calculation_status": "success",
                    }

                calculation_process.append(
                    f"步骤2：is_consumable_part={base_data.is_consumable_part}"
                )

                if base_data.is_consumable_part:  # 是损耗型
                    # 步骤7：预防性维修LCC对比
                    if (
                        base_data.preventive_maintenance_cost is None
                        or base_data.lcc_after_improvement is None
                    ):
                        return {
                            "final_result": "缺乏增加预防性维修的LCC或改进后LCC",
                            "calculation_process": "; ".join(calculation_process)
                            + "; 步骤7：缺少预防性维修LCC或改进后LCC",
                            "calculation_status": "success",
                        }

                    calculation_process.append(
                        f"步骤7：预防性维修成本={base_data.preventive_maintenance_cost}, 改进后LCC={base_data.lcc_after_improvement}"
                    )

                    if (
                        base_data.preventive_maintenance_cost
                        < base_data.lcc_after_improvement
                    ):
                        # 步骤8：在线监控判断
                        if base_data.is_online_status is None:
                            return {
                                "final_result": "缺少是否可在线监控字段",
                                "calculation_process": "; ".join(calculation_process)
                                + "; 步骤8：is_online_status为空",
                                "calculation_status": "success",
                            }

                        calculation_process.append(
                            f"步骤8：is_online_status={base_data.is_online_status}"
                        )

                        if base_data.is_online_status:
                            return {
                                "final_result": "实施预防性维修（状态差部件）",
                                "calculation_process": "; ".join(calculation_process),
                                "calculation_status": "success",
                            }
                        else:
                            return {
                                "final_result": "实施修复性维修（故障件）+实施预防性维修（所有产品）",
                                "calculation_process": "; ".join(calculation_process),
                                "calculation_status": "success",
                            }
                    else:
                        return {
                            "final_result": "实施设计改进（所有产品）",
                            "calculation_process": "; ".join(calculation_process)
                            + "; 步骤7：预防性维修成本不优于改进后LCC",
                            "calculation_status": "success",
                        }

                else:  # 不是损耗型
                    # 步骤5：LCC改进对比
                    if (
                        base_data.lcc_before_improvement is None
                        or base_data.lcc_after_improvement is None
                    ):
                        return {
                            "final_result": "缺乏改进前后LCC数据",
                            "calculation_process": "; ".join(calculation_process)
                            + "; 步骤5：缺少改进前后LCC数据",
                            "calculation_status": "success",
                        }

                    calculation_process.append(
                        f"步骤5：改进前LCC={base_data.lcc_before_improvement}, 改进后LCC={base_data.lcc_after_improvement}"
                    )

                    if (
                        base_data.lcc_after_improvement
                        < base_data.lcc_before_improvement
                    ):
                        return {
                            "final_result": "实施设计改进（所有产品）",
                            "calculation_process": "; ".join(calculation_process),
                            "calculation_status": "success",
                        }
                    else:
                        # 步骤6：故障率趋势预警（直接使用数据库字段）
                        calculation_process.append(
                            "步骤6：故障率趋势预警判断（使用数据库字段）"
                        )

                        if base_data.is_trend_rate_limit is None:
                            return {
                                "final_result": "缺少故障率变化趋势是否达到预警值字段",
                                "calculation_process": "; ".join(calculation_process)
                                + "; 步骤6：is_trend_rate_limit为空",
                                "calculation_status": "success",
                            }

                        is_trend_warning = base_data.is_trend_rate_limit
                        calculation_process.append(
                            f"步骤6：故障率趋势预警结果={is_trend_warning}"
                        )

                        if is_trend_warning:
                            return {
                                "final_result": "实施设计改进（所有产品）",
                                "calculation_process": "; ".join(calculation_process),
                                "calculation_status": "success",
                            }
                        else:
                            return {
                                "final_result": "实施修复性维修（故障件）",
                                "calculation_process": "; ".join(calculation_process),
                                "calculation_status": "success",
                            }

            else:  # 不是关键故障
                # 步骤3：故障率趋势判断（根据拟合分布和预警值判断）
                calculation_process.append(
                    "步骤3：故障率趋势判断（根据拟合分布和预警值判断）"
                )

                # 补充具体的故障率趋势判断逻辑
                is_trend_warning = await self._is_trend_warning(base_data)
                calculation_process.append(
                    f"步骤3：故障率趋势预警结果={is_trend_warning}"
                )

                if is_trend_warning:
                    # 进入步骤2（损耗型判断）
                    if base_data.is_consumable_part is None:
                        return {
                            "final_result": "缺少损耗型故障字段",
                            "calculation_process": "; ".join(calculation_process)
                            + "; 步骤2：is_consumable_part为空",
                            "calculation_status": "success",
                        }

                    calculation_process.append(
                        f"步骤2：is_consumable_part={base_data.is_consumable_part}"
                    )

                    # 重复步骤7和步骤5的逻辑
                    if base_data.is_consumable_part:
                        # 步骤7逻辑（重复上面）
                        if (
                            base_data.preventive_maintenance_cost is None
                            or base_data.lcc_after_improvement is None
                        ):
                            return {
                                "final_result": "缺乏增加预防性维修的LCC或改进后LCC",
                                "calculation_process": "; ".join(calculation_process)
                                + "; 步骤7：缺少预防性维修LCC或改进后LCC",
                                "calculation_status": "success",
                            }

                        calculation_process.append(
                            f"步骤7：预防性维修成本={base_data.preventive_maintenance_cost}, 改进后LCC={base_data.lcc_after_improvement}"
                        )

                        if (
                            base_data.preventive_maintenance_cost
                            < base_data.lcc_after_improvement
                        ):
                            if base_data.is_online_status is None:
                                return {
                                    "final_result": "缺少是否可在线监控字段",
                                    "calculation_process": "; ".join(
                                        calculation_process
                                    )
                                    + "; 步骤8：is_online_status为空",
                                    "calculation_status": "success",
                                }

                            calculation_process.append(
                                f"步骤8：is_online_status={base_data.is_online_status}"
                            )

                            if base_data.is_online_status:
                                return {
                                    "final_result": "实施预防性维修（状态差部件）",
                                    "calculation_process": "; ".join(
                                        calculation_process
                                    ),
                                    "calculation_status": "success",
                                }
                            else:
                                return {
                                    "final_result": "实施修复性维修（故障件）+实施预防性维修（所有产品）",
                                    "calculation_process": "; ".join(
                                        calculation_process
                                    ),
                                    "calculation_status": "success",
                                }
                        else:
                            return {
                                "final_result": "实施设计改进（所有产品）",
                                "calculation_process": "; ".join(calculation_process)
                                + "; 步骤7：预防性维修成本不优于改进后LCC",
                                "calculation_status": "success",
                            }
                    else:
                        # 步骤5逻辑（重复上面）
                        if (
                            base_data.lcc_before_improvement is None
                            or base_data.lcc_after_improvement is None
                        ):
                            return {
                                "final_result": "缺乏改进前后LCC数据",
                                "calculation_process": "; ".join(calculation_process)
                                + "; 步骤5：缺少改进前后LCC数据",
                                "calculation_status": "success",
                            }

                        calculation_process.append(
                            f"步骤5：改进前LCC={base_data.lcc_before_improvement}, 改进后LCC={base_data.lcc_after_improvement}"
                        )

                        if (
                            base_data.lcc_after_improvement
                            < base_data.lcc_before_improvement
                        ):
                            return {
                                "final_result": "实施设计改进（所有产品）",
                                "calculation_process": "; ".join(calculation_process),
                                "calculation_status": "success",
                            }
                        else:
                            calculation_process.append(
                                "步骤6：故障率趋势预警判断（使用数据库字段）"
                            )

                            if base_data.is_trend_rate_limit is None:
                                return {
                                    "final_result": "缺少故障率变化趋势是否达到预警值字段",
                                    "calculation_process": "; ".join(
                                        calculation_process
                                    )
                                    + "; 步骤6：is_trend_rate_limit为空",
                                    "calculation_status": "success",
                                }

                            is_trend_warning = base_data.is_trend_rate_limit
                            calculation_process.append(
                                f"步骤6：故障率趋势预警结果={is_trend_warning}"
                            )

                            if is_trend_warning:
                                return {
                                    "final_result": "实施设计改进（所有产品）",
                                    "calculation_process": "; ".join(
                                        calculation_process
                                    ),
                                    "calculation_status": "success",
                                }
                            else:
                                return {
                                    "final_result": "实施修复性维修（故障件）",
                                    "calculation_process": "; ".join(
                                        calculation_process
                                    ),
                                    "calculation_status": "success",
                                }
                else:
                    return {
                        "final_result": "实施修复性维修（故障件）",
                        "calculation_process": "; ".join(calculation_process),
                        "calculation_status": "success",
                    }

        except Exception as e:
            return {
                "final_result": f"计算过程中发生错误: {str(e)}",
                "calculation_process": (
                    "; ".join(calculation_process)
                    if calculation_process
                    else "计算开始"
                ),
                "calculation_status": "failed",
                "error_message": str(e),
            }

    async def _is_trend_warning(self, base_data) -> bool:
        """故障率趋势预警判断 - 用于步骤3，根据拟合分布和预警值判断"""
        try:
            # 1. 根据产品型号和物料编码找到最优拟合
            from backend.app.fit.service.part_fit_service import part_fit_service
            from backend.app.fit.schema.fit_param import FitMethodType, FitCheckType

            best_fit = await part_fit_service.get_best_by_model_and_part(
                model=base_data.product_model,
                part=base_data.component_material_code,
                method=FitMethodType.MLE,
                check=FitCheckType.BIC,
                source=False,
            )

            # 2. 如果没找到分布，计算结束
            if not best_fit:
                return False  # 无寿命曲线，结束流程

            # 3. 根据不同分布分情况讨论
            distribution_name = best_fit.distribution

            # 3.1 Gamma分布：返回否
            if distribution_name in ["Gamma_2P", "Gamma_3P"]:
                return False

            # 3.2 Exponential和Gumbel分布：返回否
            if distribution_name in ["Exponential_1P", "Exponential_2P", "Gumbel_2P"]:
                return False

            # 3.3 需要检查beta值和故障率的分布
            if distribution_name in [
                "Weibull_2P",
                "Weibull_3P",
                "Loglogistic_2P",
                "Loglogistic_3P",
            ]:
                # 检查beta值是否大于1
                beta_value = getattr(best_fit, "beta", None)
                if beta_value is None or beta_value <= 1:
                    return False

                # 检查寿命区间故障率是否超出预计值
                return await self._check_failure_rate_exceeds_expected(
                    best_fit, base_data
                )

            # 3.4 Normal分布：只检查故障率
            if distribution_name in ["Normal_2P", "Lognormal_2P", "Lognormal_3P"]:
                return await self._check_failure_rate_exceeds_expected(
                    best_fit, base_data
                )

            # 3.5 其他分布：默认返回否
            return False

        except Exception as e:
            # 发生异常时返回False，避免影响主流程
            # print(f"故障率趋势预警判断异常: {str(e)}")
            return False

    async def _check_failure_rate_exceeds_expected(self, best_fit, base_data) -> bool:
        """检查寿命区间故障率是否超出预计值"""
        try:
            # 1. 获取预计值（FPMH单位）
            expected_rate = base_data.estimated_failure_rate
            if expected_rate is None:
                return False

            # 2. 获取产品运行信息，计算最大运行小时数
            max_hours = await self._get_max_operating_hours(base_data.product_model)

            # 3. 计算寿命区间最大故障率
            max_failure_rate = await self._calculate_max_failure_rate(
                best_fit, max_hours
            )

            # 4. 比较：寿命区间最大故障率 > 预计值
            # expected_rate单位是FPMH，需要转换为小时故障率（除以10^6）
            expected_rate_per_hour = expected_rate / 1000000
            return round(max_failure_rate, 5) > round(expected_rate_per_hour, 5)

        except Exception as e:
            print(f"故障率比较异常: {str(e)}")
            return False

    async def _get_max_operating_hours(self, product_model: str) -> float:
        """获取产品最大运行小时数（30年）"""
        try:
            # 从产品信息表查询年运行天数和天运行小时数
            from backend.app.datamanage.crud.crud_product import crud_product_dao

            async with async_db_session() as db:
                product = await crud_product_dao.get_by_model(db, product_model)

                if product and product.year_days and product.avg_worktime:
                    annual_operating_days = product.year_days  # 年运行天数
                    daily_operating_hours = product.avg_worktime  # 天运行小时数
                    years = 30  # 30年

                    max_hours = annual_operating_days * daily_operating_hours * years
                    return max_hours
                else:
                    # 如果查询不到产品或数据不完整，使用默认值
                    annual_operating_days = 300  # 年运行天数
                    daily_operating_hours = 16  # 天运行小时数
                    years = 30  # 30年

                    max_hours = annual_operating_days * daily_operating_hours * years
                    return max_hours

        except Exception as e:
            # 异常时使用默认值
            print(f"获取产品运行信息异常: {str(e)}")
            return 144000  # 默认值：30年 * 300天 * 16小时

    async def _calculate_max_failure_rate(self, best_fit, max_hours: float) -> float:
        """计算寿命区间最大故障率"""
        try:
            from reliability.Distributions import (
                Weibull_Distribution,
                Normal_Distribution,
                Lognormal_Distribution,
                Loglogistic_Distribution,
            )
            import numpy as np

            # 1. 创建时间区间（0到最大运行小时数）
            time_points = np.linspace(0, max_hours, num=1000)

            # 2. 根据分布类型计算PDF值
            distribution_name = best_fit.distribution

            if distribution_name in ["Weibull_2P", "Weibull_3P"]:
                # Weibull分布
                alpha = getattr(best_fit, "alpha", 1.0)
                beta = getattr(best_fit, "beta", 1.0)
                gamma = (
                    getattr(best_fit, "gamma", 0.0)
                    if "3P" in distribution_name
                    else 0.0
                )

                # 使用reliability库创建Weibull分布
                if "3P" in distribution_name:
                    distribution = Weibull_Distribution(
                        alpha=alpha, beta=beta, gamma=gamma
                    )
                else:
                    distribution = Weibull_Distribution(alpha=alpha, beta=beta)

                pdf_values = distribution.PDF(xvals=time_points, show_plot=False)

            elif distribution_name in ["Loglogistic_2P", "Loglogistic_3P"]:
                # Loglogistic分布
                alpha = getattr(best_fit, "alpha", 1.0)
                beta = getattr(best_fit, "beta", 1.0)
                gamma = (
                    getattr(best_fit, "gamma", 0.0)
                    if "3P" in distribution_name
                    else 0.0
                )

                # 使用reliability库创建Loglogistic分布
                if "3P" in distribution_name:
                    distribution = Loglogistic_Distribution(
                        alpha=alpha, beta=beta, gamma=gamma
                    )
                else:
                    distribution = Loglogistic_Distribution(alpha=alpha, beta=beta)

                pdf_values = distribution.PDF(xvals=time_points, show_plot=False)

            elif distribution_name in ["Lognormal_2P", "Lognormal_3P"]:
                # Lognormal分布
                mu = getattr(best_fit, "mu", 0.0)
                sigma = getattr(best_fit, "sigma", 1.0)
                gamma = (
                    getattr(best_fit, "gamma", 0.0)
                    if "3P" in distribution_name
                    else 0.0
                )

                # 使用reliability库创建Lognormal分布
                if "3P" in distribution_name:
                    distribution = Lognormal_Distribution(
                        mu=mu, sigma=sigma, gamma=gamma
                    )
                else:
                    distribution = Lognormal_Distribution(mu=mu, sigma=sigma)

                pdf_values = distribution.PDF(xvals=time_points, show_plot=False)

            elif distribution_name == "Normal_2P":
                # Normal分布
                mu = getattr(best_fit, "mu", 0.0)
                sigma = getattr(best_fit, "sigma", 1.0)

                # 使用reliability库创建Normal分布
                distribution = Normal_Distribution(mu=mu, sigma=sigma)
                pdf_values = distribution.PDF(xvals=time_points, show_plot=False)

            else:
                # 其他分布暂不支持
                return 0.0

            # 3. 返回PDF值列表中的最大值
            return float(np.max(pdf_values)) if len(pdf_values) > 0 else 0.0

        except Exception as e:
            print(f"计算最大故障率异常: {str(e)}")
            return 0.0

    async def _save_calculation_result(self, base_data_id: int, result: Dict[str, Any]):
        """保存计算结果到数据库"""
        async with async_db_session() as db:
            # 清除旧结果
            await rcm_calculation_result_dao.clear_by_base_data_id(db, base_data_id)

            # 保存新结果
            result_data = {
                "base_data_id": base_data_id,
                "final_result": result["final_result"],
                "calculation_process": result.get("calculation_process", ""),
                "calculation_status": result.get("calculation_status", "success"),
                "error_message": result.get("error_message"),
                "calculation_time": datetime.now(),
            }

            await rcm_calculation_result_dao.create(db, result_data)

    async def get_calculation_result(self, base_data_id: int):
        """获取计算结果"""
        async with async_db_session() as db:
            return await rcm_calculation_result_dao.get_by_base_data_id(
                db, base_data_id
            )

    async def get_calculation_history(self, limit: int = 100):
        """获取计算历史"""
        async with async_db_session() as db:
            return await rcm_calculation_result_dao.get_calculation_history(db, limit)

    async def get_latest_calculation_results(self) -> List[Dict[str, Any]]:
        """获取最新的RCM计算结果"""
        async with async_db_session() as db:
            results = await rcm_calculation_result_dao.get_latest_results(db)
            return await self._convert_results_to_api_format(results)

    async def get_calculation_results_with_filters(
        self,
        product_model: str = None,
        component_name: str = None,
        component_material_code: str = None,
        failure_mode: str = None,
        final_result: str = None,
        calculation_status: str = None,
        calculation_time_start: datetime = None,
        calculation_time_end: datetime = None,
    ) -> List[Dict[str, Any]]:
        """根据过滤条件获取RCM计算结果"""
        async with async_db_session() as db:
            stmt = await rcm_calculation_result_dao.get_results_with_filters(
                db,
                product_model=product_model,
                component_name=component_name,
                component_material_code=component_material_code,
                failure_mode=failure_mode,
                final_result=final_result,
                calculation_status=calculation_status,
                calculation_time_start=calculation_time_start,
                calculation_time_end=calculation_time_end,
            )
            result = await db.execute(stmt)
            results = result.scalars().all()
            return await self._convert_results_to_api_format(results)

    async def get_calculation_statistics(self) -> Dict[str, Any]:
        """获取RCM计算统计信息"""
        async with async_db_session() as db:
            return await rcm_calculation_result_dao.get_calculation_statistics(db)

    async def _convert_results_to_api_format(self, results) -> List[Dict[str, Any]]:
        """将计算结果转换为API格式"""
        api_results = []
        for result in results:
            # 获取关联的基础数据
            async with async_db_session() as db:
                base_data = await rcm_base_data_dao.select_model(
                    db, result.base_data_id
                )

            api_result = {
                "id": result.id,
                "base_data_id": result.base_data_id,
                "product_model": base_data.product_model if base_data else "",
                "component_name": base_data.component_name if base_data else "",
                "component_material_code": (
                    base_data.component_material_code if base_data else ""
                ),
                "failure_mode": base_data.failure_mode if base_data else None,
                "final_result": result.final_result,
                "calculation_status": result.calculation_status,
                "calculation_time": result.calculation_time,
                "created_time": result.created_time,
                "updated_time": result.updated_time,
            }
            api_results.append(api_result)

        return api_results

    async def get_select(
        self,
        product_model: str = None,
        component_name: str = None,
        component_material_code: str = None,
        final_result: str = None,
    ):
        """获取查询语句，用于分页查询"""
        async with async_db_session() as db:
            return await rcm_calculation_result_dao.get_results_with_filters(
                db,
                product_model=product_model,
                component_name=component_name,
                component_material_code=component_material_code,
                final_result=final_result,
            )


rcm_calculation_service = RCMCalculationService()
