# -*- coding: utf-8 -*-
"""
车流量分析工具 - 整合版
功能：加载车辆荷载数据，计算每日车流量，识别高峰期，支持参数自定义和UI展示
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
from pathlib import Path
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from io import BytesIO
import warnings

warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimSun']
plt.rcParams['axes.unicode_minus'] = False


class VehicleTrafficAnalyzer:
    """车流量分析核心逻辑类"""
    
    def __init__(self, bridge_name=None, data_dir=None):
        """
        初始化分析器
        
        Args:
            bridge_name: 桥梁名称
            data_dir: 数据目录路径
        """
        self.bridge_name = bridge_name
        self.data_dir = data_dir
        self.df1 = None
        self.df2 = None
        self.direction1_name = None
        self.direction2_name = None
        self.daily_stats1 = None
        self.daily_stats2 = None
    
    def load_data(self):
        """加载数据文件"""
        if not self.data_dir or not os.path.exists(self.data_dir):
            raise FileNotFoundError(f"数据目录不存在: {self.data_dir}")
        
        # 自动发现所有txt文件
        data_path = Path(self.data_dir)
        txt_files = list(data_path.glob("*.txt"))
        
        if len(txt_files) < 2:
            raise FileNotFoundError(f"需要至少两个方向的数据文件，但只找到 {len(txt_files)} 个文件")
        
        # 选择前两个文件
        file1_path = txt_files[0]
        file2_path = txt_files[1]
        
        # 从文件名解析方向名
        self.direction1_name = self._parse_direction_from_filename(file1_path.name)
        self.direction2_name = self._parse_direction_from_filename(file2_path.name)
        
        # 读取数据
        self.df1 = pd.read_csv(file1_path, sep='\t', encoding='utf-8')
        self.df2 = pd.read_csv(file2_path, sep='\t', encoding='utf-8')
        
        # 转换时间列
        for df in [self.df1, self.df2]:
            df['DataTime'] = pd.to_datetime(df['DataTime'])
            df['日期'] = df['DataTime'].dt.date
        
        # 计算每日车流量
        self.daily_stats1 = self.df1.groupby('日期').size()
        self.daily_stats2 = self.df2.groupby('日期').size()
        
        return {
            'direction1': self.direction1_name,
            'direction2': self.direction2_name,
            'total_days': len(self.daily_stats1),
            'total_vehicles1': len(self.df1),
            'total_vehicles2': len(self.df2)
        }
    
    def _parse_direction_from_filename(self, filename):
        """从文件名中解析方向名"""
        stem = Path(filename).stem
        parts = stem.split('_')
        
        if len(parts) >= 4:
            return parts[-1]
        elif len(parts) >= 2:
            for part in reversed(parts):
                if '-' in part:
                    return part
            return parts[-1]
        else:
            return stem
    
    def find_peaks(self, daily_stats, algorithm='std', peak_count=2, std_multiplier=1.0, percentile=90):
        """
        识别高峰期
        
        Args:
            daily_stats: 每日车流量数据
            algorithm: 识别算法 ('std', 'percentile', 'fixed')
            peak_count: 高峰数量
            std_multiplier: 标准差倍数
            percentile: 百分位数
        
        Returns:
            高峰期列表 [(日期, 车流量), ...]
        """
        sorted_data = daily_stats.sort_index()
        
        if algorithm == 'std':
            # 标准差法
            mean_traffic = sorted_data.mean()
            std_traffic = sorted_data.std()
            threshold = mean_traffic + std_multiplier * std_traffic
            high_traffic_days = sorted_data[sorted_data > threshold]
            
            if len(high_traffic_days) == 0:
                # 如果没有明显高峰，返回最大值
                sorted_values = sorted_data.sort_values(ascending=False)
                return [(sorted_values.index[i], sorted_values.iloc[i]) 
                       for i in range(min(peak_count, len(sorted_values)))]
            
            # 将高峰日期分组
            peak_groups = self._group_peaks(high_traffic_days)
            
            # 为每个高峰期找到最大值
            peak_maxes = []
            for group in peak_groups:
                group_data = sorted_data[group]
                max_date = group_data.idxmax()
                max_val = group_data.max()
                peak_maxes.append((max_date, max_val))
            
            # 按车流量排序并返回前N个
            peak_maxes.sort(key=lambda x: x[1], reverse=True)
            return peak_maxes[:peak_count]
        
        elif algorithm == 'percentile':
            # 百分位法
            threshold = np.percentile(sorted_data, percentile)
            high_traffic_days = sorted_data[sorted_data >= threshold]
            
            if len(high_traffic_days) == 0:
                sorted_values = sorted_data.sort_values(ascending=False)
                return [(sorted_values.index[i], sorted_values.iloc[i]) 
                       for i in range(min(peak_count, len(sorted_values)))]
            
            peak_groups = self._group_peaks(high_traffic_days)
            peak_maxes = []
            for group in peak_groups:
                group_data = sorted_data[group]
                max_date = group_data.idxmax()
                max_val = group_data.max()
                peak_maxes.append((max_date, max_val))
            
            peak_maxes.sort(key=lambda x: x[1], reverse=True)
            return peak_maxes[:peak_count]
        
        elif algorithm == 'fixed':
            # 固定数量法：直接取前N个最大值
            sorted_values = sorted_data.sort_values(ascending=False)
            return [(sorted_values.index[i], sorted_values.iloc[i]) 
                   for i in range(min(peak_count, len(sorted_values)))]
        
        else:
            raise ValueError(f"未知的算法: {algorithm}")
    
    def _group_peaks(self, high_traffic_days):
        """将高峰日期分组"""
        if len(high_traffic_days) == 0:
            return []
        
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
        
        return peak_groups
    
    def generate_plot(self, params):
        """
        生成车流量统计图表
        
        Args:
            params: 绘图参数字典
        
        Returns:
            matplotlib Figure对象
        """
        if self.daily_stats1 is None or self.daily_stats2 is None:
            raise ValueError("请先加载数据")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 颜色映射
        color_map = {
            '蓝色': '#1f77b4',
            '红色': '#d62728',
            '绿色': '#2ca02c',
            '橙色': '#ff7f0e',
            '紫色': '#9467bd'
        }
        
        marker_map = {
            '圆形': 'o',
            '方形': 's',
            '三角形': '^',
            '菱形': 'D'
        }
        
        # 方向1图表
        color1 = color_map.get(params['direction1_color'], '#1f77b4')
        marker_style = marker_map.get(params['marker_style'], 'o')
        
        ax1.plot(self.daily_stats1.index, self.daily_stats1.values, 
                color=color1, linewidth=params['line_width'], alpha=0.9,
                marker=marker_style, markersize=3, 
                markeredgecolor=color1, markerfacecolor=color1)
        ax1.set_title(f'{self.direction1_name}每日车流量统计', fontsize=16, fontweight='bold')
        ax1.set_xlabel('日期', fontsize=14)
        ax1.set_ylabel('车流量', fontsize=14)
        
        if params['show_grid']:
            ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        ax1.tick_params(axis='x', rotation=45, labelsize=12)
        
        # 标记高峰期
        if params['mark_peaks']:
            peaks1 = self.find_peaks(
                self.daily_stats1,
                algorithm=params['algorithm'],
                peak_count=params['peak_count'],
                std_multiplier=params['std_multiplier'],
                percentile=params['percentile']
            )
            
            peak_color = color_map.get(params['peak_color'], '#d62728')
            peak_size = params['peak_size']
            
            for i, (date, val) in enumerate(peaks1):
                ax1.plot(date, val, 'o', color=peak_color, markersize=peak_size, 
                        markeredgecolor='black', markeredgewidth=1.5)
                
                if params['show_peak_labels']:
                    label_text = f'高峰{i+1}: {val}\n{date}'
                    offset_y = -30 if i % 2 == 0 else 30
                    ax1.annotate(label_text, xy=(date, val), xytext=(10, offset_y),
                              textcoords='offset points',
                              bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                              arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 显示平均值线
        if params['show_mean_line']:
            mean1 = self.daily_stats1.mean()
            ax1.axhline(y=mean1, color='red', linestyle='--', alpha=0.8, 
                       linewidth=2, label=f'平均值: {mean1:.0f}')
            ax1.legend(fontsize=12)
        
        # 方向2图表
        color2 = color_map.get(params['direction2_color'], '#d62728')
        
        ax2.plot(self.daily_stats2.index, self.daily_stats2.values,
                color=color2, linewidth=params['line_width'], alpha=0.9,
                marker=marker_style, markersize=3,
                markeredgecolor=color2, markerfacecolor=color2)
        ax2.set_title(f'{self.direction2_name}每日车流量统计', fontsize=16, fontweight='bold')
        ax2.set_xlabel('日期', fontsize=14)
        ax2.set_ylabel('车流量', fontsize=14)
        
        if params['show_grid']:
            ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        ax2.tick_params(axis='x', rotation=45, labelsize=12)
        
        # 标记高峰期
        if params['mark_peaks']:
            peaks2 = self.find_peaks(
                self.daily_stats2,
                algorithm=params['algorithm'],
                peak_count=params['peak_count'],
                std_multiplier=params['std_multiplier'],
                percentile=params['percentile']
            )
            
            for i, (date, val) in enumerate(peaks2):
                ax2.plot(date, val, 'o', color=peak_color, markersize=peak_size,
                        markeredgecolor='black', markeredgewidth=1.5)
                
                if params['show_peak_labels']:
                    label_text = f'高峰{i+1}: {val}\n{date}'
                    offset_y = -30 if i % 2 == 0 else 30
                    ax2.annotate(label_text, xy=(date, val), xytext=(10, offset_y),
                              textcoords='offset points',
                              bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7),
                              arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 显示平均值线
        if params['show_mean_line']:
            mean2 = self.daily_stats2.mean()
            ax2.axhline(y=mean2, color='blue', linestyle='--', alpha=0.8,
                       linewidth=2, label=f'平均值: {mean2:.0f}')
            ax2.legend(fontsize=12)
        
        plt.tight_layout()
        return fig


class VehicleTrafficUI:
    """车流量分析UI界面类"""
    
    def __init__(self, parent, bridge_name=None, data_dir=None, standalone=True):
        """
        初始化UI
        
        Args:
            parent: 父窗口
            bridge_name: 桥梁名称
            data_dir: 数据目录
            standalone: 是否为独立窗口模式
        """
        self.parent = parent
        self.standalone = standalone
        self.analyzer = VehicleTrafficAnalyzer(bridge_name, data_dir)
        self.fig = None
        self.canvas = None
        
        # 默认参数
        self.params = {
            'mark_peaks': True,
            'peak_count': 2,
            'algorithm': 'std',
            'std_multiplier': 1.0,
            'percentile': 90,
            'peak_color': '红色',
            'peak_size': 8,
            'show_peak_labels': True,
            'show_mean_line': True,
            'direction1_color': '蓝色',
            'direction2_color': '红色',
            'line_width': 2.5,
            'marker_style': '圆形',
            'show_grid': True
        }
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        # 主容器（左右分栏）
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧：参数配置区域
        left_frame = ttk.LabelFrame(main_frame, text="参数配置", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 右侧：图表显示区域
        right_frame = ttk.LabelFrame(main_frame, text="图表显示", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 创建参数配置区域
        self.create_bridge_section(left_frame)
        self.create_peak_params_section(left_frame)
        self.create_chart_style_section(left_frame)
        self.create_action_buttons(left_frame)
        
        # 创建图表显示区域
        self.create_chart_area(right_frame)
    
    def create_bridge_section(self, parent):
        """创建桥梁选择区域"""
        frame = ttk.LabelFrame(parent, text="桥梁选择", padding="5")
        frame.pack(fill=tk.X, pady=5)
        
        # 桥梁名称显示
        ttk.Label(frame, text="桥梁:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.bridge_label = ttk.Label(frame, text=self.analyzer.bridge_name or "未选择")
        self.bridge_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 数据目录显示
        ttk.Label(frame, text="数据目录:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.data_dir_label = ttk.Label(frame, text=self.analyzer.data_dir or "未设置")
        self.data_dir_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=5)
        
        ttk.Button(btn_frame, text="加载数据", command=self.load_data, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="选择目录", command=self.select_data_dir, width=12).pack(side=tk.LEFT, padx=2)
    
    def create_peak_params_section(self, parent):
        """创建高峰标记参数区域"""
        frame = ttk.LabelFrame(parent, text="高峰标记参数", padding="5")
        frame.pack(fill=tk.X, pady=5)
        
        row = 0
        
        # 是否标记高峰期
        self.mark_peaks_var = tk.BooleanVar(value=self.params['mark_peaks'])
        ttk.Checkbutton(frame, text="标记高峰期", variable=self.mark_peaks_var,
                      command=self.on_param_change).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        row += 1
        
        # 高峰数量
        ttk.Label(frame, text="高峰数量:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.peak_count_var = tk.StringVar(value=str(self.params['peak_count']))
        peak_count_cb = ttk.Combobox(frame, textvariable=self.peak_count_var, 
                                   values=['1', '2', '3', '4', '5'], width=10, state='readonly')
        peak_count_cb.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        peak_count_cb.bind('<<ComboboxSelected>>', lambda e: self.on_param_change())
        row += 1
        
        # 识别算法
        ttk.Label(frame, text="识别算法:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.algorithm_var = tk.StringVar(value=self.params['algorithm'])
        algorithm_map = {'std': '标准差法', 'percentile': '百分位法', 'fixed': '固定数量法'}
        algorithm_cb = ttk.Combobox(frame, textvariable=self.algorithm_var,
                                  values=['标准差法', '百分位法', '固定数量法'], width=10, state='readonly')
        algorithm_cb.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        algorithm_cb.bind('<<ComboboxSelected>>', lambda e: self.on_param_change())
        row += 1
        
        # 标准差倍数
        ttk.Label(frame, text="标准差倍数:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.std_multiplier_var = tk.DoubleVar(value=self.params['std_multiplier'])
        std_spin = ttk.Spinbox(frame, from_=0.5, to=3.0, increment=0.1, 
                              textvariable=self.std_multiplier_var, width=10)
        std_spin.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        std_spin.bind('<Return>', lambda e: self.on_param_change())
        std_spin.bind('<FocusOut>', lambda e: self.on_param_change())
        row += 1
        
        # 标记颜色
        ttk.Label(frame, text="标记颜色:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.peak_color_var = tk.StringVar(value=self.params['peak_color'])
        peak_color_cb = ttk.Combobox(frame, textvariable=self.peak_color_var,
                                   values=['红色', '绿色', '橙色', '紫色'], width=10, state='readonly')
        peak_color_cb.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        peak_color_cb.bind('<<ComboboxSelected>>', lambda e: self.on_param_change())
        row += 1
        
        # 标记大小
        ttk.Label(frame, text="标记大小:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.peak_size_var = tk.IntVar(value=self.params['peak_size'])
        size_spin = ttk.Spinbox(frame, from_=4, to=15, textvariable=self.peak_size_var, width=10)
        size_spin.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        size_spin.bind('<Return>', lambda e: self.on_param_change())
        size_spin.bind('<FocusOut>', lambda e: self.on_param_change())
        row += 1
        
        # 显示标注文字
        self.show_peak_labels_var = tk.BooleanVar(value=self.params['show_peak_labels'])
        ttk.Checkbutton(frame, text="显示标注文字", variable=self.show_peak_labels_var,
                      command=self.on_param_change).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    
    def create_chart_style_section(self, parent):
        """创建图表样式参数区域"""
        frame = ttk.LabelFrame(parent, text="图表样式参数", padding="5")
        frame.pack(fill=tk.X, pady=5)
        
        row = 0
        
        # 显示平均值线
        self.show_mean_line_var = tk.BooleanVar(value=self.params['show_mean_line'])
        ttk.Checkbutton(frame, text="显示平均值线", variable=self.show_mean_line_var,
                      command=self.on_param_change).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        row += 1
        
        # 方向1颜色
        ttk.Label(frame, text="方向1颜色:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.direction1_color_var = tk.StringVar(value=self.params['direction1_color'])
        dir1_color_cb = ttk.Combobox(frame, textvariable=self.direction1_color_var,
                                   values=['蓝色', '红色', '绿色', '橙色', '紫色'], width=10, state='readonly')
        dir1_color_cb.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        dir1_color_cb.bind('<<ComboboxSelected>>', lambda e: self.on_param_change())
        row += 1
        
        # 方向2颜色
        ttk.Label(frame, text="方向2颜色:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.direction2_color_var = tk.StringVar(value=self.params['direction2_color'])
        dir2_color_cb = ttk.Combobox(frame, textvariable=self.direction2_color_var,
                                   values=['蓝色', '红色', '绿色', '橙色', '紫色'], width=10, state='readonly')
        dir2_color_cb.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        dir2_color_cb.bind('<<ComboboxSelected>>', lambda e: self.on_param_change())
        row += 1
        
        # 线条宽度
        ttk.Label(frame, text="线条宽度:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.line_width_var = tk.DoubleVar(value=self.params['line_width'])
        width_spin = ttk.Spinbox(frame, from_=1.0, to=5.0, increment=0.5,
                               textvariable=self.line_width_var, width=10)
        width_spin.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        width_spin.bind('<Return>', lambda e: self.on_param_change())
        width_spin.bind('<FocusOut>', lambda e: self.on_param_change())
        row += 1
        
        # 标记点样式
        ttk.Label(frame, text="标记点样式:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.marker_style_var = tk.StringVar(value=self.params['marker_style'])
        marker_cb = ttk.Combobox(frame, textvariable=self.marker_style_var,
                               values=['圆形', '方形', '三角形', '菱形'], width=10, state='readonly')
        marker_cb.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        marker_cb.bind('<<ComboboxSelected>>', lambda e: self.on_param_change())
        row += 1
        
        # 显示网格线
        self.show_grid_var = tk.BooleanVar(value=self.params['show_grid'])
        ttk.Checkbutton(frame, text="显示网格线", variable=self.show_grid_var,
                      command=self.on_param_change).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    
    def create_action_buttons(self, parent):
        """创建操作按钮区域"""
        frame = ttk.LabelFrame(parent, text="操作", padding="5")
        frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(frame, text="生成图表", command=self.generate_chart, width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame, text="复制图片", command=self.copy_plot, width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame, text="导出图片", command=self.export_plot, width=12).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(frame, text="重置参数", command=self.reset_params, width=12).pack(side=tk.LEFT, padx=2, pady=2)
    
    def create_chart_area(self, parent):
        """创建图表显示区域"""
        self.chart_frame = ttk.Frame(parent)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # 初始提示
        self.chart_label = ttk.Label(self.chart_frame, text="请先加载数据", font=("Arial", 14))
        self.chart_label.pack(expand=True)
    
    def select_data_dir(self):
        """选择数据目录"""
        data_dir = filedialog.askdirectory(title="选择车辆荷载数据目录")
        if data_dir:
            self.analyzer.data_dir = data_dir
            self.data_dir_label.config(text=data_dir)
    
    def load_data(self):
        """加载数据"""
        try:
            if not self.analyzer.data_dir:
                messagebox.showwarning("警告", "请先选择数据目录！")
                return
            
            result = self.analyzer.load_data()
            
            # 更新UI显示
            self.bridge_label.config(text=self.analyzer.bridge_name or "未知桥梁")
            
            messagebox.showinfo("成功", 
                f"数据加载成功！\n\n"
                f"方向1: {result['direction1']}\n"
                f"方向2: {result['direction2']}\n"
                f"总天数: {result['total_days']}\n"
                f"方向1总车辆: {result['total_vehicles1']}\n"
                f"方向2总车辆: {result['total_vehicles2']}")
            
            # 自动生成图表
            self.generate_chart()
            
        except Exception as e:
            messagebox.showerror("错误", f"加载数据失败: {e}")
    
    def on_param_change(self):
        """参数变化时的回调"""
        # 更新参数字典
        self.params['mark_peaks'] = self.mark_peaks_var.get()
        self.params['peak_count'] = int(self.peak_count_var.get())
        
        algorithm_map = {'标准差法': 'std', '百分位法': 'percentile', '固定数量法': 'fixed'}
        self.params['algorithm'] = algorithm_map.get(self.algorithm_var.get(), 'std')
        
        self.params['std_multiplier'] = self.std_multiplier_var.get()
        self.params['peak_color'] = self.peak_color_var.get()
        self.params['peak_size'] = self.peak_size_var.get()
        self.params['show_peak_labels'] = self.show_peak_labels_var.get()
        self.params['show_mean_line'] = self.show_mean_line_var.get()
        self.params['direction1_color'] = self.direction1_color_var.get()
        self.params['direction2_color'] = self.direction2_color_var.get()
        self.params['line_width'] = self.line_width_var.get()
        self.params['marker_style'] = self.marker_style_var.get()
        self.params['show_grid'] = self.show_grid_var.get()
        
        # 如果数据已加载，自动重新生成图表
        if self.analyzer.daily_stats1 is not None:
            self.generate_chart()
    
    def generate_chart(self):
        """生成图表"""
        try:
            if self.analyzer.daily_stats1 is None or self.analyzer.daily_stats2 is None:
                messagebox.showwarning("警告", "请先加载数据！")
                return
            
            # 生成图表
            self.fig = self.analyzer.generate_plot(self.params)
            
            # 清除旧的图表
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            
            # 创建新的图表
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            messagebox.showerror("错误", f"生成图表失败: {e}")
    
    def copy_plot(self):
        """复制图片到剪贴板"""
        try:
            if self.fig is None:
                messagebox.showwarning("警告", "请先生成图表！")
                return
            
            # 保存为临时图片
            temp_path = "temp_traffic_plot.png"
            self.fig.savefig(temp_path, dpi=300, bbox_inches='tight')
            
            # 使用PIL读取图片
            from PIL import Image
            img = Image.open(temp_path)
            
            # 转换为BMP格式
            output = BytesIO()
            img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # 去掉BMP文件头
            output.close()
            
            # 复制到剪贴板
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            
            # 删除临时文件
            os.remove(temp_path)
            
            messagebox.showinfo("成功", "图片已复制到剪贴板！")
            
        except ImportError:
            messagebox.showerror("错误", "需要安装pywin32库才能复制到剪贴板\n请运行: pip install pywin32")
        except Exception as e:
            messagebox.showerror("错误", f"复制图片失败: {e}")
    
    def export_plot(self):
        """导出图片"""
        try:
            if self.fig is None:
                messagebox.showwarning("警告", "请先生成图表！")
                return
            
            # 选择保存路径
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG图片", "*.png"), ("所有文件", "*.*")],
                title="保存图片"
            )
            
            if file_path:
                self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("成功", f"图片已保存到:\n{file_path}")
                
        except Exception as e:
            messagebox.showerror("错误", f"导出图片失败: {e}")
    
    def reset_params(self):
        """重置参数为默认值"""
        self.params = {
            'mark_peaks': True,
            'peak_count': 2,
            'algorithm': 'std',
            'std_multiplier': 1.0,
            'percentile': 90,
            'peak_color': '红色',
            'peak_size': 8,
            'show_peak_labels': True,
            'show_mean_line': True,
            'direction1_color': '蓝色',
            'direction2_color': '红色',
            'line_width': 2.5,
            'marker_style': '圆形',
            'show_grid': True
        }
        
        # 更新UI控件
        self.mark_peaks_var.set(self.params['mark_peaks'])
        self.peak_count_var.set(str(self.params['peak_count']))
        self.algorithm_var.set('标准差法')
        self.std_multiplier_var.set(self.params['std_multiplier'])
        self.peak_color_var.set(self.params['peak_color'])
        self.peak_size_var.set(self.params['peak_size'])
        self.show_peak_labels_var.set(self.params['show_peak_labels'])
        self.show_mean_line_var.set(self.params['show_mean_line'])
        self.direction1_color_var.set(self.params['direction1_color'])
        self.direction2_color_var.set(self.params['direction2_color'])
        self.line_width_var.set(self.params['line_width'])
        self.marker_style_var.set(self.params['marker_style'])
        self.show_grid_var.set(self.params['show_grid'])
        
        # 重新生成图表
        if self.analyzer.daily_stats1 is not None:
            self.generate_chart()
        
        messagebox.showinfo("成功", "参数已重置为默认值")


def open_vehicle_traffic_analyzer(parent, bridge_name=None, data_dir=None):
    """
    打开车流量分析工具
    
    Args:
        parent: 父窗口
        bridge_name: 桥梁名称
        data_dir: 数据目录
    """
    # 创建新窗口
    window = tk.Toplevel(parent)
    window.title("车流量分析工具")
    window.geometry("1200x700")
    
    # 创建UI
    ui = VehicleTrafficUI(window, bridge_name, data_dir)
    
    # 居中显示
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')
