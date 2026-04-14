import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class VehicleLoadProcessor:
    # ==================== 配置区域 ====================
    # 桥名配置 - 如果通过参数传入bridge_name，则不需要修改此处
    # 文件名格式：S003244001103020040_6_崖门大桥_崖南-金门.txt
    # 格式说明：门架号_桥ID_桥名_方向名
    # 系统会自动从文件名中解析方向名，无需手动指定
    BRIDGE_NAME = "崖门大桥"  # 默认桥名（如果通过参数传入则会被覆盖）
    
    # 以下配置已废弃，系统会自动从文件名解析
    # 保留这些变量仅用于向后兼容
    DIRECTION1_FILE = None  # 自动发现，无需手动指定
    DIRECTION2_FILE = None  # 自动发现，无需手动指定
    DIRECTION1_NAME = None  # 自动从文件名解析
    DIRECTION2_NAME = None  # 自动从文件名解析


    
    # Word模板文件路径 - 请根据实际情况修改
    # TEMPLATE_PATH = r"D:\03-chengxu\cursor\report_gen\年报模版.docx"
    
    # 鲜艳的配色方案
    COLORS = {
        'blue': '#1f77b4',      # 鲜艳的蓝色
        'red': '#d62728',        # 鲜艳的红色
        'green': '#2ca02c',      # 鲜艳的绿色
        'orange': '#ff7f0e',     # 鲜艳的橙色
        'purple': '#9467bd'      # 鲜艳的紫色
    }
    # ================================================
    
    def __init__(self, bridge_name=None, data_dir=None, output_dir=None, 
                 direction1_file=None, direction2_file=None,
                 direction1_name=None, direction2_name=None):
        """
        初始化车辆荷载分析器
        
        Args:
            bridge_name: 桥梁名称，如果为None则使用类属性BRIDGE_NAME
            data_dir: 数据目录，如果为None则自动推导
            output_dir: 输出目录，如果为None则自动推导
            direction1_file: 方向1数据文件名，如果为None则使用类属性
            direction2_file: 方向2数据文件名，如果为None则使用类属性
            direction1_name: 方向1名称，如果为None则使用类属性
            direction2_name: 方向2名称，如果为None则使用类属性
        """
        # 使用传入的桥名或类属性
        self.bridge_name = bridge_name or self.BRIDGE_NAME
        
        # 如果提供了data_dir和output_dir，使用提供的路径（统一路径管理）
        if data_dir:
            self.data_dir = str(data_dir)
        else:
            # 兼容旧代码：使用相对路径
            script_path = Path(__file__).resolve()
            chelianghezai_dir = script_path.parent
            self.data_dir = str(chelianghezai_dir / self.bridge_name / "数据")
        
        if output_dir:
            self.output_dir = str(output_dir)
        else:
            # 兼容旧代码：输出目录在数据目录下
            self.output_dir = str(Path(self.data_dir) / "详细分析结果")
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 使用传入的方向配置或类属性（如果为None则自动发现）
        self.direction1_file = direction1_file or self.DIRECTION1_FILE
        self.direction2_file = direction2_file or self.DIRECTION2_FILE
        # 方向名会在load_data时自动从文件名解析，这里先设置默认值
        self.direction1_name = direction1_name or self.DIRECTION1_NAME
        self.direction2_name = direction2_name or self.DIRECTION2_NAME
        
        # 初始化数据
        self.df1 = None
        self.df2 = None
        self.df_combined = None
        
    def parse_direction_from_filename(self, filename):
        """
        从文件名中解析方向名
        文件名格式：S003244001103020040_6_崖门大桥_崖南-金门.txt
        格式：门架号_桥ID_桥名_方向名
        返回方向名（最后一部分）
        """
        # 移除扩展名
        stem = Path(filename).stem
        
        # 按下划线分割
        parts = stem.split('_')
        
        if len(parts) >= 4:
            # 格式：门架号_桥ID_桥名_方向名
            # 方向名是最后一部分
            direction_name = parts[-1]
            return direction_name
        elif len(parts) >= 2:
            # 如果格式不标准，尝试提取包含"-"的部分作为方向名
            for part in reversed(parts):
                if '-' in part:
                    return part
            # 如果没有"-"，返回最后一部分
            return parts[-1]
        else:
            # 如果格式完全不符合，返回整个文件名（不含扩展名）
            return stem
    
    def load_data(self):
        """加载数据文件"""
        print("正在加载数据...")
        print(f"数据目录: {self.data_dir}")
        
        # 检查数据目录是否存在
        data_path = Path(self.data_dir)
        if not data_path.exists():
            raise FileNotFoundError(f"数据目录不存在: {self.data_dir}")
        
        # 自动发现所有txt文件
        txt_files = list(data_path.glob("*.txt"))
        
        if len(txt_files) < 2:
            raise FileNotFoundError(f"需要至少两个方向的数据文件，但只找到 {len(txt_files)} 个文件")
        
        # 如果用户指定了文件名，优先使用指定的文件
        if self.direction1_file and self.direction2_file:
            file1_path = data_path / self.direction1_file
            file2_path = data_path / self.direction2_file
            
            if file1_path.exists() and file2_path.exists():
                print(f"使用指定的文件:")
                print(f"  文件1: {file1_path.name}")
                print(f"  文件2: {file2_path.name}")
            else:
                print(f"⚠️ 指定的文件不存在，自动发现数据文件...")
                # 自动选择前两个文件
                file1_path = txt_files[0]
                file2_path = txt_files[1]
                self.direction1_file = file1_path.name
                self.direction2_file = file2_path.name
        else:
            # 自动选择前两个文件
            file1_path = txt_files[0]
            file2_path = txt_files[1]
            self.direction1_file = file1_path.name
            self.direction2_file = file2_path.name
        
        # 从文件名自动解析方向名
        self.direction1_name = self.parse_direction_from_filename(file1_path.name)
        self.direction2_name = self.parse_direction_from_filename(file2_path.name)
        
        # 移除详细的文件识别打印
        
        # 读取数据，假设是制表符分隔
        self.df1 = pd.read_csv(file1_path, sep='\t', encoding='utf-8')
        self.df2 = pd.read_csv(file2_path, sep='\t', encoding='utf-8')
        
        # 添加方向标识
        self.df1['方向'] = self.direction1_name
        self.df2['方向'] = self.direction2_name
        
        # 合并数据
        self.df_combined = pd.concat([self.df1, self.df2], ignore_index=True)
        
        # 转换时间列和重量单位
        for df in [self.df1, self.df2, self.df_combined]:
            df['DataTime'] = pd.to_datetime(df['DataTime'])
            df['日期'] = df['DataTime'].dt.date
            df['小时'] = df['DataTime'].dt.hour
            df['月份'] = df['DataTime'].dt.month
            df['年份'] = df['DataTime'].dt.year
            # 将重量从kg转换为吨
            df['TotalWeight'] = df['TotalWeight'] / 1000
        
        # 过滤掉异常轴数数据（只保留2-6轴的有效数据）
        print("正在过滤异常轴数数据...")
        original_count1 = len(self.df1)
        original_count2 = len(self.df2)
        
        self.df1 = self.df1[self.df1['AxleCount'].between(2, 6)]
        self.df2 = self.df2[self.df2['AxleCount'].between(2, 6)]
        self.df_combined = pd.concat([self.df1, self.df2], ignore_index=True)
        
        filtered_count1 = len(self.df1)
        filtered_count2 = len(self.df2)
        
        print(f"✅ 数据加载完成: {self.direction1_name}({len(self.df1)}条), {self.direction2_name}({len(self.df2)}条)")
        
    def extract_plate_province(self, plate):
        """提取车牌归属地"""
        if pd.isna(plate) or plate == '':
            return '未知'
        
        # 中国各省简称映射
        province_map = {
            '京': '北京', '津': '天津', '冀': '河北', '晋': '山西', '蒙': '内蒙古',
            '辽': '辽宁', '吉': '吉林', '黑': '黑龙江', '沪': '上海', '苏': '江苏',
            '浙': '浙江', '皖': '安徽', '闽': '福建', '赣': '江西', '鲁': '山东',
            '豫': '河南', '鄂': '湖北', '湘': '湖南', '粤': '广东', '桂': '广西',
            '琼': '海南', '渝': '重庆', '川': '四川', '贵': '贵州', '云': '云南',
            '藏': '西藏', '陕': '陕西', '甘': '甘肃', '青': '青海', '宁': '宁夏',
            '新': '新疆', '台': '台湾', '港': '香港', '澳': '澳门'
        }
        
        # 提取第一个字符作为省份简称
        first_char = str(plate)[0]
        return province_map.get(first_char, '其他')
    
    def analyze_detailed_stats(self):
        """详细统计分析"""
        # 仅保留关键进度提示
        
        # 基础统计
        total_vehicles = len(self.df_combined)
        direction1_count = len(self.df1)
        direction2_count = len(self.df2)
        
        # 轴数统计 - 数据已经过滤为2-6轴
        axle_stats1 = self.df1['AxleCount'].value_counts().sort_index()
        axle_stats2 = self.df2['AxleCount'].value_counts().sort_index()
        
        # 车牌颜色统计
        color_stats1 = self.df1['CarPlateColor'].value_counts()
        color_stats2 = self.df2['CarPlateColor'].value_counts()
        
        # 车型统计
        type_stats1 = self.df1['CarType'].value_counts()
        type_stats2 = self.df2['CarType'].value_counts()
        
        # 车重详细统计
        weight_stats1 = self.analyze_detailed_weight_distribution(self.df1)
        weight_stats2 = self.analyze_detailed_weight_distribution(self.df2)
        
        # 归属地统计
        self.df1['归属地'] = self.df1['CarPlate'].apply(self.extract_plate_province)
        self.df2['归属地'] = self.df2['CarPlate'].apply(self.extract_plate_province)
        province_stats1 = self.df1['归属地'].value_counts().head(10)
        province_stats2 = self.df2['归属地'].value_counts().head(10)
        
        # 每日车流量统计
        daily_stats1 = self.df1.groupby('日期').size()
        daily_stats2 = self.df2.groupby('日期').size()
        
        # 分时流量统计 - 计算平均每天每个小时的车流量
        # 计算监测期内的总天数
        total_days = (self.df_combined['日期'].max() - self.df_combined['日期'].min()).days + 1
        
        # 获取监测期的时间范围
        start_date = self.df_combined['日期'].min()
        end_date = self.df_combined['日期'].max()
        
        # 计算平均每天每个小时的车流量
        hourly_stats1 = self.df1.groupby('小时').size() / total_days
        hourly_stats2 = self.df2.groupby('小时').size() / total_days
        
        # 超重车统计
        overweight_stats1 = self.analyze_overweight_vehicles(self.df1)
        overweight_stats2 = self.analyze_overweight_vehicles(self.df2)
        
        # 夜间重车行驶情况分析
        night_heavy_ratio1 = self.analyze_night_heavy_vehicles(self.df1)
        night_heavy_ratio2 = self.analyze_night_heavy_vehicles(self.df2)
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_days': total_days,
            'total_vehicles': total_vehicles,
            'direction1_count': direction1_count,
            'direction2_count': direction2_count,
            'axle_stats1': axle_stats1,
            'axle_stats2': axle_stats2,
            'color_stats1': color_stats1,
            'color_stats2': color_stats2,
            'type_stats1': type_stats1,
            'type_stats2': type_stats2,
            'weight_stats1': weight_stats1,
            'weight_stats2': weight_stats2,
            'province_stats1': province_stats1,
            'province_stats2': province_stats2,
            'daily_stats1': daily_stats1,
            'daily_stats2': daily_stats2,
            'hourly_stats1': hourly_stats1,
            'hourly_stats2': hourly_stats2,
            'overweight_stats1': overweight_stats1,
            'overweight_stats2': overweight_stats2,
            'night_heavy_ratio1': night_heavy_ratio1,
            'night_heavy_ratio2': night_heavy_ratio2
        }
    
    def analyze_detailed_weight_distribution(self, df):
        """详细分析车重分布"""
        weights = df['TotalWeight']
        
        # 定义重量区间
        weight_ranges = [
            (0, 10, '10吨以下'),
            (10, 20, '10-20吨'),
            (20, 30, '20-30吨'),
            (30, 40, '30-40吨'),
            (40, 51.45, '40-51.45吨'),
            (51.45, 60, '51.45-60吨'),
            (60, float('inf'), '60吨以上')
        ]
        
        weight_dist = {}
        for min_w, max_w, label in weight_ranges:
            if max_w == float('inf'):
                count = len(weights[weights >= min_w])
            else:
                count = len(weights[(weights >= min_w) & (weights < max_w)])
            weight_dist[label] = count
        
        # 计算百分比
        total = len(weights)
        weight_percentages = {k: (v/total)*100 for k, v in weight_dist.items()}
        
        return {
            'counts': weight_dist,
            'percentages': weight_percentages,
            'total': total,
            'mean_weight': weights.mean(),
            'max_weight': weights.max(),
            'min_weight': weights.min()
        }
    
    def analyze_overweight_vehicles(self, df):
        """分析超重车辆"""
        weights = df['TotalWeight']
        
        # 超过51.45吨的车辆
        over_51_45 = len(weights[weights > 51.45])
        over_60 = len(weights[weights > 60])
        
        return {
            'over_51_45_count': over_51_45,
            'over_60_count': over_60,
            'over_51_45_percentage': (over_51_45 / len(weights)) * 100,
            'over_60_percentage': (over_60 / len(weights)) * 100
        }
    

    
    def analyze_night_heavy_vehicles(self, df):
        """分析夜间重车行驶情况"""
        # 定义夜间时间段：0点到8点
        night_hours = [0, 1, 2, 3, 4, 5, 6, 7]
        
        # 筛选夜间时段的车辆
        night_vehicles = df[df['小时'].isin(night_hours)]
        
        if len(night_vehicles) == 0:
            return 0.0
        
        # 定义重车：超过40吨的车辆
        heavy_vehicles = night_vehicles[night_vehicles['TotalWeight'] > 40]
        
        # 计算夜间重车比例
        night_heavy_ratio = len(heavy_vehicles) / len(night_vehicles)
        
        return night_heavy_ratio
    
    def find_two_peaks(self, daily_stats):
        """识别两个不同的高峰期，返回每个高峰期内的最大值"""
        # 将数据按时间排序
        sorted_data = daily_stats.sort_index()
        
        # 计算平均值和标准差，用于识别显著高峰
        mean_traffic = sorted_data.mean()
        std_traffic = sorted_data.std()
        threshold = mean_traffic + 1.0 * std_traffic  # 高于平均值1个标准差的认为是高峰
        
        # 找到所有超过阈值的日期
        high_traffic_days = sorted_data[sorted_data > threshold]
        
        if len(high_traffic_days) == 0:
            # 如果没有明显高峰，返回最大值和第二大值
            sorted_values = sorted_data.sort_values(ascending=False)
            peak1_date = sorted_values.index[0]
            peak1_val = sorted_values.iloc[0]
            peak2_date = sorted_values.index[1] if len(sorted_values) > 1 else peak1_date
            peak2_val = sorted_values.iloc[1] if len(sorted_values) > 1 else peak1_val
            return peak1_date, peak2_date, peak1_val, peak2_val
        
        # 将高峰日期分组，相邻的日期归为同一个高峰期
        peak_groups = []
        current_group = [high_traffic_days.index[0]]
        
        for i in range(1, len(high_traffic_days)):
            current_date = high_traffic_days.index[i]
            prev_date = current_group[-1]
            
            # 如果与前一个日期相差不超过7天，归为同一组
            if (current_date - prev_date).days <= 7:
                current_group.append(current_date)
            else:
                # 开始新的一组
                peak_groups.append(current_group)
                current_group = [current_date]
        
        # 添加最后一组
        if current_group:
            peak_groups.append(current_group)
        
        # 为每个高峰期找到最大值
        peak_maxes = []
        for group in peak_groups:
            group_data = sorted_data[group]
            max_date = group_data.idxmax()
            max_val = group_data.max()
            peak_maxes.append((max_date, max_val))
        
        # 按车流量排序
        peak_maxes.sort(key=lambda x: x[1], reverse=True)
        
        # 确保至少有两个不同时间段的高峰
        if len(peak_maxes) >= 2:
            peak1_date, peak1_val = peak_maxes[0]
            
            # 找到与第一个高峰时间相差至少30天的第二个高峰
            peak2_date, peak2_val = None, None
            for i in range(1, len(peak_maxes)):
                candidate_date, candidate_val = peak_maxes[i]
                if abs((peak1_date - candidate_date).days) >= 30:
                    peak2_date, peak2_val = candidate_date, candidate_val
                    break
            
            # 如果找不到相差30天的，就取第二大的
            if peak2_date is None:
                peak2_date, peak2_val = peak_maxes[1] if len(peak_maxes) > 1 else peak_maxes[0]
            
            return peak1_date, peak2_date, peak1_val, peak2_val
        else:
            # 只有一个高峰期，返回该高峰期的最大值和次大值
            if len(peak_maxes) == 1:
                peak1_date, peak1_val = peak_maxes[0]
                # 在整个数据中找第二大值
                sorted_values = sorted_data.sort_values(ascending=False)
                peak2_date = sorted_values.index[1] if len(sorted_values) > 1 else peak1_date
                peak2_val = sorted_values.iloc[1] if len(sorted_values) > 1 else peak1_val
                return peak1_date, peak2_date, peak1_val, peak2_val
            else:
                # 没有高峰期，返回最大值和第二大值
                sorted_values = sorted_data.sort_values(ascending=False)
                peak1_date = sorted_values.index[0]
                peak1_val = sorted_values.iloc[0]
                peak2_date = sorted_values.index[1] if len(sorted_values) > 1 else peak1_date
                peak2_val = sorted_values.iloc[1] if len(sorted_values) > 1 else peak1_val
                return peak1_date, peak2_date, peak1_val, peak2_val
    

    

    def get_dfs(self):
        return self.df1, self.df2, self.df_combined
