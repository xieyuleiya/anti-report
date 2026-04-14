# -*- coding: utf-8 -*-
"""
统一 GUI 界面 - 整合数据下载和数据分析功能
"""

import sys
import os
import threading
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import List, Dict, Tuple, Set
from io import StringIO

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 兼容 Windows 控制台编码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import pandas as pd
from config import (
    BRIDGE_CONFIG_EXCEL_PATH, OTHER_DATA_EXCEL_PATH, OTHER_DATA_SHEET_NAME,
    OUTPUT_ROOT, START_DATE, END_DATE, get_analyzer_data_dir
)
from main_downloader import UnifiedDownloader
from utils.analyzer_utils import DataDiscovery, get_analyzer_info
from main_analyzer import UnifiedAnalyzer
from utils.api_checker import APIConnectivityChecker



class UnifiedGUI:
    """统一GUI界面 - 整合下载和分析功能"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("数据下载与分析系统")
        self.root.geometry("1400x800")
        
        # 初始化组件
        self.downloader = UnifiedDownloader()
        self.analyzer = UnifiedAnalyzer()
        self.api_checker = APIConnectivityChecker()
        
        # 下载相关状态
        self.all_bridges: List[str] = []
        self.bridge_checkboxes: Dict[str, tk.BooleanVar] = {}
        self.selected_bridges: Set[str] = set()  # 记住之前的选择
        self.other_data_categories: List[str] = []  # 其他数据的种类列表
        self.other_category_checkboxes: Dict[str, tk.BooleanVar] = {}
        self.download_thread = None
        self.is_downloading = False
        
        # 分析相关状态
        self.analyze_available_items: List[Tuple[str, str]] = []
        self.analyze_checkboxes: Dict[Tuple[str, str], tk.BooleanVar] = {}
        
        self.setup_ui()
        
        # 延迟加载数据，避免阻塞UI初始化
        # 使用 after 方法在UI显示后再加载数据
        self.root.after(100, self.load_data_async)
    
    def setup_ui(self):
        """设置界面"""
        # 创建标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 下载标签页
        self.download_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.download_frame, text="📥 数据下载")
        self.setup_download_tab()
        
        # 分析标签页
        self.analyze_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analyze_frame, text="📊 数据分析")
        self.setup_analyze_tab()
        
        # 特殊分析标签页
        self.special_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.special_frame, text="🔬 特殊分析")
        self.setup_special_analysis_tab()
    
    def setup_download_tab(self):
        """设置下载标签页"""
        # 主容器（左右分栏）
        main_frame = ttk.Frame(self.download_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧：配置区域
        left_frame = ttk.LabelFrame(main_frame, text="下载配置", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 1. 桥梁选择区域
        bridge_frame = ttk.LabelFrame(left_frame, text="选择桥梁", padding="5")
        bridge_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 搜索框
        search_frame = ttk.Frame(bridge_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(search_frame, text="🔍 搜索:").pack(side=tk.LEFT, padx=5)
        self.bridge_search_var = tk.StringVar()
        self.bridge_search_var.trace('w', self.filter_bridges)
        search_entry = ttk.Entry(search_frame, textvariable=self.bridge_search_var, width=20)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 桥梁列表（可滚动）
        bridge_list_frame = ttk.Frame(bridge_frame)
        bridge_list_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(bridge_list_frame, height=200)
        scrollbar = ttk.Scrollbar(bridge_list_frame, orient="vertical", command=canvas.yview)
        self.bridge_scrollable_frame = ttk.Frame(canvas)
        
        self.bridge_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.bridge_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.download_canvas = canvas # 存储以供后续重新绑定
        self.bridge_list_container = self.bridge_scrollable_frame
        
        # 绑定鼠标滚轮事件
        self._bind_mousewheel(canvas, canvas)
        self._bind_mousewheel(self.bridge_scrollable_frame, canvas)
        
        # 桥梁操作按钮
        bridge_btn_frame = ttk.Frame(bridge_frame)
        bridge_btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(bridge_btn_frame, text="✅ 全选", command=self.select_all_bridges).pack(side=tk.LEFT, padx=2)
        ttk.Button(bridge_btn_frame, text="❌ 取消全选", command=self.deselect_all_bridges).pack(side=tk.LEFT, padx=2)
        ttk.Button(bridge_btn_frame, text="🔄 刷新", command=self.load_bridges).pack(side=tk.LEFT, padx=2)
        
        # 2. 数据类型选择区域
        data_type_frame = ttk.LabelFrame(left_frame, text="数据类型", padding="5")
        data_type_frame.pack(fill=tk.X, pady=5)
        
        # 其他数据（可展开）
        self.other_data_var = tk.BooleanVar()
        self.other_data_frame = ttk.Frame(data_type_frame)
        self.other_data_frame.pack(fill=tk.X, pady=2)
        
        # 其他数据复选框（只控制是否选中，不控制展开）
        self.other_data_checkbox = ttk.Checkbutton(
            self.other_data_frame,
            text="其他数据",
            variable=self.other_data_var
        )
        self.other_data_checkbox.pack(side=tk.LEFT)
        
        # 展开/收起按钮
        self.other_data_expanded = False  # 展开状态
        self.expand_btn = ttk.Button(
            self.other_data_frame,
            text="▼ 展开",
            width=8,
            command=self.toggle_other_data_expand
        )
        self.expand_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # 其他数据种类（可展开的子选项）- 初始不显示
        self.other_categories_frame = ttk.Frame(data_type_frame)
        # 初始不显示，只有点击展开按钮时才显示
        
        # 船撞数据
        self.ship_data_var = tk.BooleanVar()
        self.ship_data_checkbox = ttk.Checkbutton(
            data_type_frame,
            text="船撞数据",
            variable=self.ship_data_var
        )
        self.ship_data_checkbox.pack(anchor=tk.W, pady=2)
        
        # 车辆荷载数据
        self.vehicle_data_var = tk.BooleanVar()
        self.vehicle_data_checkbox = ttk.Checkbutton(
            data_type_frame,
            text="车辆荷载数据",
            variable=self.vehicle_data_var
        )
        self.vehicle_data_checkbox.pack(anchor=tk.W, pady=2)
        
        # 3. 监测值数据类型选择
        monitor_type_frame = ttk.LabelFrame(left_frame, text="监测值数据类型", padding="5")
        monitor_type_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(monitor_type_frame, text="选择数据类型:").pack(side=tk.LEFT, padx=5)
        self.monitor_type_var = tk.StringVar(value="1")  # 默认选择分钟级数据
        
        type_frame = ttk.Frame(monitor_type_frame)
        type_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(type_frame, text="秒级 (0)", variable=self.monitor_type_var, value="0").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="分钟级 (1)", variable=self.monitor_type_var, value="1").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="十分钟级 (2)", variable=self.monitor_type_var, value="2").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="小时级 (3)", variable=self.monitor_type_var, value="3").pack(side=tk.LEFT, padx=10)
        
        # 4. 时间范围设置
        date_frame = ttk.LabelFrame(left_frame, text="时间范围", padding="5")
        date_frame.pack(fill=tk.X, pady=5)
        
        date_inner_frame = ttk.Frame(date_frame)
        date_inner_frame.pack(fill=tk.X)
        
        ttk.Label(date_inner_frame, text="开始日期:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.start_date_var = tk.StringVar(value=START_DATE)
        start_date_entry = ttk.Entry(date_inner_frame, textvariable=self.start_date_var, width=15)
        start_date_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(date_inner_frame, text="(YYYY-MM-DD)").grid(row=0, column=2, sticky=tk.W, padx=5)
        
        ttk.Label(date_inner_frame, text="结束日期:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.end_date_var = tk.StringVar(value=END_DATE)
        end_date_entry = ttk.Entry(date_inner_frame, textvariable=self.end_date_var, width=15)
        end_date_entry.grid(row=1, column=1, padx=5, pady=2)
        ttk.Label(date_inner_frame, text="(YYYY-MM-DD)").grid(row=1, column=2, sticky=tk.W, padx=5)
        
        # 4. 操作按钮
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            button_frame,
            text="🔍 检查API",
            command=self.check_api
        ).pack(side=tk.LEFT, padx=5)
        
        self.download_btn = ttk.Button(
            button_frame,
            text="🚀 开始下载",
            command=self.start_download
        )
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_download_btn = ttk.Button(
            button_frame,
            text="⏹ 停止下载",
            command=self.stop_download,
            state=tk.DISABLED
        )
        self.stop_download_btn.pack(side=tk.LEFT, padx=5)
        
        # 右侧：日志区域
        right_frame = ttk.LabelFrame(main_frame, text="下载日志", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 统计信息
        self.stats_label = ttk.Label(right_frame, text="等待开始...", foreground="gray")
        self.stats_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 日志文本框
        self.download_log_text = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            width=50,
            height=30
        )
        self.download_log_text.pack(fill=tk.BOTH, expand=True)
    
    def setup_analyze_tab(self):
        """设置分析标签页（复用analyzer_gui的代码）"""
        # 顶部按钮区域
        button_frame = ttk.Frame(self.analyze_frame, padding="10")
        button_frame.pack(fill=tk.X)
        
        # 开始分析按钮放在最左边（左上角）
        ttk.Button(
            button_frame,
            text="🚀 开始分析",
            command=self.start_analysis
        ).pack(side=tk.LEFT, padx=5)
        
        # 进度条紧跟在开始分析按钮后面
        self.analyze_progress = ttk.Progressbar(
            button_frame,
            mode='indeterminate',
            length=200
        )
        self.analyze_progress.pack(side=tk.LEFT, padx=5)
        
        # 状态标签
        self.analyze_status_label = ttk.Label(button_frame, text="就绪", foreground="green")
        self.analyze_status_label.pack(side=tk.LEFT, padx=5)
        
        # 分隔符（可选，用于视觉分组）
        separator = ttk.Separator(button_frame, orient='vertical')
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 其他按钮
        ttk.Button(
            button_frame,
            text="🔄 刷新列表",
            command=self.scan_available_data
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="✅ 全选",
            command=self.select_all_analyze
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="❌ 取消全选",
            command=self.deselect_all_analyze
        ).pack(side=tk.LEFT, padx=5)
        
        # 主内容区域（左右分栏）
        main_frame = ttk.Frame(self.analyze_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧：选择列表
        left_frame = ttk.LabelFrame(main_frame, text="可选分析项目", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 创建滚动区域
        canvas = tk.Canvas(left_frame)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        self.analyze_scrollable_frame = ttk.Frame(canvas)
        
        self.analyze_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.analyze_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.analyze_canvas = canvas # 存储以供后续重新绑定
        self.analyze_list_frame = self.analyze_scrollable_frame
        
        # 绑定鼠标滚轮事件
        self._bind_mousewheel(canvas, canvas)
        self._bind_mousewheel(self.analyze_scrollable_frame, canvas)
        
        # 右侧：日志输出
        right_frame = ttk.LabelFrame(main_frame, text="分析日志", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.analyze_log_text = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            width=40,
            height=25
        )
        self.analyze_log_text.pack(fill=tk.BOTH, expand=True)

    def _on_mousewheel(self, event, canvas):
        """处理鼠标滚轮事件"""
        if sys.platform == "win32":
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif sys.platform == "darwin":
            canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

    def _bind_mousewheel(self, widget, canvas):
        """递归地为组件及其所有子组件绑定鼠标滚轮事件"""
        if sys.platform == "linux":
            widget.bind("<Button-4>", lambda e: self._on_mousewheel(e, canvas), add="+")
            widget.bind("<Button-5>", lambda e: self._on_mousewheel(e, canvas), add="+")
        else:
            widget.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, canvas), add="+")
        
        for child in widget.winfo_children():
            self._bind_mousewheel(child, canvas)
    
    # ========== 下载相关方法 ==========
    
    def load_data_async(self):
        """异步加载数据（在后台线程中执行）"""
        # 在后台线程中加载桥梁列表
        thread1 = threading.Thread(target=self.load_bridges_thread, daemon=True)
        thread1.start()
        
        # 在后台线程中扫描可用数据
        thread2 = threading.Thread(target=self.scan_available_data_thread, daemon=True)
        thread2.start()
    
    def load_bridges_thread(self):
        """在后台线程中加载桥梁列表"""
        try:
            bridges_set = set()
            
            # 从车辆荷载工作表读取
            try:
                df_vehicle = pd.read_excel(BRIDGE_CONFIG_EXCEL_PATH, sheet_name="车辆荷载")
                if '桥梁名称' in df_vehicle.columns:
                    bridges_set.update(df_vehicle['桥梁名称'].dropna().unique())
            except Exception as e:
                self.root.after(0, lambda: self.download_log(f"⚠️ 读取车辆荷载桥梁列表失败: {e}"))
            
            # 从船撞工作表读取
            try:
                df_ship = pd.read_excel(BRIDGE_CONFIG_EXCEL_PATH, sheet_name="船撞")
                if '桥梁名称' in df_ship.columns:
                    bridges_set.update(df_ship['桥梁名称'].dropna().unique())
            except Exception as e:
                self.root.after(0, lambda: self.download_log(f"⚠️ 读取船撞桥梁列表失败: {e}"))
            
            # 从其他数据工作表读取
            try:
                df_other = pd.read_excel(OTHER_DATA_EXCEL_PATH, sheet_name=OTHER_DATA_SHEET_NAME)
                if '桥名' in df_other.columns:
                    bridges_set.update(df_other['桥名'].dropna().unique())
            except Exception as e:
                self.root.after(0, lambda: self.download_log(f"⚠️ 读取其他数据桥梁列表失败: {e}"))
            
            self.all_bridges = sorted(list(bridges_set))
            
            # 加载其他数据的种类
            self.load_other_data_categories_thread()
            
            # 更新UI（必须在主线程中执行）
            self.root.after(0, self.update_bridge_list)
            self.root.after(0, lambda: self.download_log(f"✅ 加载完成，找到 {len(self.all_bridges)} 座桥梁"))
            
        except Exception as e:
            self.root.after(0, lambda: self.download_log(f"❌ 加载桥梁列表失败: {e}"))
            import traceback
            self.root.after(0, lambda: self.download_log(traceback.format_exc()))
    
    def load_bridges(self):
        """从Excel加载桥梁列表（同步版本，保留用于兼容）"""
        self.download_log("🔍 正在加载桥梁列表...")
        self.load_bridges_thread()
    
    def load_other_data_categories_thread(self):
        """在后台线程中加载其他数据的种类列表"""
        try:
            df = pd.read_excel(OTHER_DATA_EXCEL_PATH, sheet_name=OTHER_DATA_SHEET_NAME)
            if len(df.columns) > 4:
                categories = df.iloc[:, 4].dropna().unique().tolist()
                self.other_data_categories = [str(c) for c in categories if str(c).strip()]
        except Exception as e:
            self.other_data_categories = ["温度", "温湿度"]  # 默认值
    
    def load_other_data_categories(self):
        """加载其他数据的种类列表（同步版本，保留用于兼容）"""
        try:
            df = pd.read_excel(OTHER_DATA_EXCEL_PATH, sheet_name=OTHER_DATA_SHEET_NAME)
            if len(df.columns) > 4:
                categories = df.iloc[:, 4].dropna().unique().tolist()
                self.other_data_categories = [str(c) for c in categories if str(c).strip()]
        except Exception as e:
            self.download_log(f"⚠️ 加载其他数据种类失败: {e}")
            self.other_data_categories = ["温度", "温湿度"]  # 默认值
    
    def update_bridge_list(self):
        """更新桥梁列表显示（选中的置顶）"""
        # 清空现有列表
        for widget in self.bridge_list_container.winfo_children():
            widget.destroy()
        self.bridge_checkboxes.clear()
        
        # 获取搜索关键词
        search_key = self.bridge_search_var.get().lower()
        
        # 分离选中的和未选中的桥梁
        selected_bridges = []
        unselected_bridges = []
        
        for bridge in self.all_bridges:
            if search_key and search_key not in bridge.lower():
                continue
            
            if bridge in self.selected_bridges:
                selected_bridges.append(bridge)
            else:
                unselected_bridges.append(bridge)
        
        # 先显示选中的桥梁（置顶）
        for bridge in sorted(selected_bridges):
            var = tk.BooleanVar(value=True)
            self.bridge_checkboxes[bridge] = var
            
            checkbox = ttk.Checkbutton(
                self.bridge_list_container,
                text=bridge,
                variable=var,
                command=lambda b=bridge: self.update_selected_bridges(b)
            )
            checkbox.pack(anchor=tk.W, padx=5, pady=2)
        
        # 如果有选中的桥梁，添加分隔线
        if selected_bridges and unselected_bridges:
            separator = ttk.Separator(self.bridge_list_container, orient='horizontal')
            separator.pack(fill=tk.X, padx=5, pady=5)
        
        # 再显示未选中的桥梁
        for bridge in sorted(unselected_bridges):
            var = tk.BooleanVar(value=False)
            self.bridge_checkboxes[bridge] = var
            
            checkbox = ttk.Checkbutton(
                self.bridge_list_container,
                text=bridge,
                variable=var,
                command=lambda b=bridge: self.update_selected_bridges(b)
            )
            checkbox.pack(anchor=tk.W, padx=5, pady=2)
    
    def filter_bridges(self, *args):
        """过滤桥梁列表"""
        self.update_bridge_list()
    
    def update_selected_bridges(self, bridge: str):
        """更新选中的桥梁集合，并刷新列表（选中的置顶）"""
        if self.bridge_checkboxes[bridge].get():
            self.selected_bridges.add(bridge)
        else:
            self.selected_bridges.discard(bridge)
        # 刷新列表，让选中的置顶
        self.update_bridge_list()
        # 重新绑定鼠标滚轮到新生成的子组件
        if hasattr(self, 'download_canvas'):
            self._bind_mousewheel(self.bridge_list_container, self.download_canvas)
    
    def select_all_bridges(self):
        """全选桥梁"""
        # 先更新选中集合
        for bridge in self.bridge_checkboxes.keys():
            self.selected_bridges.add(bridge)
        # 然后刷新列表（选中的会置顶）
        self.update_bridge_list()
        # 设置所有复选框为选中状态
        for var in self.bridge_checkboxes.values():
            var.set(True)
        self.download_log("✅ 已全选所有桥梁")
    
    def deselect_all_bridges(self):
        """取消全选桥梁"""
        self.selected_bridges.clear()
        # 刷新列表
        self.update_bridge_list()
        self.download_log("❌ 已取消全选桥梁")
    
    def toggle_other_data_expand(self):
        """切换其他数据种类的展开/收起状态"""
        if self.other_data_expanded:
            # 收起
            if self.other_categories_frame.winfo_ismapped():
                self.other_categories_frame.pack_forget()
            self.other_data_expanded = False
            self.expand_btn.config(text="▼ 展开")
        else:
            # 展开
            # 先检查是否已经pack，如果没有则pack，使用after参数让它紧跟在other_data_frame之后
            if not self.other_categories_frame.winfo_ismapped():
                self.other_categories_frame.pack(fill=tk.X, padx=(20, 0), pady=2, after=self.other_data_frame)
            
            # 如果已经有内容，就不重复创建
            if not self.other_categories_frame.winfo_children():
                # 显示种类选项
                for category in self.other_data_categories:
                    var = tk.BooleanVar()
                    self.other_category_checkboxes[category] = var
                    ttk.Checkbutton(
                        self.other_categories_frame,
                        text=f"  {category}",
                        variable=var
                    ).pack(anchor=tk.W, padx=(10, 0))
                
                # 添加全选/取消全选按钮
                btn_frame = ttk.Frame(self.other_categories_frame)
                btn_frame.pack(fill=tk.X, padx=(10, 0), pady=(5, 0))
                ttk.Button(btn_frame, text="全选", command=self.select_all_other_categories, width=8).pack(side=tk.LEFT, padx=2)
                ttk.Button(btn_frame, text="取消全选", command=self.deselect_all_other_categories, width=8).pack(side=tk.LEFT, padx=2)
            
            self.other_data_expanded = True
            self.expand_btn.config(text="▲ 收起")
    
    def select_all_other_categories(self):
        """全选其他数据种类"""
        for var in self.other_category_checkboxes.values():
            var.set(True)
    
    def deselect_all_other_categories(self):
        """取消全选其他数据种类"""
        for var in self.other_category_checkboxes.values():
            var.set(False)
    
    def check_api(self):
        """检查API连通性"""
        data_types = []
        if self.other_data_var.get():
            data_types.append('other')
        if self.ship_data_var.get():
            data_types.append('ship')
        if self.vehicle_data_var.get():
            data_types.append('vehicle')
        
        if not data_types:
            messagebox.showwarning("警告", "请至少选择一种数据类型！")
            return
        
        self.download_log("\n" + "="*60)
        self.download_log("🔍 开始检查API连通性...")
        self.download_log("="*60 + "\n")
        
        # 在新线程中执行API检查
        thread = threading.Thread(target=self.run_api_check, args=(data_types,))
        thread.daemon = True
        thread.start()
    
    def run_api_check(self, data_types: List[str]):
        """执行API检查（在后台线程中）"""
        try:
            api_results = self.downloader._check_api_connectivity(data_types)
            summary = self.downloader.api_checker.get_summary(api_results)
            self.download_log(summary)
            
            if self.downloader.api_checker.is_all_apis_connected(api_results):
                self.download_log("\n✅ 所有API接口连通正常！")
            else:
                self.download_log("\n⚠️ 部分API接口连通异常，请检查网络或联系管理员。")
        except Exception as e:
            self.download_log(f"\n❌ API检查失败: {e}")
            import traceback
            self.download_log(traceback.format_exc())
    
    def start_download(self):
        """开始下载"""
        # 获取选中的桥梁
        selected_bridges = [b for b, var in self.bridge_checkboxes.items() if var.get()]
        if not selected_bridges:
            messagebox.showwarning("警告", "请至少选择一座桥梁！")
            return
        
        # 获取选中的数据类型
        data_types = []
        if self.other_data_var.get():
            data_types.append('other')
        if self.ship_data_var.get():
            data_types.append('ship')
        if self.vehicle_data_var.get():
            data_types.append('vehicle')
        
        if not data_types:
            messagebox.showwarning("警告", "请至少选择一种数据类型！")
            return
        
        # 验证日期格式
        try:
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d")
            end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d")
            if start_date > end_date:
                messagebox.showerror("错误", "开始日期不能晚于结束日期！")
                return
        except ValueError:
            messagebox.showerror("错误", "日期格式错误！请使用 YYYY-MM-DD 格式")
            return
        
        # 确认对话框
        confirm_msg = f"将下载以下数据：\n\n"
        confirm_msg += f"桥梁 ({len(selected_bridges)} 座): {', '.join(selected_bridges[:3])}"
        if len(selected_bridges) > 3:
            confirm_msg += f" 等{len(selected_bridges)}座"
        confirm_msg += f"\n数据类型: {', '.join(data_types)}\n"
        confirm_msg += f"时间范围: {self.start_date_var.get()} 到 {self.end_date_var.get()}\n\n"
        confirm_msg += f"确认开始下载？"
        
        if not messagebox.askyesno("确认", confirm_msg):
            return
        
        # 保存选择
        self.selected_bridges = set(selected_bridges)
        
        # 在新线程中执行下载
        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.stop_download_btn.config(state=tk.NORMAL)
        
        thread = threading.Thread(target=self.run_download, args=(selected_bridges, data_types))
        thread.daemon = True
        thread.start()
        self.download_thread = thread
    
    def run_download(self, bridge_names: List[str], data_types: List[str]):
        """执行下载（在后台线程中）"""
        # 重定向标准输出到日志
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        class LogRedirect:
            def __init__(self, log_func):
                self.log_func = log_func
                self.buffer = StringIO()
            
            def write(self, text):
                if text.strip():
                    self.log_func(text.rstrip())
                self.buffer.write(text)
            
            def flush(self):
                pass
        
        log_redirect = LogRedirect(self.download_log)
        sys.stdout = log_redirect
        sys.stderr = log_redirect
        
        # 统计信息
        stats = {
            'total_bridges': len(bridge_names),
            'success_bridges': 0,
            'failed_bridges': 0,
            'cancelled_bridges': 0,
            'start_time': datetime.now()
        }
        
        try:
            # 获取用户选择的数据类型
            data_type = int(self.monitor_type_var.get())
            
            # 重新初始化下载器，使用用户选择的数据类型
            self.downloader = UnifiedDownloader(data_type=data_type)
            
            self.download_log("\n" + "="*60)
            self.download_log("🚀 开始下载数据")
            self.download_log("="*60 + "\n")
            self.download_log(f"桥梁: {', '.join(bridge_names)}")
            self.download_log(f"数据类型: {', '.join(data_types)}")
            self.download_log(f"监测值数据类型: {'秒级' if data_type == 0 else '分钟级' if data_type == 1 else '十分钟级' if data_type == 2 else '小时级'} ({data_type})")
            self.download_log(f"时间范围: {self.start_date_var.get()} 到 {self.end_date_var.get()}\n")
            
            # 临时修改下载器的时间范围
            self.downloader.other_downloader.start_date = self.start_date_var.get()
            self.downloader.other_downloader.end_date = self.end_date_var.get()
            self.downloader.ship_downloader.start_date = self.start_date_var.get()
            self.downloader.ship_downloader.end_date = self.end_date_var.get()
            self.downloader.vehicle_downloader.start_date = self.start_date_var.get()
            self.downloader.vehicle_downloader.end_date = self.end_date_var.get()
            
            # 处理其他数据的种类选择
            if 'other' in data_types:
                selected_categories = [cat for cat, var in self.other_category_checkboxes.items() if var.get()]
                if selected_categories:
                    self.downloader.other_downloader.target_categories = selected_categories
                else:
                    # 如果没有选择具体种类，使用全部
                    self.downloader.other_downloader.target_categories = None
            
            # 逐个桥梁下载，以便可以随时停止
            for i, bridge_name in enumerate(bridge_names, 1):
                # 检查是否被停止
                if not self.is_downloading:
                    self.download_log(f"\n⚠️ 下载已停止，剩余 {len(bridge_names) - i + 1} 座桥梁未下载")
                    stats['cancelled_bridges'] = len(bridge_names) - i + 1
                    break
                
                self.download_log(f"\n{'='*60}")
                self.download_log(f"🔧 开始处理桥梁: {bridge_name} ({i}/{len(bridge_names)})")
                self.download_log(f"{'='*60}")
                
                bridge_success = 0
                bridge_total = 0
                
                # 下载其他数据（温湿度等）
                if 'other' in data_types and self.is_downloading:
                    bridge_total += 1
                    self.download_log(f"\n📊 下载其他数据...")
                    try:
                        if self.downloader.other_downloader.download_bridge_data(bridge_name):
                            bridge_success += 1
                            self.download_log(f"✅ {bridge_name} 其他数据下载成功")
                        else:
                            self.download_log(f"❌ {bridge_name} 其他数据下载失败")
                    except Exception as e:
                        self.download_log(f"❌ {bridge_name} 其他数据下载出错: {e}")
                
                # 下载船撞数据
                if 'ship' in data_types and self.is_downloading:
                    bridge_total += 1
                    self.download_log(f"\n🚢 下载船撞数据...")
                    try:
                        if self.downloader.ship_downloader.download_bridge_data(bridge_name):
                            bridge_success += 1
                            self.download_log(f"✅ {bridge_name} 船撞数据下载成功")
                        else:
                            self.download_log(f"❌ {bridge_name} 船撞数据下载失败")
                    except Exception as e:
                        self.download_log(f"❌ {bridge_name} 船撞数据下载出错: {e}")
                
                # 下载车辆荷载数据
                if 'vehicle' in data_types and self.is_downloading:
                    bridge_total += 1
                    self.download_log(f"\n🚗 下载车辆荷载数据...")
                    try:
                        if self.downloader.vehicle_downloader.download_bridge_data(bridge_name):
                            bridge_success += 1
                            self.download_log(f"✅ {bridge_name} 车辆荷载数据下载成功")
                        else:
                            self.download_log(f"❌ {bridge_name} 车辆荷载数据下载失败")
                    except Exception as e:
                        self.download_log(f"❌ {bridge_name} 车辆荷载数据下载出错: {e}")
                
                if bridge_success > 0:
                    stats['success_bridges'] += 1
                elif bridge_total > 0:
                    stats['failed_bridges'] += 1
                
                self.download_log(f"\n📊 {bridge_name} 完成情况: {bridge_success}/{bridge_total}")
            
            # 恢复原始时间范围
            self.downloader.other_downloader.start_date = original_start
            self.downloader.other_downloader.end_date = original_end
            self.downloader.ship_downloader.start_date = original_start
            self.downloader.ship_downloader.end_date = original_end
            self.downloader.vehicle_downloader.start_date = original_start
            self.downloader.vehicle_downloader.end_date = original_end
            
        except Exception as e:
            self.download_log(f"\n❌ 下载过程中出错: {e}")
            import traceback
            self.download_log(traceback.format_exc())
            if not self.is_downloading:
                # 如果是用户停止导致的异常，不计入失败
                pass
            else:
                stats['failed_bridges'] += len(bridge_names) - stats['success_bridges'] - stats['cancelled_bridges']
        
        finally:
            # 恢复标准输出
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
            # 更新统计信息
            elapsed = (datetime.now() - stats['start_time']).total_seconds()
            stats_text = f"✅ 成功: {stats['success_bridges']}/{stats['total_bridges']} | "
            if stats['cancelled_bridges'] > 0:
                stats_text += f"⏹ 已停止: {stats['cancelled_bridges']} | "
            stats_text += f"❌ 失败: {stats['failed_bridges']}/{stats['total_bridges']} | "
            stats_text += f"⏱️ 耗时: {elapsed:.1f}秒"
            
            if stats['cancelled_bridges'] > 0:
                self.stats_label.config(text=stats_text, foreground="orange")
            elif stats['success_bridges'] == stats['total_bridges']:
                self.stats_label.config(text=stats_text, foreground="green")
            else:
                self.stats_label.config(text=stats_text, foreground="orange")
            
            self.is_downloading = False
            self.download_btn.config(state=tk.NORMAL)
            self.stop_download_btn.config(state=tk.DISABLED)
            
            self.download_log("\n" + "="*60)
            if stats['cancelled_bridges'] > 0:
                self.download_log("⏹ 下载已停止")
            else:
                self.download_log("📊 下载完成")
            self.download_log("="*60 + "\n")
            
            # 显示完成消息
            if stats['cancelled_bridges'] > 0:
                messagebox.showinfo("已停止", 
                    f"下载已停止！\n"
                    f"成功: {stats['success_bridges']}/{stats['total_bridges']}\n"
                    f"已停止: {stats['cancelled_bridges']} 座桥梁")
            else:
                messagebox.showinfo("完成", f"下载完成！\n成功: {stats['success_bridges']}/{stats['total_bridges']}")
    
    def stop_download(self):
        """停止下载"""
        if not self.is_downloading:
            return
        
        # 确认停止
        if not messagebox.askyesno("确认停止", "确定要停止当前下载任务吗？\n\n已完成的桥梁数据将保留，未完成的将停止。", icon='warning'):
            return
        
        self.is_downloading = False
        self.download_log("\n" + "="*60)
        self.download_log("⏹ 用户请求停止下载...")
        self.download_log("="*60)
        self.download_log("正在等待当前任务完成...")
        
        # 更新按钮状态
        self.stop_download_btn.config(state=tk.DISABLED, text="⏹ 停止中...")
        self.root.update_idletasks()
    
    def download_log(self, message: str):
        """添加下载日志"""
        self.download_log_text.insert(tk.END, message + "\n")
        self.download_log_text.see(tk.END)
        self.root.update_idletasks()
    
    # ========== 分析相关方法 ==========
    
    def scan_available_data_thread(self):
        """在后台线程中扫描可用的数据"""
        # 更新UI状态（必须在主线程中执行）
        self.root.after(0, lambda: self.analyze_log("🔍 正在扫描可用的数据..."))
        self.root.after(0, lambda: self.analyze_status_label.config(text="扫描中...", foreground="blue"))
        
        try:
            # 获取所有可用的桥梁和数据类型（耗时操作）
            summary = DataDiscovery.get_analysis_summary()
            
            # 更新UI（必须在主线程中执行）
            self.root.after(0, self.update_analyze_list, summary)
            
        except Exception as e:
            self.root.after(0, lambda: self.analyze_log(f"❌ 扫描失败: {e}"))
            self.root.after(0, lambda: self.analyze_status_label.config(text="扫描失败", foreground="red"))
            import traceback
            self.root.after(0, lambda: self.analyze_log(traceback.format_exc()))
    
    def update_analyze_list(self, summary):
        """更新分析列表（在主线程中执行）"""
        # 清空现有列表
        for widget in self.analyze_list_frame.winfo_children():
            widget.destroy()
        self.analyze_checkboxes.clear()
        self.analyze_available_items.clear()
        
        if not summary:
            self.analyze_log("⚠️ 未找到任何可用的数据")
            self.analyze_status_label.config(text="未找到数据", foreground="orange")
            return
        
        # 按桥梁分组显示
        for bridge_name, data_types in sorted(summary.items()):
            # 桥梁标题行（包含标签和打开文件夹按钮）
            bridge_row_frame = ttk.Frame(self.analyze_list_frame)
            bridge_row_frame.pack(anchor=tk.W, pady=(10, 5), fill=tk.X)

            # 桥梁名称标签
            bridge_label = ttk.Label(
                bridge_row_frame,
                text=f"🌉 {bridge_name}",
                font=("Arial", 10, "bold")
            )
            bridge_label.pack(side=tk.LEFT)

            # 打开文件夹按钮（仅图标）
            open_btn = ttk.Button(
                bridge_row_frame,
                text="📂",
                width=3,
                command=lambda bn=bridge_name: self.open_bridge_folder(bn)
            )
            open_btn.pack(side=tk.LEFT, padx=(10, 0))
            
            # 数据类型复选框
            for data_type in sorted(data_types):
                # 检查是否有对应的分析器
                analyzer_info = get_analyzer_info(data_type)
                if not analyzer_info:
                    continue
                
                item_key = (bridge_name, data_type)
                self.analyze_available_items.append(item_key)
                
                var = tk.BooleanVar()
                self.analyze_checkboxes[item_key] = var
                
                checkbox = ttk.Checkbutton(
                    self.analyze_list_frame,
                    text=f"  {data_type} - {analyzer_info['description']}",
                    variable=var
                )
                checkbox.pack(anchor=tk.W, padx=(20, 0))
        
        count = len(self.analyze_available_items)
        self.analyze_log(f"✅ 扫描完成，找到 {count} 个可分析项目")
        self.analyze_status_label.config(text=f"找到 {count} 个项目", foreground="green")
        
        # 重新绑定鼠标滚轮到新生成的子组件
        if hasattr(self, 'analyze_canvas'):
            self._bind_mousewheel(self.analyze_list_frame, self.analyze_canvas)
    
    def scan_available_data(self):
        """扫描可用的数据（同步版本，保留用于兼容）"""
        self.analyze_log("🔍 正在扫描可用的数据...")
        self.analyze_status_label.config(text="扫描中...", foreground="blue")
        self.root.update_idletasks()
        self.scan_available_data_thread()

    def open_bridge_folder(self, bridge_name: str):
        """打开桥梁的数据文件夹"""
        try:
            # 获取桥梁的主数据目录（使用第一个可用的数据类型）
            summary = DataDiscovery.get_analysis_summary()
            if bridge_name not in summary or not summary[bridge_name]:
                messagebox.showwarning("警告", f"未找到 {bridge_name} 的数据目录")
                return

            # 使用第一个数据类型的目录作为桥梁的主目录
            first_data_type = summary[bridge_name][0]
            data_dir = get_analyzer_data_dir(bridge_name, first_data_type)
            folder_path = Path(data_dir).parent.parent  # 获取父目录的父目录（桥梁目录）

            if not folder_path.exists():
                messagebox.showwarning("警告", f"文件夹不存在: {folder_path}")
                return

            # 使用 explorer 打开文件夹（使用 Popen 不等待返回）
            subprocess.Popen(["explorer", str(folder_path)])
            self.analyze_log(f"📂 已打开文件夹: {folder_path}")

        except Exception as e:
            self.analyze_log(f"❌ 打开文件夹失败: {e}")
            messagebox.showerror("错误", f"打开文件夹失败: {e}")

    def select_all_analyze(self):
        """全选分析项目"""
        for var in self.analyze_checkboxes.values():
            var.set(True)
        self.analyze_log("✅ 已全选所有项目")
    
    def deselect_all_analyze(self):
        """取消全选分析项目"""
        for var in self.analyze_checkboxes.values():
            var.set(False)
        self.analyze_log("❌ 已取消全选")
    
    def start_analysis(self):
        """开始分析"""
        selected = self.get_selected_analyze_items()
        
        if not selected:
            messagebox.showwarning("警告", "请至少选择一个分析项目！")
            return
        
        # 确认对话框
        bridge_names = sorted(set(bridge for bridge, _ in selected))
        data_types = sorted(set(data_type for _, data_type in selected))
        
        confirm_msg = f"将分析以下项目：\n\n"
        confirm_msg += f"桥梁 ({len(bridge_names)} 座): {', '.join(bridge_names)}\n"
        confirm_msg += f"数据类型 ({len(data_types)} 种): {', '.join(data_types)}\n\n"
        confirm_msg += f"共 {len(selected)} 个分析任务\n\n确认执行？"
        
        if not messagebox.askyesno("确认", confirm_msg):
            return
        
        # 在新线程中执行分析，避免界面卡顿
        thread = threading.Thread(target=self.run_analysis, args=(selected,))
        thread.daemon = True
        thread.start()
    
    def get_selected_analyze_items(self) -> List[Tuple[str, str]]:
        """获取选中的分析项目"""
        selected = []
        for item_key, var in self.analyze_checkboxes.items():
            if var.get():
                selected.append(item_key)
        return selected
    
    def run_analysis(self, selected: List[Tuple[str, str]]):
        """执行分析（在后台线程中运行）"""
        self.analyze_progress.start()
        self.analyze_status_label.config(text="分析中...", foreground="blue")
        self.analyze_log("\n" + "="*60)
        self.analyze_log("🚀 开始执行分析任务")
        self.analyze_log("="*60 + "\n")
        
        # 按桥梁分组
        bridge_tasks: Dict[str, List[str]] = {}
        for bridge_name, data_type in selected:
            if bridge_name not in bridge_tasks:
                bridge_tasks[bridge_name] = []
            bridge_tasks[bridge_name].append(data_type)
        
        success_count = 0
        total_count = len(selected)
        
        # 重定向标准输出到日志
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        class LogRedirect:
            def __init__(self, log_func):
                self.log_func = log_func
                self.buffer = StringIO()
            
            def write(self, text):
                if text.strip():
                    self.log_func(text.rstrip())
                self.buffer.write(text)
            
            def flush(self):
                pass
        
        log_redirect = LogRedirect(self.analyze_log)
        sys.stdout = log_redirect
        sys.stderr = log_redirect
        
        try:
            for bridge_name, data_types in sorted(bridge_tasks.items()):
                self.analyze_log(f"\n{'─'*60}")
                self.analyze_log(f"🌉 分析桥梁: {bridge_name}")
                self.analyze_log(f"📊 数据类型: {', '.join(data_types)}")
                self.analyze_log(f"{'─'*60}\n")
                
                # 执行分析
                try:
                    success = self.analyzer.analyze_bridge(bridge_name, data_types)
                    if success:
                        success_count += len(data_types)
                        self.analyze_log(f"✅ {bridge_name} 分析完成\n")
                    else:
                        self.analyze_log(f"⚠️ {bridge_name} 部分分析失败\n")
                except Exception as e:
                    self.analyze_log(f"❌ {bridge_name} 分析出错: {e}\n")
                    import traceback
                    self.analyze_log(traceback.format_exc() + "\n")
            
            # 完成
            self.analyze_log("\n" + "="*60)
            self.analyze_log(f"📊 分析完成: {success_count}/{total_count} 成功")
            self.analyze_log("="*60 + "\n")
            
            self.analyze_status_label.config(
                text=f"完成: {success_count}/{total_count} 成功",
                foreground="green" if success_count == total_count else "orange"
            )
            
        except Exception as e:
            self.analyze_log(f"❌ 执行过程中出错: {e}\n")
            import traceback
            self.analyze_log(traceback.format_exc() + "\n")
            self.analyze_status_label.config(text="执行失败", foreground="red")
        
        finally:
            # 恢复标准输出
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.analyze_progress.stop()
            messagebox.showinfo("完成", f"分析完成！\n成功: {success_count}/{total_count}")
    
    def analyze_log(self, message: str):
        """添加分析日志"""
        self.analyze_log_text.insert(tk.END, message + "\n")
        self.analyze_log_text.see(tk.END)
        self.root.update_idletasks()
    
    def setup_special_analysis_tab(self):
        """设置特殊分析标签页"""
        # 主容器（上下分栏：按钮区域 + 内容区域）
        main_frame = ttk.Frame(self.special_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题和按钮区域（上方）
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 标题（更小更紧凑）
        title_label = ttk.Label(
            top_frame, 
            text="特殊分析功能", 
            font=("Arial", 12, "bold")
        )
        title_label.pack(pady=(0, 5))
        
        # 功能按钮区域（使用网格布局，每行3个按钮，更紧凑）
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(fill=tk.X)
        
        # 特殊分析功能列表
        self.special_functions = [
            {
                "name": "交互式绘图器",
                "description": "周聚合数据交互式绘图，支持多测点对比",
                "icon": "📊",
                "handler": self.open_interactive_plotter
            },
            {
                "name": "频谱分析",
                "description": "预留功能，待开发",
                "icon": "🔧",
                "handler": self.placeholder_function
            },
            {
                "name": "1550倾角仪数据分析",
                "description": "1550倾角仪数据下载、趋势分析和报告生成",
                "icon": "📐",
                "handler": self.open_1550_analyzer
            },
            {
                "name": "车流量分析",
                "description": "车辆荷载每日车流量统计和高峰期分析",
                "icon": "�",
                "handler": self.open_vehicle_traffic_analyzer
            },
            {
                "name": "功能5",
                "description": "预留功能，待开发",
                "icon": "🔧",
                "handler": self.placeholder_function
            },
            {
                "name": "功能6",
                "description": "预留功能，待开发",
                "icon": "🔧",
                "handler": self.placeholder_function
            },
        ]
        
        # 当前显示的功能UI容器
        self.special_content_frame = None
        self.current_special_function = None
        
        # 创建功能按钮（更紧凑的布局）
        row = 0
        col = 0
        max_cols = 6  # 改为一行6个按钮，更紧凑
        
        for func_info in self.special_functions:
            # 功能按钮（直接放在网格中，不创建额外容器）
            btn = ttk.Button(
                button_frame,
                text=f"{func_info['icon']} {func_info['name']}",
                command=lambda f=func_info: self.show_special_function(f),
                width=15  # 减小按钮宽度
            )
            btn.grid(row=row, column=col, padx=3, pady=3, sticky=(tk.W, tk.E))
            
            # 更新行列位置
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # 配置网格权重
        for i in range(max_cols):
            button_frame.columnconfigure(i, weight=1, uniform="btn")
        
        # 内容显示区域（下方，用于显示选中功能的UI）
        # 使用 Canvas + Scrollbar 实现可滚动区域
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建画布
        canvas = tk.Canvas(canvas_frame, yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=canvas.yview)
        
        # 创建可滚动的内容框架
        self.special_content_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=self.special_content_frame, anchor=tk.NW)
        
        # 配置滚动区域
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # 确保内容框架宽度与画布一致
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        def on_canvas_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        canvas.bind('<Configure>', configure_scroll_region)
        self.special_content_frame.bind('<Configure>', on_canvas_configure)
        
        # 鼠标滚轮支持
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # 初始显示提示信息
        initial_label = ttk.Label(
            self.special_content_frame,
            text="请从上方选择一个功能",
            font=("Arial", 12),
            foreground="gray"
        )
        initial_label.pack(expand=True)
        self.initial_label = initial_label
    
    def show_special_function(self, func_info):
        """显示特殊分析功能界面"""
        # 清除之前的内容
        if self.special_content_frame is not None:
            for widget in self.special_content_frame.winfo_children():
                widget.destroy()
            # 如果初始标签存在，也清除
            if hasattr(self, 'initial_label'):
                self.initial_label = None
        
        # 调用对应的处理函数
        self.current_special_function = func_info
        func_info['handler']()
    
    def open_interactive_plotter(self):
        """打开交互式绘图器"""
        try:
            from special_analysis.interactive_plotter import InteractivePlotter
            
            # 在内容框架中创建交互式绘图器
            self.plotter = InteractivePlotter(parent=self.special_content_frame, standalone=False)
            
        except Exception as e:
            messagebox.showerror("错误", f"打开交互式绘图器失败: {e}")
            import traceback
            traceback.print_exc()
    
    def open_1550_analyzer(self):
        """打开1550倾角仪数据分析功能"""
        try:
            # 添加项目根目录到路径，以便作为包导入
            import sys
            project_root = os.path.dirname(__file__)
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            # 作为包导入
            from special_analysis_1550.main_ui import MainUI
            
            # 在内容框架中创建1550分析器（嵌入模式）
            self.analyzer_1550 = MainUI(parent=self.special_content_frame, standalone=False)
            
        except Exception as e:
            messagebox.showerror("错误", f"打开1550倾角仪数据分析失败: {e}")
            import traceback
            traceback.print_exc()
    
    def open_vehicle_traffic_analyzer(self):
        """打开车流量分析功能"""
        try:
            # 清空内容框架
            for widget in self.special_content_frame.winfo_children():
                widget.destroy()
            
            # 添加项目根目录到路径，以便作为包导入
            import sys
            project_root = os.path.dirname(__file__)
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            # 作为包导入
            from special_analysis.vehicle_traffic_analyzer import VehicleTrafficUI
            
            # 获取当前选中的桥梁
            selected_bridges = [b for b, var in self.bridge_checkboxes.items() if var.get()]
            bridge_name = selected_bridges[0] if selected_bridges else None
            
            # 获取数据目录
            from utils.analyzer_utils import AnalyzerPathManager
            data_dir = None
            if bridge_name:
                path_mgr = AnalyzerPathManager(bridge_name)
                data_dir = path_mgr.get_data_dir("车辆荷载")
            
            # 在内容框架中创建车流量分析器（嵌入模式）
            self.vehicle_traffic_ui = VehicleTrafficUI(
                parent=self.special_content_frame,
                bridge_name=bridge_name,
                data_dir=data_dir,
                standalone=False
            )
            
        except Exception as e:
            messagebox.showerror("错误", f"打开车流量分析失败: {e}")
            import traceback
            traceback.print_exc()
    
    def placeholder_function(self):
        """占位函数 - 用于预留功能"""
        messagebox.showinfo("提示", f"功能 '{self.current_special_function['name']}' 正在开发中，敬请期待！")
    

def main():
    """主函数"""
    # 尝试使用 TkinterDnD 以支持拖拽功能
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()
    
    app = UnifiedGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

