#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用车辆荷载数据格式标准化工具
将车辆荷载数据文件标准化为统一格式
"""

import pandas as pd
import os
import sys
from datetime import datetime

def detect_encoding(file_path):
    """检测文件编码，尝试常见编码"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1000)  # 尝试读取前1000个字符
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    return 'utf-8'  # 默认返回utf-8

def standardize_vehicle_data(input_file, output_file=None):
    """
    标准化车辆荷载数据格式
    
    Args:
        input_file (str): 输入文件路径
        output_file (str): 输出文件路径，如果为None则自动生成
    
    Returns:
        bool: 处理是否成功
    """
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在: {input_file}")
        return False
    
    if output_file is None:
        # 自动生成输出文件名
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_标准化.txt"
    
    print(f"开始处理文件: {input_file}")
    
    # 检测文件编码
    encoding = detect_encoding(input_file)
    print(f"检测到文件编码: {encoding}")
    
    # 定义标准列名映射（支持多种可能的列名）
    column_mapping = {
        # 车道相关
        'CarLane': '车道',
        '车道': '车道',
        'lane': '车道',
        
        # 车牌号相关
        'CarPlate': '车牌号',
        '车牌号': '车牌号',
        'plate': '车牌号',
        'Plate': '车牌号',
        
        # 车牌颜色相关
        'CarPlateColor': '车牌颜色',
        '车牌颜色': '车牌颜色',
        'PlateColor': '车牌颜色',
        'color': '车牌颜色',
        
        # 时间相关
        'DataTime': '时间',
        '时间': '时间',
        'datetime': '时间',
        'DateTime': '时间',
        'timestamp': '时间',
        
        # 车型相关
        'CarType': '车型',
        '车型': '车型',
        'type': '车型',
        'Type': '车型',
        
        # 轴数相关
        'AxleCount': '轴数',
        '轴数': '轴数',
        'axle': '轴数',
        'Axle': '轴数',
        
        # 总重相关
        'TotalWeight': '总重(kg)',
        '总重': '总重(kg)',
        'weight': '总重(kg)',
        'Weight': '总重(kg)',
        '总重(kg)': '总重(kg)'
    }
    
    # 定义标准列顺序
    standard_columns = ['车道', '车牌号', '车牌颜色', '时间', '车型', '轴数', '总重(kg)']
    
    try:
        # 先读取文件头部来了解列结构
        print("正在分析文件结构...")
        sample_df = pd.read_csv(input_file, sep='\t', encoding=encoding, nrows=5)
        print(f"原始列名: {list(sample_df.columns)}")
        
        # 分块读取大文件
        chunk_size = 10000  # 每次读取10000行
        chunks = []
        
        print("正在分块读取文件...")
        for chunk in pd.read_csv(input_file, sep='\t', encoding=encoding, chunksize=chunk_size):
            # 重命名列（只重命名存在的列）
            chunk_columns = {}
            for old_col, new_col in column_mapping.items():
                if old_col in chunk.columns:
                    chunk_columns[old_col] = new_col
            
            chunk = chunk.rename(columns=chunk_columns)
            
            # 确保所有标准列都存在，如果不存在则创建空列
            for col in standard_columns:
                if col not in chunk.columns:
                    chunk[col] = ''
            
            # 确保列顺序正确
            chunk = chunk.reindex(columns=standard_columns)
            
            # 处理时间格式
            if '时间' in chunk.columns:
                chunk['时间'] = pd.to_datetime(chunk['时间'], errors='coerce')
                # 格式化为标准时间格式
                chunk['时间'] = chunk['时间'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # 处理数值列
            if '总重(kg)' in chunk.columns:
                chunk['总重(kg)'] = pd.to_numeric(chunk['总重(kg)'], errors='coerce')
            
            if '轴数' in chunk.columns:
                chunk['轴数'] = pd.to_numeric(chunk['轴数'], errors='coerce')
            
            # 清理空值行（如果时间列为空则删除该行）
            chunk = chunk.dropna(subset=['时间'], how='all')
            
            # 填充空值
            chunk['车道'] = chunk['车道'].fillna('')
            chunk['车牌号'] = chunk['车牌号'].fillna('')
            chunk['车牌颜色'] = chunk['车牌颜色'].fillna('')
            chunk['车型'] = chunk['车型'].fillna('')
            
            chunks.append(chunk)
            print(f"已处理 {len(chunks) * chunk_size} 行...")
        
        print("正在合并数据...")
        # 合并所有块
        df = pd.concat(chunks, ignore_index=True)
        
        print(f"数据总行数: {len(df)}")
        print(f"数据列数: {len(df.columns)}")
        print("列名:", list(df.columns))
        
        # 创建输出目录（如果不存在）
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 保存标准化后的数据
        print(f"正在保存到: {output_file}")
        df.to_csv(output_file, sep='\t', index=False, encoding='utf-8-sig')
        
        print("数据标准化完成！")
        
        # 显示前几行作为预览
        print("\n标准化后的数据预览:")
        print(df.head(10))
        
        # 显示数据统计信息
        print("\n数据统计信息:")
        print(f"总记录数: {len(df)}")
        if not df['时间'].empty and df['时间'].notna().any():
            print(f"时间范围: {df['时间'].min()} 到 {df['时间'].max()}")
        if not df['车型'].empty and df['车型'].notna().any():
            print(f"车型分布:")
            print(df['车型'].value_counts().head(10))
        if not df['车牌颜色'].empty and df['车牌颜色'].notna().any():
            print(f"车牌颜色分布:")
            print(df['车牌颜色'].value_counts())
        
        return True
        
    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python vehicle_data_standardizer.py <输入文件路径> [输出文件路径]")
        print("示例: python vehicle_data_standardizer.py data.txt")
        print("示例: python vehicle_data_standardizer.py data.txt output.txt")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 执行标准化
    success = standardize_vehicle_data(input_file, output_file)
    
    if success:
        print(f"\n标准化完成！")
    else:
        print("标准化失败！")

if __name__ == "__main__":
    main()
