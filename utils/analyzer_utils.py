# -*- coding: utf-8 -*-
"""
分析器工具模块 - 提供统一的路径管理和数据发现功能
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from config import (
    OUTPUT_ROOT, 
    get_analyzer_data_dir, 
    get_analyzer_output_dir,
    create_analyzer_output_dir,
    get_available_bridges,
    get_available_data_types
)


class AnalyzerPathManager:
    """分析器路径管理器 - 统一管理所有分析器的路径"""
    
    def __init__(self, bridge_name: str):
        """
        初始化路径管理器
        
        Args:
           bridge_name: 桥极名称
        """
        self.bridge_name = bridge_name
        self.output_root = OUTPUT_ROOT
    
    def get_data_dir(self, data_type: str) -> Path:
        """
        获取指定数据类型的数据目录
        """
        unified = Path(get_analyzer_data_dir(self.bridge_name, data_type))
        return unified
    
    def get_output_dir(self, analyzer_type: str = None) -> Path:
        """
        获取分析器输出目录
        """
        return Path(get_analyzer_output_dir(self.bridge_name, analyzer_type))
    
    def create_output_dir(self, analyzer_type: str = None) -> Path:
        """
        创建并返回分析器输出目录
        """
        return Path(create_analyzer_output_dir(self.bridge_name, analyzer_type))
    
    def has_data(self, data_type: str) -> bool:
        """
        检查指定数据类型是否有数据
        """
        data_dir = self.get_data_dir(data_type)
        if not data_dir.exists():
            return False
        return any(data_dir.iterdir())
    
    def get_data_files(self, data_type: str, pattern: str = "*.txt") -> List[Path]:
        """
        获取指定数据类型的数据文件列表
        """
        data_dir = self.get_data_dir(data_type)
        if not data_dir.exists():
            return []
        return list(data_dir.rglob(pattern))


class DataDiscovery:
    """数据发现工具 - 自动发现可用的桥梁和数据类型"""
    
    @staticmethod
    def get_all_bridges() -> List[str]:
        bridges = set(get_available_bridges())
        return sorted(bridges)
    
    @staticmethod
    def get_bridge_data_types(bridge_name: str) -> List[str]:
        types = set(get_available_data_types(bridge_name))
        return sorted(types)
    
    @staticmethod
    def get_analysis_summary() -> Dict[str, List[str]]:
        summary = {}
        bridges = DataDiscovery.get_all_bridges()
        for bridge in bridges:
            data_types = DataDiscovery.get_bridge_data_types(bridge)
            if data_types:
                summary[bridge] = data_types
        return summary
    
    @staticmethod
    def print_summary():
        summary = DataDiscovery.get_analysis_summary()
        print("=" * 60)
        print("📊 数据可用性摘要")
        print("=" * 60)
        
        if not summary:
            print("⚠️ 未找到任何已下载的数据")
            print(f"   数据根目录: {OUTPUT_ROOT}")
            return
        
        print(f"\n📁 数据根目录: {OUTPUT_ROOT}")
        print(f"🌉 找到 {len(summary)} 座桥梁的数据:\n")
        
        for bridge, data_types in summary.items():
            print(f"  🌉 {bridge}")
            for data_type in data_types:
                data_dir = Path(get_analyzer_data_dir(bridge, data_type))
                file_count = len(list(data_dir.rglob("*.txt"))) if data_dir.exists() else 0
                print(f"    ✓ {data_type} ({file_count} 个文件)")
            print()
        
        print("=" * 60)


# 数据类型到分析器模块的映射 - 已优化为直接指向模块包 [NEW ARCH]
DATA_TYPE_TO_ANALYZER = {
    "温湿度": {
        "module": "analyzers.temperature_humidity",
        "class": "TemperatureHumidityAnalyzer",
        "description": "温湿度数据分析"
    },
    "车辆荷载": {
        "module": "analyzers.vehicle_load",
        "class": "VehicleLoadAnalyzer",
        "description": "车辆荷载数据分析"
    },
    "车辆荷载多年度": {
        "module": "analyzers.multi_year_vehicle",
        "class": "MultiYearVehicleAnalyzer",
        "description": "车辆荷载多年度对比分析"
    },
    "船撞": {
        "module": "analyzers.ship_collision",
        "class": "ShipCollisionAnalyzer",
        "description": "船撞数据分析"
    },
    "温度": {
        "module": "analyzers.temperature_time_series",
        "class": "TemperatureTimeSeriesAnalyzer",
        "description": "温度时间序列分析"
    },
    "风速": {
        "module": "analyzers.wind_speed",
        "class": "WindSpeedAnalyzer",
        "description": "风速数据分析"
    },
    "索力": {
        "module": "analyzers.backup.cable_force_analyzer",
        "class": "CableForceAnalyzer",
        "description": "索力数据分析 (备份)"
    },
}


def get_analyzer_info(data_type: str) -> Optional[Dict]:
    """
    获取指定数据类型对应的分析器信息
    """
    return DATA_TYPE_TO_ANALYZER.get(data_type)
