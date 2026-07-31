#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import date
from typing import Any

import pandas as pd

from backend.app.fit_aaron.service.aaron_data_process_service import (
    process_fault_data_rowwise1,
    process_fault_data_rowwise_replace,
)
from backend.app.fit_aaron.service.aaron_tag_adapter import data_result_to_tags


# Aaron于2026-07-17新增：Aaron部件级数据处理编排服务
# 新增原因：客户后端DAO返回的是对象列表，本地main_new.py处理函数接收的是DataFrame
# 新增作用：负责“数据库对象 -> DataFrame -> data_result -> tags”的完整适配，不改威布尔拟合函数

class AaronPartDataService:
    async def build_tags(
        self,
        *,
        model: str,
        part: str,
        despatch_data: list[Any],
        failure_data: list[Any],
        product_data: Any,
        ebom_data: Any,
        replace_data: list[Any],
        repair_data: list[Any] | None,
        repair_despatch_data: list[Any] | None,
        input_date: date,
    ) -> list[list[Any]]:
        despatch_df = objects_to_dataframe(despatch_data)
        failure_df = normalize_failure_dataframe(objects_to_dataframe(failure_data))
        product_df = object_to_dataframe(product_data)
        replace_df = objects_to_dataframe(replace_data)
        repair_df = objects_to_dataframe(repair_data or [])
        repair_despatch_df = objects_to_dataframe(repair_despatch_data or [])

        total_bl_quantity = get_total_bl_quantity(ebom_data)
        if total_bl_quantity <= 0:
            total_bl_quantity = 1

        result = build_base_result(model, despatch_df, failure_df, total_bl_quantity)
        failure_df = prepare_failure_dataframe(failure_df)

        # Aaron于2026-07-17更改：先不接入质保期过滤
        # 更改原因：当前客户确认的主任务是必换件逻辑和data_result转tags，质保期可作为后续独立开关
        is_zhibao = pd.DataFrame()
        is_consider_zhibao = False

        if not replace_df.empty:
            despatch_replace_data = build_despatch_replace_data(
                replace_df=replace_df,
                repair_df=repair_df,
                repair_despatch_df=repair_despatch_df,
            )
            data_result = process_fault_data_rowwise_replace(
                result,
                failure_df,
                product_df,
                despatch_replace_data,
                input_date=input_date,
            )
        else:
            data_result = process_fault_data_rowwise1(
                result,
                failure_df,
                product_df,
                is_zhibao,
                input_date=input_date,
                is_consider_zhibao=is_consider_zhibao,
            )

        # Aaron于2026-07-21新增：临时调试日志，观察data_result生成质量
        # 新增原因：必换件样本中Aaron页面只出现Exponential_1P，需要确认failure是否在data_result阶段丢失
        # 新增作用：在Celery/后端PowerShell窗口输出行数、状态分布、有效寿命数量，便于定位字段映射或过滤问题
        print(f'[AaronDebug] model={model}, part={part}')
        print(f'[AaronDebug] replace_branch={not replace_df.empty}')
        print(f'[AaronDebug] data_result_rows_before_filter={len(data_result)}')
        if not data_result.empty:
            if 'state_1' in data_result.columns:
                print(f'[AaronDebug] data_result_state_count={data_result["state_1"].value_counts(dropna=False).to_dict()}')
                failure_rows = data_result[data_result['state_1'] == 'failure']
                debug_cols = [
                    col for col in [
                        'identifier', 'identifier_index', 'life_cycle_time',
                        'fault_1', 'fault_day_1', 'fault_time_1', 'state_1',
                    ] if col in failure_rows.columns
                ]
                print(f'[AaronDebug] failure_rows_before_filter={failure_rows[debug_cols].to_dict("records")}')
            if 'fault_time_1' in data_result.columns:
                print(f'[AaronDebug] fault_time_null_count={int(data_result["fault_time_1"].isna().sum())}')
                print(f'[AaronDebug] fault_time_positive_count={int((data_result["fault_time_1"] > 0).sum())}')
                print(f'[AaronDebug] fault_time_non_positive_count={int((data_result["fault_time_1"] <= 0).sum())}')

        if not data_result.empty and 'fault_time_1' in data_result.columns:
            data_result = data_result[data_result['fault_time_1'] > 0]

        tags = data_result_to_tags(data_result)
        print(f'[AaronDebug] data_result_rows_after_filter={len(data_result)}')
        print(f'[AaronDebug] tags_count={len(tags)}')
        print(f'[AaronDebug] tags_failure_count={sum(1 for item in tags if item[-1] == "failure")}')
        print(f'[AaronDebug] tags_suspense_count={sum(1 for item in tags if item[-1] == "suspense")}')

        return tags


