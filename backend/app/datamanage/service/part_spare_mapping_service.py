#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
from datetime import date
from typing import Optional

import pandas as pd

from backend.app.datamanage.crud.crud_part_spare_mapping import (
    part_spare_mapping_dao,
)
from backend.app.datamanage.schema.part_spare_mapping import (
    PartSpareMappingExcelImportResponse,
)
from backend.database.db import async_db_session


class PartSpareMappingService:
    @staticmethod
    async def get_select(
        product_model: Optional[str] = None,
        product_config_code: Optional[str] = None,
        original_part_name: Optional[str] = None,
        original_part_code: Optional[str] = None,
        spare_part_name: Optional[str] = None,
        spare_part_code: Optional[str] = None,
    ):
        return await part_spare_mapping_dao.get_select(
            product_model=product_model,
            product_config_code=product_config_code,
            original_part_name=original_part_name,
            original_part_code=original_part_code,
            spare_part_name=spare_part_name,
            spare_part_code=spare_part_code,
        )

    @staticmethod
    def _get_product_config_code_value(row: pd.Series) -> str | None:
        if "product_config_code" in row.index:
            raw_value = row["product_config_code"]
        elif "派生码" in row.index:
            raw_value = row["派生码"]
        else:
            return None

        if pd.isna(raw_value):
            return None

        value = str(raw_value).strip()
        return value or None

    @staticmethod
    async def import_from_excel(
        excel_content: bytes,
    ) -> PartSpareMappingExcelImportResponse:
        try:
            df = pd.read_excel(io.BytesIO(excel_content), sheet_name="配置表")

            required_columns = [
                "产品型号",
                "零部件名称（原装）",
                "零部件物料编码（原装）",
                "零部件名称（备品）",
                "零部件物料编码（备品）",
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
            errors: list[str] = []
            valid_data: list[dict[str, object]] = []

            for index, row in df.iterrows():
                try:
                    if (
                        pd.isna(row["产品型号"])
                        or pd.isna(row["零部件名称（原装）"])
                        or pd.isna(row["零部件物料编码（原装）"])
                        or pd.isna(row["零部件名称（备品）"])
                        or pd.isna(row["零部件物料编码（备品）"])
                    ):
                        failed_count += 1
                        errors.append(
                            f"第{index + 2}行: 产品型号、零部件名称和编码为必填项"
                        )
                        continue

                    product_model = str(row["产品型号"]).strip()
                    product_config_code = (
                        PartSpareMappingService._get_product_config_code_value(row)
                    )
                    original_part_name = str(row["零部件名称（原装）"]).strip()
                    original_part_code = str(row["零部件物料编码（原装）"]).strip()
                    spare_part_name = str(row["零部件名称（备品）"]).strip()
                    spare_part_code = str(row["零部件物料编码（备品）"]).strip()
                    created_by = (
                        str(row["创建人"]).strip()
                        if "创建人" in row.index and not pd.isna(row["创建人"])
                        else None
                    )

                    changed_time = None
                    if "更新时间" in row.index and not pd.isna(row["更新时间"]):
                        if isinstance(row["更新时间"], date):
                            changed_time = row["更新时间"]
                        else:
                            try:
                                changed_time = pd.to_datetime(row["更新时间"]).date()
                            except Exception:
                                changed_time = None

                    valid_data.append(
                        {
                            "product_model": product_model,
                            "product_config_code": product_config_code,
                            "original_part_name": original_part_name,
                            "original_part_code": original_part_code,
                            "spare_part_name": spare_part_name,
                            "spare_part_code": spare_part_code,
                            "created_by": created_by,
                            "changed_time": changed_time,
                        }
                    )
                    success_count += 1
                except Exception as exc:
                    failed_count += 1
                    errors.append(f"第{index + 2}行: {exc}")

            if valid_data:
                async with async_db_session() as db:
                    await part_spare_mapping_dao.clear_all(db)
                    await part_spare_mapping_dao.bulk_create(db, valid_data)

            return PartSpareMappingExcelImportResponse(
                total_rows=len(df),
                success_rows=success_count,
                failed_rows=failed_count,
                errors=errors,
            )

        except Exception as exc:
            return PartSpareMappingExcelImportResponse(
                total_rows=0,
                success_rows=0,
                failed_rows=0,
                errors=[f"Excel文件解析失败: {exc}"],
            )


part_spare_mapping_service = PartSpareMappingService()
