import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import numpy as np
from pathlib import Path
import re

plt.rcParams['font.sans-serif'] = ['SimSun']
plt.rcParams['axes.unicode_minus'] = False

def natural_sort_key(text):
    return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', text)]

class WindSpeedPlotter:
    def __init__(self, bridge_name, output_dir, original_data, wind_data):
        self.bridge_name = bridge_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.original_data = original_data
        self.wind_data = wind_data
        
        self.colors = {
            'blue': '#1f77b4', 'red': '#d62728', 'green': '#2ca02c',
            'orange': '#ff7f0e', 'purple': '#9467bd', 'brown': '#8c564b',
            'pink': '#e377c2', 'gray': '#7f7f7f'
        }
        
        # 定义风力等级和对应的风速范围
        self.wind_force_levels = [
            (0, 0.3), (0.3, 1.6), (1.6, 3.4), (3.4, 5.5), (5.5, 8.0),
            (8.0, 10.8), (10.8, 13.9), (13.9, 17.2), (17.2, 20.8),
            (20.8, 24.5), (24.5, 28.5), (28.5, 32.7), (32.7, 37.0),
            (37.0, 41.5), (41.5, 46.2), (46.2, 51.0), (51.0, 56.1), (56.1, 100)
        ]
        
        # 专业的配色方案 (针对8个显示的等级)
        self.level_colors = [
            '#87CEEB', '#90EE90', '#FFD700', '#FFA500', 
            '#FF6347', '#8B4513', '#8B0000', '#4B0082'
        ]
        
        print(f"🎨 风速绘图器初始化完成: {self.bridge_name}")

    def plot_wind_time_series(self):
        """绘制风速和风向时间序列图"""
        print("📊 绘制风速和风向时序图...")
        for sensor_name, data in self.original_data.items():
            if data is None or data.empty: continue
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8))
            
            ax1.plot(data['Time'], data['WindSpeed'], color=self.colors['blue'], linewidth=1.0, alpha=0.8)
            ax1.set_title(f'{sensor_name}风速时序图', fontsize=16, fontweight='bold')
            ax1.set_ylabel('风速 (m/s)', fontsize=14)
            ax1.grid(True, alpha=0.3)
            
            ax2.scatter(data['Time'], data['WindDirection'], color=self.colors['red'], s=3, alpha=0.4)
            ax2.set_title(f'{sensor_name}风向时序图', fontsize=16, fontweight='bold')
            ax2.set_ylabel('风向 (°)', fontsize=14)
            ax2.set_ylim(0, 360)
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / f"{sensor_name}风速风向时序图.png", dpi=300, bbox_inches='tight')
            plt.close()

    def plot_comprehensive_wind_analysis(self):
        """绘制综合风速分析图 (包含高级玫瑰图)"""
        print("📊 绘制综合风速分析图...")
        for sensor_name, data in self.original_data.items():
            if data is None or data.empty: continue
            
            fig = plt.figure(figsize=(18, 6))
            
            # 1. 风速分布 (左图)
            ax1 = plt.subplot(1, 3, 1)
            ax1.hist(data['WindSpeed'], bins=20, alpha=0.7, color=self.colors['blue'], edgecolor='darkblue', density=True)
            ax1.set_title('风速分布', fontsize=16, fontweight='bold', pad=20)
            ax1.set_xlabel('风速 (m/s)', fontsize=14)
            ax1.set_ylabel('密度', fontsize=14)
            ax1.grid(True, alpha=0.3)
            
            # 2. 风向分布 (中图)
            ax2 = plt.subplot(1, 3, 2)
            direction_bins = np.arange(0, 361, 10)
            direction_labels = [f'{i}°' for i in range(0, 360, 10)]
            counts = pd.cut(data['WindDirection'], bins=direction_bins, labels=direction_labels, include_lowest=True).value_counts()
            percentages = (counts / len(data) * 100).fillna(0)
            sorted_indices = sorted(percentages.index, key=lambda x: int(x.replace('°', '')))
            sorted_v = percentages.reindex(sorted_indices)
            
            ax2.bar(range(len(sorted_v)), sorted_v.values, color=self.colors['green'], alpha=0.7)
            ax2.set_title('风向分布', fontsize=16, fontweight='bold', pad=20)
            ax2.set_xlabel('风向 (°)', fontsize=14)
            ax2.set_ylabel('频率 (%)', fontsize=14)
            ax2.set_xticks(range(0, len(sorted_v), 6))
            ax2.set_xticklabels([sorted_indices[i] for i in range(0, len(sorted_v), 6)], rotation=45)
            ax2.grid(True, alpha=0.3)
            
            # 3. 高级风向玫瑰图 (右图)
            ax3 = plt.subplot(1, 3, 3, projection='polar')
            self._draw_premium_rose(ax3, data)
            ax3.set_title('风向玫瑰图', fontsize=16, fontweight='bold', pad=30)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / f"{sensor_name}综合分析图.png", dpi=300, bbox_inches='tight')
            plt.close()

    def plot_wind_rose(self):
        """独立绘制高级风向玫瑰图"""
        print("🌹 绘制分层风向玫瑰图...")
        for sensor_name, data in self.original_data.items():
            if data is None or data.empty: continue
            fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(8, 8))
            self._draw_premium_rose(ax, data)
            ax.set_title(f'{sensor_name} 风向玫瑰图', fontsize=18, fontweight='bold', pad=40)
            plt.savefig(self.output_dir / f"{sensor_name}风向玫瑰图.png", dpi=300, bbox_inches='tight')
            plt.close()

    def _draw_premium_rose(self, ax, data):
        """高级分层玫瑰图绘制逻辑"""
        directions = np.radians(data['WindDirection'])
        speeds = data['WindSpeed']
        
        # 8个主要方向
        dir_bins = np.radians([-22.5, 22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5])
        dir_labels = ['北风', '东北风', '东风', '东南风', '南风', '西南风', '西风', '西北风']
        
        # 计算全局最大频率以对齐半径
        max_f = 0
        dir_stats = []
        for i in range(len(dir_bins)-1):
            mask = (directions >= dir_bins[i]) & (directions < dir_bins[i+1])
            if mask.any():
                f = mask.sum() / len(data) * 100
                max_f = max(max_f, f)
                dir_stats.append((i, f, speeds[mask]))
            else:
                dir_stats.append((i, 0, None))
                
        max_r = max(20, min(50, max_f * 1.1))
        width = np.radians(45)
        
        for i, total_f, dir_speeds in dir_stats:
            if total_f < 0.01: continue
            
            angle = dir_bins[i]
            
            # 计算该方向内各风力等级的分布
            level_fs = []
            for j, (low, high) in enumerate(self.wind_force_levels):
                count = ((dir_speeds >= low) & (dir_speeds < high)).sum()
                level_fs.append(count / len(dir_speeds) * total_f)
            
            # 从内向外累积绘制
            curr_r = 0
            for j, lf in enumerate(level_fs):
                if lf < 0.05: continue
                
                # 颜色映射 (0-1: 浅蓝, 2: 浅绿, 3: 金, 4: 橙, 5: 红, 6: 棕, 7: 深红, 8+: 紫)
                color_idx = min(7, j if j <= 1 else j - 1) if j < 8 else 7
                color = self.level_colors[color_idx]
                
                radius_start = curr_r
                radius_end = curr_r + lf
                
                # 绘制扇形
                theta_sector = np.linspace(angle, angle + width, 30)
                ax.fill_between(theta_sector, radius_start, radius_end, 
                               color=color, alpha=0.8, edgecolor='black', linewidth=0.2)
                curr_r = radius_end

        # 格式化
        ax.set_theta_direction(-1)
        ax.set_theta_zero_location('N')
        ax.set_xticks(np.radians([0, 45, 90, 135, 180, 225, 270, 315]))
        ax.set_xticklabels(dir_labels, fontsize=12)
        ax.set_ylim(0, max_r)
        
        # 频率刻度
        ticks = np.arange(0, max_r + 5, 5)
        ax.set_yticks(ticks)
        ax.set_yticklabels([f'{t}%' for t in ticks], fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # 专业的图例
        legend_labels = ['≤1级', '2级', '3级', '4级', '5级', '6级', '7级', '≥8级']
        elements = [patches.Patch(color=c, alpha=0.7) for c in self.level_colors]
        ax.legend(elements, legend_labels, loc='upper right', bbox_to_anchor=(1.25, 1.1), fontsize=10, frameon=True)

    def create_wind_statistics_table(self, stats_summary):
        """创建风速统计表格"""
        if not stats_summary: return None
        table_data = []
        for name in sorted(stats_summary.keys(), key=natural_sort_key):
            s = stats_summary[name]
            table_data.append({
                '测点名称': name,
                '平均风速(m/s)': f"{s['wind_speed_mean']:.2f}",
                '最大风速(m/s)': f"{s['wind_speed_max']:.2f}",
                '最小风速(m/s)': f"{s['wind_speed_min']:.2f}",
                '风速标准差(m/s)': f"{s['wind_speed_std']:.2f}",
                '平均风向(°)': f"{s['wind_direction_mean']:.2f}",
                '记录数量': s['records_count']
            })
        df = pd.DataFrame(table_data)
        df.to_csv(self.output_dir / '风速统计表.csv', index=False, encoding='utf-8-sig')
        return df
