#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : fastapi-base-backend
@File    : conf.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/28 16:26
'''
from functools import lru_cache
from typing import Callable

from pydantic_settings import BaseSettings
from reliability.Distributions import Weibull_Distribution, Normal_Distribution, Gamma_Distribution, \
    Loglogistic_Distribution, Lognormal_Distribution, Exponential_Distribution, Gumbel_Distribution

from backend.app.predict.schema.distribute_param import DistributeType


class PredictSettings(BaseSettings):
    # 映射配置
    DISTRIBUTION_FUNCTIONS: dict[DistributeType, Callable] = {
        DistributeType.Weibull_2P: Weibull_Distribution,
        DistributeType.Weibull_3P: Weibull_Distribution,
        DistributeType.Normal_2P: Normal_Distribution,
        DistributeType.Gamma_2P: Gamma_Distribution,
        DistributeType.Gamma_3P: Gamma_Distribution,
        DistributeType.Loglogistic_2P: Loglogistic_Distribution,
        DistributeType.Loglogistic_3P: Loglogistic_Distribution,
        DistributeType.Lognormal_2P: Lognormal_Distribution,
        DistributeType.Lognormal_3P: Lognormal_Distribution,
        DistributeType.Exponential_1P: Exponential_Distribution,
        DistributeType.Exponential_2P: Exponential_Distribution,
        DistributeType.Gumbel_2P: Gumbel_Distribution
    }

    PARAM_MAPPING: dict[DistributeType, dict[str, str]] = {
        DistributeType.Weibull_2P: {'alpha': 'alpha', 'beta': 'beta'},
        DistributeType.Weibull_3P: {'alpha': 'alpha', 'beta': 'beta', 'gamma': 'gamma'},
        DistributeType.Normal_2P: {'mu': 'mu', 'sigma': 'sigma'},
        DistributeType.Gamma_2P: {'alpha': 'alpha', 'beta': 'beta'},
        DistributeType.Gamma_3P: {'alpha': 'alpha', 'beta': 'beta', 'gamma': 'gamma'},
        DistributeType.Loglogistic_2P: {'alpha': 'alpha', 'beta': 'beta'},
        DistributeType.Loglogistic_3P: {'alpha': 'alpha', 'beta': 'beta', 'gamma': 'gamma'},
        DistributeType.Lognormal_2P: {'mu': 'mu', 'sigma': 'sigma'},
        DistributeType.Lognormal_3P: {'mu': 'mu', 'sigma': 'sigma', 'gamma': 'gamma'},
        DistributeType.Exponential_1P: {'lambda': 'lambda'},
        DistributeType.Exponential_2P: {'lambda': 'lambda', 'gamma': 'gamma'},
        DistributeType.Gumbel_2P: {'mu': 'mu', 'beta': 'beta'},
    }


@lru_cache
def get_predict_settings() -> PredictSettings:
    """获取全局配置，使用LRU保证配置实例只被创建一次"""
    return PredictSettings()


# 创建配置实例
predict_settings = get_predict_settings()
