# -*- coding: utf-8 -*-
"""
时间完整性检查脚本
检查指定文件夹中所有文件的时间完整性，生成详细的Excel报告
"""

from pathlib import Path
from datetime import datetime
import sys
import os
# 添加备用功能模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from time_completeness_checker import TimeCompletenessChecker

# ==================== 配置区域 ====================
# 请在此处修改检查参数

# 要检查的文件夹路径
FOLDER_PATH = r"D:\useful\01-work file\07.报告\00-自动报告目录\佛清广高速公路铺锦互通主线3号桥\原始数据\倾角"
# FOLDER_PATH = r"D:\useful\01-work file\07.报告\00-自动报告目录\佛清广高速公路铺锦互通主线3号桥\原始数据\位移"



# 检查的时间区间
START_DATE = "2025-01-01"  # 开始日期，格式：YYYY-MM-DD
END_DATE = "2025-11-13"    # 结束日期，格式：YYYY-MM-DD

# ==================== 配置区域结束 ====================


def main():
    """主函数"""
    print("=" * 80)
    print("时间完整性检查工具")
    print("=" * 80)
    
    # 使用固定的配置参数
    folder_path = FOLDER_PATH
    start_date = START_DATE
    end_date = END_DATE
    
    print(f"\n📋 检查配置:")
    print(f"  文件夹路径: {folder_path}")
    print(f"  开始日期: {start_date}")
    print(f"  结束日期: {end_date}")
    
    # 验证输入
    if not folder_path:
        print("❌ 错误: 文件夹路径不能为空")
        return
    
    if not Path(folder_path).exists():
        print(f"❌ 错误: 文件夹不存在: {folder_path}")
        return
    
    try:
        # 创建检查器
        checker = TimeCompletenessChecker(
            folder_path=folder_path,
            start_date=start_date,
            end_date=end_date
        )
        
        # 执行检查
        print("\n" + "=" * 80)
        results = checker.check_all_files()
        
        if not results:
            print("\n⚠️ 没有找到任何文件或检查结果为空")
            return
        
        # 生成报告
        print("\n" + "=" * 80)
        report_path = checker.generate_report(results)
        
        # 显示摘要
        print("\n" + "=" * 80)
        print("📊 检查摘要:")
        print("=" * 80)
        
        total_files = len(results)
        error_files = sum(1 for r in results.values() if 'error' in r)
        files_with_missing = sum(1 for r in results.values() 
                                if 'error' not in r and r.get('missing_count', 0) > 0)
        total_records = sum(r.get('total_records', 0) for r in results.values() if 'error' not in r)
        total_missing = sum(r.get('missing_count', 0) for r in results.values() if 'error' not in r)
        
        print(f"  总文件数: {total_files}")
        print(f"  错误文件数: {error_files}")
        print(f"  有缺失的文件数: {files_with_missing}")
        print(f"  总记录数: {total_records:,}")
        print(f"  总缺失天数: {total_missing:,}")
        
        # 计算整体缺失率（基于天数）
        expected_days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1
        if expected_days > 0:
            # 计算所有文件中有数据的唯一天数
            all_dates = set()
            for r in results.values():
                if 'error' not in r:
                    all_dates.update(r.get('daily_stats', {}).keys())
            actual_days = len(all_dates)
            total_missing_days = expected_days - actual_days
            missing_rate = (total_missing_days / expected_days) * 100
            print(f"  整体缺失率: {missing_rate:.2f}% (缺失 {total_missing_days} 天 / 共 {expected_days} 天)")
        
        print(f"\n✅ 检查完成！详细报告已保存到: {report_path}")
        print("=" * 80)
        
    except ValueError as e:
        print(f"❌ 参数错误: {str(e)}")
    except Exception as e:
        print(f"❌ 检查过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

