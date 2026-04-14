import pandas as pd
import numpy as np
from datetime import datetime
import os
from pathlib import Path
from docx.oxml.shared import OxmlElement, qn

def natural_sort_key(s):
    import re
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

class TemperatureTimeSeriesProcessor:
    def __init__(self, bridge_name, data_dir, output_dir):
        self.bridge_name = bridge_name
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.colors = {
            'blue': '#1f77b4', 'red': '#d62728', 'green': '#2ca02c', 'orange': '#ff7f0e',
            'purple': '#9467bd', 'brown': '#8c564b', 'pink': '#e377c2', 'gray': '#7f7f7f'
        }
        
        self.file_mapping = {}
        self.temperature_data = {}
        self.original_data = {}
        self.grouped_data = {}
        
        print(f"🌡️ 温度时间序列分析器初始化完成")

    def run(self):
        return self.run_analysis()
    
    def build_file_mapping(self):
        """构建文件映射关系"""
        if not self.data_dir.exists():
            print(f"❌ 数据目录不存在: {self.data_dir}")
            return False
            
        txt_files = list(self.data_dir.glob("*.txt"))
        if not txt_files:
            print("❌ 未找到任何数据文件")
            return False
        
        print(f"🔍 正在解析 {len(txt_files)} 个数据文件...")
        for txt_file in txt_files:
            filename = txt_file.stem
            parts = filename.split('_')
            
            if len(parts) >= 7:
                channel_id = parts[0]
                bridge_name = parts[1]
                data_type = parts[2]
                left_right = parts[3]
                sensor_group = parts[4]
                channel_name = parts[5]
                location = parts[6]
                sensor_name = f"{channel_name}（{location}）"
                group_key = f"{left_right}_{location}"
                
                self.file_mapping[txt_file] = {
                    'bridge_name': bridge_name,
                    'sensor_id': channel_id,
                    'sensor_name': sensor_name,
                    'sensor_desc': f"{left_right} {location} 温度测点",
                    'category': data_type,
                    'location_large': left_right,
                    'location_small': location,
                    'group_key': group_key,
                    'channel_name': channel_name,
                    'location': location
                }
            
        print(f"📊 成功映射 {len(self.file_mapping)} 个有效文件")
        return True
    
    def load_temperature_data(self):
        """加载温度数据"""
        print(f"📊 正在加载温度数据...")
        
        loaded_count = 0
        for file_path, attributes in self.file_mapping.items():
            sensor_name = attributes['sensor_name']
            try:
                data = pd.read_csv(file_path, sep='\t', header=None, encoding='utf-8')
                if len(data.columns) >= 2:
                    data.columns = ['DateTime', 'Temperature'] + [f'Col{i}' for i in range(2, len(data.columns))]
                else:
                    data.columns = ['DateTime', 'Temperature']
                
                data['Time'] = pd.to_datetime(data['DateTime'], format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
                if data['Time'].isna().all():
                    data['Time'] = pd.to_datetime(data['DateTime'], errors='coerce')
                
                data = data[['Time', 'Temperature']]
                data['Sensor_Name'] = sensor_name
                data['Display_Name'] = sensor_name
                data['Channel_Name'] = attributes['channel_name']
                data['Location'] = attributes['location']
                data['Location_Large'] = attributes['location_large']
                data['Location_Small'] = attributes['location_small']
                data['Group_Key'] = attributes['group_key']
                
                data.dropna(subset=['Time', 'Temperature'], inplace=True)
                self.temperature_data[sensor_name] = data
                self.original_data[sensor_name] = data.copy()
                loaded_count += 1
            except Exception as e:
                print(f"❌ 加载测点 {sensor_name} 数据失败: {e}")
        
        self.group_data_by_location()
        print(f"✅ 成功加载 {loaded_count} 个测点数据")
    
    def group_data_by_location(self):
        """按位置分组数据"""
        for sensor_name, data in self.temperature_data.items():
            if data is not None and not data.empty:
                group_key = data['Group_Key'].iloc[0]
                if group_key not in self.grouped_data:
                    self.grouped_data[group_key] = []
                self.grouped_data[group_key].append(data)
    
    def group_data_by_location_after_preprocess(self):
        """预处理后重新按位置分组数据"""
        self.grouped_data = {}
        for sensor_name, data in self.temperature_data.items():
            if data is not None and not data.empty:
                group_key = data['Group_Key'].iloc[0]
                if group_key not in self.grouped_data:
                    self.grouped_data[group_key] = []
                self.grouped_data[group_key].append(data)
    
    def preprocess_data(self):
        """数据预处理"""
        print(f"🔧 正在进行数据预处理...")
        processed_count = 0
        for sensor_name, data in self.temperature_data.items():
            if data is not None and not data.empty:
                data['Temperature'] = pd.to_numeric(data['Temperature'], errors='coerce')
                data['Date'] = data['Time'].dt.date
                
                daily_data = data.groupby('Date').agg({
                    'Temperature': ['mean', 'max', 'min']
                }).round(2)
                
                daily_data.columns = ['Temperature_mean', 'Temperature_max', 'Temperature_min']
                daily_data.reset_index(inplace=True)
                
                # 保留元数据
                first_row = data.iloc[0]
                daily_data['Sensor_Name'] = sensor_name
                daily_data['Display_Name'] = first_row['Display_Name']
                daily_data['Channel_Name'] = first_row['Channel_Name']
                daily_data['Location'] = first_row['Location']
                daily_data['Location_Large'] = first_row['Location_Large']
                daily_data['Location_Small'] = first_row['Location_Small']
                daily_data['Group_Key'] = first_row['Group_Key']
                
                self.temperature_data[sensor_name] = daily_data
                processed_count += 1
        
        self.group_data_by_location_after_preprocess()
        print(f"✅ 完成 {processed_count} 个测点的数据预处理")
    
    def analyze_basic_stats(self):
        """基础统计分析"""
        print(f"📊 正在进行基础统计分析...")
        stats_summary = {}
        all_original_temperatures = []
        
        for sensor_name, data in self.temperature_data.items():
            if data is not None and not data.empty:
                temp_mean = data['Temperature_mean'].mean()
                temp_max = data['Temperature_max'].max()
                temp_min = data['Temperature_min'].min()
                
                # 收集原始数据用于极值
                if sensor_name in self.original_data:
                    orig = self.original_data[sensor_name]
                    # 采样加速極值计算，或直接计算
                    # 为了保证准确性，直接对原始数据计算极值记录
                    for _, row in orig.iterrows():
                        if pd.notna(row['Temperature']):
                            all_original_temperatures.append({
                                'sensor_name': sensor_name,
                                'temperature': row['Temperature'],
                                'time': row['Time'],
                                'group': row['Group_Key']
                            })
                
                stats_summary[sensor_name] = {
                    'temp_mean': temp_mean, 'temp_max': temp_max, 'temp_min': temp_min,
                    'temp_range': temp_max - temp_min, 'days_count': len(data),
                    'date_range': f"{data['Date'].min()} 到 {data['Date'].max()}"
                }
        
        global_stats = {}
        if all_original_temperatures:
            max_temp_record = max(all_original_temperatures, key=lambda x: x['temperature'])
            min_temp_record = min(all_original_temperatures, key=lambda x: x['temperature'])
            global_stats = {
                'max_temp': max_temp_record['temperature'],
                'max_temp_sensor': max_temp_record['sensor_name'],
                'max_temp_group': max_temp_record['group'],
                'max_temp_time': max_temp_record['time'],
                'min_temp': min_temp_record['temperature'],
                'min_temp_sensor': min_temp_record['sensor_name'],
                'min_temp_group': min_temp_record['group'],
                'min_temp_time': min_temp_record['time'],
            }
            print(f"🌡️ 监测期间最高温度: {global_stats['max_temp']:.2f}°C, 最低: {global_stats['min_temp']:.2f}°C")
        
        return stats_summary, global_stats

    def run_analysis(self):
        """执行完整分析流程"""
        if not self.build_file_mapping(): return False
        self.load_temperature_data()
        self.preprocess_data()
        stats_summary, global_stats = self.analyze_basic_stats()
        
        from .plotter import TemperatureTimeSeriesPlotter
        plotter = TemperatureTimeSeriesPlotter(self.bridge_name, self.output_dir)
        plotter.draw_all_time_series(self.original_data, self.grouped_data)
        
        # 保存csv汇总
        table_rows = []
        for sensor_name, stats in stats_summary.items():
            table_rows.append({
                '测点名称': sensor_name,
                '平均温度(°C)': f"{stats['temp_mean']:.2f}",
                '最高温度(°C)': f"{stats['temp_max']:.2f}",
                '最低温度(°C)': f"{stats['temp_min']:.2f}",
                '温度差值(°C)': f"{stats['temp_range']:.2f}",
                '数据天数': stats['days_count']
            })
        pd.DataFrame(table_rows).to_csv(self.output_dir / "温度统计表.csv", index=False, encoding='utf-8-sig')
        print(f"✅ 统计表已保存: 温度统计表.csv")
        
        from .reporter import TemperatureTimeSeriesReporter
        reporter = TemperatureTimeSeriesReporter(self.bridge_name, self.output_dir, stats_summary, global_stats, self.grouped_data, self.file_mapping)
        reporter.generate_word_report()
        return True

    def get_data(self):
        return self.temperature_data, self.original_data, self.grouped_data, self.file_mapping