def objects_to_dataframe(items: list[Any]) -> pd.DataFrame:
    rows = []
    for item in items:
        rows.append(object_to_dict(item))
    return pd.DataFrame(rows)


def object_to_dataframe(item: Any) -> pd.DataFrame:
    if item is None:
        return pd.DataFrame()
    return pd.DataFrame([object_to_dict(item)])


def object_to_dict(item: Any) -> dict[str, Any]:
    if item is None:
        return {}
    if hasattr(item, 'model_dump'):
        return item.model_dump()
    if isinstance(item, dict):
        return item
    return {key: value for key, value in vars(item).items() if not key.startswith('_')}


def normalize_failure_dataframe(failure_df: pd.DataFrame) -> pd.DataFrame:
    if failure_df.empty:
        return failure_df

    # Aaron于2026-07-17新增：对齐main_new.py使用的故障字段名
    # 新增原因：客户后端模型字段名为product_number/discovery_date，原型代码使用product_no/fault_date
    rename_map = {
        'product_number': 'product_no',
        'discovery_date': 'fault_date',
        'product_lifetime_stage': 'repair_level',
        'manufacturing_date': 'production_data',
    }
    for source, target in rename_map.items():
        if source in failure_df.columns and target not in failure_df.columns:
            failure_df = failure_df.rename(columns={source: target})

    return failure_df


def prepare_failure_dataframe(failure_df: pd.DataFrame) -> pd.DataFrame:
    failure_df = failure_df.copy()
    if failure_df.empty:
        return failure_df

    if 'fault_date' in failure_df.columns:
        failure_df['fault_date'] = pd.to_datetime(failure_df['fault_date'], errors='coerce')
        failure_df['fault_date_only'] = failure_df['fault_date'].dt.normalize()

    return failure_df


def get_total_bl_quantity(ebom_data: Any) -> int:
    if ebom_data is None:
        return 1
    if isinstance(ebom_data, list):
        quantities = [getattr(item, 'bl_quantity', None) for item in ebom_data]
    else:
        quantities = [getattr(ebom_data, 'bl_quantity', None)]

    total = 0
    for quantity in quantities:
        try:
            value = float(quantity or 0)
            total += int(value) if value.is_integer() else 1
        except (TypeError, ValueError):
            total += 1
    return total


def build_base_result(
    model: str,
    despatch_df: pd.DataFrame,
    failure_df: pd.DataFrame,
    total_bl_quantity: int,
) -> pd.DataFrame:
    # Aaron于2026-07-17新增：复刻main_new.py中生成result的步骤
    # 新增原因：process_fault_data_rowwise1/replace需要model、identifier、identifier_index、life_cycle_time四列作为初始样本
    if despatch_df.empty:
        data_process = pd.DataFrame(columns=['model', 'identifier', 'life_cycle_time'])
    else:
        data_process = despatch_df.drop_duplicates(subset=['identifier'], keep='first')
        data_process = data_process[['model', 'identifier', 'life_cycle_time']]

    if not failure_df.empty and {'product_no', 'production_data'}.issubset(failure_df.columns):
        production_failure_df = failure_df.copy()
        production_failure_df['production_data_dt'] = pd.to_datetime(
            production_failure_df['production_data'], errors='coerce'
        ).dt.normalize()

        # Aaron于2026-07-21更改：已有产品寿命起点不再依赖“新造”中文字段过滤
        # 更改原因：Windows脚本写入时中文常量曾被转成问号，导致生产日期修正逻辑没有命中
        # 更改作用：同一产品同时存在发运日期和故障生产日期时，取更早的有效日期作为life_cycle_time
        if not data_process.empty and not production_failure_df.empty:
            production_min = (
                production_failure_df.dropna(subset=['production_data_dt'])
                .groupby('product_no')['production_data_dt']
                .min()
            )
            if not production_min.empty:
                data_process['life_cycle_time_dt'] = pd.to_datetime(
                    data_process['life_cycle_time'], errors='coerce'
                ).dt.normalize()
                adjust_mask = data_process['identifier'].isin(production_min.index)
                for idx in data_process[adjust_mask].index:
                    product_no = data_process.at[idx, 'identifier']
                    production_date = production_min.get(product_no)
                    current_date = data_process.at[idx, 'life_cycle_time_dt']
                    if pd.notna(production_date) and (pd.isna(current_date) or production_date < current_date):
                        data_process.at[idx, 'life_cycle_time'] = production_date.date()
                data_process = data_process.drop(columns=['life_cycle_time_dt'])

        missing_source_df = production_failure_df
        if 'repair_level' in production_failure_df.columns:
            new_repair_level = '新造'
            matched_source_df = production_failure_df[
                production_failure_df['repair_level'].astype(str) == new_repair_level
            ]
            if not matched_source_df.empty:
                missing_source_df = matched_source_df

        missing_mask = ~missing_source_df['product_no'].isin(data_process['identifier'])
        new_entries = missing_source_df[missing_mask].copy().drop_duplicates(subset=['product_no'])
        if not new_entries.empty:
            to_add = pd.DataFrame(
                {
                    'model': model,
                    'identifier': new_entries['product_no'],
                    'life_cycle_time': new_entries['production_data_dt'].dt.date,
                }
            )
            data_process = pd.concat([data_process, to_add], ignore_index=True)

    if data_process.empty:
        return pd.DataFrame(columns=['model', 'identifier', 'identifier_index', 'life_cycle_time'])

    expanded_df = data_process.loc[data_process.index.repeat(total_bl_quantity)].copy()
    expanded_df['suffix'] = expanded_df.groupby(level=0).cumcount() + 1
    expanded_df['identifier_index'] = (
        expanded_df['identifier'].astype(str) + '-' + expanded_df['suffix'].astype(str)
    )
    return expanded_df[['model', 'identifier', 'identifier_index', 'life_cycle_time']]


