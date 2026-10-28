#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用已实现的零部件预测，核对 YGZN2Q271 / PS00 在两个年度窗口的故障次数。"""
import asyncio
import sys
import traceback
from pathlib import Path

import pandas as pd
from openpyxl.utils import get_column_letter
from sqlalchemy import func, select

project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

from backend.app.datamanage.crud.crud_failure import CRUDFailure
from backend.app.datamanage.model import FailureModel
from backend.app.forecast.schema.forecast_param import PartForecastParam
from backend.app.forecast.service.part_forecast_service import part_forecast_service
from backend.common.product_config import apply_product_config_code_filter
from backend.database.db import async_db_session

MODEL = "YGZN2Q271"
CONFIG = "PS00"
PARTS = [
    "CNR0000615870",
    "CNR0000622160",
    "CNR0000622161",
    "CNR0000637935",
    "CNR0000637936",
    "M000000673039",
    "M000000717648",
    "M000002469279",
    "Z500000183465",
    "Z500000189932",
    "CNR0000021938",
    "CNR0000615857",
    "CNR0000028904",
    "CNR0000231133",
    "CNR0000231158",
]
WINDOWS = [
    ("2024", "2024-01-01", "2024-12-30"),
    ("2025", "2025-01-01", "2025-12-30"),
]
OUTPUT = Path(__file__).resolve().parent / "YGZN2Q271_PS00_两个年度窗口预测.xlsx"


async def count_window_failures(part: str, start: str, end: str) -> int:
    """窗口内实际故障条数，过滤条件与打标拟合的 get_by_model_and_part 相同。

    终判物料编码、型号、派生码（PS00 含空值）、非零公里、责任不含「用户」、生产日期非空。
    日期由拟合用的「不晚于截止日」改为窗口闭区间，含开始日和结束日。
    每条故障记录计一次，不把同一产品同一天合并。
    """
    async with async_db_session() as db:
        where_list = [
            FailureModel.product_model == MODEL,
            FailureModel.fault_material_code == part,
            FailureModel.is_zero_distance == 0,
            CRUDFailure._non_user_responsibility_condition(FailureModel),
            FailureModel.manufacturing_date.isnot(None),
            FailureModel.discovery_date >= start,
            FailureModel.discovery_date <= end,
        ]
        apply_product_config_code_filter(where_list, FailureModel.product_config_code, CONFIG)
        stmt = select(func.count()).select_from(FailureModel).where(*where_list)
        count = await db.scalar(stmt)
        return int(count or 0)


def deviation_rate(predicted, actual) -> float | None:
    """偏差率 = (预测次数 - 实际故障次数) / 实际故障次数。实际为 0 或预测缺失时留空。"""
    if predicted is None or actual in (None, 0) or pd.isna(predicted):
        return None
    return (float(predicted) - float(actual)) / float(actual)


def with_actual(summary: dict, actual: int) -> dict:
    """把实际次数和偏差率插到预测次数右侧，其余列顺序不变。"""
    ordered = {}
    for key, value in summary.items():
        ordered[key] = value
        if key == "预测次数":
            ordered["实际故障次数"] = actual
            ordered["偏差率"] = deviation_rate(value, actual)
    return ordered


async def forecast_one(part: str, label: str, start: str, end: str) -> tuple[dict, list[dict]]:
    result = await part_forecast_service.forecast(
        PartForecastParam(
            model=MODEL,
            part=part,
            product_config_code=CONFIG,
            input_date=start,
            end_date=end,
        )
    )
    trace = result.trace
    summary = {
        "型号": result.model,
        "派生码": result.product_config_code,
        "物料编码": result.part,
        "窗口": label,
        "拟合截止": start,
        "窗口开始": str(result.input_date),
        "窗口结束": str(result.end_date),
        "预测次数": result.quantity,
        "参与台数": result.unit_count,
        "选定分布": trace.distribution,
        "每天运行小时": trace.hours_per_day,
        "BOM用量": trace.bom_quantity,
        "乘BOM前次数": trace.product_quantity,
        "窗口前已上线": trace.in_service_count,
        "窗口内上线": trace.entered_during_window_count,
        "上线晚于结束": trace.skipped_count,
        "卡点": "；".join(trace.notes),
        "错误": "",
    }
    details = [
        {
            "物料编码": part,
            "窗口": label,
            "产品编号": unit.product_number,
            "上线日": str(unit.online_date),
            "情况": unit.situation,
            "A点运行小时": unit.hours_at_start,
            "B点运行小时": unit.hours_at_end,
            "乘BOM前差值": unit.contribution,
        }
        for unit in result.units
    ]
    return summary, details


def write_workbook(summaries: list[dict], details: list[dict]) -> None:
    summary_frame = pd.DataFrame(summaries)
    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
        summary_frame.to_excel(writer, sheet_name="汇总", index=False)
        pd.DataFrame(details).to_excel(writer, sheet_name="产品明细", index=False)
        if "偏差率" in summary_frame.columns:
            sheet = writer.sheets["汇总"]
            column = summary_frame.columns.get_loc("偏差率") + 1
            letter = get_column_letter(column)
            for row in range(2, len(summary_frame) + 2):
                sheet[f"{letter}{row}"].number_format = "0.00%"


async def main() -> None:
    summaries = []
    details = []
    total = len(PARTS) * len(WINDOWS)
    done = 0
    for part in PARTS:
        for label, start, end in WINDOWS:
            done += 1
            print(f"[{done}/{total}] {part} {label} {start} -> {end}", flush=True)
            try:
                summary, rows = await forecast_one(part, label, start, end)
            except Exception as exc:  # noqa: BLE001
                print(f"失败 {part} {label}: {getattr(exc, 'msg', exc)}", flush=True)
                traceback.print_exc()
                summary = {
                    "型号": MODEL,
                    "派生码": CONFIG,
                    "物料编码": part,
                    "窗口": label,
                    "拟合截止": start,
                    "窗口开始": start,
                    "窗口结束": end,
                    "预测次数": None,
                    "参与台数": None,
                    "选定分布": "",
                    "每天运行小时": None,
                    "BOM用量": None,
                    "乘BOM前次数": None,
                    "窗口前已上线": None,
                    "窗口内上线": None,
                    "上线晚于结束": None,
                    "卡点": "",
                    "错误": str(getattr(exc, "msg", exc)),
                }
                rows = []
            actual = await count_window_failures(part, start, end)
            summaries.append(with_actual(summary, actual))
            details.extend(rows)
            write_workbook(summaries, details)
            print(f"已写入 {done}/{total} {OUTPUT.name}", flush=True)
    print(f"完成 {OUTPUT}", flush=True)


async def fill_existing() -> None:
    """只补实际故障次数和偏差率，不重新拟合。"""
    summary_frame = pd.read_excel(OUTPUT, sheet_name="汇总")
    details = pd.read_excel(OUTPUT, sheet_name="产品明细")
    rows = []
    for record in summary_frame.to_dict(orient="records"):
        start = str(record["窗口开始"])[:10]
        end = str(record["窗口结束"])[:10]
        actual = await count_window_failures(record["物料编码"], start, end)
        record.pop("实际故障次数", None)
        record.pop("偏差率", None)
        rows.append(with_actual(record, actual))
        print(f"{record['物料编码']} {record['窗口']} 实际={actual}", flush=True)
    write_workbook(rows, details.to_dict(orient="records"))
    print(f"完成 {OUTPUT}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--fill-actual":
        asyncio.run(fill_existing())
    else:
        asyncio.run(main())
