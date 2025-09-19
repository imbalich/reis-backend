#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence, List, Dict, Any
from datetime import datetime, date
import pandas as pd
import io

from sqlalchemy import Select

from backend.database.db import async_db_session
from backend.app.datamanage.crud.crud_warehouse import warehouse_dao
from backend.app.datamanage.schema.warehouse import (
    WarehouseImportRow,
    WarehouseImportResponse,
    WarehouseExcelImportRow,
    WarehouseExcelImportResponse,
    GetWarehouseDetails,
    GetWarehouseListResponse,
    WarehouseFilterParam,
)


class WarehouseService:
    """仓库服务类"""

    async def get_select(
        self,
        area: str | None = None,
        name: str | None = None,
        code: str | None = None,
    ) -> Select:
        """
        获取仓库查询语句

        :param area: 归属区域
        :param name: 库房名称
        :param code: 库房编码
        :return: 查询语句
        """
        return await warehouse_dao.get_select(area=area, name=name, code=code)

    async def import_from_excel(
        self, excel_content: bytes
    ) -> WarehouseExcelImportResponse:
        """
        从Excel导入仓库数据（完全覆盖）

        Excel格式要求：
        - Sheet名称：配置表
        - 表头：区域、库房编号、库房名称、二级配属、创建人、更新时间
        - 第一行为表头，从第二行开始为数据
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(
                io.BytesIO(excel_content), sheet_name="配置表", engine="openpyxl"
            )

            # 验证列名
            expected_columns = [
                "区域",
                "库房编号",
                "库房名称",
                "二级配属",
                "创建人",
                "更新时间",
            ]
            if not all(col in df.columns for col in expected_columns):
                missing_cols = [
                    col for col in expected_columns if col not in df.columns
                ]
                return WarehouseExcelImportResponse(
                    total_rows=0,
                    success_rows=0,
                    failed_rows=0,
                    errors=[f"Excel文件格式错误：缺少必要的列 {missing_cols}"],
                )

            # 处理数据
            total_rows = len(df)
            success_rows = 0
            failed_rows = 0
            errors = []
            warehouses_data = []
            for index, row in df.iterrows():
                try:
                    # 验证必填字段
                    if pd.isna(row["库房编号"]) or pd.isna(row["库房名称"]):
                        failed_rows += 1
                        errors.append(f"第{index+2}行：库房编号、库房名称为必填项")
                        continue

                    # 获取数据
                    area = (
                        str(row["区域"]).strip() if not pd.isna(row["区域"]) else None
                    )
                    code = str(row["库房编号"]).strip()
                    name = str(row["库房名称"]).strip()
                    allotment_two = (
                        str(row["二级配属"]).strip()
                        if not pd.isna(row["二级配属"])
                        else None
                    )
                    created_by = (
                        str(row["创建人"]).strip()
                        if not pd.isna(row["创建人"])
                        else None
                    )

                    # 处理更新时间
                    changed_time = None
                    if not pd.isna(row["更新时间"]):
                        try:
                            if isinstance(row["更新时间"], str):
                                changed_time = datetime.strptime(
                                    row["更新时间"], "%Y-%m-%d"
                                ).date()
                            else:
                                changed_time = row["更新时间"].date()
                        except:
                            # 如果日期格式不正确，记录错误但继续处理
                            errors.append(f"第{index+2}行：更新时间格式不正确，已忽略")

                    # 构建数据
                    warehouse_data = {
                        "area": area,
                        "code": code,
                        "name": name,
                        "allotment_two": allotment_two,
                        "created_by": created_by,
                        "changed_time": changed_time,
                    }

                    warehouses_data.append(warehouse_data)
                    success_rows += 1

                except Exception as e:
                    failed_rows += 1
                    error_msg = str(e)
                    # 提供更详细的错误信息
                    if "NOT NULL constraint failed" in error_msg:
                        errors.append(f"第{index+2}行：必填字段不能为空")
                    elif (
                        "Data too long" in error_msg
                        or "String data, right truncated" in error_msg
                    ):
                        errors.append(f"第{index+2}行：数据长度超出限制")
                    else:
                        errors.append(f"第{index+2}行：{error_msg}")

            # 如果数据有效，执行数据库操作
            if warehouses_data:
                async with async_db_session() as db:
                    # 清空现有数据
                    await warehouse_dao.clear_all(db)
                    # 批量创建新数据
                    await warehouse_dao.bulk_create(db, warehouses_data)

            return WarehouseExcelImportResponse(
                total_rows=total_rows,
                success_rows=success_rows,
                failed_rows=failed_rows,
                errors=errors,
            )

        except Exception as e:
            return WarehouseExcelImportResponse(
                total_rows=0,
                success_rows=0,
                failed_rows=0,
                errors=[f"Excel处理失败：{str(e)}"],
            )


warehouse_service = WarehouseService()
