# -*- coding: utf-8 -*-
"""
统一数据下载入口
整合所有下载模块，提供统一的调用接口
"""

import os
import sys
from datetime import datetime
import time

# 导入配置
from config import (
    BRIDGES_TO_DOWNLOAD, validate_config,
    OUTPUT_ROOT, START_DATE, END_DATE,
    get_enabled_data_types, get_other_data_categories
)

# 导入下载器
from downloaders.other_data_downloader import OtherDataDownloader
from downloaders.ship_collision_downloader import ShipCollisionDownloader
from downloaders.vehicle_load_downloader import VehicleLoadDownloader

# 导入API检查器
from utils.api_checker import APIConnectivityChecker

class UnifiedDownloader:
    """统一数据下载器"""

    def __init__(self, data_type=1):
        self.other_downloader = OtherDataDownloader(data_type=data_type)
        self.ship_downloader = ShipCollisionDownloader()
        self.vehicle_downloader = VehicleLoadDownloader()
        self.api_checker = APIConnectivityChecker()



    def download_all_data(self, bridge_names=None, data_types=None, skip_api_check=False):
        """
        下载所有指定桥梁的所有类型数据
        
        Args:
            bridge_names: 桥梁名称列表，如果为None则使用配置文件中的桥梁列表
            data_types: 数据类型列表，可选值：['other', 'ship', 'vehicle']，如果为None则使用配置文件中的设置
            skip_api_check: 是否跳过API检查，默认False
        """
        print("🚀 开始统一数据下载...")
        print(f"📋 配置信息:")
        print(f"  - 输出根目录: {OUTPUT_ROOT}")
        print(f"  - 时间范围: {START_DATE} 到 {END_DATE}")
        
        # 验证配置
        if not validate_config():
            print("❌ 配置验证失败，请检查配置文件")
            print("💡 请检查以下项目:")
            print("   - 输出目录是否存在且可写")
            print("   - Excel配置文件是否存在")
            print("   - 时间范围是否有效")
            print("   - API密钥是否正确")
            return False

        # 确定要下载的桥梁
        if bridge_names is None:
            bridge_names = BRIDGES_TO_DOWNLOAD
        print(f"  - 目标桥梁: {bridge_names}")

        # 确定要下载的数据类型
        if data_types is None:
            data_types = get_enabled_data_types()
        print(f"  - 数据类型: {data_types}")
        
        # 显示详细的数据类型配置
        print(f"  - 其他数据类型: {get_other_data_categories()}")
        print(f"  - 船撞数据: {'是' if 'ship' in data_types else '否'}")
        print(f"  - 车辆荷载数据: {'是' if 'vehicle' in data_types else '否'}")

        # API连通性检查（可选）
        if not skip_api_check:
            print(f"\n🔍 开始API连通性检查...")
            api_results = self._check_api_connectivity(data_types)
            
            # 显示API检查摘要
            summary = self.api_checker.get_summary(api_results)
            print(summary)
            
            # 检查API连通性
            if not self.api_checker.is_all_apis_connected(api_results):
                print("❌ API连通性检查失败，无法开始下载")
                print("💡 请检查以下项目:")
                print("   - 网络连接是否正常")
                print("   - API服务器是否可用")
                print("   - API密钥是否正确")
                print("   - 防火墙设置是否允许连接")
                print("\n🔧 建议操作:")
                print("   - 使用 'python main_downloader.py check' 单独检查API连通性")
                print("   - 联系系统管理员确认API服务状态")
                return False
            
            print("✅ API连通性检查通过，开始下载...")
        else:
            print("⚠️ 跳过API连通性检查，直接开始下载...")

        total_start = time.perf_counter()
        success_count = 0
        total_bridges = len(bridge_names)

        for i, bridge_name in enumerate(bridge_names, 1):
            print(f"\n{'='*60}")
            print(f"🔧 开始处理桥梁: {bridge_name} ({i}/{total_bridges})")
            print(f"{'='*60}")

            bridge_success = 0
            bridge_total = 0

            # 下载其他数据（温湿度等）
            if 'other' in data_types:
                bridge_total += 1
                print(f"\n📊 下载其他数据...")
                if self.other_downloader.download_bridge_data(bridge_name):
                    bridge_success += 1
                    print(f"✅ {bridge_name} 其他数据下载成功")
                else:
                    print(f"❌ {bridge_name} 其他数据下载失败")

            # 下载船撞数据
            if 'ship' in data_types:
                bridge_total += 1
                print(f"\n🚢 下载船撞数据...")
                if self.ship_downloader.download_bridge_data(bridge_name):
                    bridge_success += 1
                    print(f"✅ {bridge_name} 船撞数据下载成功")
                else:
                    print(f"❌ {bridge_name} 船撞数据下载失败")

            # 下载车辆荷载数据
            if 'vehicle' in data_types:
                bridge_total += 1
                print(f"\n🚗 下载车辆荷载数据...")
                if self.vehicle_downloader.download_bridge_data(bridge_name):
                    bridge_success += 1
                    print(f"✅ {bridge_name} 车辆荷载数据下载成功")
                else:
                    print(f"❌ {bridge_name} 车辆荷载数据下载失败")

            print(f"\n📊 {bridge_name} 完成情况: {bridge_success}/{bridge_total}")
            if bridge_success > 0:
                success_count += 1

        total_elapsed = time.perf_counter() - total_start
        print(f"\n{'='*60}")
        print(f"🎉 统一下载完成！")
        print(f"📊 统计信息:")
        print(f"  - 总耗时: {total_elapsed:.2f}秒")
        print(f"  - 成功桥梁: {success_count}/{total_bridges}")
        print(f"  - 成功率: {(success_count/total_bridges*100):.1f}%")
        print(f"  - 输出目录: {OUTPUT_ROOT}")
        
        if success_count == total_bridges:
            print(f"  - 状态: ✅ 全部成功")
        elif success_count > 0:
            print(f"  - 状态: ⚠️ 部分成功")
        else:
            print(f"  - 状态: ❌ 全部失败")
        
        print(f"{'='*60}")

        return success_count > 0

    def download_single_bridge(self, bridge_name: str, data_types=None):
        """
        下载单个桥梁的数据
        
        Args:
            bridge_name: 桥梁名称
            data_types: 数据类型列表，可选值：['other', 'ship', 'vehicle']，如果为None则下载所有类型
        """
        return self.download_all_data([bridge_name], data_types)

    def download_single_data_type(self, data_type: str, bridge_names=None):
        """
        下载单个类型的数据
        
        Args:
            data_type: 数据类型，可选值：'other', 'ship', 'vehicle'
            bridge_names: 桥梁名称列表，如果为None则使用配置文件中的桥梁列表
        """
        return self.download_all_data(bridge_names, [data_type])

    def get_available_bridges(self):
        """获取所有模块可用的桥梁列表"""
        bridges = set()
        
        # 获取其他数据模块的桥梁
        try:
            other_bridges = self.other_downloader.get_available_bridges()
            bridges.update(other_bridges)
        except Exception as e:
            print(f"获取其他数据桥梁列表失败: {e}")
        
        # 获取船撞数据模块的桥梁
        try:
            ship_bridges = self.ship_downloader.get_available_bridges()
            bridges.update(ship_bridges)
        except Exception as e:
            print(f"获取船撞数据桥梁列表失败: {e}")
        
        # 获取车辆荷载数据模块的桥梁
        try:
            vehicle_bridges = self.vehicle_downloader.get_available_bridges()
            bridges.update(vehicle_bridges)
        except Exception as e:
            print(f"获取车辆荷载数据桥梁列表失败: {e}")
        
        return sorted(list(bridges))

    def _check_api_connectivity(self, data_types):
        """
        根据要下载的数据类型检查相应的API连通性
        
        Args:
            data_types: 要下载的数据类型列表
            
        Returns:
            API检查结果字典
        """
        # 根据数据类型确定需要检查的API
        api_names_to_check = []
        
        if 'other' in data_types:
            api_names_to_check.append("其他数据")
        if 'ship' in data_types:
            api_names_to_check.append("船撞数据")
        if 'vehicle' in data_types:
            api_names_to_check.append("车辆荷载数据")
        
        if not api_names_to_check:
            print("⚠️ 没有需要检查的API接口")
            return {}
        
        # 检查指定的API接口
        return self.api_checker.check_specific_apis(api_names_to_check)

