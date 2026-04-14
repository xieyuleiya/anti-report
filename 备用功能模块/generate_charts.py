# -*- coding: utf-8 -*-
"""生成温湿度分析图表"""
import sys
import os
from pathlib import Path
from datetime import datetime
import statistics

# 设置matplotlib中文字体
try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib import font_manager
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimSun', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    HAS_MATPLOTLIB = True
except ImportError:
    print("警告: matplotlib未安装，无法生成图表")
    HAS_MATPLOTLIB = False

# 数据文件路径
data_file = Path(r"D:\useful\03-chengxu\report_gen\数据下载\金马大桥\原始数据\温湿度\2025-11-19-22-41-16温湿度测点JM-RHS-TO3-001-01_.txt")
output_dir = Path(r"D:\useful\03-chengxu\report_gen\温湿度\分析结果\金马大桥")
output_dir.mkdir(parents=True, exist_ok=True)

bridge_name = "金马大桥"
station_name = "JM-RHS-TO3-001-01"
humidity_threshold = 50

print("=" * 60)
print(f"{bridge_name}温湿度数据分析 - 图表生成")
print(f"测点: {station_name}")
print("=" * 60)

# 读取数据
print("\n正在读取数据文件...")
times = []
temperatures = []
humidities = []
time_objects = []

try:
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # 分割数据（制表符或空格）
            if '\t' in line:
                parts = line.split('\t')
            else:
                parts = line.split()
                if len(parts) >= 4:
                    parts = [parts[0] + ' ' + parts[1], parts[2], parts[3]]
            
            parts = [p.strip() for p in parts if p.strip()]
            
            if len(parts) >= 3:
                try:
                    time_str = parts[0]
                    temp = float(parts[1])
                    humidity = float(parts[2])
                    
                    times.append(time_str)
                    temperatures.append(temp)
                    humidities.append(humidity)
                    
                    # 转换为datetime对象
                    try:
                        dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
                    except:
                        try:
                            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        except:
                            dt = None
                    time_objects.append(dt)
                except (ValueError, IndexError):
                    continue
except Exception as e:
    print(f"读取数据出错: {e}")
    sys.exit(1)

print(f"成功读取 {len(temperatures)} 条记录")

if not HAS_MATPLOTLIB:
    print("\n无法生成图表，因为matplotlib未安装")
    sys.exit(1)

# 过滤有效的时间对象
valid_indices = [i for i, dt in enumerate(time_objects) if dt is not None]
if not valid_indices:
    print("错误: 无法解析时间数据")
    sys.exit(1)

valid_times = [time_objects[i] for i in valid_indices]
valid_temps = [temperatures[i] for i in valid_indices]
valid_humids = [humidities[i] for i in valid_indices]

print(f"有效时间数据: {len(valid_times)} 条")

# 生成图表
print("\n正在生成图表...")

