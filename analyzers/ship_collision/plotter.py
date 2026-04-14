import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['SimSun']
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['axes.unicode_minus'] = False

class ShipCollisionPlotter:
    def __init__(self, bridge_name: str, output_dir: Path, navigation_data, deviation_data):
        self.bridge_name = bridge_name
        self.output_dir = output_dir
        self.navigation_data = navigation_data
        self.deviation_data = deviation_data

    def plot_daily_traffic(self):
        """绘制每日通航量统计"""
        # 鲜艳的配色方案
        colors = {
            'blue': '#1f77b4',      # 鲜艳的蓝色
            'red': '#d62728',        # 鲜艳的红色
            'green': '#2ca02c',      # 鲜艳的绿色
            'orange': '#ff7f0e',     # 鲜艳的橙色
            'purple': '#9467bd'      # 鲜艳的紫色
        }
        
        # 助航数据每日统计 - 单独图表
        if self.navigation_data is not None and not self.navigation_data.empty:
            fig, ax = plt.subplots(figsize=(15, 6))
            daily_nav = self.navigation_data.groupby('Date').size()
            
            # 使用平滑的线条
            ax.plot(daily_nav.index, daily_nav.values, color=colors['blue'], linewidth=2.5, alpha=0.9, 
                    marker='o', markersize=3, markeredgecolor=colors['blue'], markerfacecolor=colors['blue'])
            ax.set_title(f'{self.bridge_name} - 每日助航船舶数量统计', fontsize=16, fontweight='bold')
            ax.set_ylabel('船舶数量', fontsize=14)
            ax.set_xlabel('日期', fontsize=14)
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax.tick_params(axis='both', which='major', labelsize=12)
            
            # 添加平均值线
            avg_nav = daily_nav.mean()
            ax.axhline(y=avg_nav, color=colors['red'], linestyle='--', alpha=0.8, linewidth=2, 
                       label=f'平均值: {avg_nav:.1f}')
            ax.legend(fontsize=12)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / '每日助航船舶数量统计.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # 偏航数据每日统计 - 单独图表
        if self.deviation_data is not None and not self.deviation_data.empty:
            fig, ax = plt.subplots(figsize=(15, 6))
            daily_dev = self.deviation_data.groupby('Date').size()
            
            # 使用平滑的线条
            ax.plot(daily_dev.index, daily_dev.values, color=colors['red'], linewidth=2.5, alpha=0.9,
                    marker='s', markersize=3, markeredgecolor=colors['red'], markerfacecolor=colors['red'])
            ax.set_title(f'{self.bridge_name} - 每日偏航船舶数量统计', fontsize=16, fontweight='bold')
            ax.set_ylabel('船舶数量', fontsize=14)
            ax.set_xlabel('日期', fontsize=14)
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax.tick_params(axis='both', which='major', labelsize=12)
            
            # 添加平均值线
            avg_dev = daily_dev.mean()
            ax.axhline(y=avg_dev, color=colors['blue'], linestyle='--', alpha=0.8, linewidth=2,
                       label=f'平均值: {avg_dev:.1f}')
            ax.legend(fontsize=12)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / '每日偏航船舶数量统计.png', dpi=300, bbox_inches='tight')
            plt.close()
    
    def plot_ship_type_distribution(self):
        """绘制船舶类型分布（柱状图）"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 鲜艳的配色方案
        colors = {
            'blue': '#1f77b4',      # 鲜艳的蓝色
            'red': '#d62728',        # 鲜艳的红色
            'green': '#2ca02c',      # 鲜艳的绿色
            'orange': '#ff7f0e',     # 鲜艳的橙色
            'purple': '#9467bd'      # 鲜艳的紫色
        }
        
        # 助航船舶类型分布
        if self.navigation_data is not None and not self.navigation_data.empty:
            nav_ship_types = self.navigation_data['ShipType'].value_counts()
            bars1 = ax1.bar(range(len(nav_ship_types)), nav_ship_types.values, color=colors['blue'], alpha=0.8)
            ax1.set_title(f'{self.bridge_name} - 助航船舶类型分布', fontsize=16, fontweight='bold')
            ax1.set_xlabel('船舶类型', fontsize=14)
            ax1.set_ylabel('船舶数量', fontsize=14)
            ax1.set_xticks(range(len(nav_ship_types)))
            ax1.set_xticklabels(nav_ship_types.index, rotation=45)
            ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax1.tick_params(axis='both', which='major', labelsize=12)
            
            # 添加数值标签
            for i, v in enumerate(nav_ship_types.values):
                percentage = v / nav_ship_types.values.sum() * 100
                ax1.text(i, v + v*0.01, f'{v:,}\n({percentage:.1f}%)', 
                        ha='center', va='bottom', fontsize=14, fontweight='bold')
        
        # 偏航船舶类型分布
        if self.deviation_data is not None and not self.deviation_data.empty:
            dev_ship_types = self.deviation_data['ShipType'].value_counts()
            bars2 = ax2.bar(range(len(dev_ship_types)), dev_ship_types.values, color=colors['red'], alpha=0.8)
            ax2.set_title(f'{self.bridge_name} - 偏航船舶类型分布', fontsize=16, fontweight='bold')
            ax2.set_xlabel('船舶类型', fontsize=14)
            ax2.set_ylabel('船舶数量', fontsize=14)
            ax2.set_xticks(range(len(dev_ship_types)))
            ax2.set_xticklabels(dev_ship_types.index, rotation=45)
            ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax2.tick_params(axis='both', which='major', labelsize=12)
            
            # 添加数值标签
            for i, v in enumerate(dev_ship_types.values):
                percentage = v / dev_ship_types.values.sum() * 100
                ax2.text(i, v + v*0.01, f'{v:,}\n({percentage:.1f}%)', 
                        ha='center', va='bottom', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '船舶类型分布.png', dpi=300, bbox_inches='tight')
        plt.close()  # 关闭图片，不显示
    
    def plot_direction_distribution(self):
        """绘制航行方向分布"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 鲜艳的配色方案
        colors = {
            'blue': '#1f77b4',      # 鲜艳的蓝色
            'red': '#d62728',        # 鲜艳的红色
            'green': '#2ca02c',      # 鲜艳的绿色
            'orange': '#ff7f0e',     # 鲜艳的橙色
            'purple': '#9467bd'      # 鲜艳的紫色
        }
        
        # 助航船舶方向分布
        if self.navigation_data is not None and not self.navigation_data.empty:
            nav_direction = self.navigation_data['FromUpDown'].value_counts()
            ax1.bar(nav_direction.index, nav_direction.values, color=[colors['blue'], colors['green']], alpha=0.8)
            ax1.set_title(f'{self.bridge_name} - 助航船舶方向分布', fontsize=16, fontweight='bold')
            ax1.set_ylabel('船舶数量', fontsize=14)
            ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax1.tick_params(axis='both', which='major', labelsize=12)
            for i, v in enumerate(nav_direction.values):
                ax1.text(i, v + max(nav_direction.values) * 0.01, str(v), ha='center', va='bottom', fontsize=14, fontweight='bold')
        
        # 偏航船舶方向分布
        if self.deviation_data is not None and not self.deviation_data.empty:
            dev_direction = self.deviation_data['FromUpDown'].value_counts()
            ax2.bar(dev_direction.index, dev_direction.values, color=[colors['red'], colors['orange']], alpha=0.8)
            ax2.set_title(f'{self.bridge_name} - 偏航船舶方向分布', fontsize=16, fontweight='bold')
            ax2.set_ylabel('船舶数量', fontsize=14)
            ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax2.tick_params(axis='both', which='major', labelsize=12)
            for i, v in enumerate(dev_direction.values):
                ax2.text(i, v + max(dev_direction.values) * 0.01, str(v), ha='center', va='bottom', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '航行方向分布.png', dpi=300, bbox_inches='tight')
        plt.close()  # 关闭图片，不显示
    
    def plot_tonnage_distribution(self):
        """绘制吨位分布"""
        # 鲜艳的配色方案
        colors = {
            'blue': '#1f77b4',      # 鲜艳的蓝色
            'red': '#d62728',        # 鲜艳的红色
            'green': '#2ca02c',      # 鲜艳的绿色
            'orange': '#ff7f0e',     # 鲜艳的橙色
            'purple': '#9467bd'      # 鲜艳的紫色
        }
        
        # 助航船舶吨位分布 - 单独图表
        if self.navigation_data is not None and not self.navigation_data.empty and 'Tonnage' in self.navigation_data.columns:
            valid_nav_tonnage = self.navigation_data['Tonnage'].dropna()
            if len(valid_nav_tonnage) > 0:
                fig, ax = plt.subplots(figsize=(15, 6))
                ax.hist(valid_nav_tonnage, bins=30, alpha=0.8, color=colors['blue'], edgecolor=colors['blue'])
                ax.set_title(f'{self.bridge_name} - 助航船舶吨位分布', fontsize=16, fontweight='bold')
                ax.set_xlabel('吨位', fontsize=14)
                ax.set_ylabel('船舶数量', fontsize=14)
                ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
                ax.tick_params(axis='both', which='major', labelsize=12)
                ax.axvline(valid_nav_tonnage.mean(), color=colors['red'], linestyle='--', linewidth=2,
                           label=f'平均值: {valid_nav_tonnage.mean():.1f}')
                ax.legend(fontsize=12)
                
                plt.tight_layout()
                plt.savefig(self.output_dir / '助航船舶吨位分布.png', dpi=300, bbox_inches='tight')
                plt.close()
        
        # 偏航船舶吨位分布 - 单独图表
        if self.deviation_data is not None and not self.deviation_data.empty and 'Tonnage' in self.deviation_data.columns:
            valid_dev_tonnage = self.deviation_data['Tonnage'].dropna()
            if len(valid_dev_tonnage) > 0:
                fig, ax = plt.subplots(figsize=(15, 6))
                ax.hist(valid_dev_tonnage, bins=30, alpha=0.8, color=colors['red'], edgecolor=colors['red'])
                ax.set_title(f'{self.bridge_name} - 偏航船舶吨位分布', fontsize=16, fontweight='bold')
                ax.set_xlabel('吨位', fontsize=14)
                ax.set_ylabel('船舶数量', fontsize=14)
                ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
                ax.tick_params(axis='both', which='major', labelsize=12)
                ax.axvline(valid_dev_tonnage.mean(), color=colors['blue'], linestyle='--', linewidth=2,
                           label=f'平均值: {valid_dev_tonnage.mean():.1f}')
                ax.legend(fontsize=12)
                
                plt.tight_layout()
                plt.savefig(self.output_dir / '偏航船舶吨位分布.png', dpi=300, bbox_inches='tight')
                plt.close()
    

    def generate_charts(self):
        print("\n绘制图表...")
        self.plot_daily_traffic()
        self.plot_ship_type_distribution()
        self.plot_direction_distribution()
        self.plot_tonnage_distribution()
        print("图表绘制完成")
