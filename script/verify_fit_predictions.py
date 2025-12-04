#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
拟合预测验证脚本

功能：
1. 读取Excel文件（包含产品型号、零部件物料编码、input_date）
2. 对每个输入执行拟合
3. 计算多个时间区间的预测值
4. 导出结果到CSV文件

使用方法：
    python script/verify_fit_predictions.py

配置说明：
1. 修改 EXCEL_INPUT_PATH 为Excel文件路径
2. 修改 TIME_INTERVALS 为需要计算的时间区间列表
3. 修改 FIT_METHOD 为拟合方法（可选：MLE, LS, RRX, RRY）
4. 修改 OUTPUT_PATH 为输出CSV文件路径（可选）
"""

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.fit.utils.fit_verification_utils import FitVerificationUtils
from backend.app.fit.schema.fit_param import FitMethodType


async def main():
    """
    主函数
    """
    # ========== 配置参数 ==========

    # Excel输入文件路径
    EXCEL_INPUT_PATH = "script/weibull.xlsx"  # 修改为实际路径

    # 时间区间列表（每个元素为 (start_date, end_date)）
    # 示例：计算未来6个月，每个月一个区间
    base_date = date(2023, 1, 1)  # 基准日期，可以根据需要修改
    TIME_INTERVALS: List[Tuple[date, date]] = [
        (base_date, base_date + timedelta(days=365)),  # 第1个年
        (base_date + timedelta(days=365), base_date + timedelta(days=730)),  # 第2个年
        (base_date + timedelta(days=730), base_date + timedelta(days=1095)),  # 第3个年
        # (base_date + timedelta(days=1095), base_date + timedelta(days=1460)),  # 第4个年
        # (base_date + timedelta(days=1460), base_date + timedelta(days=1825)),  # 第5个年
    ]

    # 拟合方法
    FIT_METHOD = FitMethodType.MLE  # 可选：MLE, LS, RRX, RRY

    # 输出CSV文件路径（可选，如果为None则自动生成）
    OUTPUT_PATH = None  # 例如: "output/fit_predictions_20250101.csv"

    # ========== 执行验证 ==========

    print("=" * 80)
    print("拟合预测验证")
    print("=" * 80)
    print(f"Excel输入文件: {EXCEL_INPUT_PATH}")
    print(f"拟合方法: {FIT_METHOD.value}")
    print(f"时间区间数量: {len(TIME_INTERVALS)}")
    print("=" * 80)
    print()

    try:
        # 1. 读取Excel输入
        print("正在读取Excel文件...")
        input_data = await FitVerificationUtils.read_excel_input(EXCEL_INPUT_PATH)
        print(f"读取到 {len(input_data)} 条输入数据")
        print()

        # 2. 对每个输入计算预测值
        all_results = []

        for idx, item in enumerate(input_data, 1):
            print(
                f"[{idx}/{len(input_data)}] 处理: {item['model']} - {item['part']} (input_date: {item['input_date']})"
            )

            try:
                results = (
                    await FitVerificationUtils.calculate_predictions_for_intervals(
                        model=item["model"],
                        part=item["part"],
                        input_date=item["input_date"],
                        time_intervals=TIME_INTERVALS,
                        method=FIT_METHOD,
                    )
                )
                all_results.extend(results)
                print(f"  成功: 计算了 {len(results)} 个时间区间的预测值")
            except Exception as e:
                print(f"  错误: {str(e)}")
                # 即使失败也添加错误记录
                for start_date, end_date in TIME_INTERVALS:
                    all_results.append(
                        {
                            "model": item["model"],
                            "part": item["part"],
                            "input_date": item["input_date"],
                            "start_date": start_date,
                            "end_date": end_date,
                            "prediction": None,
                            "distribution": None,
                            "product_count": None,
                            "error": str(e),
                        }
                    )
            print()

        # 3. 导出结果
        if OUTPUT_PATH is None:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            OUTPUT_PATH = f"output/fit_predictions_{timestamp}.csv"

        print("正在导出结果...")
        FitVerificationUtils.export_to_csv(all_results, OUTPUT_PATH)

        # 4. 统计信息
        print()
        print("=" * 80)
        print("统计信息")
        print("=" * 80)
        successful_count = sum(
            1 for r in all_results if r.get("prediction") is not None
        )
        failed_count = len(all_results) - successful_count
        print(f"总记录数: {len(all_results)}")
        print(f"成功: {successful_count}")
        print(f"失败: {failed_count}")
        print()

        if successful_count > 0:
            predictions = [
                r["prediction"] for r in all_results if r.get("prediction") is not None
            ]
            actual_counts = [
                r["actual_count"]
                for r in all_results
                if r.get("actual_count") is not None
            ]
            differences = [
                r["difference"] for r in all_results if r.get("difference") is not None
            ]

            print(f"预测值统计:")
            print(f"  最小值: {min(predictions):.4f}")
            print(f"  最大值: {max(predictions):.4f}")
            print(f"  平均值: {sum(predictions) / len(predictions):.4f}")
            print(f"  总和: {sum(predictions):.4f}")

            if actual_counts:
                print(f"\n实际值统计:")
                print(f"  最小值: {min(actual_counts)}")
                print(f"  最大值: {max(actual_counts)}")
                print(f"  平均值: {sum(actual_counts) / len(actual_counts):.2f}")
                print(f"  总和: {sum(actual_counts)}")

            if differences:
                print(f"\n差异统计 (预测值 - 实际值):")
                print(f"  最小值: {min(differences):.4f}")
                print(f"  最大值: {max(differences):.4f}")
                print(f"  平均值: {sum(differences) / len(differences):.4f}")
                print(f"  总和: {sum(differences):.4f}")

        print()
        print("验证完成！")

    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请检查Excel文件路径是否正确")
    except ValueError as e:
        print(f"错误: {e}")
        print("请检查Excel文件格式是否正确")
    except Exception as e:
        print(f"未预期的错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
