import pandas as pd
import numpy as np
import re
from typing import List, Dict, Any, Set, Tuple
from backend.app.sense.utils.format_process_utils import split_multiple_names

class WOEAnalysisService:

    @staticmethod
    def _top_negative_woe(df: pd.DataFrame, topn: int = 8) -> pd.DataFrame:
        """
        只保留 woe<0，按|woe|降序取前 topn
        """
        df = df[df['woe'] < 0]
        df = df.reindex(df['woe'].abs().sort_values(ascending=False).index)
        return df.head(topn)

    @staticmethod
    def analyze_all_features(data) -> Dict[str, Any]:
        """
        对指定特征做 WOE/IV 分析：
        - self_create_by（自检人）：多标签处理
        - 其他特征：单标签处理
        data: 可以是 DataFrame，也可以是字典列表（如 tags['data']）
        返回结构化结果，便于存储和前端展示
        """
        # 自动转换为 DataFrame
        if isinstance(data, pd.DataFrame):
            df = data
        else:
            df = pd.DataFrame(data)
        categorical_cols = ['extra_source_code', 'extra_supplier', 'check_tools_sign', 'rela_self_value', 'version']
        target_col = 'is_figure'
        special_cols = ['version']
        woe_results = {}
        iv_summary = []
        # 处理 self_create_by（操作员工，多标签）
        if 'self_create_by' in df.columns:
            name_woe_part, name_iv_total, name_dict = WOEAnalysisService.self_create_features(df, 'self_create_by', target_col)
            iv_summary.append({'feature': 'self_create_by', 'iv': name_iv_total})
            woe_results['self_create_by'] = WOEAnalysisService._top_negative_woe(name_woe_part)
        # 处理其他单标签特征
        for feat in categorical_cols:
            if feat not in df.columns:
                continue
            is_special = feat in special_cols
            woe_df, iv = WOEAnalysisService.calc_woe_iv(df, feat, target_col, is_special=is_special)
            woe_results[feat] = WOEAnalysisService._top_negative_woe(woe_df)
            iv_summary.append({'feature': feat, 'iv': iv})
        # 结构化输出
        iv_df = pd.DataFrame(iv_summary).sort_values('iv', ascending=False).reset_index(drop=True)
        iv_df['sort_result'] = iv_df.index + 1
        iv_df = iv_df[[ 'feature', 'sort_result']]
        results = [{
            'model_type': 'WOE',
            'f1_score': 1.0,
            'feature_importance': iv_df.to_dict(orient='records'),
            'categorical_analysis': {k: v.to_dict(orient='records') for k, v in woe_results.items()}
        }]
        return {"results": results}

    @staticmethod
    def self_create_features(df: pd.DataFrame, name_col: str,
                             target_col: str) -> Tuple[pd.DataFrame, float, Set[str]]:
        """处理姓名特征并计算WOE/IV"""
        name_dict = WOEAnalysisService.build_name_dictionary(df, name_col)
        df[name_col + 'list'] = df[name_col].apply(lambda x: split_multiple_names(x, name_dict))

        total_good, total_bad = WOEAnalysisService._get_total_good_bad(df, target_col)
        woe_name_list = []

        for name in name_dict:
            # 创建姓名存在标志列
            flag_col = f'is_{name}'
            df[flag_col] = df[name_col + 'list'].apply(lambda x: int(name in x))

            # 分组计算统计信息
            for flag_value, group_df in df.groupby(flag_col):
                stats = WOEAnalysisService._compute_group_stats(
                    group_df, target_col, total_good, total_bad
                )
                woe_name_list.append({
                    'value': name,
                    'group': '参与' if flag_value == 1 else '未参与',
                    **stats
                })

        woe_name_df = pd.DataFrame(woe_name_list)
        woe_name_part = woe_name_df[woe_name_df['group'] == '参与'].copy().sort_values('woe')
        name_iv_total = woe_name_df.groupby('value')['iv'].sum().sum()

        return woe_name_part, name_iv_total, name_dict

    @staticmethod
    def calc_woe_iv(df: pd.DataFrame, feature: str, target: str,
                    is_special: bool = False) -> Tuple[pd.DataFrame, float]:
        """通用特征WOE/IV计算"""
        if feature not in df.columns:
            return pd.DataFrame(), 0

        # 处理缺失值
        if df[feature].dtype == 'object':
            df[feature] = df[feature].fillna('MISSING')
        else:
            df[feature] = df[feature].fillna(-999)

        total_good, total_bad = WOEAnalysisService._get_total_good_bad(df, target, is_special)
        lst = []

        for cat, group_df in df.groupby(feature):
            if is_special:
                group_df = group_df.drop_duplicates('product_no')

            stats = WOEAnalysisService._compute_group_stats(
                group_df, target, total_good, total_bad
            )
            lst.append({'value': cat, **stats})

        woe_df = pd.DataFrame(lst).sort_values('woe', ascending=False)
        iv_sum = woe_df['iv'].sum()
        return woe_df, iv_sum

    @staticmethod
    def build_name_dictionary(df: pd.DataFrame, name_col: str) -> Set[str]:
        name_dict = set()
        for cell in df[name_col].dropna():
            cell = str(cell).strip()
            if 2 <= len(cell) <= 3 and all('\u4e00' <= char <= '\u9fff' for char in cell):
                name_dict.add(cell)
        return name_dict

    @staticmethod
    def _get_total_good_bad(df: pd.DataFrame, target_col: str,
                            is_special: bool = False) -> Tuple[int, int]:
        """计算总体好坏样本数量"""
        if is_special:
            unique_df = df.drop_duplicates('product_no')
            total_good = (unique_df[target_col] == 0).sum()
            total_bad = (unique_df[target_col] == 1).sum()
        else:
            total_good = (df[target_col] == 0).sum()
            total_bad = (df[target_col] == 1).sum()
        return total_good, total_bad

    @staticmethod
    def _compute_group_stats(group_df: pd.DataFrame, target_col: str,
                             total_good: int, total_bad: int) -> dict:
        """计算单个分组的WOE/IV统计信息"""
        eps = 1e-8
        good = (group_df[target_col] == 0).sum()
        bad = (group_df[target_col] == 1).sum()
        count = len(group_df)

        bad_rate = bad / (count + eps)
        rate_good = (good + eps) / (total_good + eps)
        rate_bad = (bad + eps) / (total_bad + eps)
        woe = np.log(rate_good / rate_bad)
        iv = (rate_good - rate_bad) * woe

        return {
            'good': good,
            'bad': bad,
            'count': count,
            'bad_rate': bad_rate,
            'woe': woe,
            'iv': iv,
            'Fault': f"{bad}/{count}"
        }

