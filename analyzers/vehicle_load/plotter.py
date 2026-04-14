import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import pandas as pd
from pathlib import Path

# 设置中文字体为宋体，英文字体为Times New Roman
plt.rcParams['font.sans-serif'] = ['SimSun']  # 宋体
plt.rcParams['font.serif'] = ['Times New Roman']  # Times New Roman
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

class VehicleLoadPlotter:
    def __init__(self, bridge_name: str, output_dir: Path, direction1_name: str, direction2_name: str, df1=None, df2=None, df_combined=None):
        self.bridge_name = bridge_name
        self.output_dir = str(output_dir)
        self.direction1_name = direction1_name
        self.direction2_name = direction2_name
        self.df1 = df1
        self.df2 = df2
        self.df_combined = df_combined
        self.COLORS = {
            'blue': '#1f77b4',
            'red': '#d62728',
            'green': '#2ca02c',
            'orange': '#ff7f0e',
            'purple': '#9467bd'
        }

    def find_two_peaks(self, daily_stats):
        # 将数据按时间排序
        sorted_data = daily_stats.sort_index()
        mean_traffic = sorted_data.mean()
        std_traffic = sorted_data.std()
        threshold = mean_traffic + 1.0 * std_traffic
        high_traffic_days = sorted_data[sorted_data > threshold]
        
        if len(high_traffic_days) == 0:
            sorted_values = sorted_data.sort_values(ascending=False)
            peak1_date = sorted_values.index[0]
            peak1_val = sorted_values.iloc[0]
            peak2_date = sorted_values.index[1] if len(sorted_values) > 1 else peak1_date
            peak2_val = sorted_values.iloc[1] if len(sorted_values) > 1 else peak1_val
            return peak1_date, peak2_date, peak1_val, peak2_val
        
        peak_groups = []
        current_group = [high_traffic_days.index[0]]
        for i in range(1, len(high_traffic_days)):
            current_date = high_traffic_days.index[i]
            prev_date = current_group[-1]
            if (current_date - prev_date).days <= 7:
                current_group.append(current_date)
            else:
                peak_groups.append(current_group)
                current_group = [current_date]
        if current_group:
            peak_groups.append(current_group)
        
        peak_maxes = []
        for group in peak_groups:
            group_data = sorted_data[group]
            max_date = group_data.idxmax()
            max_val = group_data.max()
            peak_maxes.append((max_date, max_val))
        
        peak_maxes.sort(key=lambda x: x[1], reverse=True)
        if len(peak_maxes) >= 2:
            peak1_date, peak1_val = peak_maxes[0]
            peak2_date, peak2_val = None, None
            for i in range(1, len(peak_maxes)):
                candidate_date, candidate_val = peak_maxes[i]
                if abs((peak1_date - candidate_date).days) >= 30:
                    peak2_date, peak2_val = candidate_date, candidate_val
                    break
            if peak2_date is None:
                peak2_date, peak2_val = peak_maxes[1] if len(peak_maxes) > 1 else peak_maxes[0]
            return peak1_date, peak2_date, peak1_val, peak2_val
        else:
            if len(peak_maxes) == 1:
                peak1_date, peak1_val = peak_maxes[0]
                sorted_values = sorted_data.sort_values(ascending=False)
                peak2_date = sorted_values.index[1] if len(sorted_values) > 1 else peak1_date
                peak2_val = sorted_values.iloc[1] if len(sorted_values) > 1 else peak1_val
                return peak1_date, peak2_date, peak1_val, peak2_val
            else:
                sorted_values = sorted_data.sort_values(ascending=False)
                peak1_date = sorted_values.index[0]
                peak1_val = sorted_values.iloc[0]
                peak2_date = sorted_values.index[1] if len(sorted_values) > 1 else peak1_date
                peak2_val = sorted_values.iloc[1] if len(sorted_values) > 1 else peak1_val
                return peak1_date, peak2_date, peak1_val, peak2_val

    def create_enhanced_charts(self, stats):
        """创建增强的统计图表"""
        print("正在生成增强统计图表...")
        
        # 创建输出目录
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # 1. 轴数统计图
        self.plot_enhanced_axle_stats(stats)
        
        # 2. 车牌颜色统计图
        self.plot_enhanced_color_stats(stats)
        
        # 3. 车型统计图
        self.plot_enhanced_type_stats(stats)
        
        # 4. 车重统计图
        self.plot_enhanced_weight_stats(stats)
        
        # 5. 归属地统计图
        self.plot_enhanced_province_stats(stats)
        
        # 6. 每日车流量统计
        self.plot_enhanced_daily_traffic(stats)
        
        # 7. 分时流量统计
        self.plot_enhanced_hourly_traffic(stats)
        
        # 8. 各轴车辆车重分布
        self.plot_enhanced_axle_weight_distribution()
        
        print("增强图表生成完成！")
    
    def plot_enhanced_axle_stats(self, stats):
        """绘制增强的轴数统计图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 刘屋-白土方向
        ax1.bar(stats['axle_stats1'].index, stats['axle_stats1'].values, color=self.COLORS['blue'], alpha=0.8)
        ax1.set_title(f'{self.direction1_name}通行车辆轴数统计', fontsize=16, fontweight='bold')
        ax1.set_xlabel('轴数', fontsize=14)
        ax1.set_ylabel('车辆数量', fontsize=14)
        ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax1.tick_params(axis='both', which='major', labelsize=12)
        
        # 添加数值标签
        for i, v in enumerate(stats['axle_stats1'].values):
            ax1.text(stats['axle_stats1'].index[i], v + v*0.01, f'{v}', ha='center', va='bottom', fontweight='bold')
        
        # 白土-刘屋方向
        ax2.bar(stats['axle_stats2'].index, stats['axle_stats2'].values, color=self.COLORS['red'], alpha=0.8)
        ax2.set_title(f'{self.direction2_name}通行车辆轴数统计', fontsize=16, fontweight='bold')
        ax2.set_xlabel('轴数', fontsize=14)
        ax2.set_ylabel('车辆数量', fontsize=14)
        ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax2.tick_params(axis='both', which='major', labelsize=12)
        
        # 添加数值标签
        for i, v in enumerate(stats['axle_stats2'].values):
            ax2.text(stats['axle_stats2'].index[i], v + v*0.01, f'{v}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '轴数统计结果.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_enhanced_color_stats(self, stats):
        """绘制增强的车牌颜色统计图（柱状图）"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 刘屋-白土方向
        colors1 = stats['color_stats1']
        bars1 = ax1.bar(range(len(colors1)), colors1.values, color=self.COLORS['blue'], alpha=0.8)
        ax1.set_title(f'{self.direction1_name}车牌颜色统计', fontsize=16, fontweight='bold')
        ax1.set_xlabel('车牌颜色', fontsize=14)
        ax1.set_ylabel('车辆数量', fontsize=14)
        ax1.set_xticks(range(len(colors1)))
        ax1.set_xticklabels(colors1.index, rotation=45)
        ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax1.tick_params(axis='both', which='major', labelsize=12)
        
        # 添加数值标签
        for i, v in enumerate(colors1.values):
            percentage = v / colors1.values.sum() * 100
            ax1.text(i, v + v*0.01, f'{v}\n({percentage:.1f}%)', 
                    ha='center', va='bottom', fontsize=14, fontweight='bold')
        
        # 白土-刘屋方向
        colors2 = stats['color_stats2']
        bars2 = ax2.bar(range(len(colors2)), colors2.values, color=self.COLORS['red'], alpha=0.8)
        ax2.set_title(f'{self.direction2_name}车牌颜色统计', fontsize=16, fontweight='bold')
        ax2.set_xlabel('车牌颜色', fontsize=14)
        ax2.set_ylabel('车辆数量', fontsize=14)
        ax2.set_xticks(range(len(colors2)))
        ax2.set_xticklabels(colors2.index, rotation=45)
        ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax2.tick_params(axis='both', which='major', labelsize=12)
        
        # 添加数值标签
        for i, v in enumerate(colors2.values):
            percentage = v / colors2.values.sum() * 100
            ax2.text(i, v + v*0.01, f'{v}\n({percentage:.1f}%)', 
                    ha='center', va='bottom', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '车牌颜色统计结果.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_enhanced_type_stats(self, stats):
        """绘制增强的车型统计图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 刘屋-白土方向
        types1 = stats['type_stats1']
        bars1 = ax1.bar(range(len(types1)), types1.values, color=self.COLORS['blue'], alpha=0.8)
        ax1.set_title(f'{self.direction1_name}车型统计', fontsize=16, fontweight='bold')
        ax1.set_xlabel('车型', fontsize=14)
        ax1.set_ylabel('车辆数量', fontsize=14)
        ax1.set_xticks(range(len(types1)))
        ax1.set_xticklabels(types1.index, rotation=45)
        ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax1.tick_params(axis='both', which='major', labelsize=12)
        
        # 添加数值标签
        for i, v in enumerate(types1.values):
            ax1.text(i, v + v*0.01, f'{v}', ha='center', va='bottom', rotation=45, fontweight='bold')
        
        # 白土-刘屋方向
        types2 = stats['type_stats2']
        bars2 = ax2.bar(range(len(types2)), types2.values, color=self.COLORS['red'], alpha=0.8)
        ax2.set_title(f'{self.direction2_name}车型统计', fontsize=16, fontweight='bold')
        ax2.set_xlabel('车型', fontsize=14)
        ax2.set_ylabel('车辆数量', fontsize=14)
        ax2.set_xticks(range(len(types2)))
        ax2.set_xticklabels(types2.index, rotation=45)
        ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax2.tick_params(axis='both', which='major', labelsize=12)
        
        # 添加数值标签
        for i, v in enumerate(types2.values):
            ax2.text(i, v + v*0.01, f'{v}', ha='center', va='bottom', rotation=45, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '车型统计结果.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_enhanced_weight_stats(self, stats):
        """绘制增强的车重统计图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 刘屋-白土方向
        weights1 = stats['weight_stats1']['counts']
        ax1.bar(weights1.keys(), weights1.values(), color=self.COLORS['blue'], alpha=0.8)
        ax1.set_title(f'{self.direction1_name}车重分布统计', fontsize=16, fontweight='bold')
        ax1.set_xlabel('重量区间', fontsize=14)
        ax1.set_ylabel('车辆数量', fontsize=14)
        ax1.tick_params(axis='x', rotation=45, labelsize=12)
        ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        # 添加百分比标签
        for i, (k, v) in enumerate(weights1.items()):
            percentage = stats['weight_stats1']['percentages'][k]
            ax1.text(i, v + v*0.01, f'{percentage:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # 白土-刘屋方向
        weights2 = stats['weight_stats2']['counts']
        ax2.bar(weights2.keys(), weights2.values(), color=self.COLORS['red'], alpha=0.8)
        ax2.set_title(f'{self.direction2_name}车重分布统计', fontsize=16, fontweight='bold')
        ax2.set_xlabel('重量区间', fontsize=14)
        ax2.set_ylabel('车辆数量', fontsize=14)
        ax2.tick_params(axis='x', rotation=45, labelsize=12)
        ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        # 添加百分比标签
        for i, (k, v) in enumerate(weights2.items()):
            percentage = stats['weight_stats2']['percentages'][k]
            ax2.text(i, v + v*0.01, f'{percentage:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '车重统计结果.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_enhanced_province_stats(self, stats):
        """绘制增强的归属地统计图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 刘屋-白土方向
        provinces1 = stats['province_stats1']
        bars1 = ax1.bar(range(len(provinces1)), provinces1.values, color=self.COLORS['blue'], alpha=0.8)
        ax1.set_title(f'{self.direction1_name}车辆归属地统计', fontsize=16, fontweight='bold')
        ax1.set_xlabel('省份', fontsize=14)
        ax1.set_ylabel('车辆数量', fontsize=14)
        ax1.set_xticks(range(len(provinces1)))
        ax1.set_xticklabels(provinces1.index, rotation=45)
        ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax1.tick_params(axis='both', which='major', labelsize=12)
        
        # 添加数值标签
        for i, v in enumerate(provinces1.values):
            ax1.text(i, v + v*0.01, f'{v}', ha='center', va='bottom', rotation=45, fontweight='bold')
        
        # 白土-刘屋方向
        provinces2 = stats['province_stats2']
        bars2 = ax2.bar(range(len(provinces2)), provinces2.values, color=self.COLORS['red'], alpha=0.8)
        ax2.set_title(f'{self.direction2_name}车辆归属地统计', fontsize=16, fontweight='bold')
        ax2.set_xlabel('省份', fontsize=14)
        ax2.set_ylabel('车辆数量', fontsize=14)
        ax2.set_xticks(range(len(provinces2)))
        ax2.set_xticklabels(provinces2.index, rotation=45)
        ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax2.tick_params(axis='both', which='major', labelsize=12)
        
        # 添加数值标签
        for i, v in enumerate(provinces2.values):
            ax2.text(i, v + v*0.01, f'{v}', ha='center', va='bottom', rotation=45, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '归属地统计结果.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_enhanced_daily_traffic(self, stats):
        """绘制增强的每日车流量统计"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 刘屋-白土方向
        daily1 = stats['daily_stats1']
        ax1.plot(daily1.index, daily1.values, color=self.COLORS['blue'], linewidth=2.5, alpha=0.9, 
                marker='o', markersize=3, markeredgecolor=self.COLORS['blue'], markerfacecolor=self.COLORS['blue'])
        ax1.set_title(f'{self.direction1_name}每日车流量统计', fontsize=16, fontweight='bold')
        ax1.set_xlabel('日期', fontsize=14)
        ax1.set_ylabel('车流量', fontsize=14)
        ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax1.tick_params(axis='x', rotation=45, labelsize=12)
        
        # 标记两个高峰期
        peak1_idx1, peak2_idx1, peak1_val1, peak2_val1 = self.find_two_peaks(daily1)
        ax1.plot(peak1_idx1, peak1_val1, 'ro', markersize=8)
        ax1.annotate(f'高峰期1: {peak1_val1}\n日期: {peak1_idx1}', 
                     xy=(peak1_idx1, peak1_val1), xytext=(10, -30),
                     textcoords='offset points', bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                     arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        ax1.plot(peak2_idx1, peak2_val1, 'go', markersize=6)
        ax1.annotate(f'高峰期2: {peak2_val1}\n日期: {peak2_idx1}', 
                     xy=(peak2_idx1, peak2_val1), xytext=(10, 30),
                     textcoords='offset points', bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7),
                     arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 添加平均值线
        mean1 = daily1.mean()
        ax1.axhline(y=mean1, color=self.COLORS['red'], linestyle='--', alpha=0.8, linewidth=2, label=f'平均值: {mean1:.0f}')
        ax1.legend(fontsize=12)
        
        # 白土-刘屋方向
        daily2 = stats['daily_stats2']
        ax2.plot(daily2.index, daily2.values, color=self.COLORS['red'], linewidth=2.5, alpha=0.9,
                marker='s', markersize=3, markeredgecolor=self.COLORS['red'], markerfacecolor=self.COLORS['red'])
        ax2.set_title(f'{self.direction2_name}每日车流量统计', fontsize=16, fontweight='bold')
        ax2.set_xlabel('日期', fontsize=14)
        ax2.set_ylabel('车流量', fontsize=14)
        ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax2.tick_params(axis='x', rotation=45, labelsize=12)
        
        # 标记两个高峰期
        peak1_idx2, peak2_idx2, peak1_val2, peak2_val2 = self.find_two_peaks(daily2)
        ax2.plot(peak1_idx2, peak1_val2, 'ro', markersize=8)
        ax2.annotate(f'高峰期1: {peak1_val2}\n日期: {peak1_idx2}', 
                     xy=(peak1_idx2, peak1_val2), xytext=(10, -30),
                     textcoords='offset points', bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                     arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        ax2.plot(peak2_idx2, peak2_val2, 'go', markersize=6)
        ax2.annotate(f'高峰期2: {peak2_val2}\n日期: {peak2_idx2}', 
                     xy=(peak2_idx2, peak2_val2), xytext=(10, 30),
                     textcoords='offset points', bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7),
                     arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 添加平均值线
        mean2 = daily2.mean()
        ax2.axhline(y=mean2, color=self.COLORS['blue'], linestyle='--', alpha=0.8, linewidth=2, label=f'平均值: {mean2:.0f}')
        ax2.legend(fontsize=12)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '每日车流量统计结果.png'), dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_enhanced_hourly_traffic(self, stats):
        """绘制增强的分时流量统计"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 刘屋-白土方向
        hourly1 = stats['hourly_stats1']
        ax1.bar(hourly1.index, hourly1.values, color=self.COLORS['blue'], alpha=0.8)
        ax1.set_title(f'{self.direction1_name}分时流量统计', fontsize=16, fontweight='bold')
        ax1.set_xlabel('小时', fontsize=14)
        ax1.set_ylabel('平均车流量', fontsize=14)
        ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax1.set_xticks(range(0, 24, 2))
        ax1.tick_params(axis='both', which='major', labelsize=12)
        
        # 白土-刘屋方向
        hourly2 = stats['hourly_stats2']
        ax2.bar(hourly2.index, hourly2.values, color=self.COLORS['red'], alpha=0.8)
        ax2.set_title(f'{self.direction2_name}分时流量统计', fontsize=16, fontweight='bold')
        ax2.set_xlabel('小时', fontsize=14)
        ax2.set_ylabel('平均车流量', fontsize=14)
        ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax2.set_xticks(range(0, 24, 2))
        ax2.tick_params(axis='both', which='major', labelsize=12)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '分时流量统计结果.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # 第一张图：两个方向车流量 + 双向平均车流量
        plt.figure(figsize=(12, 6))
        x = range(24)
        
        # 计算双向平均车流量（应该在中间）
        avg_traffic = (hourly1.values + hourly2.values) / 2
        
        plt.plot(x, hourly1.values, 'o-', label=f'{self.direction1_name}车流量', 
                color=self.COLORS['blue'], linewidth=2.5, markersize=6)
        plt.plot(x, hourly2.values, 's-', label=f'{self.direction2_name}车流量', 
                color=self.COLORS['red'], linewidth=2.5, markersize=6)
        plt.plot(x, avg_traffic, '^-', label='双向平均车流量', 
                color=self.COLORS['green'], linewidth=3, markersize=8)
        
        plt.title('双向分时流量对比', fontsize=16, fontweight='bold')
        plt.xlabel('小时', fontsize=14)
        plt.ylabel('平均车流量', fontsize=14)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(x[::2])
        plt.tick_params(axis='both', which='major', labelsize=12)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '双向分时流量对比.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # 第二张图：两个方向平均重量 + 双向平均重量
        plt.figure(figsize=(12, 6))
        
        # 计算各方向的平均重量
        hourly_weight1 = self.df1.groupby('小时')['TotalWeight'].mean()
        hourly_weight2 = self.df2.groupby('小时')['TotalWeight'].mean()
        
        # 计算双向平均重量（应该在中间）
        avg_weight = (hourly_weight1.values + hourly_weight2.values) / 2
        
        plt.plot(x, hourly_weight1.values, 'o-', label=f'{self.direction1_name}平均重量', 
                color=self.COLORS['blue'], linewidth=2.5, markersize=6)
        plt.plot(x, hourly_weight2.values, 's-', label=f'{self.direction2_name}平均重量', 
                color=self.COLORS['red'], linewidth=2.5, markersize=6)
        plt.plot(x, avg_weight, '^-', label='双向平均重量', 
                color=self.COLORS['green'], linewidth=3, markersize=8)
        
        plt.title('双向车辆平均重量（分时段统计）', fontsize=16, fontweight='bold')
        plt.xlabel('小时', fontsize=14)
        plt.ylabel('平均重量（吨）', fontsize=14)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(x[::2])
        plt.tick_params(axis='both', which='major', labelsize=12)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '双向车辆平均重量统计.png'), dpi=300, bbox_inches='tight')
        plt.close()
        

    
    def plot_enhanced_axle_weight_distribution(self):
        """绘制增强的各轴车辆车重分布"""
        # 只统计2-6轴的有效数据
        valid_axles = range(2, 7)
        
        for axle_count in valid_axles:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # 高陂-上径方向 - 数据已经过滤为2-6轴
            df1_axle = self.df1[self.df1['AxleCount'] == axle_count]
            if not df1_axle.empty:
                ax1.hist(df1_axle['TotalWeight'], bins=30, alpha=0.7, color=self.COLORS['blue'], edgecolor=self.COLORS['blue'])
                ax1.set_title(f'{self.direction1_name} {axle_count}轴车车重分布', fontsize=16, fontweight='bold')
                ax1.set_xlabel('车重（吨）', fontsize=14)
                ax1.set_ylabel('车辆数量', fontsize=14)
                ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
                ax1.tick_params(axis='both', which='major', labelsize=12)
                
                # 添加统计信息
                mean_weight = df1_axle['TotalWeight'].mean()
                ax1.axvline(x=mean_weight, color=self.COLORS['red'], linestyle='--', alpha=0.8, linewidth=2,
                           label=f'平均重量: {mean_weight:.1f}吨')
                ax1.legend(fontsize=12)
            
            # 上径-高陂方向 - 数据已经过滤为2-6轴
            df2_axle = self.df2[self.df2['AxleCount'] == axle_count]
            if not df2_axle.empty:
                ax2.hist(df2_axle['TotalWeight'], bins=30, alpha=0.7, color=self.COLORS['red'], edgecolor=self.COLORS['red'])
                ax2.set_title(f'{self.direction2_name} {axle_count}轴车车重分布', fontsize=16, fontweight='bold')
                ax2.set_xlabel('车重（吨）', fontsize=14)
                ax2.set_ylabel('车辆数量', fontsize=14)
                ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
                ax2.tick_params(axis='both', which='major', labelsize=12)
                
                # 添加统计信息
                mean_weight = df2_axle['TotalWeight'].mean()
                ax2.axvline(x=mean_weight, color=self.COLORS['blue'], linestyle='--', alpha=0.8, linewidth=2,
                           label=f'平均重量: {mean_weight:.1f}吨')
                ax2.legend(fontsize=12)
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, f'{axle_count}轴车车重分布.png'), dpi=300, bbox_inches='tight')
            plt.close()
    

    