def build_despatch_replace_data(
    *,
    replace_df: pd.DataFrame,
    repair_df: pd.DataFrame,
    repair_despatch_df: pd.DataFrame,
) -> pd.DataFrame:
    if repair_despatch_df.empty:
        return pd.DataFrame(columns=['identifier', 'life_cycle_time'])

    repair_despatch_df = repair_despatch_df.copy()
    if 'repair_level' in repair_despatch_df.columns:
        repair_despatch_df['repair_level'] = standardize_repair_levels(repair_despatch_df['repair_level'])

    target_levels = get_replace_target_levels(replace_df, repair_df)
    if target_levels:
        repair_despatch_df = repair_despatch_df[repair_despatch_df['repair_level'].isin(target_levels)]

    return repair_despatch_df[['identifier', 'life_cycle_time']]


def get_replace_target_levels(replace_df: pd.DataFrame, repair_df: pd.DataFrame) -> list[str]:
    if replace_df.empty or repair_df.empty:
        return []

    replace_level = replace_df.iloc[0].get('replace_level')
    if not replace_level or 'repair_levels' not in repair_df.columns:
        return []

    # Aaron于2026-07-17更改：客户库当前未建模dm_repair_interval.repair_years，优先用id_repair近似筛选必换修级
    # 更改原因：main_new.py用repair_years取整倍数，客户后端Repair模型只有id_repair和repair_levels
    # 更改作用：在字段不足时仍保留必换件时间轴；如果后续补充repair_years，可在此处替换为严格逻辑
    if 'id_repair' not in repair_df.columns:
        return [replace_level]

    base_rows = repair_df[repair_df['repair_levels'] == replace_level]
    if base_rows.empty:
        return [replace_level]

    try:
        base_order = int(base_rows.iloc[0]['id_repair'])
    except (TypeError, ValueError):
        return [replace_level]

    if base_order == 0:
        return [replace_level]

    target_df = repair_df[
        (repair_df['id_repair'].astype(int) % base_order == 0)
        & (repair_df['repair_levels'] != '新造')
    ]
    return target_df['repair_levels'].dropna().tolist()


def standardize_repair_levels(repair_levels_list):
    mapping_dict = {
        '三级修': '首轮三级修',
        '首轮三级修改制': '首轮三级修',
        '次轮三级修改制': '次轮三级修',
        '三级三级修': '三轮三级修',
        '三次三级修': '三轮三级修',
        '三轮三级修改制': '三轮三级修',
        '首轮四级修改制': '首轮四级修',
        '次轮四级修改制': '次轮四级修',
        '首轮五级修改制': '首轮五级修',
        '次轮五级修改制': '次轮五级修',
        '四轮五级修改制': '四轮五级修',
        '首轮C4修': 'C4',
        'C4扩大': 'C4',
        '二年检': 'C4',
        '次轮C4修': '2C4',
        '二次二年检': '2C4',
        '首轮C5修': 'C5',
        '四年检': 'C5',
        '架修': '架修-1',
        '大修': '大修-1',
    }
    return [mapping_dict.get(level, level) for level in repair_levels_list]


aaron_part_data_service = AaronPartDataService()

