import asyncio
import sys
import os

sys.path.append(os.path.dirname(__file__))

from backend.database.db import async_db_session
from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.fit.schema.base_param import DespatchParam


async def check_exclude_repair_level_data():
    async with async_db_session() as db:
        # 查询型号为 YGN2Q213 的等级修 despatch 数据（排除新造和故障修）
        despatchs = await despatch_dao.get_by_model_exclude_repair_level(db, "YGN2Q213")
        print(f"找到 {len(despatchs)} 条等级修 despatch 记录")

        # 检查每条记录的字段值
        null_count = 0
        for i, despatch in enumerate(despatchs):
            if despatch.repair_level_num is None:
                null_count += 1
                print(f"\n记录 {i+1} (ID: {despatch.id}):")
                print(f"  model: {despatch.model}")
                print(f"  identifier: {despatch.identifier}")
                print(f"  repair_level: {despatch.repair_level}")
                print(f"  life_cycle_time: {despatch.life_cycle_time}")
                print(f"  repair_level_num: {despatch.repair_level_num} (NULL!)")

                # 尝试转换为 DespatchParam
                try:
                    despatch_param = DespatchParam.model_validate(despatch)
                    print("  [SUCCESS] 转换成功")
                except Exception as e:
                    print(f"  [ERROR] 转换失败: {e}")

        print(f"\n总结: 共 {null_count} 条记录的 repair_level_num 为 NULL")


if __name__ == "__main__":
    asyncio.run(check_exclude_repair_level_data())
