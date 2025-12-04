#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科学库存批量计算测试脚本
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.calcu.service.science_warehouse_service_change import (
    ScienceWarehouseServiceChange,
)
from backend.app.datamanage.crud.crud_warehouse_inventory import warehouse_inventory_dao
from backend.database.db import async_db_session


async def get_all_warehouse_spare_pairs():
    """
    从库房备品表中获取所有库房-备件组合
    :return: 库房-备件组合列表，格式为 [(warehouse_code, spare_part_code), ...]
    """
    async with async_db_session() as db:
        all_inventories = await warehouse_inventory_dao.get_all(db)
        # 提取唯一的库房-备件组合
        pairs = []
        seen = set()
        for inventory in all_inventories:
            pair = (inventory.warehouse_code, inventory.part_code)
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)
        return pairs


async def main():
    """主函数"""
    
    # warehouse_spare_pairs = [
    #     ("GA06", "CNR0000021939"),
    #     ("GB11", "CNR0000021939"),
    #     ("GC04", "CNR0000021939"),
    # ]
    # 从库房备品表中获取所有库房-备件组合
    print("正在从库房备品表中获取所有库房-备件组合...")
    warehouse_spare_pairs = await get_all_warehouse_spare_pairs()
    print(f"共找到 {len(warehouse_spare_pairs)} 个库房-备件组合")

    if not warehouse_spare_pairs:
        print("警告：未找到任何库房-备件组合，请检查数据库")
        return

    result = await ScienceWarehouseServiceChange.batch_warehouse_spare_calculate(
        time_interval_days=180,
        input_date="2025-12-01",
        warehouse_spare_pairs=warehouse_spare_pairs,
        save_to_db=True,
    )

    print("=" * 80)
    print("批量计算结果")
    print("=" * 80)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
