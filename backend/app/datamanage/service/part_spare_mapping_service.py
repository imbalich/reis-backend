#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
from typing import Optional, List
import pandas as pd
from datetime import date

from backend.database.db import async_db_session
from backend.app.datamanage.crud.crud_part_spare_mapping import (
    part_spare_mapping_dao,
)
from backend.app.datamanage.schema.part_spare_mapping import (
    PartSpareMappingExcelImportResponse,
    PartSpareMappingExcelImportRow,
)


class PartSpareMappingService:
    @staticmethod
    async def get_select(
        product_model: Optional[str] = None,
        derived_code: Optional[str] = None,
        original_part_name: Optional[str] = None,
        original_part_code: Optional[str] = None,
        spare_part_name: Optional[str] = None,
        spare_part_code: Optional[str] = None,
    ):
        return await part_spare_mapping_dao.get_select(
            product_model=product_model,
            derived_code=derived_code,
            original_part_name=original_part_name,
            original_part_code=original_part_code,
            spare_part_name=spare_part_name,
            spare_part_code=spare_part_code,
        )

    @staticmethod
    async def import_from_excel(
        excel_content: bytes,
    ) -> PartSpareMappingExcelImportResponse:
        try:
            df = pd.read_excel(io.BytesIO(excel_content), sheet_name="配置表")

            required_columns = [
                "产品型号",
                "派生码",
                "零部件名称（原装）",
                "零部件物料编码（原装）",
                "零部件名称（备品）",
                "零部件物料编码（备品）",
                "创建人",
                "更新时间",
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return PartSpareMappingExcelImportResponse(
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
                    # 验证必填字段
                    if (
                        pd.isna(row["产品型号"])
                        or pd.isna(row["派生码"])
                        or pd.isna(row["零部件名称（原装）"])
                        or pd.isna(row["零部件物料编码（原装）"])
                        or pd.isna(row["零部件名称（备品）"])
                        or pd.isna(row["零部件物料编码（备品）"])
                    ):
                        failed_count += 1
                        errors.append(
                            f"第{index+2}行: 产品型号、派生码、零部件名称和编码为必填项"
                        )
                        continue

                    # 数据转换和验证
                    product_model = str(row["产品型号"]).strip()
                    derived_code = str(row["派生码"]).strip()
                    original_part_name = str(row["零部件名称（原装）"]).strip()
                    original_part_code = str(row["零部件物料编码（原装）"]).strip()
                    spare_part_name = str(row["零部件名称（备品）"]).strip()
                    spare_part_code = str(row["零部件物料编码（备品）"]).strip()
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

                    valid_data.append(
                        {
                            "product_model": product_model,
                            "derived_code": derived_code,
                            "original_part_name": original_part_name,
                            "original_part_code": original_part_code,
                            "spare_part_name": spare_part_name,
                            "spare_part_code": spare_part_code,
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
                    await part_spare_mapping_dao.clear_all(db)
                    # 批量插入新数据
                    await part_spare_mapping_dao.bulk_create(db, valid_data)

            return PartSpareMappingExcelImportResponse(
                total_rows=len(df),
                success_rows=success_count,
                failed_rows=failed_count,
                errors=errors,
            )

        except Exception as e:
            return PartSpareMappingExcelImportResponse(
                total_rows=0,
                success_rows=0,
                failed_rows=0,
                errors=[f"Excel文件解析失败: {str(e)}"],
            )


part_spare_mapping_service = PartSpareMappingService()
