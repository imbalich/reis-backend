#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import date

from backend.app.fit.schema.fit_param import CreateFitPartInParam, FitCheckType, FitMethodType
from backend.app.fit.utils.time_utils import dateutils
from backend.app.fit_aaron.service.part_fit_service import part_fit_service
from backend.app.forecast.schema.forecast_param import (
    PartCurveResult,
    PartFitCurvesParam,
    PartForecastParam,
    PartForecastResult,
)
from backend.common.exception import errors
from backend.common.product_config import normalize_product_config_code


class PartForecastService:
    """
    零部件寿命预测服务。

    只根据打标和拟合结果计算期望故障次数，不读取库房、备品和配属。
    """

    # 预测只用这四种。其余分布即使拟合成功也不进入预测。
    _PREDICTION_DISTRIBUTIONS = frozenset({
        "Weibull_2P",
        "Weibull_3P",
        "Lognormal_2P",
        "Lognormal_3P",
        "Gamma_2P",
        "Gamma_3P",
        "Exponential_1P",
        "Exponential_2P",
        "Loglogistic_2P",
        "Loglogistic_3P",
        "Normal_2P"
    })
    _CHECK_FIELD = {
        FitCheckType.BIC: "bic",
        FitCheckType.AICc: "aicc",
        FitCheckType.AD: "ad",
        FitCheckType.Log: "log_likelihood",
    }

    @staticmethod
    async def fit_curves(obj: PartFitCurvesParam) -> list[PartCurveResult]:
        """
        对单个零部件按拟合截止日期调用现行 Aaron 拟合，返回这一次的全部候选曲线。

        是否写入、是否直接使用七日内已有结果，都由 Aaron 拟合决定。
        这里不挑选最优曲线，查询按 BIC 从小到大返回该组的全部分布。
        """
        # 拟合截止日期。Aaron 只用这一天之前的故障。
        input_date = dateutils.validate_and_parse_date(obj.input_date)
        # 空派生码、NULL 和空白统一成 PS00，与 Aaron 的查询口径一致。
        product_config_code = normalize_product_config_code(obj.product_config_code)
        method = obj.method or FitMethodType.MLE
        model = obj.model.strip()
        part = obj.part.strip()
        # 与 Aaron 写入规则一致：今天且极大似然为系统生成，读取时 source 为 False；其余为 True。
        source = not (input_date == date.today() and method == FitMethodType.MLE)
        await part_fit_service.create(
            obj=CreateFitPartInParam(
                model=model,
                product_config_code=product_config_code,
                part=part,
                input_date=input_date.isoformat(),
                method=method,
            )
        )
        # BIC 只决定组内顺序，该组的全部候选曲线都会返回。
        rows = await part_fit_service.get_by_model_and_part(
            model=model,
            part=part,
            input_date=input_date,
            method=method,
            check=FitCheckType.BIC,
            source=source,
            product_config_code=product_config_code,
        )
        return [PartCurveResult.model_validate(row) for row in rows]

    @staticmethod
    def select_curve(
        curves: list[PartCurveResult],
        check: FitCheckType = FitCheckType.BIC,
    ) -> PartCurveResult:
        """
        从拟合得到的全部候选曲线里选出预测用的一条。

        只保留 _PREDICTION_DISTRIBUTIONS 中留下的分布。
        再按 FitCheckType 排序并取出最优曲线。
        BIC、AICc、AD 越小越好；Log-likelihood 越大越好。
        没有可用曲线，或保留下来的曲线都缺少该指标时，拒绝继续预测。
        """
        kept = [
            curve
            for curve in curves
            if curve.distribution in PartForecastService._PREDICTION_DISTRIBUTIONS
        ]
        if not kept:
            raise errors.DataValidationError(msg="限定分布中没有可用曲线")
        field = PartForecastService._CHECK_FIELD[check]
        # 指标为空的曲线不参与比较，避免空值被当成最优。
        scored = [curve for curve in kept if getattr(curve, field) is not None]
        if not scored:
            raise errors.DataValidationError(msg=f"限定分布缺少{check.value}，无法选择曲线")
        # Log-likelihood 越大越好，其余三个指标越小越好。
        reverse = check == FitCheckType.Log
        scored.sort(key=lambda curve: getattr(curve, field), reverse=reverse)
        return scored[0]

    @staticmethod
    async def forecast(obj: PartForecastParam) -> PartForecastResult:
        """
        计算一个零部件在窗口内的期望故障次数。当前尚未实现。

        计划中的计算顺序：
        1. 用 fit_curves 按窗口开始日取得全部候选曲线。窗口开始日同时作为拟合截止日期。
        2. 用 select_curve 从限定分布中按拟合优度选出一条曲线。
        3. 只保留窗口开始日已经在役的零件位置。寿命起点晚于窗口开始日的位置不参与。
        4. 每个位置累加 F(当前年龄 + 窗口运行小时) - F(当前年龄)。
           当前年龄是窗口开始日减去寿命起点后换算得到的运行小时。
        """
        # 数量计算还没有实现，避免未完成时返回空的预测结果。
        raise NotImplementedError("零部件预测尚未实现")


# 供接口层调用。方法都是静态的，这个实例不保存状态。
part_forecast_service = PartForecastService()