# 1. 温度时序图
print("生成温度时序图...")
plt.figure(figsize=(15, 6))
plt.plot(valid_times, valid_temps, color='red', linewidth=0.8, alpha=0.7, label=station_name)
plt.title(f'{bridge_name} - 各测点温度时序图（原始数据）', fontsize=16, fontweight='bold')
plt.ylabel('温度 (°C)', fontsize=14)
plt.xlabel('时间', fontsize=14)
plt.grid(True, alpha=0.3)
plt.legend(fontsize=12)
plt.tick_params(axis='both', which='major', labelsize=12)
plt.xticks(rotation=45)
plt.gcf().autofmt_xdate()
plt.tight_layout()
temp_chart_path = output_dir / '各测点温度时序图.png'
plt.savefig(temp_chart_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ 已保存: {temp_chart_path}")

# 2. 湿度时序图
print("生成湿度时序图...")
plt.figure(figsize=(15, 6))
plt.plot(valid_times, valid_humids, color='blue', linewidth=0.8, alpha=0.7, label=station_name)
plt.axhline(y=humidity_threshold, color='red', linestyle='--', 
           alpha=0.7, label=f'湿度超限阈值 ({humidity_threshold}%)')
plt.title(f'{bridge_name} - 各测点湿度时序图（原始数据）', fontsize=16, fontweight='bold')
plt.ylabel('湿度 (%)', fontsize=14)
plt.xlabel('时间', fontsize=14)
plt.grid(True, alpha=0.3)
plt.legend(fontsize=12)
plt.tick_params(axis='both', which='major', labelsize=12)
plt.xticks(rotation=45)
plt.gcf().autofmt_xdate()
plt.tight_layout()
humid_chart_path = output_dir / '各测点湿度时序图.png'
plt.savefig(humid_chart_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ 已保存: {humid_chart_path}")

# 3. 温湿度频数分布图
print("生成温湿度频数分布图...")
fig, axes = plt.subplots(2, 1, figsize=(10, 10))

# 温度分布
axes[0].hist(valid_temps, bins=30, alpha=0.7, color='red', edgecolor='darkred')
mean_temp = statistics.mean(valid_temps)
axes[0].axvline(mean_temp, color='blue', linestyle='--', 
               label=f'平均值: {mean_temp:.2f}°C')
axes[0].set_title(f'{station_name} - 温度分布（原始数据）', fontsize=16, fontweight='bold')
axes[0].set_xlabel('温度 (°C)', fontsize=14)
axes[0].set_ylabel('频数', fontsize=14)
axes[0].grid(True, alpha=0.3)
axes[0].tick_params(axis='both', which='major', labelsize=12)
axes[0].legend(fontsize=12)

# 湿度分布
axes[1].hist(valid_humids, bins=30, alpha=0.7, color='blue', edgecolor='darkblue')
mean_humidity = statistics.mean(valid_humids)
axes[1].axvline(mean_humidity, color='red', linestyle='--', 
               label=f'平均值: {mean_humidity:.2f}%')
axes[1].axvline(humidity_threshold, color='orange', linestyle='--', 
               label=f'超限阈值: {humidity_threshold}%')
axes[1].set_title(f'{station_name} - 湿度分布（原始数据）', fontsize=16, fontweight='bold')
axes[1].set_xlabel('湿度 (%)', fontsize=14)
axes[1].set_ylabel('频数', fontsize=14)
axes[1].grid(True, alpha=0.3)
axes[1].tick_params(axis='both', which='major', labelsize=12)
axes[1].legend(fontsize=12)

plt.tight_layout()
dist_chart_path = output_dir / '各测点温湿度频数分布图.png'
plt.savefig(dist_chart_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ 已保存: {dist_chart_path}")

# 4. 湿度超限柱状图
print("生成湿度超限统计图...")
thresholds = [50, 60, 70, 80, 90, 100]
exceedance_counts = []
exceedance_percentages = []

total_records = len(valid_humids)
for threshold in thresholds:
    if threshold == 100:
        count = sum(1 for h in valid_humids if h == threshold)
    else:
        count = sum(1 for h in valid_humids if h > threshold)
    exceedance_counts.append(count)
    percentage = (count / total_records) * 100
    exceedance_percentages.append(percentage)

plt.figure(figsize=(10, 6))
bars = plt.bar(thresholds, exceedance_percentages, color='skyblue', alpha=0.7, 
             edgecolor='navy', width=8)

# 在柱子上添加数值标签
for bar, count, percentage in zip(bars, exceedance_counts, exceedance_percentages):
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 1,
           f'{count}条\n{percentage:.1f}%', ha='center', va='bottom', 
           fontweight='bold', fontsize=14)

plt.title(f'{station_name} - 湿度超限记录数统计', fontsize=16, fontweight='bold')
plt.xlabel('超限特征 (%)', fontsize=14)
plt.ylabel('百分比 (%)', fontsize=14)
plt.grid(True, alpha=0.3, axis='y')
plt.xticks(thresholds, [f'>{t}%' if t != 100 else f'={t}%' for t in thresholds])
plt.tick_params(axis='both', which='major', labelsize=12)
plt.ylim(0, max(exceedance_percentages) * 1.15)
plt.tight_layout()
exceed_chart_path = output_dir / '湿度超限记录数统计图.png'
plt.savefig(exceed_chart_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ 已保存: {exceed_chart_path}")

print("\n" + "=" * 60)
print("所有图表已生成完成！")
print("=" * 60)
print(f"\n图表保存位置: {output_dir}")
print("\n生成的图表文件:")
print(f"  1. {temp_chart_path.name}")
print(f"  2. {humid_chart_path.name}")
print(f"  3. {dist_chart_path.name}")
print(f"  4. {exceed_chart_path.name}")

