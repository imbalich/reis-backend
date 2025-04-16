#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：sense_predict_service.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/4/1 16:39
"""

from backend.database.db import async_db_session

"""
检验
故障数据是否是二分类变量
tags = await ProcessService.process(model, part)
fit = await ModelProcessService.tag_fit(tags)
log_fit = await ModelProcessService.log_fit()
tree_fit = await ModelProcessService.tree_fit()
random_fit = await ModelProcessService.random_fit()

async def tag_fit(tags: dict[str, Any]):
data_pre = await ModelProcessService.data_code(tags.data) 输出编码后的x和y预测集和训练集
best_model = await ModelProcessService.model_create(data_pre) 输出最佳预测模型
## 这部分分为三个方法，逻辑回归，决策树，随机森林
fit = await ModelProcessService.fit(best_model,data_pre.X_train_final,data_pre.X_test_final) 输出SHAP值结果，及重要度排序

data_code：
先对tags数据划分为训练集和预测集，然后分别进行频次编码,需要的数据为pd.DataFrame,并检查数据是否存在类别不平衡，如果存在，处理类别不平衡
返回处理好的训练集和预测集

best_model
三种方法都需要 grid_search.fit(X_resampled, y_resampled)，输入训练集和预测集，输出最佳模型best_model
基于best_model交叉验证评估，输出F1和ROC分数

SHAP分析，类别分析，整体分析
输入最佳模型,x_训练集,x_预测集
输出每个类别和整体下的重要度排序

逻辑回归和交叉验证单独写一个公共函数，供三种方法同时使用，输入训练集和预测集（
"""


class SensePredictService:
    @staticmethod
    async def sense_predict(model: str, part: str):
        async with async_db_session():
            pass


sense_predict_service: SensePredictService = SensePredictService()
