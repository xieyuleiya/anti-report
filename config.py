# -*- coding: utf-8 -*-
"""
统一配置文件 - 所有下载模块的配置参数
"""

import os
from datetime import datetime

# ========== 基础配置 ==========
# 输出根目录
OUTPUT_ROOT = r"D:\useful\01-work file\07.报告\00-自动报告目录"

# 要下载的桥梁列表（支持多个桥梁）
BRIDGES_TO_DOWNLOAD = [
    # "李家沙特大桥",
    # "崖门大桥",
    # "佛清广高速公路铺锦互通主线3号桥",
    # "白土北江特大桥",
    # "江口北江特大桥",
    # "乌石北江特大桥",
    # "大潮韩江大桥",
    # "小榄水道桥",
    # "南中大桥",
    # "江海大桥",
    "潮荷大桥",
    # 可以添加更多桥梁
]

# ========== 时间范围配置 ==========
# 支持跨年连续日期范围，格式：YYYY-MM-DD
START_DATE = "2026-01-01"  # 开始日期
END_DATE = "2026-03-01"    # 结束日期   

# ========== 数据下载配置 ==========
# 批量下载配置
BATCH_SIZE_DAYS = 400  # 每批下载的天数
WAIT_SECONDS = 0.3    # 批次间等待时间

# ========== 下载配置 ==========
# 要启用的数据类型（取消注释即可启用，注释掉表示不启用）
ENABLED_DATA_TYPES = [
    # "other_data",  # 其他数据（温湿度、温度、应变等）
    # "ship_collision",  # 船撞数据    
    "vehicle_load",  # 车辆荷载数据
]

# 其他数据的额外配置（仅在启用时有效）
OTHER_DATA_CATEGORIES = ["温度", "温湿度"]  # None表示下载全部种类

# ========== 船撞和车辆荷载数据模块配置 ==========
# 船撞和车辆荷载数据共用配置文件路径
BRIDGE_CONFIG_EXCEL_PATH = r"D:\useful\01-work file\07.报告\00-自动报告目录\00-基础资料\桥梁测点通道.xlsx"
OTHER_DATA_EXCEL_PATH = BRIDGE_CONFIG_EXCEL_PATH
OTHER_DATA_SHEET_NAME = "桥梁测点通道"

# ========== API配置 ==========
# API密钥
API_KEY = "337F11D3-7181-4570-9F44-CD42396BA266"

# API请求头
HEADERS = {'Content-Type': 'application/json'}

# ========== 辅助函数 ==========
def is_other_data_enabled() -> bool:
    """检查是否启用其他数据下载"""
    return "other_data" in ENABLED_DATA_TYPES

def get_other_data_categories():
    """获取其他数据要下载的种类"""
    return OTHER_DATA_CATEGORIES if is_other_data_enabled() else None

def is_ship_collision_enabled() -> bool:
    """检查是否启用船撞数据下载"""
    return "ship_collision" in ENABLED_DATA_TYPES

def is_vehicle_load_enabled() -> bool:
    """检查是否启用车辆荷载数据下载"""
    return "vehicle_load" in ENABLED_DATA_TYPES

def get_enabled_data_types():
    """获取所有启用的数据类型"""
    enabled_types = []
    if is_other_data_enabled():
        enabled_types.append('other')
    if is_ship_collision_enabled():
        enabled_types.append('ship')
    if is_vehicle_load_enabled():
        enabled_types.append('vehicle')
    return enabled_types

def get_output_dir(bridge_name: str, data_type: str) -> str:
    """
    获取指定桥梁和数据类型的输出目录
    
    Args:
        bridge_name: 桥梁名称
        data_type: 数据类型（如"船撞"、"车辆荷载"、"温湿度"等）
    
    Returns:
        输出目录路径
    """
    return os.path.join(OUTPUT_ROOT, bridge_name, "原始数据", data_type)

def create_output_dirs(bridge_name: str, data_type: str) -> str:
    """
    创建并返回指定桥梁和数据类型的输出目录
    
    Args:
        bridge_name: 桥梁名称
        data_type: 数据类型
    
    Returns:
        输出目录路径
    """
    output_dir = get_output_dir(bridge_name, data_type)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

# ========== 分析器路径管理函数 ==========
def get_analyzer_data_dir(bridge_name: str, data_type: str) -> str:
    """
    获取分析器使用的数据目录路径（与下载器保持一致）
    
    Args:
        bridge_name: 桥梁名称
        data_type: 数据类型（如"船撞"、"车辆荷载"、"温湿度"、"温度"、"风速"、"索力"等）
    
    Returns:
        数据目录路径
    """
    return get_output_dir(bridge_name, data_type)

def get_analyzer_output_dir(bridge_name: str, analyzer_type: str = None) -> str:
    """
    获取分析器的输出目录路径
    
    Args:
        bridge_name: 桥梁名称
        analyzer_type: 分析器类型（可选，如"温湿度"、"车辆荷载"等），用于创建子目录
    
    Returns:
        输出目录路径
    """
    if analyzer_type:
        return os.path.join(OUTPUT_ROOT, bridge_name, "分析结果", analyzer_type)
    else:
        return os.path.join(OUTPUT_ROOT, bridge_name, "分析结果")

