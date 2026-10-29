#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

import numpy as np
from sqlalchemy import select

from backend.app.calcu.schema.distribute_param import DistributionParams
from backend.app.calcu.service.distribute_service import DistributeService
from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.model.failure import Failure  # 预测模块仅面向铁路(评审S7)
from backend.app.fit.schema.fit_param import CreateFitPartInParam, FitCheckType, FitMethodType
from backend.app.fit.utils.convert_model import convert_to_total_quantity, get_ebom_tree_with_parents
from backend.app.fit.utils.time_utils import dateutils
from backend.app.fit_aaron.service.part_fit_service import part_fit_service
from backend.app.forecast.schema.forecast_param import (
    PartCurveResult,
    PartFitCurvesParam,
    PartForecastParam,
    PartForecastResult,
    PartForecastTrace,
    PartForecastUnit,
)
from backend.common.exception import errors
from backend.common.product_config import (
    apply_product_config_code_filter,
    normalize_product_config_code,
)
from backend.database.db import async_db_session


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
    # 上线日 = 发运日与生产日期中较早者 + 90 天。
    _ONLINE_LEAD_DAYS = 90
    _SITUATION_IN_SERVICE = "窗口前已上线"
    _SITUATION_ENTERED = "窗口内上线"
    _SITUATION_SKIPPED = "上线晚于窗口结束"

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
        # 先丢掉不在预测名单里的分布，剩下的才参与排序。
        kept = [
            curve
            for curve in curves
            if curve.distribution in PartForecastService._PREDICTION_DISTRIBUTIONS
        ]
        if not kept:
            raise errors.DataValidationError(msg="限定分布中没有可用曲线")
        # 把检验类型对应到曲线上的字段：BIC、AICc、AD 或对数似然。
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
        用选定曲线预测一个零部件在 A 到 B 之间的期望故障次数。

        按单台产品计算，不按零件位置展开。上线日是发运日与生产日期中较早者再加 90 天。
        上线日早于 A：A、B 的运行小时都从该上线日起算。
        上线日介于 A 和 B：A 点运行小时为 0，B 点从上线日起算。
        上线日晚于 B：该产品跳过。
        每台产品贡献选定分布在这两个运行小时上的 CDF 差值，再对全部产品求和。
        求和后再乘该物料在当前 BOM 中的用量。用量为 0 或没有 BOM 时，预测次数为 0。
        拟合截止日期使用 A。
        """
        if not obj.input_date or not obj.end_date:
            raise errors.DataValidationError(msg="预测需要窗口开始日和结束日")
        # A 是窗口开始日，也是拟合截止日期。B 是窗口结束日。
        point_a = dateutils.validate_and_parse_date(obj.input_date)
        point_b = dateutils.validate_and_parse_date(obj.end_date)
        if point_b < point_a:
            raise errors.DataValidationError(msg="窗口结束日不能早于开始日")
        product_config_code = normalize_product_config_code(obj.product_config_code)
        model = obj.model.strip()
        part = obj.part.strip()
        # 一台产品走一天，折算成多少运行小时。
        hours_per_day = await PartForecastService._hours_per_day(model, product_config_code)
        # 只用 A 之前的故障拟合，取出这一次的全部候选曲线。
        curves = await PartForecastService.fit_curves(
            PartFitCurvesParam(
                model=model,
                part=part,
                product_config_code=product_config_code,
                input_date=point_a.isoformat(),
            )
        )
        # 从限定分布里按默认的 BIC 选出一条，再还原成可计算的分布函数。
        curve = PartForecastService.select_curve(curves)
        distribution = await PartForecastService._distribution_from_curve(curve)
        # 产品编号和上线日。后面按这个日期判断每台产品落在窗口的哪一种情况。
        online_by_product = await PartForecastService._product_online_dates(model, product_config_code)
        units, start_hours, end_hours = PartForecastService._classify_units(
            online_by_product, point_a, point_b, hours_per_day
        )
        # 只给参与预测的产品计算 CDF 差值，并写回对应明细。被跳过的保持为空。
        differences = PartForecastService._cdf_differences(distribution, start_hours, end_hours)
        PartForecastService._fill_contributions(units, differences)
        product_quantity = float(sum(differences))
        # BOM 是这个型号上该物料装几只，各台产品相同，所以在总和上乘一次。
        bom_quantity = await PartForecastService._bom_quantity(model, product_config_code, part)
        quantity = product_quantity * bom_quantity
        trace = PartForecastService._build_trace(
            curve.distribution, hours_per_day, bom_quantity, product_quantity, units
        )
        return PartForecastResult(
            model=model,
            part=part,
            product_config_code=product_config_code,
            input_date=point_a,
            end_date=point_b,
            quantity=quantity,
            # 台数只统计没有被跳过的产品，一台产品只计一次。
            unit_count=len(start_hours),
            trace=trace,
            units=units,
        )

    @staticmethod
    async def _hours_per_day(model: str, product_config_code: str) -> float:
        """每天平均运行小时 = 年运行天数 × 日均工作时间 / 365。"""
        async with async_db_session() as db:
            # 同一型号加派生码只取一条产品参数，用来折算运行小时。
            product = await product_dao.railway.get_by_model(db, model, product_config_code)
        if product is None or not product.year_days or not product.avg_worktime:
            raise errors.DataValidationError(msg=f"型号 {model} 缺少年运行天数或日均工作时间")
        return product.year_days * product.avg_worktime / 365

    @staticmethod
    async def _bom_quantity(model: str, product_config_code: str, part: str) -> int:
        """
        当前有效 BOM 里，一台产品安装该物料的数量。

        用量按父子层级相乘后再相加。没有 BOM 或算出来是 0 时返回 0，预测次数随之变成 0。
        """
        async with async_db_session() as db:
            # 带上父级，才能把上层组件的用量乘进这只物料。
            ebom_rows = await get_ebom_tree_with_parents(db, model, product_config_code, part)
        return convert_to_total_quantity(ebom_rows, part)

    @staticmethod
    def _classify_units(
        online_by_product: dict[str, date],
        point_a: date,
        point_b: date,
        hours_per_day: float,
    ) -> tuple[list[PartForecastUnit], list[float], list[float]]:
        """
        给每台产品标上窗口情况。

        返回明细、参与产品的 A 点运行小时、参与产品的 B 点运行小时。
        后两个列表与明细里未被跳过的产品顺序一致。
        """
        units: list[PartForecastUnit] = []
        start_hours: list[float] = []
        end_hours: list[float] = []
        for product_number, online in sorted(online_by_product.items()):
            window = PartForecastService._window_hours(online, point_a, point_b, hours_per_day)
            if window is None:
                units.append(
                    PartForecastUnit(
                        product_number=product_number,
                        online_date=online,
                        situation=PartForecastService._SITUATION_SKIPPED,
                    )
                )
                continue
            situation = (
                PartForecastService._SITUATION_ENTERED
                if online > point_a
                else PartForecastService._SITUATION_IN_SERVICE
            )
            units.append(
                PartForecastUnit(
                    product_number=product_number,
                    online_date=online,
                    situation=situation,
                    hours_at_start=window[0],
                    hours_at_end=window[1],
                )
            )
            start_hours.append(window[0])
            end_hours.append(window[1])
        return units, start_hours, end_hours

    @staticmethod
    def _fill_contributions(units: list[PartForecastUnit], differences: list[float]) -> None:
        """把乘 BOM 前的 CDF 差值写进参与预测的产品。被跳过的产品保持为空。"""
        difference_index = 0
        for unit in units:
            if unit.situation == PartForecastService._SITUATION_SKIPPED:
                continue
            unit.contribution = differences[difference_index]
            difference_index += 1

    @staticmethod
    def _build_trace(
        distribution: str,
        hours_per_day: float,
        bom_quantity: int,
        product_quantity: float,
        units: list[PartForecastUnit],
    ) -> PartForecastTrace:
        """汇总三类台数，并写下会改变结果含义的卡点。"""
        in_service_count = sum(unit.situation == PartForecastService._SITUATION_IN_SERVICE for unit in units)
        entered_count = sum(unit.situation == PartForecastService._SITUATION_ENTERED for unit in units)
        skipped_count = sum(unit.situation == PartForecastService._SITUATION_SKIPPED for unit in units)
        notes: list[str] = []
        if bom_quantity == 0:
            notes.append("BOM用量为0，预测次数变成0")
        if in_service_count + entered_count == 0:
            notes.append("没有产品落在窗口内")
        return PartForecastTrace(
            distribution=distribution,
            hours_per_day=hours_per_day,
            bom_quantity=bom_quantity,
            product_quantity=product_quantity,
            in_service_count=in_service_count,
            entered_during_window_count=entered_count,
            skipped_count=skipped_count,
            notes=notes,
        )

    @staticmethod
    async def _product_online_dates(model: str, product_config_code: str) -> dict[str, date]:
        """
        每台产品的上线日，键是产品编号。

        发运日取新造发运的出厂日期，生产日期取故障表中的新造日期。
        两者都有时取较早者，只有一个时用那一个，然后再加 90 天。
        """
        # 产品编号 -> 发运日与生产日期中较早的那天，此时还没加 90 天。
        bases: dict[str, date] = {}
        async with async_db_session() as db:
            # 发运日只取新造，并且排除 0000 开头的编号。同一产品有多条时保留最早的出厂日期。
            despatches = await despatch_dao.get_despatchs_by_model(db, model, product_config_code)
            for row in despatches:
                shipped = row.life_cycle_time
                identifier = (row.identifier or "").strip()
                if not identifier or shipped is None:
                    continue
                current = bases.get(identifier)
                if current is None or shipped < current:
                    bases[identifier] = shipped
            # 生产日期来自故障表的新造日期。这里不按零部件过滤，因为新造日期属于整台产品。
            where_list = [
                Failure.product_model == model,
                Failure.manufacturing_date.isnot(None),
                Failure.product_number.isnot(None),
            ]
            apply_product_config_code_filter(where_list, Failure.product_config_code, product_config_code)
            rows = await db.execute(select(Failure.product_number, Failure.manufacturing_date).where(*where_list))
            for product_number, manufacturing_date in rows.all():
                produced = PartForecastService._parse_day(manufacturing_date)
                identifier = (product_number or "").strip()
                if not identifier or produced is None:
                    continue
                # 比已有发运日更早才替换，这样两个日期同时存在时留下较早者。
                current = bases.get(identifier)
                if current is None or produced < current:
                    bases[identifier] = produced
        lead = timedelta(days=PartForecastService._ONLINE_LEAD_DAYS)
        # 上线日比基准日晚 90 天。没有发运也没有新造日期的产品不会出现在这里。
        return {identifier: base + lead for identifier, base in bases.items()}

    @staticmethod
    def _window_hours(
        online: date,
        point_a: date,
        point_b: date,
        hours_per_day: float,
    ) -> tuple[float, float] | None:
        """按上线日相对 A、B 的位置，返回这两个点的运行小时。晚于 B 的产品返回空。"""
        # 情况三：上线日晚于 B，窗口内还没有这台产品，不可能发生故障。
        if online > point_b:
            return None
        # 情况二：上线日落在 A 和 B 之间。A 点还没上线，运行小时按 0。
        if online > point_a:
            hours_a = 0.0
        # 情况一：上线日早于或等于 A。A、B 都从该上线日起算已运行小时。
        else:
            hours_a = (point_a - online).days * hours_per_day
        # B 点运行小时。上线日等于 B 时这里是 0，差值为 0，产品仍算参与。
        hours_b = (point_b - online).days * hours_per_day
        return hours_a, hours_b

    @staticmethod
    async def _distribution_from_curve(curve: PartCurveResult):
        """把选定曲线的参数还原成可计算 CDF 的分布。"""
        params = DistributionParams(
            distribution=curve.distribution,
            alpha=curve.alpha,
            beta=curve.beta,
            gamma=curve.gamma,
            alpha_1=curve.alpha_1,
            beta_1=curve.beta_1,
            alpha_2=curve.alpha_2,
            beta_2=curve.beta_2,
            proportion_1=curve.proportion_1,
            ds=curve.ds,
            mu=curve.mu,
            sigma=curve.sigma,
            lambda_=curve.lambda_,
            log_likelihood=curve.log_likelihood,
            aicc=curve.aicc,
            bic=curve.bic,
            ad=curve.ad,
            optimizer=curve.optimizer,
        )
        # 按分布名称把 alpha、beta、lambda 等参数交给对应的分布类。
        distribution = await DistributeService.get_distribution_by_params(params)
        if distribution is None:
            raise errors.DataValidationError(msg=f"无法用 {curve.distribution} 的参数构造分布")
        return distribution

    @staticmethod
    def _cdf_differences(distribution, start_hours: list[float], end_hours: list[float]) -> list[float]:
        """每台参与产品的 CDF(B) - CDF(A)。没有产品时返回空列表。"""
        if not start_hours:
            return []
        # 两个数组一一对应同一台产品：起点运行小时上的 CDF，和终点运行小时上的 CDF。
        start_cdf = np.atleast_1d(distribution.CDF(xvals=np.array(start_hours), show_plot=False))
        end_cdf = np.atleast_1d(distribution.CDF(xvals=np.array(end_hours), show_plot=False))
        # 逐台相减。差值是这台产品在 A 到 B 之间发生故障的概率，此时还没有乘 BOM。
        return [float(item) for item in (end_cdf - start_cdf)]

    @staticmethod
    def _parse_day(value) -> date | None:
        """把故障表里的新造日期字符串转成日期。无法识别时返回空。"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value).strip()
        if len(text) < 10:
            return None
        # 故障表里的新造日期是字符串，只取前 10 位的年月日。
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


# 供接口层调用。方法都是静态的，这个实例不保存状态。
part_forecast_service = PartForecastService()
