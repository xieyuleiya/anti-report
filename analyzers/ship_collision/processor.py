import pandas as pd
from pathlib import Path

class ShipCollisionProcessor:
    def __init__(self, bridge_name: str, data_dir: Path):
        self.bridge_name = bridge_name
        self.data_dir = data_dir
        self.navigation_data = None
        self.deviation_data = None
        
    def load_data(self):
        """加载助航和偏航数据"""
        try:
            # 读取助航数据
            navigation_file = self.data_dir / "助航统计.txt"
            if navigation_file.exists():
                self.navigation_data = pd.read_csv(navigation_file, sep='\t')
            else:
                print("助航数据文件不存在")
            
            # 读取偏航数据
            deviation_file = self.data_dir / "偏航统计.txt"
            if deviation_file.exists():
                self.deviation_data = pd.read_csv(deviation_file, sep='\t')
            else:
                print("偏航数据文件不存在")
                
        except Exception as e:
            print(f"数据加载失败: {e}")
        
        print(f"✅ 船舶数据加载完成")
        return self.navigation_data, self.deviation_data
    
    def preprocess_data(self):
        """数据预处理"""
        for data, name in [(self.navigation_data, "助航"), (self.deviation_data, "偏航")]:
            if data is not None and not data.empty:
                # 转换时间列
                data['EnterTime'] = pd.to_datetime(data['EnterTime'])
                data['Date'] = data['EnterTime'].dt.date
                data['Hour'] = data['EnterTime'].dt.hour
                data['Month'] = data['EnterTime'].dt.month
                data['Year'] = data['EnterTime'].dt.year
                
                # 处理数值列
                numeric_cols = ['Length', 'Width', 'Tonnage']
                for col in numeric_cols:
                    if col in data.columns:
                        data[col] = pd.to_numeric(data[col], errors='coerce')
        
        print(f"✅ 船舶数据预处理完成")
    
    def analyze_basic_stats(self):
        """基础统计分析"""
        print("\n基础统计分析")
        print("=" * 50)
        
        for data, name in [(self.navigation_data, "助航"), (self.deviation_data, "偏航")]:
            if data is not None and not data.empty:
                # 仅保留核心统计提示，不再向控制台打印各类分布
                pass
    
