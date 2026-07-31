#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd


# Aaron于2026-07-17新增：从本地weibull/data_process_service_new.py迁移的纯pandas处理逻辑
# 新增原因：Aaron分支需要复用main_new.py的数据处理结果data_result，而不是继续使用旧part_tag_process_service
# 新增作用：只处理DataFrame，不直接访问数据库；数据库查询仍由客户后端DAO负责

def process_fault_data_rowwise1(
    result: pd.DataFrame,
    failure_data: pd.DataFrame,
    product_data: pd.DataFrame,
    is_zhibao: pd.DataFrame,
    input_date=None,
    is_consider_zhibao: bool = False,
) -> pd.DataFrame:
    result = result.copy()

    if input_date is None or pd.isna(input_date):
        input_date = pd.Timestamp.now().normalize()
    else:
        input_date = pd.to_datetime(input_date).normalize()

    if len(is_zhibao) > 0:
        is_zhibao['deadline'] = pd.to_datetime(is_zhibao['deadline'], errors='coerce')

    for col in ['fault_1', 'fault_day_1', 'fault_time_1', 'state_1']:
        result.loc[:, col] = None

    year_days = None
    avg_worktime = None
    if not product_data.empty:
        year_days = product_data.get('year_days', [None]).iloc[0]
        avg_worktime = product_data.get('avg_worktime', [None]).iloc[0]

    failure_data = failure_data.copy()
    if 'fault_date_only' not in failure_data.columns:
        failure_data['fault_date_only'] = pd.to_datetime(
            failure_data.get('fault_date'), errors='coerce'
        ).dt.normalize()

    failure_data = failure_data[failure_data['fault_date_only'] <= input_date]
    failure_data = failure_data.sort_values(
        ['product_no', 'fault_date_only'], ascending=[True, True]
    ).reset_index(drop=True)

    assignments = {}
    unique_identifiers = result['identifier'].unique()

    for identifier in unique_identifiers:
        faults = failure_data[failure_data['product_no'] == identifier].reset_index(drop=True)
        identifier_rows = result[result['identifier'] == identifier]
        if identifier_rows.empty:
            continue

        available_suffixes = sorted(
            identifier_rows['identifier_index'].str.split('-').str[-1].astype(int).tolist()
        )
        life_cycle_time = identifier_rows['life_cycle_time'].iloc[0]
        life_cycle_dt = pd.to_datetime(life_cycle_time, errors='coerce')
        prev_fault_dates = {s: life_cycle_dt for s in available_suffixes}

        current_suffix_idx = 0
        current_suffix = available_suffixes[current_suffix_idx]
        prev_replacement = None
        prev_fault_date_str = None
        zb_info = pd.DataFrame()
        if len(is_zhibao) > 0:
            zb_info = is_zhibao[is_zhibao['identifier'] == identifier]

        for _, fault in faults.iterrows():
            fault_date = pd.to_datetime(fault.get('fault_date_only'), errors='coerce')
            fault_value = fault_date.strftime('%Y-%m-%d') if pd.notna(fault_date) else None

            if prev_replacement is not None or prev_fault_date_str is not None:
                fault_part_serial = fault.get('fault_part_serial_number')
                current_replacement = fault.get('replacement_part_number')

                if prev_replacement is None and fault_part_serial is None:
                    current_suffix_idx = (current_suffix_idx + 1) % len(available_suffixes)
                    current_suffix = available_suffixes[current_suffix_idx]
                elif (fault_part_serial != prev_replacement) or (fault_value == prev_fault_date_str):
                    current_suffix_idx = (current_suffix_idx + 1) % len(available_suffixes)
                    current_suffix = available_suffixes[current_suffix_idx]

                prev_replacement = current_replacement
            else:
                prev_replacement = fault.get('replacement_part_number')

            identifier_index = f'{identifier}-{current_suffix}'
            fault_day = None
            fault_time = None

            if identifier_index in identifier_rows['identifier_index'].values and pd.notna(fault_date):
                prev_date = prev_fault_dates.get(current_suffix)
                if pd.notna(prev_date):
                    if is_consider_zhibao is True:
                        fault_day = tiaoxiu_process(zb_info, prev_date, fault_date, input_date)
                    else:
                        fault_day = int((fault_date - prev_date).days)
                    prev_fault_dates[current_suffix] = fault_date

                    if year_days is not None and avg_worktime is not None:
                        fault_time = round(fault_day * year_days * avg_worktime / 365, 5)

            assignments.setdefault(identifier_index, []).append({
                'fault': fault_value,
                'fault_day': fault_day,
                'fault_time': fault_time,
                'state': 'failure',
            })
            prev_fault_date_str = fault_value

        for suffix in available_suffixes:
            identifier_index = f'{identifier}-{suffix}'
            prev_date = prev_fault_dates.get(suffix)
            current_date = input_date

            fault_day = None
            fault_time = None
            if pd.notna(prev_date):
                if is_consider_zhibao is True:
                    over_deadline = zb_info[zb_info['reason'] == '已超过维修期限']
                    if not over_deadline.empty:
                        act_time = over_deadline['deadline'].iloc[0]
                        if pd.notna(act_time):
                            current_date = act_time
                    fault_day = tiaoxiu_process(zb_info, prev_date, current_date, input_date)
                else:
                    fault_day = int((current_date - prev_date).days)

                if year_days is not None and avg_worktime is not None:
                    fault_time = round(fault_day * year_days * avg_worktime / 365, 5)

            assignments.setdefault(identifier_index, []).append({
                'fault': current_date.strftime('%Y-%m-%d'),
                'fault_day': fault_day,
                'fault_time': fault_time,
                'state': 'suspension',
            })

    output_rows = []
    for _, row in result.iterrows():
        identifier_index = row['identifier_index']
        row_assignments = assignments.get(identifier_index, [])
        if not row_assignments:
            output_rows.append(row.copy())
            continue
        for assignment in row_assignments:
            new_row = row.copy()
            new_row['fault_1'] = assignment['fault']
            new_row['fault_day_1'] = assignment['fault_day']
            new_row['fault_time_1'] = assignment['fault_time']
            new_row['state_1'] = assignment['state']
            output_rows.append(new_row)

    return pd.DataFrame(output_rows)


