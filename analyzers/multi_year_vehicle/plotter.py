import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
from pathlib import Path

# 设置中文字体为宋体，英文字体为Times New Roman
plt.rcParams['font.sans-serif'] = ['SimSun']
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['font.size'] = 9 
plt.rcParams['axes.unicode_minus'] = False 
plt.rcParams['figure.constrained_layout.use'] = True 

class MultiYearVehiclePlotter:
    COLORS = {
        'blue': '#1f77b4', 'red': '#d62728', 'green': '#2ca02c', 'orange': '#ff7f0e',
        'purple': '#9467bd', 'brown': '#8c564b', 'pink': '#e377c2', 'gray': '#7f7f7f',
        'olive': '#bcbd22', 'cyan': '#17becf'
    }
    FIG_SIZE = (12.2/2.54, 6.0/2.54)
    TITLE_FS = 12
    LABEL_FS = 10
    TICK_FS = 9
    LEGEND_FS = 9

    def __init__(self, bridge_name, output_dir, years, directions):
        self.bridge_name = bridge_name
        self.output_dir = Path(output_dir)
        self.years = years
        self.directions = directions
        self.color_list = list(self.COLORS.values())

    def plot_yearly_total_traffic(self, stats):
        fig, ax = plt.subplots(1, 1, figsize=self.FIG_SIZE)
        total_counts = [stats['yearly_summary'][y]['total_vehicles'] for y in self.years]
        bars = ax.bar(self.years, total_counts, color=self.color_list[:len(self.years)], alpha=0.8)
        ax.set_title(f'{self.bridge_name}年度总车流量对比', fontsize=self.TITLE_FS, fontweight='bold')
        ax.set_xlabel('年份', fontsize=self.LABEL_FS)
        ax.set_ylabel('车辆总数', fontsize=self.LABEL_FS)
        ax.grid(True, alpha=0.3)
        for bar, count in zip(bars, total_counts):
            h = bar.get_height()
            ax.text(bar.get_x()+bar.get_width()/2., h+h*0.01, f'{count:,}', ha='center', va='bottom', fontweight='bold', fontsize=10)
        plt.savefig(self.output_dir / '年度总车流量对比.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_yearly_direction_traffic(self, stats):
        fig, axes = plt.subplots(1, len(self.directions), figsize=self.FIG_SIZE, sharey=True)
        if len(self.directions) == 1: axes = [axes]
        for i, direction in enumerate(self.directions):
            counts = [stats['yearly_summary'][y]['direction_counts'][direction] for y in self.years]
            bars = axes[i].bar(self.years, counts, color=self.color_list[:len(self.years)], alpha=0.8)
            axes[i].set_title(f'{direction}年度车流量对比', fontsize=self.TITLE_FS, fontweight='bold')
            axes[i].set_ylabel('车辆数量', fontsize=self.LABEL_FS)
            axes[i].grid(True, alpha=0.3)
            for bar, count in zip(bars, counts):
                if count > 0:
                    h = bar.get_height()
                    axes[i].text(bar.get_x() + bar.get_width()/2., h + h*0.01, f'{count:,}', ha='center', va='bottom', fontweight='bold', fontsize=8)
        plt.savefig(self.output_dir / '各方向年度车流量对比.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_yearly_axle_comparison(self, stats):
        all_axles = sorted(list(set(a for y in self.years for d in self.directions for a in stats['yearly_direction_stats'][y][d]['axle_stats'].index)))
        fig, axes = plt.subplots(1, len(self.directions), figsize=self.FIG_SIZE, sharey=True)
        if len(self.directions) == 1: axes = [axes]
        for i, direction in enumerate(self.directions):
            x = np.arange(len(all_axles))
            width = 0.8 / len(self.years)
            for j, year in enumerate(self.years):
                axle_stats = stats['yearly_direction_stats'][year][direction]['axle_stats']
                y_data = [axle_stats.get(axle, 0) for axle in all_axles]
                axes[i].bar(x + j*width, y_data, width, label=f'{year}年', color=self.color_list[j], alpha=0.8)
            axes[i].set_title(f'{direction}轴数统计对比', fontsize=self.TITLE_FS, fontweight='bold')
            axes[i].set_xticks(x + width * (len(self.years)-1) / 2)
            axes[i].set_xticklabels(all_axles)
            axes[i].legend(fontsize=self.LEGEND_FS)
        plt.savefig(self.output_dir / '轴数统计年度对比.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_yearly_color_comparison(self, stats):
        allowed = ['蓝色', '渐变绿色', '黄色', '黄绿双拼色', '白色', '黑色', '未确定']
        present = set(c for y in self.years for d in self.directions for c in stats['yearly_direction_stats'][y][d]['color_stats'].index)
        all_colors = [c for c in allowed if c in present]
        fig, axes = plt.subplots(1, len(self.directions), figsize=self.FIG_SIZE, sharey=True)
        if len(self.directions) == 1: axes = [axes]
        for i, direction in enumerate(self.directions):
            x = np.arange(len(all_colors))
            width = 0.8 / len(self.years)
            for j, year in enumerate(self.years):
                c_stats = stats['yearly_direction_stats'][year][direction]['color_stats']
                y_data = [c_stats.get(c, 0) for c in all_colors]
                axes[i].bar(x + j*width, y_data, width, label=f'{year}年', color=self.color_list[j], alpha=0.8)
            axes[i].set_title(f'{direction}车牌颜色对比', fontsize=self.TITLE_FS, fontweight='bold')
            axes[i].set_xticks(x + width*(len(self.years)-1)/2)
            axes[i].set_xticklabels(all_colors, rotation=45)
        plt.savefig(self.output_dir / '车牌颜色统计年度对比.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_yearly_weight_comparison(self, stats):
        cats = ['10吨以下', '10-20吨', '20-30吨', '30-40吨', '40-51.45吨', '51.45-60吨', '60吨以上']
        fig, axes = plt.subplots(1, len(self.directions), figsize=self.FIG_SIZE, sharey=True)
        if len(self.directions) == 1: axes = [axes]
        for i, direction in enumerate(self.directions):
            x = np.arange(len(cats))
            width = 0.8 / len(self.years)
            for j, year in enumerate(self.years):
                w_stats = stats['yearly_direction_stats'][year][direction]['weight_stats']
                y_data = [w_stats['percentages'].get(c, 0) for c in cats]
                axes[i].bar(x + j*width, y_data, width, label=f'{year}年', color=self.color_list[j], alpha=0.8)
            axes[i].set_title(f'{direction}车重分布对比', fontsize=self.TITLE_FS, fontweight='bold')
            axes[i].set_xticks(x + width*(len(self.years)-1)/2)
            axes[i].set_xticklabels(cats, rotation=45)
            axes[i].set_ylabel('比例(%)')
        plt.savefig(self.output_dir / '车重分布年度对比.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_yearly_hourly_comparison(self, stats):
        hours = list(range(24))
        fig, axes = plt.subplots(1, len(self.directions), figsize=self.FIG_SIZE, sharey=True)
        if len(self.directions) == 1: axes = [axes]
        for j, direction in enumerate(self.directions):
            for i, year in enumerate(self.years):
                h_stats = stats['yearly_direction_stats'][year][direction]['hourly_stats']
                h_data = [h_stats.get(h, 0) for h in hours]
                axes[j].plot(hours, h_data, 'o-', label=f'{year}年', color=self.color_list[i], linewidth=2, markersize=4)
            axes[j].set_title(f'{direction}分时流量对比', fontsize=self.TITLE_FS, fontweight='bold')
            axes[j].set_xticks(range(0, 24, 2))
            axes[j].legend(fontsize=7)
        plt.savefig(self.output_dir / '分时流量年度综合对比.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_yearly_daily_timeseries_comparison(self, stats):
        days = np.arange(1, 367)
        fig, axes = plt.subplots(1, len(self.directions), figsize=self.FIG_SIZE, sharey=True)
        if len(self.directions) == 1: axes = [axes]
        for j, direction in enumerate(self.directions):
            for i, year in enumerate(self.years):
                daily = stats['yearly_direction_stats'][year][direction]['daily_stats']
                if daily is None or daily.empty: continue
                idx = pd.to_datetime(daily.index)
                doy = idx.dayofyear
                series = pd.Series(daily.values, index=doy).groupby(level=0).sum().reindex(days, fill_value=np.nan)
                axes[j].plot(days, series.values, label=f'{year}年', color=self.color_list[i], linewidth=1)
                axes[j].hlines(y=np.nanmean(series.values), xmin=1, xmax=366, colors=self.color_list[i], linestyles='--', linewidth=0.8)
            axes[j].set_title(f'{direction}日流量趋势对比', fontsize=self.TITLE_FS, fontweight='bold')
            axes[j].set_xticks([1,32,60,91,121,152,182,213,244,274,305,335])
            axes[j].set_xticklabels([f'{m}月' for m in range(1,13)])
        plt.savefig(self.output_dir / '随时间日流量年度综合对比.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_all(self, stats):
        self.plot_yearly_total_traffic(stats)
        self.plot_yearly_direction_traffic(stats)
        self.plot_yearly_axle_comparison(stats)
        self.plot_yearly_color_comparison(stats)
        self.plot_yearly_weight_comparison(stats)
        self.plot_yearly_hourly_comparison(stats)
        self.plot_yearly_daily_timeseries_comparison(stats)