def main():
    """主函数"""
    downloader = UnifiedDownloader()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'all':
            # 下载所有数据
            downloader.download_all_data()
        
        elif command == 'bridge':
            # 下载指定桥梁的所有数据
            if len(sys.argv) > 2:
                bridge_name = sys.argv[2]
                downloader.download_single_bridge(bridge_name)
            else:
                print("❌ 请指定桥梁名称")
                print("用法: python main_downloader.py bridge <桥梁名称>")
        
        elif command == 'type':
            # 下载指定类型的数据
            if len(sys.argv) > 2:
                data_type = sys.argv[2].lower()
                if data_type in ['other', 'ship', 'vehicle']:
                    downloader.download_single_data_type(data_type)
                else:
                    print("❌ 无效的数据类型")
                    print("有效类型: other, ship, vehicle")
            else:
                print("❌ 请指定数据类型")
                print("用法: python main_downloader.py type <数据类型>")
        
        elif command == 'list':
            # 列出可用桥梁
            bridges = downloader.get_available_bridges()
            print("📋 可用桥梁列表:")
            for bridge in bridges:
                print(f"  - {bridge}")
        
        elif command == 'check':
            # 检查API连通性
            print("🔍 检查所有API接口连通性...")
            results = downloader.api_checker.check_all_apis()
            summary = downloader.api_checker.get_summary(results)
            print(summary)
            
            if downloader.api_checker.is_all_apis_connected(results):
                print("🎉 所有API接口连通正常！")
            else:
                print("⚠️ 部分API接口连通异常，请检查网络或联系管理员。")
        
        elif command == 'help':
            # 显示帮助信息
            print("📖 使用说明:")
            print("  python main_downloader.py all                    # 下载所有数据")
            print("  python main_downloader.py bridge <桥梁名称>       # 下载指定桥梁的所有数据")
            print("  python main_downloader.py type <数据类型>        # 下载指定类型的数据")
            print("  python main_downloader.py list                   # 列出可用桥梁")
            print("  python main_downloader.py check                  # 检查API连通性")
            print("  python main_downloader.py help                   # 显示帮助信息")
            print("\n数据类型:")
            print("  other   - 其他数据（温湿度等）")
            print("  ship    - 船撞数据")
            print("  vehicle - 车辆荷载数据")
        
        else:
            print(f"❌ 未知命令: {command}")
            print("使用 'python main_downloader.py help' 查看帮助信息")
    
    else:
        # 默认下载所有数据
        print("📝 未指定命令，默认下载所有数据")
        print("使用 'python main_downloader.py help' 查看帮助信息")
        downloader.download_all_data()

if __name__ == "__main__":
    main() 