#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
from typing import Optional, List
import pandas as pd
from datetime import date

from backend.database.db import async_db_session
from backend.app.datamanage.crud.crud_warehouse_inventory import warehouse_inventory_dao
from backend.app.datamanage.schema.warehouse_inventory import (
    WarehouseInventoryExcelImportResponse,
    WarehouseInventoryExcelImportRow,
)


class WarehouseInventoryService:
    @staticmethod
    async def get_select(
        warehouse_code: Optional[str] = None,
        warehouse_name: Optional[str] = None,
        part_code: Optional[str] = None,
        part_name: Optional[str] = None,
    ):
        return await warehouse_inventory_dao.get_select(
            warehouse_code=warehouse_code,
            warehouse_name=warehouse_name,
            part_code=part_code,
            part_name=part_name,
        )

    @staticmethod
    async def import_from_excel(
        excel_content: bytes,
    ) -> WarehouseInventoryExcelImportResponse:
        try:
            df = pd.read_excel(io.BytesIO(excel_content), sheet_name="配置表")

            required_columns = [
                "库房编号",
                "库房名称",
                "零部件物料编码",
                "零部件名称",
                "默认数量",
                "创建人",
                "更新时间",
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return WarehouseInventoryExcelImportResponse(
                    total_rows=0,
                    success_rows=0,
                    failed_rows=0,
                    errors=[f"缺少必要列: {', '.join(missing_columns)}"],
                )

            success_count = 0
            failed_count = 0
            errors = []
            valid_data = []

            for index, row in df.iterrows():
                try:
                    if pd.isna(row["库房编号"]) or pd.isna(row["零部件物料编码"]):
                        failed_count += 1
                        errors.append(
                            f"第{index+2}行: 库房编号和零部件物料编码为必填项"
                        )
                        continue

                    # 数据转换和验证
                    warehouse_code = str(row["库房编号"]).strip()
                    warehouse_name = (
                        str(row["库房名称"]).strip()
                        if not pd.isna(row["库房名称"])
                        else ""
                    )
                    part_code = str(row["零部件物料编码"]).strip()
                    part_name = (
                        str(row["零部件名称"]).strip()
                        if not pd.isna(row["零部件名称"])
                        else ""
                    )
                    default_quantity = (
                        int(row["默认数量"]) if not pd.isna(row["默认数量"]) else 1
                    )
                    created_by = (
                        str(row["创建人"]).strip()
                        if not pd.isna(row["创建人"])
                        else None
                    )

                    # 处理更新时间
                    changed_time = None
                    if not pd.isna(row["更新时间"]):
                        if isinstance(row["更新时间"], date):
                            changed_time = row["更新时间"]
                        else:
                            try:
                                changed_time = pd.to_datetime(row["更新时间"]).date()
                            except:
                                pass

                    # 验证默认数量
                    if default_quantity < 0:
                        failed_count += 1
                        errors.append(f"第{index+2}行: 默认数量不能为负数")
                        continue

                    valid_data.append(
                        {
                            "warehouse_code": warehouse_code,
                            "warehouse_name": warehouse_name,
                            "part_code": part_code,
                            "part_name": part_name,
                            "default_quantity": default_quantity,
                            "created_by": created_by,
                            "changed_time": changed_time,
                        }
                    )
                    success_count += 1

                except Exception as e:
                    failed_count += 1
                    errors.append(f"第{index+2}行: {str(e)}")

            # 如果有有效数据，执行批量导入
            if valid_data:
                async with async_db_session() as db:
                    # 清空现有数据
                    await warehouse_inventory_dao.clear_all(db)
                    # 批量插入新数据
                    await warehouse_inventory_dao.bulk_create(db, valid_data)

            return WarehouseInventoryExcelImportResponse(
                total_rows=len(df),
                success_rows=success_count,
                failed_rows=failed_count,
                errors=errors,
            )

        except Exception as e:
            return WarehouseInventoryExcelImportResponse(
                total_rows=0,
                success_rows=0,
                failed_rows=0,
                errors=[f"Excel文件解析失败: {str(e)}"],
            )


warehouse_inventory_service = WarehouseInventoryService()
