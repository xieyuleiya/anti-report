import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# 设置中文字体为宋体，英文字体为Times New Roman
plt.rcParams['font.sans-serif'] = ['SimSun']
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['axes.unicode_minus'] = False

class TemperatureHumidityPlotter:
    def __init__(self, bridge_name: str, output_dir: Path, data: dict, humidity_threshold: int):
        self.bridge_name = bridge_name
        self.output_dir = output_dir
        self.temperature_humidity_data = data
        self.humidity_threshold = humidity_threshold

    def plot_all_stations_temperature_humidity(self):
        """绘制所有测点的温度湿度时序图（使用原始数据）"""
        if not self.temperature_humidity_data:
            print("⚠️ 没有数据可绘制")
            return
        
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']
        
        # 绘制温度时序图
        plt.figure(figsize=(15, 6))
        color_idx = 0
        for station_name, data in self.temperature_humidity_data.items():
            if data is not None and not data.empty:
                color = colors[color_idx % len(colors)]
                plt.plot(data['Time'], data['Temperature'], 
                        color=color, linewidth=0.8, alpha=0.7, 
                        label=station_name)
                color_idx += 1
        
        plt.title(f'{self.bridge_name} - 各测点温度时序图', fontsize=16, fontweight='bold')
        plt.ylabel('温度 (°C)', fontsize=14)
        plt.xlabel('时间', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=12)
        plt.tick_params(axis='both', which='major', labelsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.output_dir / '各测点温度时序图.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 绘制湿度时序图
        plt.figure(figsize=(15, 6))
        color_idx = 0
        for station_name, data in self.temperature_humidity_data.items():
            if data is not None and not data.empty:
                color = colors[color_idx % len(colors)]
                plt.plot(data['Time'], data['Humidity'], 
                        color=color, linewidth=0.8, alpha=0.7, 
                        label=station_name)
                color_idx += 1
        
        plt.title(f'{self.bridge_name} - 各测点湿度时序图', fontsize=16, fontweight='bold')
        plt.ylabel('湿度 (%)', fontsize=14)
        plt.xlabel('时间', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=12)
        plt.tick_params(axis='both', which='major', labelsize=12)
        plt.xticks(rotation=45)
        
        # 添加湿度超限线
        plt.axhline(y=self.humidity_threshold, color='red', linestyle='--', 
                   alpha=0.7, label=f'湿度超限阈值 ({self.humidity_threshold}%)')
        plt.legend()
        plt.tight_layout()
        plt.savefig(self.output_dir / '各测点湿度时序图.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_temperature_humidity_distribution(self):
        """绘制各测点的温度湿度频数分布图（使用原始数据）"""
        if not self.temperature_humidity_data:
            print("⚠️ 没有数据可绘制")
            return
        
        n_stations = len(self.temperature_humidity_data)
        fig, axes = plt.subplots(2, n_stations, figsize=(5*n_stations, 10))
        
        if n_stations == 1:
            axes = axes.reshape(2, 1)
        
        station_idx = 0
        for station_name, data in self.temperature_humidity_data.items():
            if data is not None and not data.empty:
                # 温度分布（原始数据）
                axes[0, station_idx].hist(data['Temperature'], bins=30, alpha=0.7, 
                                        color='red', edgecolor='darkred')
                axes[0, station_idx].set_title(f'{station_name}-温度', fontsize=16, fontweight='bold')
                axes[0, station_idx].set_xlabel('温度 (°C)', fontsize=14)
                axes[0, station_idx].set_ylabel('频数', fontsize=14)
                axes[0, station_idx].grid(True, alpha=0.3)
                axes[0, station_idx].tick_params(axis='both', which='major', labelsize=12)
                
                # 添加平均值线
                mean_temp = data['Temperature'].mean()
                axes[0, station_idx].axvline(mean_temp, color='blue', linestyle='--', 
                                           label=f'平均值: {mean_temp:.2f}°C')
                axes[0, station_idx].legend(fontsize=12)
                
                # 湿度分布（原始数据）
                axes[1, station_idx].hist(data['Humidity'], bins=30, alpha=0.7, 
                                        color='blue', edgecolor='darkblue')
                axes[1, station_idx].set_title(f'{station_name}-湿度', fontsize=16, fontweight='bold')
                axes[1, station_idx].set_xlabel('湿度 (%)', fontsize=14)
                axes[1, station_idx].set_ylabel('频数', fontsize=14)
                axes[1, station_idx].grid(True, alpha=0.3)
                axes[1, station_idx].tick_params(axis='both', which='major', labelsize=12)
                
                # 添加平均值线和超限线
                mean_humidity = data['Humidity'].mean()
                axes[1, station_idx].axvline(mean_humidity, color='red', linestyle='--', 
                                           label=f'平均值: {mean_humidity:.2f}%')
                axes[1, station_idx].axvline(self.humidity_threshold, color='orange', linestyle='--', 
                                           label=f'超限阈值: {self.humidity_threshold}%')
                axes[1, station_idx].legend(fontsize=12)
                
                station_idx += 1
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '各测点温湿度频数分布图.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_humidity_exceedance_bar_chart(self):
        """绘制湿度超限柱状图统计（使用原始数据）"""
        if not self.temperature_humidity_data:
            print("⚠️ 没有数据可绘制")
            return
        
        n_stations = len(self.temperature_humidity_data)
        fig, axes = plt.subplots(1, n_stations, figsize=(6*n_stations, 5))
        
        if n_stations == 1:
            axes = [axes]
        
        station_idx = 0
        for station_name, data in self.temperature_humidity_data.items():
            if data is not None and not data.empty:
                ax = axes[station_idx]
                
                # 定义超限阈值（包含50%）
                thresholds = [50, 60, 70, 80, 90, 100]
                exceedance_counts = []
                exceedance_percentages = []
                
                # 计算各阈值的记录数和百分比
                total_records = len(data)
                for threshold in thresholds:
                    if threshold == 100:
                        # 等于100%的记录数
                        count = len(data[data['Humidity'] == threshold])
                    else:
                        # 大于阈值的记录数
                        count = len(data[data['Humidity'] > threshold])
                    exceedance_counts.append(count)
                    percentage = (count / total_records) * 100
                    exceedance_percentages.append(percentage)
                
                # 绘制柱状图（调整柱子宽度）
                bars = ax.bar(thresholds, exceedance_percentages, color='skyblue', alpha=0.7, 
                             edgecolor='navy', width=8)  # 进一步减小柱子宽度
                
                # 在柱子上添加数值标签（记录数和百分比）
                for bar, count, percentage in zip(bars, exceedance_counts, exceedance_percentages):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                           f'{count}条\n{percentage:.1f}%', ha='center', va='bottom', 
                           fontweight='bold', fontsize=14)
                
                # 设置标题和标签
                ax.set_title(f'{station_name} - 湿度超限', fontsize=16, fontweight='bold')
                ax.set_xlabel('超限特征 (%)', fontsize=14)
                ax.set_ylabel('百分比 (%)', fontsize=14)
                ax.grid(True, alpha=0.3, axis='y')
                
                # 设置x轴刻度
                ax.set_xticks(thresholds)
                ax.set_xticklabels([f'>{t}%' if t != 100 else f'={t}%' for t in thresholds])
                ax.tick_params(axis='both', which='major', labelsize=12)
                
                # 设置y轴范围，留出标签空间
                ax.set_ylim(0, max(exceedance_percentages) * 1.15)
                
                station_idx += 1
        
        plt.tight_layout()
        plt.savefig(self.output_dir / '湿度超限记录数统计图.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_temperature_statistics_table(self, stats_summary):
        """创建温度统计表格"""
        if not stats_summary:
            print("⚠️ 没有统计数据可生成表格")
            return None
        
        # 创建温度统计DataFrame
        temp_table_data = []
        for station_name, stats in stats_summary.items():
            temp_table_data.append({
                '测点名称': station_name,
                '温度平均值(°C)': f"{stats['temp_mean']:.2f}",
                '温度最大值(°C)': f"{stats['temp_max']:.2f}",
                '温度最小值(°C)': f"{stats['temp_min']:.2f}",
                '温度差值(°C)': f"{stats['temp_range']:.2f}",
                '温度标准差(°C)': f"{stats['temp_std']:.2f}"
            })
        
        # 保存为CSV文件
        df_temp_table = pd.DataFrame(temp_table_data)
        temp_table_path = self.output_dir / '温度统计表.csv'
        df_temp_table.to_csv(temp_table_path, index=False, encoding='utf-8-sig')
        print(f"✅ 温度统计表格已保存: {temp_table_path}")
        
        return df_temp_table
    
    def create_humidity_statistics_table(self, stats_summary):
        """创建湿度统计表格"""
        if not stats_summary:
            print("⚠️ 没有统计数据可生成表格")
            return None
        
        # 创建湿度统计DataFrame
        humidity_table_data = []
        for station_name, stats in stats_summary.items():
            humidity_table_data.append({
                '测点名称': station_name,
                '湿度平均值(%)': f"{stats['humidity_mean']:.2f}",
                '湿度最大值(%)': f"{stats['humidity_max']:.2f}",
                '湿度最小值(%)': f"{stats['humidity_min']:.2f}",
                '湿度差值(%)': f"{stats['humidity_range']:.2f}",
                '湿度标准差(%)': f"{stats['humidity_std']:.2f}",
                '湿度超限记录频率(%)': f"{stats['over_limit_rate']:.2f}"
            })
        
        # 保存为CSV文件
        df_humidity_table = pd.DataFrame(humidity_table_data)
        humidity_table_path = self.output_dir / '湿度统计表.csv'
        df_humidity_table.to_csv(humidity_table_path, index=False, encoding='utf-8-sig')
        print(f"✅ 湿度统计表格已保存: {humidity_table_path}")
        
        return df_humidity_table
    

    