def create_analyzer_output_dir(bridge_name: str, analyzer_type: str = None) -> str:
    """
    创建并返回分析器的输出目录
    
    Args:
        bridge_name: 桥梁名称
        analyzer_type: 分析器类型（可选）
    
    Returns:
        输出目录路径
    """
    output_dir = get_analyzer_output_dir(bridge_name, analyzer_type)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def get_available_bridges() -> list:
    """
    获取已下载数据的桥梁列表（扫描OUTPUT_ROOT目录）
    
    Returns:
        桥梁名称列表
    """
    bridges = []
    if os.path.exists(OUTPUT_ROOT):
        for item in os.listdir(OUTPUT_ROOT):
            bridge_path = os.path.join(OUTPUT_ROOT, item)
            if os.path.isdir(bridge_path):
                # 检查是否有"原始数据"目录
                raw_data_path = os.path.join(bridge_path, "原始数据")
                if os.path.exists(raw_data_path):
                    bridges.append(item)
    return sorted(bridges)

def get_available_data_types(bridge_name: str) -> list:
    """
    获取指定桥梁已下载的数据类型列表
    
    Args:
        bridge_name: 桥梁名称
    
    Returns:
        数据类型列表（如["温湿度", "车辆荷载", "船撞"]）
    """
    data_types = []
    raw_data_dir = os.path.join(OUTPUT_ROOT, bridge_name, "原始数据")
    if os.path.exists(raw_data_dir):
        for item in os.listdir(raw_data_dir):
            data_type_path = os.path.join(raw_data_dir, item)
            if os.path.isdir(data_type_path):
                # 检查目录是否非空
                if any(os.listdir(data_type_path)):
                    data_types.append(item)
    return sorted(data_types)

def validate_config():
    """
    验证配置的有效性
    """
    print("🔍 开始验证配置...")
    errors = []
    warnings = []
    
    # 检查输出根目录
    print(f"  📁 检查输出根目录: {OUTPUT_ROOT}")
    if not os.path.exists(OUTPUT_ROOT):
        try:
            os.makedirs(OUTPUT_ROOT, exist_ok=True)
            print(f"    ✅ 已创建输出根目录")
        except Exception as e:
            errors.append(f"无法创建输出根目录 {OUTPUT_ROOT}: {e}")
            print(f"    ❌ 创建输出根目录失败: {e}")
    else:
        print(f"    ✅ 输出根目录已存在")
    
    # 检查桥梁列表
    print(f"  🌉 检查桥梁列表: {len(BRIDGES_TO_DOWNLOAD)} 座桥梁")
    if not BRIDGES_TO_DOWNLOAD:
        errors.append("桥梁列表不能为空")
        print(f"    ❌ 桥梁列表为空")
    else:
        print(f"    ✅ 桥梁列表有效")
    
    # 检查日期格式
    print(f"  📅 检查日期格式: {START_DATE} 到 {END_DATE}")
    try:
        start_dt = datetime.strptime(START_DATE, "%Y-%m-%d")
        end_dt = datetime.strptime(END_DATE, "%Y-%m-%d")
        print(f"    ✅ 日期格式正确")
        
        # 检查开始日期不能晚于结束日期
        if start_dt > end_dt:
            errors.append(f"开始日期 {START_DATE} 不能晚于结束日期 {END_DATE}")
            print(f"    ❌ 开始日期晚于结束日期")
        else:
            days_diff = (end_dt - start_dt).days
            print(f"    ✅ 时间范围有效 ({days_diff} 天)")
            
            # 检查时间范围是否过大
            if days_diff > 365:
                warnings.append(f"时间范围较大 ({days_diff} 天)，下载可能需要较长时间")
                print(f"    ⚠️ 时间范围较大 ({days_diff} 天)")
    
    except ValueError as e:
        errors.append(f"日期格式错误: {e}")
        print(f"    ❌ 日期格式错误: {e}")
    
    # 检查配置文件路径
    config_files = [
        ("其他数据配置", OTHER_DATA_EXCEL_PATH),
        ("桥梁配置", BRIDGE_CONFIG_EXCEL_PATH)
    ]
    
    for config_name, file_path in config_files:
        print(f"  📄 检查{config_name}文件: {os.path.basename(file_path)}")
        if not os.path.exists(file_path):
            errors.append(f"配置文件不存在: {file_path}")
            print(f"    ❌ 文件不存在")
        else:
            file_size = os.path.getsize(file_path)
            print(f"    ✅ 文件存在 ({file_size:,} 字节)")
    
    # 检查API密钥
    print(f"  🔑 检查API密钥")
    if not API_KEY or len(API_KEY) < 10:
        errors.append("API密钥无效或过短")
        print(f"    ❌ API密钥无效")
    else:
        print(f"    ✅ API密钥格式正确")
    
    # 检查下载配置
    print(f"  ⚙️ 检查下载配置")
    enabled_types = get_enabled_data_types()
    if not enabled_types:
        warnings.append("没有启用任何数据类型，请检查ENABLED_DATA_TYPES配置")
        print(f"    ⚠️ 没有启用任何数据类型")
    else:
        print(f"    ✅ 启用的数据类型: {enabled_types}")
    
    # 显示结果
    print(f"\n📊 配置验证结果:")
    if errors:
        print(f"  ❌ 错误 ({len(errors)} 个):")
        for error in errors:
            print(f"    - {error}")
    
    if warnings:
        print(f"  ⚠️ 警告 ({len(warnings)} 个):")
        for warning in warnings:
            print(f"    - {warning}")
    
    if not errors and not warnings:
        print(f"  ✅ 配置完全正确")
    elif not errors:
        print(f"  ⚠️ 配置有警告但可以继续")
    else:
        print(f"  ❌ 配置有错误，无法继续")
    
    return len(errors) == 0 