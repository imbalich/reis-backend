#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：model_process_service.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/4/1 17:34
"""

from typing import Any

import numpy as np
import pandas as pd

from imblearn.combine import SMOTEENN
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score, train_test_split
from sklearn.tree import DecisionTreeClassifier


class ModelProcessService:
    @staticmethod
    async def model_process(tags: dict[str, Any]):
        await ModelProcessService.get_data_pro(tags)

    @staticmethod
    async def get_data_pro(tags):
        data = tags['data']
        df = pd.DataFrame(data)
        x = df.drop('is_figure', axis=1)
        y = df['is_figure']
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
        # 定义需要进行频次编码的分类列
        categorical_cols = ['extra_source_code', 'self_create_by', 'check_tools_sign']
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

            # 应用到训练集（填充缺失值为0）
            x_train_code[col] = x_train[col].map(freq_map).fillna(0)
            x_test_code[col] = x_test[col].map(freq_map).fillna(0)

        # 检查数据是否存在类别不平衡
        class_counts = y_train.value_counts()
        is_imbalanced = (class_counts.iloc[0] / class_counts.iloc[1] > 2) or (
            class_counts.iloc[1] / class_counts.iloc[0] > 2
        )

        if is_imbalanced:
            smoteenn = SMOTEENN(random_state=42, sampling_strategy=0.5)
            x_train_code, y_train = smoteenn.fit_resample(x_train_code, y_train)

        return {
            'x_train': x_train_code,
            'y_train': y_train,
            'X_test': x_test_code,
            'y_test': y_test,
            'categorical_cols': categorical_cols,
            'numerical_cols': numerical_cols,
        }

    @staticmethod
    async def model_create(data):
        # 准备数据
        x_train = data['x_train']
        y_train = data['y_train']
        # print("SMOTEENN 过采样后 y_train 分布:", np.unique(y_train, return_counts=True))

        # 定义模型和参数网格
        models = {
            'LogisticRegression': {
                'model': LogisticRegression(penalty='elasticnet', solver='saga', max_iter=5000, random_state=42),
                'params': {
                    'C': [1, 10],
                    'penalty': ['l1'],
                    # 'class_weight': ['balanced', None]
                },
            },
            'DecisionTree': {
                'model': DecisionTreeClassifier(criterion='gini', random_state=66),
                'params': {
                    'max_depth': [5, 10],
                    'min_samples_split': [5, 10],
                    'min_samples_leaf': [1, 2, 4],
                    'class_weight': ['balanced', None],
                },
            },
            'RandomForest': {
                'model': RandomForestClassifier(random_state=66),
                'params': {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [10, 15],
                    'min_samples_split': [5, 10],
                    'min_samples_leaf': [2, 4],
                    'class_weight': ['balanced', None],
                },
            },
        }

        # 存储结果
        model_results = []

        # 对每个模型进行网格搜索
        for name, config in models.items():
            # 使用两种评分标准
            gs = GridSearchCV(
                estimator=config['model'],
                param_grid=config['params'],
                scoring={'f1': 'f1', 'roc_auc': 'roc_auc'},
                refit='f1',  # 优先用F1选择最佳模型
                cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
                n_jobs=-1,
                verbose=1,
            )
            gs.fit(x_train, y_train)
            cv_f1 = cross_val_score(
                gs.best_estimator_,
                x_train,
                y_train,
                cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
                scoring='f1',
            )
            cv_roc = cross_val_score(
                gs.best_estimator_,
                x_train,
                y_train,
                cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
                scoring='roc_auc',
            )
            # 计算平均值和标准差
            f1 = np.mean(cv_f1).item()
            roc_auc = np.mean(cv_roc).item()

            model_results.append({
                'model_type': name,
                'best_model': gs.best_estimator_,
                'f1_score': f1,
                'roc_auc_score': roc_auc,
            })

            # 按性能排序（F1优先，ROC_AUC次之）
        ranked_models = sorted(model_results, key=lambda x: (-x['f1_score'], -x['roc_auc_score']))

        return {
            'ranked_models': ranked_models,
        }

    @staticmethod
    async def shap_analysis(model_result, test_data):
        test_data['x_train']
        X_test = test_data['X_test']
        test_data['y_test']
        categorical_cols = test_data['categorical_cols']
        test_data['numerical_cols']

        for model_info in model_result['ranked_models']:
            model_info['best_model']
            X_test.loc[X_test.index, categorical_cols].copy()


model_rocess_service: ModelProcessService = ModelProcessService()