def tiaoxiu_process(zb_info, prev_date, current_date, input_date):
    fault_day = int((current_date - prev_date).days)
    if fault_day < 0:
        fault_day = int((input_date - prev_date).days)

    jump_repair = zb_info[
        (zb_info['reason'] == '跳修')
        & (zb_info['deadline'] > prev_date)
        & (zb_info['deadline'] < current_date)
    ]
    if not jump_repair.empty:
        interval_years = jump_repair['repair_interval'].iloc[0]
        fault_day -= int(float(interval_years) * 365 * len(jump_repair))
        fault_day = int(fault_day)
    return fault_day


def process_fault_data_rowwise_replace(
    result: pd.DataFrame,
    failure_data: pd.DataFrame,
    product_data: pd.DataFrame,
    despatch_replace_data: pd.DataFrame,
    input_date=None,
) -> pd.DataFrame:
    result = result.copy()

    if input_date is None or pd.isna(input_date):
        input_date = pd.Timestamp.now().normalize()
    else:
        input_date = pd.to_datetime(input_date).normalize()

    for col in ['fault_1', 'fault_day_1', 'fault_time_1', 'state_1']:
        result.loc[:, col] = None

    year_days = product_data.get('year_days', [None]).iloc[0] if not product_data.empty else None
    avg_worktime = product_data.get('avg_worktime', [None]).iloc[0] if not product_data.empty else None

    failure_data = failure_data.copy()
    if 'fault_date_only' not in failure_data.columns:
        failure_data['fault_date_only'] = pd.to_datetime(
            failure_data.get('fault_date'), errors='coerce'
        ).dt.normalize()

    failure_data = failure_data[failure_data['fault_date_only'] <= input_date]
    failure_data = failure_data.sort_values(['product_no', 'fault_date_only']).reset_index(drop=True)

    assignments = {}
    unique_identifiers = result['identifier'].unique()

    for identifier in unique_identifiers:
        id_replace_dates = []
        if not despatch_replace_data.empty:
            raw_dates = despatch_replace_data[despatch_replace_data['identifier'] == identifier]['life_cycle_time']
            id_replace_dates = pd.to_datetime(raw_dates, errors='coerce').dropna().dt.normalize().tolist()
            id_replace_dates = sorted(list(set([d for d in id_replace_dates if d < input_date])))

        id_faults = failure_data[failure_data['product_no'] == identifier].to_dict('records')
        identifier_rows = result[result['identifier'] == identifier]
        if identifier_rows.empty:
            continue

        available_suffixes = sorted(identifier_rows['identifier_index'].str.split('-').str[-1].astype(int).tolist())
        life_cycle_dt = pd.to_datetime(identifier_rows['life_cycle_time'].iloc[0], errors='coerce').normalize()
        prev_event_dates = {s: life_cycle_dt for s in available_suffixes}

        current_suffix_idx = 0
        current_suffix = available_suffixes[current_suffix_idx]
        prev_replacement = None
        prev_fault_date_str = None

        timeline = []
        for f in id_faults:
            timeline.append({'date': f['fault_date_only'], 'type': 'failure', 'data': f})
        for r_date in id_replace_dates:
            timeline.append({'date': r_date, 'type': 'mandatory_replace', 'data': None})

        timeline = sorted(timeline, key=lambda x: x['date'])

        for event in timeline:
            event_date = event['date']

            if event['type'] == 'failure':
                fault = event['data']
                fault_str = event_date.strftime('%Y-%m-%d')

                if prev_replacement is not None or prev_fault_date_str is not None:
                    fault_part_serial = fault.get('fault_part_serial_number')
                    current_replacement = fault.get('replacement_part_number')

                    if prev_replacement is None and fault_part_serial is None:
                        current_suffix_idx = (current_suffix_idx + 1) % len(available_suffixes)
                        current_suffix = available_suffixes[current_suffix_idx]
                    elif (fault_part_serial != prev_replacement) or (fault_str == prev_fault_date_str):
                        current_suffix_idx = (current_suffix_idx + 1) % len(available_suffixes)
                        current_suffix = available_suffixes[current_suffix_idx]

                    prev_replacement = current_replacement
                else:
                    prev_replacement = fault.get('replacement_part_number')

                id_index = f'{identifier}-{current_suffix}'
                prev_date = prev_event_dates[current_suffix]
                days = int((event_date - prev_date).days)
                f_time = round(days * year_days * avg_worktime / 365, 5) if year_days and avg_worktime else None

                assignments.setdefault(id_index, []).append({
                    'fault': fault_str,
                    'fault_day': days,
                    'fault_time': f_time,
                    'state': 'failure',
                })

                prev_event_dates[current_suffix] = event_date
                prev_fault_date_str = fault_str

            elif event['type'] == 'mandatory_replace':
                replace_str = event_date.strftime('%Y-%m-%d')
                for suffix in available_suffixes:
                    idx = f'{identifier}-{suffix}'
                    prev_date = prev_event_dates[suffix]
                    days = int((event_date - prev_date).days)
                    f_time = round(days * year_days * avg_worktime / 365, 5) if year_days and avg_worktime else None

                    assignments.setdefault(idx, []).append({
                        'fault': replace_str,
                        'fault_day': days,
                        'fault_time': f_time,
                        'state': 'suspension',
                    })
                    prev_event_dates[suffix] = event_date

        for suffix in available_suffixes:
            idx = f'{identifier}-{suffix}'
            prev_date = prev_event_dates[suffix]
            days = int((input_date - prev_date).days)
            f_time = round(days * year_days * avg_worktime / 365, 5) if year_days and avg_worktime else None

            assignments.setdefault(idx, []).append({
                'fault': input_date.strftime('%Y-%m-%d'),
                'fault_day': days,
                'fault_time': f_time,
                'state': 'suspension',
            })

    output_rows = []
    for _, row in result.iterrows():
        id_idx = row['identifier_index']
        res_list = assignments.get(id_idx, [])
        if not res_list:
            output_rows.append(row.copy())
        else:
            for item in res_list:
                new_row = row.copy()
                new_row['fault_1'] = item['fault']
                new_row['fault_day_1'] = item['fault_day']
                new_row['fault_time_1'] = item['fault_time']
                new_row['state_1'] = item['state']
                output_rows.append(new_row)

    return pd.DataFrame(output_rows).reset_index(drop=True)
