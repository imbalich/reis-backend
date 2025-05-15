#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : reis-backend
@File    : opt_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/5/7 16:38
'''
from reliability.Repairable_systems import optimal_replacement_time

from backend.app.calcu.schema.opt_param import OptPartParam
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.common.exception.errors import DataValidationError
from backend.database.db import async_db_session


class OptService:

    @staticmethod
    async def get_opt_part(*, obj: OptPartParam) -> tuple[float, float]:
        try:
            async with async_db_session() as db:
                fix_part = await fit_part_dao.get_by_model_and_part_and_distribution(db, obj.model, obj.part, 'Weibull_2P')
                if fix_part is None:
                    raise DataValidationError(msg=f"找不到型号为 {obj.model} 且部件为 {obj.part} 的Weibull_2P分布数据")

                opt = optimal_replacement_time(
                    cost_PM=obj.pm_price,
                    cost_CM=obj.cm_price,
                    weibull_alpha=fix_part.alpha,
                    weibull_beta=fix_part.beta,
                    q=0
                )
                return opt.ORT, opt.min_cost
        except DataValidationError:
            raise
        except Exception as e:
            raise DataValidationError(msg=f"计算最佳更换周期时发生错误: {str(e)}")


opt_service: OptService = OptService()
