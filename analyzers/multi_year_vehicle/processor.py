import pandas as pd
import numpy as np
import os
from pathlib import Path
from datetime import datetime

class MultiYearVehicleProcessor:
    def __init__(self, bridge_name, data_base_path):
        self.bridge_name = bridge_name
        self.data_base_path = Path(data_base_path)
        
        self.yearly_data = {}  # {year: {direction: dataframe}}
        self.years = []
        self.directions = []

    def parse_filename(self, filename):
        """解析文件名获取方向名称"""
        try:
            name_without_ext = filename.replace('.txt', '')
            parts = name_without_ext.split('_')
            if len(parts) >= 4:
                return parts[-1]
            return name_without_ext
        except Exception:
            return filename.replace('.txt', '')

    def scan_data_structure(self):
        """扫描数据目录结构"""
        if not self.data_base_path.exists():
            raise FileNotFoundError(f"数据目录不存在: {self.data_base_path}")
        
        year_dirs = []
        for item in os.listdir(self.data_base_path):
            item_path = self.data_base_path / item
            if item_path.is_dir() and item.isdigit():
                year_dirs.append(item)
        
        if not year_dirs:
            raise ValueError("未找到年份目录")
        
        year_dirs.sort()
        self.years = year_dirs
        
        # 获取所有方向（以第一个年份目录为准）
        first_year_path = self.data_base_path / self.years[0]
        directions_set = set()
        for filename in os.listdir(first_year_path):
            if filename.endswith('.txt'):
                directions_set.add(self.parse_filename(filename))
        
        self.directions = sorted(list(directions_set))
        return self.years, self.directions

    def load_yearly_data(self):
        """加载所有年份的数据"""
        for year in self.years:
            year_path = self.data_base_path / year
            self.yearly_data[year] = {}
            
            year_files = {}
            for filename in os.listdir(year_path):
                if filename.endswith('.txt'):
                    direction_name = self.parse_filename(filename)
                    year_files[direction_name] = filename
            
            for direction in self.directions:
                if direction in year_files:
                    file_path = year_path / year_files[direction]
                    try:
                        df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
                        df['DataTime'] = pd.to_datetime(df['DataTime'])
                        df['日期'] = df['DataTime'].dt.date
                        df['小时'] = df['DataTime'].dt.hour
                        df['月份'] = df['DataTime'].dt.month
                        df['年份'] = df['DataTime'].dt.year
                        df['方向'] = direction
                        df['年度'] = year
                        df['TotalWeight'] = df['TotalWeight'] / 1000 # kg -> t
                        
                        # 过滤轴数
                        df = df[df['AxleCount'].between(2, 6)]
                        self.yearly_data[year][direction] = df
                    except Exception as e:
                        print(f"  加载{year}年{direction}数据失败: {e}")
                        self.yearly_data[year][direction] = pd.DataFrame()
                else:
                    self.yearly_data[year][direction] = pd.DataFrame()
        
        print(f"✅ 多年度车辆数据加载完成，涵盖 {len(self.years)} 个年度")

    def extract_plate_province(self, plate):
        if pd.isna(plate) or plate == '': return '未知'
        province_map = {
            '京': '北京', '津': '天津', '冀': '河北', '晋': '山西', '蒙': '内蒙古',
            '辽': '辽宁', '吉': '吉林', '黑': '黑龙江', '沪': '上海', '苏': '江苏',
            '浙': '浙江', '皖': '安徽', '闽': '福建', '赣': '江西', '鲁': '山东',
            '豫': '河南', '鄂': '湖北', '湘': '湖南', '粤': '广东', '桂': '广西',
            '琼': '海南', '渝': '重庆', '川': '四川', '贵': '贵州', '云': '云南',
            '藏': '西藏', '陕': '陕西', '甘': '甘肃', '青': '青海', '宁': '宁夏',
            '新': '新疆', '台': '台湾', '港': '香港', '澳': '澳门'
        }
        return province_map.get(str(plate)[0], '其他')

    def normalize_plate_color(self, value):
        if pd.isna(value): return '未确定'
        s = str(value).strip()
        if '未确定' in s: return '未确定'
        if ('渐变' in s and '绿' in s) or ('渐变绿色' in s): return '渐变绿色'
        if ('黄' in s and '绿' in s) and ('双拼' in s or '双拼色' in s or '双' in s): return '黄绿双拼色'
        if '蓝' in s: return '蓝色'
        if '黄' in s: return '黄色'
        if '白' in s: return '白色'
        if '黑' in s: return '黑色'
        return '未确定'

    def analyze_weight_distribution(self, df):
        if df.empty:
            return {'counts': {}, 'percentages': {}, 'total': 0, 'mean_weight': 0, 'max_weight': 0, 'min_weight': 0}
        weights = df['TotalWeight']
        ranges = [(0, 10, '10吨以下'), (10, 20, '10-20吨'), (20, 30, '20-30吨'), 
                  (30, 40, '30-40吨'), (40, 51.45, '40-51.45吨'), (51.45, 60, '51.45-60吨'), (60, float('inf'), '60吨以上')]
        dist = {}
        for mn, mx, lbl in ranges:
            if mx == float('inf'): dist[lbl] = len(weights[weights >= mn])
            else: dist[lbl] = len(weights[(weights >= mn) & (weights < mx)])
        total = len(weights)
        pcts = {k: (v/total)*100 if total > 0 else 0 for k, v in dist.items()}
        return {'counts': dist, 'percentages': pcts, 'total': total, 'mean_weight': weights.mean(), 'max_weight': weights.max(), 'min_weight': weights.min()}

    def analyze_overweight_vehicles(self, df):
        if df.empty: return {'over_51_45_count': 0, 'over_60_count': 0, 'over_51_45_percentage': 0, 'over_60_percentage': 0}
        w = df['TotalWeight']
        t = len(w)
        o51 = len(w[w > 51.45])
        o60 = len(w[w > 60])
        return {'over_51_45_count': o51, 'over_60_count': o60, 'over_51_45_percentage': (o51/t)*100 if t>0 else 0, 'over_60_percentage': (o60/t)*100 if t>0 else 0}

    def analyze_yearly_stats(self):
        stats = {'years': self.years, 'directions': self.directions, 'yearly_summary': {}, 'yearly_direction_stats': {}}
        for year in self.years:
            yearly_total = 0
            direction_counts = {}
            year_data_list = []
            stats['yearly_direction_stats'][year] = {}
            
            for direction in self.directions:
                df = self.yearly_data[year].get(direction, pd.DataFrame())
                if not df.empty:
                    df['归属地'] = df['CarPlate'].apply(self.extract_plate_province)
                    if 'CarPlateColor' in df.columns:
                        df['CarPlateColor'] = df['CarPlateColor'].apply(self.normalize_plate_color)
                    
                    count = len(df)
                    yearly_total += count
                    direction_counts[direction] = count
                    year_data_list.append(df)
                    
                    days = (df['日期'].max() - df['日期'].min()).days + 1
                    days = max(1, days)
                    
                    stats['yearly_direction_stats'][year][direction] = {
                        'count': count,
                        'axle_stats': df['AxleCount'].value_counts().sort_index(),
                        'color_stats': df['CarPlateColor'].value_counts(),
                        'type_stats': df['CarType'].value_counts(),
                        'province_stats': df['归属地'].value_counts().head(10),
                        'weight_stats': self.analyze_weight_distribution(df),
                        'overweight_stats': self.analyze_overweight_vehicles(df),
                        'hourly_stats': df.groupby('小时').size() / days,
                        'daily_stats': df.groupby('日期').size()
                    }
                else:
                    direction_counts[direction] = 0
                    stats['yearly_direction_stats'][year][direction] = {
                        'count': 0,
                        'axle_stats': pd.Series(dtype=int),
                        'color_stats': pd.Series(dtype=int),
                        'type_stats': pd.Series(dtype=int),
                        'province_stats': pd.Series(dtype=int),
                        'weight_stats': self.analyze_weight_distribution(df),
                        'overweight_stats': self.analyze_overweight_vehicles(df),
                        'hourly_stats': pd.Series(dtype=float),
                        'daily_stats': pd.Series(dtype=int)
                    }
            
            stats['yearly_summary'][year] = {
                'total_vehicles': yearly_total,
                'direction_counts': direction_counts,
                'combined_df': pd.concat(year_data_list, ignore_index=True) if year_data_list else pd.DataFrame()
            }
        return stats
