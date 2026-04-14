import pandas as pd
import numpy as np
from pathlib import Path
import re

def natural_sort_key(text):
    """自然排序键函数，用于正确排序包含数字的字符串"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', text)]

class WindSpeedProcessor:
    # ==================== 配置区域 ====================
    # 桥名配置 - 请在此处修改桥名
    BRIDGE_NAME = "乌石北江特大桥"  # 请在此处修改桥名
    
    def __init__(self, bridge_name=None, data_dir=None, output_dir=None, excel_path=None):
        # 使用配置的桥名，如果没有传入参数则使用默认配置
        self.bridge_name = bridge_name or self.BRIDGE_NAME
        
        # 路径配置：优先使用外部注入；否则尝试统一路径；最后退回旧路径
        if data_dir is None or output_dir is None:
            try:
                from utils.analyzer_utils import AnalyzerPathManager
                path_mgr = AnalyzerPathManager(self.bridge_name)
                data_dir = data_dir or path_mgr.get_data_dir("风速")
                output_dir = output_dir or path_mgr.get_output_dir("风速")
            except Exception:
                # 退回旧目录结构
                current_dir = Path(__file__).parent
                base_path = current_dir.parent
                data_dir = data_dir or (base_path / "数据下载" / self.bridge_name / "风速" / "数据")
                output_dir = output_dir or (Path("fengsu") / self.bridge_name)

        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.excel_path = excel_path or Path(r"D:\useful\01-work file\07.报告\00-自动报告目录\00-基础资料\桥梁测点通道.xlsx")
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据存储
        self.excel_data = None
        self.file_mapping = {}
        self.wind_data = {}
        self.original_data = {}  # 存储原始数据用于绘图
        
        print(f"🌪️ 风速解析器初始化完成: {self.bridge_name}")

    def load_excel_data(self):
        """加载Excel数据"""
        try:
            print(f"📊 正在加载Excel数据: {self.excel_path}")
            self.excel_data = pd.read_excel(self.excel_path)
            print(f"✅ Excel数据加载成功，共 {len(self.excel_data)} 行")
            return True
        except Exception as e:
            print(f"❌ Excel数据加载失败: {e}")
            return False
    
    def build_file_mapping(self, filtered_data):
        """构建文件映射关系"""
        print(f"\n🔍 开始构建文件映射关系...")
        
        if not self.data_dir.exists():
            print(f"❌ 数据目录不存在: {self.data_dir}")
            return False
        
        # 获取所有txt文件
        txt_files = list(self.data_dir.glob("*.txt"))
        print(f"📁 找到 {len(txt_files)} 个数据文件")
        
        if not txt_files:
            print("❌ 未找到任何数据文件")
            return False
        
        # 遍历Excel数据，为每个测点找到对应的文件
        for _, row in filtered_data.iterrows():
            bridge_name = row.iloc[0]  # A列：桥名
            sensor_id = row.iloc[1]    # B列：通道ID
            sensor_name = row.iloc[2]  # C列：测点编号
            sensor_desc = row.iloc[3]  # D列：测点概况
            category = row.iloc[4]     # E列：测点所属种类
            location_large = row.iloc[5]  # F列：测点所属大位置
            location_small = row.iloc[6]  # G列：测点所属小位置
            
            # 仅匹配风速类测点，避免其他无关测点（如加速度、位移等）产生匹配失败提示
            if category != '风速':
                continue
            matched_files = []
            for txt_file in txt_files:
                if sensor_name in txt_file.name:
                    matched_files.append(txt_file)
            
            if matched_files:
                for matched_file in matched_files:
                    self.file_mapping[matched_file] = {
                        # ... attributes ...
                        'bridge_name': bridge_name,
                        'sensor_id': sensor_id,
                        'sensor_name': sensor_name,
                        'sensor_desc': sensor_desc,
                        'category': category,
                        'location_large': location_large,
                        'location_small': location_small,
                        'group_key': f"{location_large}_{location_small}"
                    }
            
            # 移除逐个匹配成功的打印，由外层整体汇总
        
        print(f"✅ 测点文件匹配完成，共关联 {len(self.file_mapping)} 个文件")
        return True
    
    def load_wind_data(self):
        """加载与清洗风速数据"""
        print(f"\n📊 开始加载风速数据...")
        
        for file_path, attributes in self.file_mapping.items():
            sensor_name = attributes['sensor_name']
            try:
                data = pd.read_csv(file_path, sep='\t', header=None, encoding='utf-8')
                if len(data.columns) >= 4:
                    data.columns = ['DateTime', 'WindSpeed', 'WindDirection', 'Status'] + [f'Col{i}' for i in range(4, len(data.columns))]
                else:
                    data.columns = ['DateTime', 'WindSpeed', 'WindDirection']
                
                data['Time'] = pd.to_datetime(data['DateTime'], format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
                if data['Time'].isna().all():
                    data['Time'] = pd.to_datetime(data['DateTime'], errors='coerce')
                
                data['WindSpeed'] = pd.to_numeric(data['WindSpeed'], errors='coerce')
                data['WindDirection'] = pd.to_numeric(data['WindDirection'], errors='coerce')
                
                data = data[['Time', 'WindSpeed', 'WindDirection']].dropna()
                
                self.wind_data[sensor_name] = data
                self.original_data[sensor_name] = data.copy()
            except Exception as e:
                print(f"❌ 加载测点 {sensor_name} 失败: {e}")
        
        print(f"✅ 风速数据加载完成，共加载 {len(self.wind_data)} 个测点数据")
    
    def analyze_wind_statistics(self):
        """执行统计分析"""
        print(f"\n📊 开始风速统计分析...")
        stats_summary = {}
        all_wind_speeds = []
        all_wind_directions = []
        
        for sensor_name, data in self.wind_data.items():
            if data.empty: continue
            
            # 基本统计
            ws_stats = data['WindSpeed'].describe()
            wd_stats = data['WindDirection'].describe()
            
            # 分布统计
            ws_bins = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 25, 30, 50]
            ws_labels = ['0-2', '2-4', '4-6', '6-8', '8-10', '10-12', '12-14', '14-16', '16-18', '18-20', '20-25', '25-30', '30-50']
            ws_dist = pd.cut(data['WindSpeed'], bins=ws_bins, labels=ws_labels).value_counts().to_dict()
            
            wd_bins = np.linspace(0, 360, 17)
            wd_labels = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
            wd_dist = pd.cut(data['WindDirection'], bins=wd_bins, labels=wd_labels).value_counts().to_dict()
            
            stats_summary[sensor_name] = {
                'wind_speed_mean': ws_stats['mean'],
                'wind_speed_max': ws_stats['max'],
                'wind_speed_min': ws_stats['min'],
                'wind_speed_std': ws_stats['std'],
                'wind_direction_mean': wd_stats['mean'],
                'records_count': len(data),
                'wind_speed_distribution': ws_dist,
                'wind_direction_distribution': wd_dist
            }
            
            for _, row in data.iterrows():
                all_wind_speeds.append({'sensor_name': sensor_name, 'wind_speed': row['WindSpeed'], 'time': row['Time']})
            all_wind_directions.extend(data['WindDirection'].tolist())
            
        global_stats = {}
        if all_wind_speeds:
            max_rec = max(all_wind_speeds, key=lambda x: x['wind_speed'])
            global_stats = {
                'max_wind_speed': max_rec['wind_speed'],
                'max_wind_speed_sensor': max_rec['sensor_name'],
                'max_wind_speed_time': max_rec['time'],
                'avg_wind_speed': np.mean([x['wind_speed'] for x in all_wind_speeds])
            }
            
        return stats_summary, global_stats

    def get_wind_data(self):
        return self.wind_data

    def get_original_data(self):
        return self.original_data
