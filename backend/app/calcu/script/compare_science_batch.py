# 建议路径：backend/app/calcu/script/compare_science_batch.py
import argparse
import asyncio
import json
from datetime import timedelta, date
from pathlib import Path
import sys

import pandas as pd

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.db import async_db_session
from backend.app.calcu.model.science_warehouse_result import ScienceWarehouseResult
from backend.app.datamanage.crud.crud_failure import failure_dao, CRUDFailure
from backend.app.datamanage.crud.crud_warehouse import warehouse_dao
from backend.app.datamanage.crud.crud_allotment import allotment_dao
from backend.app.datamanage.crud.crud_part_spare_mapping import part_spare_mapping_dao
from backend.app.fit.utils.time_utils import dateutils
from sqlalchemy import select, and_
from typing import List, Dict, Any


def parse_args():
    parser = argparse.ArgumentParser(description="科学库存批次结果 vs 实际故障比对")
    parser.add_argument("calculation_id", help="批次号")
    parser.add_argument("--input-date", dest="input_date", help="覆盖计算截止日期，格式YYYY-MM-DD")
    parser.add_argument("--time-interval-days", dest="time_interval_days", type=int, help="覆盖时间间隔（天）")
    parser.add_argument("--output", dest="output", help="输出Excel路径，默认 compare.xlsx")
    return parser.parse_args()


async def get_spare_mappings(spare_part_code: str) -> List[Dict[str, Any]]:
    async with async_db_session() as db:
        mappings = await part_spare_mapping_dao.get_by_spare_part_code(db, spare_part_code)
        if not mappings:
            return []
        seen = set()
        result = []
        for m in mappings:
            key = (m.product_model, m.original_part_code, m.spare_part_code)
            if key in seen:
                continue
            seen.add(key)
            result.append(
                {
                    "product_model": m.product_model,
                    "original_part_code": m.original_part_code,
                }
            )
        return result


async def get_allotment_products(warehouse_code: str, model: str) -> List[str]:
    async with async_db_session() as db:
        allotments = await warehouse_dao.get_by_code(db, warehouse_code)
        if not allotments:
            return []
        allotment_two_list = [a.allotment_two for a in allotments if a.allotment_two is not None]
        if not allotment_two_list:
            return []
        products_set = set()
        for allotment_two in allotment_two_list:
            products = await allotment_dao.get_by_allotment_two_and_model(db, allotment_two, model)
            if products:
                products_set.update([p.product_number for p in products if p.product_number])
        return list(products_set)


async def query_failures(model: str, part: str, products: List[str], start_date: date, end_date: date):
    if not products:
        return 0, []
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    async with async_db_session() as db:
        cond = and_(
            failure_dao.model.product_model == model,
            failure_dao.model.fault_material_code == part,
            failure_dao.model.product_number.in_(products),
            failure_dao.model.discovery_date >= start_str,
            failure_dao.model.discovery_date <= end_str,
            failure_dao.model.is_zero_distance == 0,
            CRUDFailure._non_user_responsibility_condition(failure_dao.model),
        )
        stmt = select(failure_dao.model.report_id).where(cond)
        res = await db.execute(stmt)
        report_ids = [r for r in res.scalars().all() if r]
        return len(report_ids), report_ids


async def load_results(calculation_id: str) -> List[ScienceWarehouseResult]:
    async with async_db_session() as db:
        stmt = select(ScienceWarehouseResult).where(
            ScienceWarehouseResult.calculation_id == calculation_id
        ).order_by(ScienceWarehouseResult.id)
        res = await db.execute(stmt)
        return res.scalars().all()


async def main():
    args = parse_args()
    results = await load_results(args.calculation_id)

    summary_rows = []
    detail_rows = []

    for row in results:
        eff_input_date = dateutils.validate_and_parse_date(args.input_date) if args.input_date else row.input_date
        eff_interval = args.time_interval_days if args.time_interval_days is not None else row.time_interval_days
        window_start = eff_input_date
        window_end = eff_input_date + timedelta(days=eff_interval)

        mappings = await get_spare_mappings(row.spare_part_code)

        item_actual_failure = 0
        item_report_ids = []

        for mapping in mappings:
            model = mapping["product_model"]
            part = mapping["original_part_code"]
            products = await get_allotment_products(row.warehouse_code, model)

            if not products:
                detail_rows.append(
                    {
                        "calculation_id": args.calculation_id,
                        "warehouse_code": row.warehouse_code,
                        "warehouse_name": row.warehouse_name,
                        "spare_part_code": row.spare_part_code,
                        "spare_part_name": row.spare_part_name,
                        "model": model,
                        "fault_part": part,
                        "products_in_allotment": 0,
                        "actual_failure_count": 0,
                        "report_ids": "",
                        "note": "配属下无产品或未查到产品编号",
                        "window_start": window_start,
                        "window_end": window_end,
                    }
                )
                continue

            count, reports = await query_failures(model, part, products, window_start, window_end)
            item_actual_failure += count
            item_report_ids.extend(reports)
            detail_rows.append(
                {
                    "calculation_id": args.calculation_id,
                    "warehouse_code": row.warehouse_code,
                    "warehouse_name": row.warehouse_name,
                    "spare_part_code": row.spare_part_code,
                    "spare_part_name": row.spare_part_name,
                    "model": model,
                    "fault_part": part,
                    "products_in_allotment": len(products),
                    "actual_failure_count": count,
                    "report_ids": ",".join(reports),
                    "note": "",
                    "window_start": window_start,
                    "window_end": window_end,
                }
            )

        item_report_ids = sorted(list(set(item_report_ids)))
        summary_rows.append(
            {
                "calculation_id": args.calculation_id,
                "warehouse_code": row.warehouse_code,
                "warehouse_name": row.warehouse_name,
                "spare_part_code": row.spare_part_code,
                "spare_part_name": row.spare_part_name,
                "max_failure_count": row.max_failure_count,
                "required_quantity": row.required_quantity,
                "time_interval_days": eff_interval,
                "input_date": eff_input_date,
                "window_start": window_start,
                "window_end": window_end,
                "actual_failure_count": item_actual_failure,
                "report_ids": ",".join(item_report_ids),
                # 新增两列
                "required_minus_max_failure": row.required_quantity - row.max_failure_count,
                "required_minus_actual_failure": row.required_quantity - item_actual_failure,
            }
        )

    # 写入 Excel
    output_path = Path(args.output or "compare.xlsx")
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="summary", index=False)
        pd.DataFrame(detail_rows).to_excel(writer, sheet_name="details", index=False)

    print(f"已生成 Excel: {output_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())