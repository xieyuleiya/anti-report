import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import pandas as pd
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimSun']
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['axes.unicode_minus'] = False

def natural_sort_key(s):
    import re
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

class TemperatureTimeSeriesPlotter:
    def __init__(self, bridge_name: str, output_dir: Path, temperature_data: dict, original_data: dict, file_mapping: dict):
        self.bridge_name = bridge_name
        self.output_dir = output_dir
        self.temperature_data = temperature_data
        self.original_data = original_data
        self.file_mapping = file_mapping
        
        self.colors = {
            'blue': '#1f77b4',
            'orange': '#ff7f0e',
            'green': '#2ca02c',
            'red': '#d62728',
            'purple': '#9467bd',
            'brown': '#8c564b',
            'pink': '#e377c2',
            'gray': '#7f7f7f',
            'olive': '#bcbd22',
            'cyan': '#17becf'
        }

    def plot_temperature_time_series_original(self):
        """绘制温度时间序列图（使用原始数据）- 修改为子图形式"""
        print("📊 使用原始数据绘制温度时序图...")
        
        # 按组别重新组织原始数据
        original_grouped_data = {}
        for sensor_name, data in self.original_data.items():
            if data is not None and not data.empty:
                group_key = data['Group_Key'].iloc[0]
                if group_key not in original_grouped_data:
                    original_grouped_data[group_key] = []
                original_grouped_data[group_key].append(data)
        
        color_list = list(self.colors.values())
        
        for group_key, group_data in original_grouped_data.items():
            print(f"正在绘制组别 {group_key} 的温度时序图（原始数据）...")
            
            # 创建子图：3/4时序图 + 1/4频率图
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), 
                                          gridspec_kw={'width_ratios': [3, 1]})
            
            color_idx = 0
            
            # 收集所有温度数据用于频率图
            all_temperatures = []
            
            # 绘制时序图（左子图）
            for data in group_data:
                if data is not None and not data.empty:
                    sensor_name = data['Sensor_Name'].iloc[0]
                    color = color_list[color_idx % len(color_list)]
                    
                    # 使用原始时间数据，使用平滑的线条
                    ax1.plot(data['Time'], data['Temperature'], 
                            color=color, linewidth=1.5, alpha=0.8, 
                            label=sensor_name, marker='o', markersize=2)
                    
                    # 收集温度数据用于频率图
                    all_temperatures.extend(data['Temperature'].dropna().tolist())
                    color_idx += 1
            
            # 设置时序图格式
            ax1.set_title(f'{self.bridge_name} - {group_key}温度时序图', 
                         fontsize=16, fontweight='bold')
            ax1.set_ylabel('温度 (°C)', fontsize=14)
            ax1.set_xlabel('时间', fontsize=14)
            ax1.grid(True, alpha=0.3)
            ax1.legend(fontsize=12)
            ax1.tick_params(axis='both', which='major', labelsize=12)
            ax1.tick_params(axis='x', rotation=45)
            
            # 绘制频率图（右子图）
            if all_temperatures:
                ax2.hist(all_temperatures, bins=20, alpha=0.7, 
                        color='blue', edgecolor='darkblue', density=True)
                ax2.set_title(f'{group_key}温度频率分布', fontsize=16, fontweight='bold')
                ax2.set_xlabel('温度 (°C)', fontsize=14)
                ax2.set_ylabel('密度', fontsize=14)
                ax2.grid(True, alpha=0.3)
                ax2.tick_params(axis='both', which='major', labelsize=12)
                
                # 添加统计信息
                mean_temp = np.mean(all_temperatures)
                std_temp = np.std(all_temperatures)
                ax2.axvline(mean_temp, color='red', linestyle='--', linewidth=2,
                           label=f'平均值: {mean_temp:.2f}°C')
                ax2.legend(fontsize=12)
            
            plt.tight_layout()
            
            # 保存图片
            output_filename = f"{group_key}温度时序图.png"
            plt.savefig(self.output_dir / output_filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ 已保存: {output_filename}")
    
    def create_temperature_statistics_table(self, stats_summary):
        """创建温度统计表格"""
        if not stats_summary:
            print("⚠️ 没有统计数据可生成表格")
            return None
        
        # 创建温度统计DataFrame - 使用自然排序
        temp_table_data = []
        # 按自然排序处理测点名称
        sorted_sensor_names = sorted(stats_summary.keys(), key=natural_sort_key)
        
        for sensor_name in sorted_sensor_names:
            stats = stats_summary[sensor_name]
            # 简化测点名（移除括号内的位置信息）
            simplified_sensor_name = sensor_name.split('（')[0]
            # 从file_mapping中获取位置信息
            location_info = "未知"
            for file_path, attributes in self.file_mapping.items():
                if attributes.get('sensor_name') == sensor_name:
                    location_info = attributes.get('group_key', "未知")
                    break
            
            temp_table_data.append({
                '位置': location_info,
                '测点名称': simplified_sensor_name,
                '温度平均值(°C)': f"{stats['temp_mean']:.2f}",
                '温度最大值(°C)': f"{stats['temp_max']:.2f}",
                '温度最小值(°C)': f"{stats['temp_min']:.2f}",
                '温度差值(°C)': f"{stats['temp_range']:.2f}"
            })
        
        # 保存为CSV文件
        df_temp_table = pd.DataFrame(temp_table_data)
        temp_table_path = self.output_dir / '温度统计表.csv'
        df_temp_table.to_csv(temp_table_path, index=False, encoding='utf-8-sig')
        print(f"✅ 温度统计表格已保存: {temp_table_path}")
        
        return df_temp_table
    
