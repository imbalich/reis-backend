#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：model_process_service.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/4/1 17:34
"""

from typing import Any, List, Dict
import shap
import numpy as np
import pandas as pd
from imblearn.combine import SMOTEENN
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from backend.common.exception import errors


class ModelProcessService:

    @staticmethod
    async def model_process(tags: dict[str, Any]) -> dict[str, Any]:
        """
        模型建立与预测
        :param tags: 处理好的数据
        :return: 预测结果
        """
        try:
            # 1、获取处理好的数据集
            data_pre = await ModelProcessService.get_data_pro(tags)

            # 2、建立模型
            model_result = await ModelProcessService.model_create(data_pre)

            # 3、模型预测
            results=[]
            x_train = data_pre["x_train"]
            x_test = data_pre["x_test"]
            x_test_old = data_pre["x_test_old"]
            categorical_cols = data_pre["categorical_cols"]
            numerical_cols = data_pre["numerical_cols"]

            for model_info in model_result["ranked_models"]:
                best_model = model_info["best_model"]
                model_type = model_info["model_type"]
                sample_idx = np.random.choice(x_test.index, size=min(100, len(x_test)), replace=False)
                x_test = x_test.loc[sample_idx]
                x_test_raw = x_test_old.loc[sample_idx, categorical_cols].copy()

                # 计算shap值
                shap_values = await ModelProcessService._calculate_shap_values(best_model, model_type, x_test, x_train)

                # 计算特征重要度
                feature_importance = []
                all_cols = categorical_cols + numerical_cols
                for col in all_cols:
                    mean_abs_shap = np.mean(np.abs(shap_values.values[:, x_train.columns.get_loc(col)]))
                    feature_importance.append({
                        'feature': col,
                        'shap_value': mean_abs_shap,
                    })

                # 计算每个特征下各类别特征重要度
                categorical_analysis = {}
                for col in categorical_cols:
                    categorical_analysis[col] = ModelProcessService._analyze_categorical_feature(x_test_raw[col],shap_values)

                # 组装结果
                results.append({
                    "model_type": model_type,
                    "feature_importance": feature_importance,
                    "categorical_analysis": categorical_analysis
                })
            return {
                "results": results
            }
        except Exception as e:
            raise errors.DataValidationError(msg=f'模型预测失败,失败原因：{str(e)}')




    @staticmethod
    async def get_data_pro(tags):
        """
        获取目标编码后的数据并划分训练集和预测集
        :param tags: 处理好的数据
        :return: 数据列表
        """
        data = tags['data']
        df = pd.DataFrame(data)
        x = df[['extra_source_code', 'extra_supplier', 'self_create_by', 'check_tools_sign', 'rela_self_value']]
        y = df['is_figure']
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.2, random_state=42
        )
        # 定义需要进行频次编码的分类列
        categorical_cols = ['extra_source_code','extra_supplier', 'self_create_by', 'check_tools_sign']
        numerical_cols = ['rela_self_value']
        x_train_code = x_train.copy()
        x_test_code = x_test.copy()
        # 频次编码映射字典
        freq_maps = {}

        # 在训练集上计算频次编码映射
        for col in categorical_cols:
            freq = x_train[col].value_counts(normalize=True)
            freq_map = freq.to_dict()
            freq_maps[col] = freq_map

            x_train_code[col] = x_train[col].map(freq_map).fillna(0)
            x_test_code[col] = x_test[col].map(freq_map).fillna(0)

        scaler = StandardScaler()
        x_train_code[numerical_cols] = scaler.fit_transform(x_train_code[numerical_cols])
        x_test_code[numerical_cols] = scaler.transform(x_test_code[numerical_cols])

        # 检查数据是否存在类别不平衡
        class_counts = y_train.value_counts()
        is_imbalanced = (class_counts.iloc[0] / class_counts.iloc[1] > 2) or (
                class_counts.iloc[1] / class_counts.iloc[0] > 2)
        if is_imbalanced:
            smoteenn = SMOTEENN(random_state=42, sampling_strategy=0.5)
            x_train_code, y_train = smoteenn.fit_resample(x_train_code, y_train)

        return {
            "x_train": x_train_code,
            "y_train": y_train,
            "x_test_old": x_test,
            "x_test": x_test_code,
            "y_test": y_test,
            "categorical_cols": categorical_cols,
            "numerical_cols": numerical_cols
        }


    @staticmethod
    async def model_create(data):
        """
        建立逻辑回归、决策树、随机森林模型
        :param data:编码完成并划分好的数据集
        :return: 模型排序与结果
        """
        # 准备数据
        x_train = data["x_train"]
        y_train = data["y_train"]
        x_test = data["x_test"]
        y_test = data["y_test"]

        # 定义模型和参数网格
        models = {
            "LogisticRegression": {
                "model": LogisticRegression(penalty='elasticnet',solver='saga',max_iter=5000, random_state=42),
                "params": {
                    'C': [0.1, 1, 10],
                    'l1_ratio': [0.1, 0.5, 0.9],
                    'class_weight': ['balanced', None]
                }
            },
            "DecisionTree": {
                "model": DecisionTreeClassifier(criterion='gini', random_state=66),
                "params": {
                    'max_depth': [None, 5, 10, 20],
                    'min_samples_split': [2,5, 10],
                    'min_samples_leaf': [1, 2, 4],
                    'class_weight': ['balanced', None]
                }
            },
            "RandomForest": {
                "model": RandomForestClassifier(random_state=66),
                "params": {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [None, 10, 20],
                    'min_samples_split': [5, 10],
                    'min_samples_leaf': [2, 4],
                    'class_weight': ['balanced', None]
                }
            }
        }

        # 存储结果
        model_results = []

        # 对每个模型进行网格搜索
        for name, config in models.items():
            # 使用两种评分标准
            gs = GridSearchCV(
                estimator=config["model"],
                param_grid=config["params"],
                scoring={'f1': 'f1', 'roc_auc': 'roc_auc'},
                refit='f1',
                cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
                n_jobs=-1,
                verbose=0
            )
            gs.fit(x_train, y_train)
            # 在测试集上评估
            y_pre = gs.predict(x_test)
            y_proba = gs.predict_proba(x_test)[:, 1]
            f1 = f1_score(y_test, y_pre)
            roc_auc = roc_auc_score(y_test, y_proba)

            model_results.append({
                "model_type": name,
                "best_model": gs.best_estimator_,
                "f1_score": f1,
                "roc_auc_score": roc_auc,
            })

        ranked_models = sorted(
            model_results,
            key=lambda x: (-x["f1_score"], -x["roc_auc_score"])
        )

        return {
            "ranked_models": ranked_models,
        }

    @staticmethod
    async def _calculate_shap_values(model, model_type: str, x_test: pd.DataFrame, x_train: pd.DataFrame):
        """
        带错误处理的SHAP计算
        :param model: 训练好的模型
        :param model_type: 模型类型
        :param x_test: 编码后的测试集
        :param x_train: 编码后的训练集
        :return: SHAP值
        """
        try:
            if model_type == "LogisticRegression":
                explainer = shap.LinearExplainer(model, x_train)
                shap_values = explainer(x_test)
            else:
                explainer = shap.TreeExplainer(
                    model,
                    data=x_train,
                    feature_perturbation="interventional"
                )
                shap_values = explainer(x_test, check_additivity=False)

            shap_values = shap_values
            return shap_values[1] if isinstance(shap_values.values, list) else shap_values

        except Exception as e:
            print(f"{model_type} SHAP计算失败: {str(e)}")

    @staticmethod
    def _analyze_categorical_feature(feature_series: pd.Series, shap_values: np.ndarray) -> List[Dict]:
        """
        分析每个特征下单个类别特征
        :param feature_series: 编码前单列特征值
        :param shap_values: SHAP值
        :return: 每个类别SHAP值并排序
        """
        analysis = []
        for value in feature_series.unique():
            mask = (feature_series == value)
            if mask.sum() > 0:
                indices = np.where(mask)[0]
                value_shap = np.mean(shap_values.values[indices], axis=0)
                if np.mean(value_shap) > 0:
                    analysis.append({
                        "value": value,
                        "count": mask.sum().item(),
                        "mean_shap": float(np.mean(value_shap)),
                    })
        sorted_analysis = sorted(analysis, key=lambda x: x["mean_shap"], reverse=True)

        return sorted_analysis[:min(3, len(sorted_analysis))]

model_process_service: ModelProcessService=ModelProcessService()
