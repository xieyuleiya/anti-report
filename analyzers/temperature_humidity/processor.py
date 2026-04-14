import pandas as pd
from pathlib import Path
import re

HUMIDITY_THRESHOLD_BY_BRIDGE = {
    "金马大桥": 50,
}

def get_bridge_config(bridge_name, data_dir_override=None):
    if data_dir_override is not None:
        data_dir = Path(data_dir_override)
    else:
        # Fallback
        DATA_ROOT = Path("D:/useful/03-chengxu/report_gen/数据下载")
        data_dir = DATA_ROOT / bridge_name / "原始数据" / "温湿度"
    humidity_threshold = HUMIDITY_THRESHOLD_BY_BRIDGE.get(bridge_name, 50)
    return data_dir, humidity_threshold

class TemperatureHumidityProcessor:
    def __init__(self, bridge_name: str, data_dir: Path):
        self.bridge_name = bridge_name
        self.data_dir, self.humidity_threshold = get_bridge_config(bridge_name, data_dir_override=data_dir)
        self.temperature_humidity_data = {}

    def load_data(self):
        """加载温湿度数据"""
        try:
            # 递归查找温湿度目录下所有txt文件（支持“数据”、“合并”等任意子目录）
            print(f"🔎 数据根目录: {self.data_dir}")
            data_files = list(self.data_dir.glob("**/*.txt"))
            
            if not data_files:
                print("⚠️ 未找到温湿度数据文件")
                return
            
            print(f"📁 找到 {len(data_files)} 个数据文件")
            
            for file_path in data_files:
                try:
                    # 从文件名提取测点信息
                    filename = file_path.stem
                    
                    # 尝试解析文件名格式：通道ID_桥名_类型_左右幅_所属测点_通道名称_位置
                    # 例如：1011_白土北江特大桥_温湿度_左幅_左幅温湿度测点_WSD-L1_箱内
                    parts = filename.split('_')
                    
                    if len(parts) >= 7:
                        # 提取通道名称（如WSD-L1）和位置（如箱内）
                        channel_name = parts[5]
                        location = parts[6]
                        # 使用"通道名称（位置）"格式作为测点名
                        station_name = f"{channel_name}（{location}）"
                    else:
                        # 尝试从文件名中提取测点名称（如：2025-11-19-22-41-16温湿度测点JM-RHS-TO3-001-01_）
                        # 查找"测点"后面的部分
                        match = re.search(r'测点([A-Z0-9\-]+)', filename)
                        if match:
                            station_name = match.group(1)
                        else:
                            # 如果解析失败，使用原始文件名
                            station_name = filename
                    
                    # 移除逐个测点的加载提示
                    
                    # 读取数据文件
                    # 尝试两种格式：
                    # 1. 完整时间戳 + 温度 + 湿度（制表符或空格分隔）
                    # 2. 日期 时间 温度 湿度（空格分隔）
                    try:
                        # 先尝试读取为完整时间戳格式（制表符分隔）
                        data = pd.read_csv(file_path, sep='\t', header=None, 
                                         names=['Time', 'Temperature', 'Humidity'],
                                         skipinitialspace=True, engine='python',
                                         on_bad_lines='skip')
                        # 如果列数不对，尝试空格分隔
                        if data.shape[1] < 3 or data.isnull().all().any():
                            data = pd.read_csv(file_path, sep=r'\s+', header=None, 
                                             engine='python', on_bad_lines='skip')
                            # 判断列数
                            if data.shape[1] >= 4:
                                # 日期和时间分开
                                data.columns = ['Date', 'Time', 'Temperature', 'Humidity'] + [f'Col{i}' for i in range(4, data.shape[1])]
                                data = data[['Date', 'Time', 'Temperature', 'Humidity']]
                                data['Time'] = data['Date'].astype(str) + ' ' + data['Time'].astype(str)
                                data = data.drop('Date', axis=1)
                            elif data.shape[1] == 3:
                                # 时间戳、温度、湿度
                                data.columns = ['Time', 'Temperature', 'Humidity']
                            else:
                                raise ValueError(f"无法识别的数据格式，列数: {data.shape[1]}")
                        
                        # 转换时间列
                        data['Time'] = pd.to_datetime(data['Time'], errors='coerce')
                    except Exception as e:
                        print(f"⚠️ 数据读取遇到问题，尝试备用方法: {e}")
                        # 备用方法：按空格分隔
                        data = pd.read_csv(file_path, sep=r'\s+', header=None, 
                                         names=['Date', 'Time', 'Temperature', 'Humidity'],
                                         engine='python', on_bad_lines='skip')
                        data['Time'] = data['Date'].astype(str) + ' ' + data['Time'].astype(str)
                        data['Time'] = pd.to_datetime(data['Time'], errors='coerce')
                        data = data.drop('Date', axis=1)
                    
                    # 确保时间列正确解析
                    if data['Time'].dtype != 'datetime64[ns]':
                        data['Time'] = pd.to_datetime(data['Time'], errors='coerce')
                    
                    # 删除空值行
                    data = data.dropna(subset=['Time'])
                    
                    # 添加测点信息
                    data['Station'] = station_name
                    
                    # 存储数据
                    self.temperature_humidity_data[station_name] = data
                    
                    # 移除成功提示
                    
                except Exception as e:
                    print(f"❌ 加载文件 {file_path.name} 失败: {e}")
                    
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
        return self.temperature_humidity_data
    
    def preprocess_data(self):
        """数据预处理"""
        print("\n🔧 数据预处理...")
        
        for station_name, data in self.temperature_humidity_data.items():
            if data is not None and not data.empty:
                # 确保数值列为数值类型
                data['Temperature'] = pd.to_numeric(data['Temperature'], errors='coerce')
                data['Humidity'] = pd.to_numeric(data['Humidity'], errors='coerce')
                
                # 添加时间特征
                data['Date'] = data['Time'].dt.date
                data['Hour'] = data['Time'].dt.hour
                data['Month'] = data['Time'].dt.month
                data['Year'] = data['Time'].dt.year
                
                # 移除无效数据
                initial_count = len(data)
                data.dropna(subset=['Temperature', 'Humidity'], inplace=True)
                final_count = len(data)
                
                if initial_count != final_count:
                    print(f"⚠️ 测点 {station_name}: 移除了 {initial_count - final_count} 条无效数据")
        
        print(f"✅ 温湿度数据预处理完成，共处理 {len(self.temperature_humidity_data)} 个测点")
    
    def analyze_basic_stats(self):
        """基础统计分析"""
        print("\n📊 基础统计分析")
        print("=" * 50)
        
        stats_summary = {}
        
        for station_name, data in self.temperature_humidity_data.items():
            if data is not None and not data.empty:
                # 仅在后台计算，不再向控制台打印详细数据
                
                # 温度统计
                temp_stats = data['Temperature'].describe()
                
                # 湿度统计
                humidity_stats = data['Humidity'].describe()
                
                # 湿度超限统计（基于原始数据）
                over_limit_count = len(data[data['Humidity'] > self.humidity_threshold])
                total_count = len(data)
                over_limit_rate = (over_limit_count / total_count) * 100
                
                # 存储统计信息
                stats_summary[station_name] = {
                    'records': len(data),
                    'temp_mean': temp_stats['mean'],
                    'temp_max': temp_stats['max'],
                    'temp_min': temp_stats['min'],
                    'temp_std': temp_stats['std'],
                    'temp_range': temp_stats['max'] - temp_stats['min'],
                    'humidity_mean': humidity_stats['mean'],
                    'humidity_max': humidity_stats['max'],
                    'humidity_min': humidity_stats['min'],
                    'humidity_std': humidity_stats['std'],
                    'humidity_range': humidity_stats['max'] - humidity_stats['min'],
                    'over_limit_count': over_limit_count,
                    'over_limit_rate': over_limit_rate
                }
        
        return stats_summary
    

        return self.temperature_humidity_data

    def get_humidity_threshold(self):
        return self.humidity_threshold
