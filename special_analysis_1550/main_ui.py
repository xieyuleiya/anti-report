# -*- coding: utf-8 -*-
"""
主UI界面 (main_ui.py)

提供图形化界面，整合以下功能：
1. 数据下载配置和执行
2. 数据分析配置和执行
3. 参数设置和保存
4. 跳转到交互绘图器

使用说明：
- 运行 main_ui.py 启动主界面
- 配置参数后点击相应按钮执行功能
- 可以保存配置以便下次使用
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import json
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import platform

# 导入功能模块
try:
    # 尝试相对导入（作为包导入时）
    from .highway_downloader import run_download as highway_run_download
    from .data_loader import DataLoader
    from .trend_analyzer import TrendAnalyzer
    from .charts import create_trend_chart, create_critical_sensors_chart
    from .report_generator import generate_month_report, generate_quarter_report, generate_all_trend_charts_report, set_template_path
    from .utils import log, setup_chinese_fonts
    from .interactive_plotter import InteractivePlotter
except ImportError:
    # 回退到绝对导入（独立运行时）
    from highway_downloader import run_download as highway_run_download
    from data_loader import DataLoader
    from trend_analyzer import TrendAnalyzer
    from charts import create_trend_chart, create_critical_sensors_chart
    from report_generator import generate_month_report, generate_quarter_report, generate_all_trend_charts_report, set_template_path
    from utils import log, setup_chinese_fonts
    from interactive_plotter import InteractivePlotter
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import io
import queue


class LogRedirector:
    """重定向stdout到UI日志的类"""
    def __init__(self, ui_instance):
        self.ui = ui_instance
        self.log_queue = queue.Queue()
        self.buffer = ""
        # 启动日志处理线程
        self.start_log_processor()
    
    def start_log_processor(self):
        """启动日志处理线程"""
        def process_logs():
            while True:
                try:
                    # 从队列获取日志消息（超时1秒）
                    message = self.log_queue.get(timeout=1)
                    if message is None:  # 结束标志
                        break
                    # 在主线程中更新日志
                    self.ui.top_level.after(0, lambda m=message: self.ui.log(m, 'info'))
                    self.log_queue.task_done()
                except queue.Empty:
                    continue
                except Exception:
                    continue
        
        self.processor_thread = threading.Thread(target=process_logs, daemon=True)
        self.processor_thread.start()
    
    def write(self, text):
        """重写write方法，将输出发送到UI日志"""
        if text:
            # 累积文本到缓冲区
            self.buffer += text
            # 如果遇到换行符，处理整行
            if '\n' in self.buffer:
                lines = self.buffer.split('\n')
                # 保留最后一行（可能不完整）
                self.buffer = lines[-1]
                # 处理完整的行
                for line in lines[:-1]:
                    clean_text = line.strip()
                    if clean_text:
                        try:
                            self.log_queue.put(clean_text, block=False)
                        except queue.Full:
                            # 如果队列满了，跳过这条消息
                            pass
        return len(text)
    
    def flush(self):
        """刷新缓冲区"""
        if self.buffer.strip():
            try:
                self.log_queue.put(self.buffer.strip(), block=False)
                self.buffer = ""
            except queue.Full:
                pass
    
    def isatty(self):
        """返回False，表示不是终端"""
        return False
    
    def close(self):
        """关闭重定向器"""
        self.flush()  # 刷新剩余内容
        self.log_queue.put(None)  # 发送结束标志


class MainUI:
    """主UI界面类"""
    
    def __init__(self, parent=None, standalone=True):
        """
        初始化主UI界面
        
        Args:
            parent: 父容器（用于嵌入模式），如果提供则嵌入到parent中
            standalone: 是否为独立窗口模式（默认True）
        """
        self.standalone = standalone
        self.parent = parent
        
        if standalone:
            # 独立窗口模式
            self.root = tk.Tk()
            self.root.title("桥梁趋势分析系统 - 主控制台")
            self.root.geometry("1400x900")  # 增大窗口以适应新布局
            self.top_level = self.root  # 独立模式下，root就是顶层窗口
        else:
            # 嵌入模式：使用parent作为容器
            if parent is None:
                raise ValueError("嵌入模式需要提供parent参数")
            self.root = parent
            # 获取顶层窗口用于after等操作
            self.top_level = parent.winfo_toplevel()
        
        # 配置变量（带默认值）
        default_base_dir = r"D:\useful\01-work file\07.报告\20250801-报告-云茂1550报告"
        self.config = {
            'BASE_DIR': default_base_dir,
            'PERIOD_NAME': "1月月报",
            'EXCEL_PATH': os.path.join(default_base_dir, "基础资料", "1550通道ID测点完整表2026.01.15.xlsx"),
            'TEMPLATE_PATH': os.path.join(default_base_dir, "基础资料", "云茂报告模版.docx"),
            'TARGET_HIGHWAYS': ["云茂"],
            'TARGET_HIGHWAY_BRIDGES': [],
            'START_DATE': (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            'END_DATE': datetime.now().strftime("%Y-%m-%d"),
            'BATCH_SIZE_DAYS': 31,
        }
        
        # 运行状态
        self.is_running = False
        self.current_task = None
        self.download_completed = False  # 下载完成标志
        
        # 进度相关
        self.download_progress_var = tk.StringVar(value="")
        self.analysis_progress_var = tk.StringVar(value="")
        self.download_progress_value = tk.DoubleVar(value=0.0)
        self.analysis_progress_value = tk.DoubleVar(value=0.0)
        
        # 创建界面
        self.create_widgets()
        
        # 加载保存的配置（在界面创建后）
        self.load_config()
        
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 使用PanedWindow分割左右两部分
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：参数配置和功能操作
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # 右侧：日志查看
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        # 创建左侧内容（配置+操作）
        self.create_left_panel(left_frame)
        
        # 创建右侧内容（日志）
        self.create_log_panel(right_frame)
        
        # 底部状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(5, 0))
    
    def create_left_panel(self, parent):
        """创建左侧面板（配置+操作）"""
        # 使用Notebook在左侧创建两个标签页
        left_notebook = ttk.Notebook(parent)
        left_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 参数配置标签页
        config_frame = ttk.Frame(left_notebook, padding="10")
        left_notebook.add(config_frame, text="参数配置")
        self.create_config_tab(config_frame)
        
        # 功能操作标签页
        action_frame = ttk.Frame(left_notebook, padding="10")
        left_notebook.add(action_frame, text="功能操作")
        self.create_action_tab(action_frame)
    
    def create_log_panel(self, parent):
        """创建右侧面板（支持日志和绘图器切换）"""
        # 使用Notebook实现标签页切换
        self.right_notebook = ttk.Notebook(parent)
        self.right_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 日志标签页
        log_container = ttk.Frame(self.right_notebook)
        log_frame = ttk.LabelFrame(log_container, text="运行日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=30, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 日志操作按钮
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(log_btn_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_btn_frame, text="保存日志", command=self.save_log).pack(side=tk.LEFT, padx=5)
        
        self.right_notebook.add(log_container, text="运行日志")
        
        # 绘图器标签页（初始为空，点击按钮后创建）
        self.plotter_container = None
        self.plotter_instance = None
        
    def create_config_tab(self, parent):
        """创建参数配置标签页"""
        # 创建滚动框架
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 基础路径配置
        base_frame = ttk.LabelFrame(scrollable_frame, text="基础路径配置", padding="10")
        base_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(base_frame, text="报告根目录:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.base_dir_var = tk.StringVar(value=self.config['BASE_DIR'])
        base_dir_entry = ttk.Entry(base_frame, textvariable=self.base_dir_var, width=60)
        base_dir_entry.grid(row=0, column=1, padx=5)
        # 绑定变化事件，自动更新相关路径
        self.base_dir_var.trace('w', lambda *args: self.update_default_paths())
        ttk.Button(base_frame, text="浏览", command=self.browse_base_dir).grid(row=0, column=2)
        
        ttk.Label(base_frame, text="本期名称:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.period_name_var = tk.StringVar(value=self.config['PERIOD_NAME'])
        ttk.Entry(base_frame, textvariable=self.period_name_var, width=60).grid(row=1, column=1, padx=5)
        
        # 文件路径配置
        file_frame = ttk.LabelFrame(scrollable_frame, text="文件路径配置（留空将使用默认路径）", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="Excel文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.excel_path_var = tk.StringVar(value=self.config.get('EXCEL_PATH', ''))
        ttk.Entry(file_frame, textvariable=self.excel_path_var, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_excel_path).grid(row=0, column=2)
        ttk.Label(file_frame, text="(默认: 基础资料/1550通道ID测点完整表2026.01.15.xlsx)", 
                 font=("Arial", 8), foreground="gray").grid(row=0, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(file_frame, text="报告模板:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.template_path_var = tk.StringVar(value=self.config.get('TEMPLATE_PATH', ''))
        ttk.Entry(file_frame, textvariable=self.template_path_var, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(file_frame, text="浏览", command=self.browse_template_path).grid(row=1, column=2)
        ttk.Label(file_frame, text="(默认: 基础资料/云茂报告模版.docx)", 
                 font=("Arial", 8), foreground="gray").grid(row=1, column=3, sticky=tk.W, padx=5)
        
        # 下载配置
        download_frame = ttk.LabelFrame(scrollable_frame, text="数据下载配置", padding="10")
        download_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(download_frame, text="目标高速公路:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.highways_var = tk.StringVar(value=", ".join(self.config['TARGET_HIGHWAYS']))
        ttk.Entry(download_frame, textvariable=self.highways_var, width=60).grid(row=0, column=1, padx=5)
        ttk.Label(download_frame, text="(多个用逗号分隔)", font=("Arial", 8)).grid(row=0, column=2, sticky=tk.W)
        
        ttk.Label(download_frame, text="开始日期:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.start_date_var = tk.StringVar(value=self.config['START_DATE'])
        ttk.Entry(download_frame, textvariable=self.start_date_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Label(download_frame, text="格式: YYYY-MM-DD", font=("Arial", 8)).grid(row=1, column=2, sticky=tk.W)
        
        ttk.Label(download_frame, text="结束日期:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.end_date_var = tk.StringVar(value=self.config['END_DATE'])
        ttk.Entry(download_frame, textvariable=self.end_date_var, width=20).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(download_frame, text="批量大小(天):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.batch_size_var = tk.StringVar(value=str(self.config['BATCH_SIZE_DAYS']))
        ttk.Entry(download_frame, textvariable=self.batch_size_var, width=20).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        # 配置操作按钮
        config_btn_frame = ttk.Frame(scrollable_frame)
        config_btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(config_btn_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_btn_frame, text="加载配置", command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_btn_frame, text="重置为默认", command=self.reset_config).pack(side=tk.LEFT, padx=5)
        
    def create_action_tab(self, parent):
        """创建功能操作标签页"""
        # 功能按钮区域
        btn_frame = ttk.LabelFrame(parent, text="功能操作", padding="20")
        btn_frame.pack(fill=tk.X, pady=5)
        
        # 数据下载按钮
        download_btn = ttk.Button(
            btn_frame, 
            text="📥 下载数据", 
            command=self.start_download,
            width=30
        )
        download_btn.pack(pady=5)
        
        # 数据分析按钮
        analysis_btn = ttk.Button(
            btn_frame, 
            text="📊 数据分析", 
            command=self.start_analysis,
            width=30
        )
        analysis_btn.pack(pady=5)
        
        # 下载+分析按钮
        both_btn = ttk.Button(
            btn_frame, 
            text="📥📊 下载并分析", 
            command=self.start_download_and_analysis,
            width=30
        )
        both_btn.pack(pady=5)
        
        # 分隔线
        ttk.Separator(btn_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # 交互绘图器按钮
        plotter_btn = ttk.Button(
            btn_frame, 
            text="📈 打开交互绘图器", 
            command=self.open_plotter,
            width=30
        )
        plotter_btn.pack(pady=5)
        
        # 下载进度显示
        download_progress_frame = ttk.LabelFrame(parent, text="下载进度", padding="10")
        download_progress_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(download_progress_frame, textvariable=self.download_progress_var).pack(anchor=tk.W)
        self.download_progress_bar = ttk.Progressbar(download_progress_frame, mode='determinate', variable=self.download_progress_value, maximum=100)
        self.download_progress_bar.pack(fill=tk.X, pady=5)
        
        # 分析进度显示
        analysis_progress_frame = ttk.LabelFrame(parent, text="分析进度", padding="10")
        analysis_progress_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(analysis_progress_frame, textvariable=self.analysis_progress_var).pack(anchor=tk.W)
        self.analysis_progress_bar = ttk.Progressbar(analysis_progress_frame, mode='determinate', variable=self.analysis_progress_value, maximum=100)
        self.analysis_progress_bar.pack(fill=tk.X, pady=5)
        
        # 总体状态
        self.progress_var = tk.StringVar(value="等待操作...")
        status_frame = ttk.LabelFrame(parent, text="运行状态", padding="10")
        status_frame.pack(fill=tk.X, pady=5)
        ttk.Label(status_frame, textvariable=self.progress_var).pack(anchor=tk.W)
        
        
    # ==================== 配置相关方法 ====================
    
    def browse_base_dir(self):
        """浏览报告根目录"""
        path = filedialog.askdirectory(title="选择报告根目录", initialdir=self.base_dir_var.get())
        if path:
            self.base_dir_var.set(path)
            # 自动更新默认路径
            self.update_default_paths()
    
    def update_default_paths(self):
        """根据BASE_DIR自动更新Excel和模板的默认路径"""
        base_dir = self.base_dir_var.get()
        if not base_dir:
            return
        
        # 如果Excel路径为空或者是默认路径，则更新
        current_excel = self.excel_path_var.get()
        default_excel = os.path.join(base_dir, "基础资料", "1550通道ID测点完整表2026.01.15.xlsx")
        
        # 检查当前Excel路径是否是默认路径（基于旧的BASE_DIR）
        if not current_excel or self._is_default_path(current_excel, "1550通道ID测点完整表"):
            self.excel_path_var.set(default_excel)
        
        # 如果模板路径为空或者是默认路径，则更新
        current_template = self.template_path_var.get()
        default_template = os.path.join(base_dir, "基础资料", "云茂报告模版.docx")
        
        if not current_template or self._is_default_path(current_template, "云茂报告模版"):
            self.template_path_var.set(default_template)
    
    def _is_default_path(self, path, filename_keyword):
        """检查路径是否是默认路径（包含关键字且在基础资料目录下）"""
        if not path:
            return True
        return "基础资料" in path and filename_keyword in path
    
    def browse_excel_path(self):
        """浏览Excel文件"""
        path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("所有文件", "*.*")],
            initialdir=os.path.dirname(self.excel_path_var.get()) if self.excel_path_var.get() else None
        )
        if path:
            self.excel_path_var.set(path)
    
    def browse_template_path(self):
        """浏览报告模板"""
        path = filedialog.askopenfilename(
            title="选择报告模板",
            filetypes=[("Word文档", "*.docx"), ("所有文件", "*.*")],
            initialdir=os.path.dirname(self.template_path_var.get()) if self.template_path_var.get() else None
        )
        if path:
            self.template_path_var.set(path)
    
    def get_config(self):
        """获取当前配置"""
        base_dir = self.base_dir_var.get()
        period_name = self.period_name_var.get()
        
        # 构建路径
        period_root = os.path.join(base_dir, period_name)
        raw_dir = os.path.join(period_root, "原始数据")
        result_dir = os.path.join(period_root, "趋势分析结果")
        
        # 获取高速公路列表
        highways_str = self.highways_var.get().strip()
        highways = [h.strip() for h in highways_str.split(",") if h.strip()] if highways_str else ["云茂"]
        
        # 如果Excel路径为空，使用默认路径
        excel_path = self.excel_path_var.get()
        if not excel_path:
            excel_path = os.path.join(base_dir, "基础资料", "1550通道ID测点完整表2026.01.15.xlsx")
        
        # 如果模板路径为空，使用默认路径
        template_path = self.template_path_var.get()
        if not template_path:
            template_path = os.path.join(base_dir, "基础资料", "云茂报告模版.docx")
        
        download_config = {
            'EXCEL_PATH': excel_path,
            'ROAD': raw_dir,
            'TARGET_HIGHWAYS': highways,
            'TARGET_HIGHWAY_BRIDGES': self.config.get('TARGET_HIGHWAY_BRIDGES', []),
            'START_DATE': self.start_date_var.get(),
            'END_DATE': self.end_date_var.get(),
            'BATCH_SIZE_DAYS': int(self.batch_size_var.get()) if self.batch_size_var.get().isdigit() else 31,
        }
        
        analysis_config = {
            'DATA_DIR': raw_dir,
            'OUTPUT_DIR': result_dir,
            'TEMPLATE_PATH': template_path,
        }
        
        return download_config, analysis_config
    
    def save_config(self):
        """保存配置到文件"""
        try:
            config_file = os.path.join(os.path.dirname(__file__), "config.json")
            config_to_save = {
                'BASE_DIR': self.base_dir_var.get(),
                'PERIOD_NAME': self.period_name_var.get(),
                'EXCEL_PATH': self.excel_path_var.get(),
                'TEMPLATE_PATH': self.template_path_var.get(),
                'TARGET_HIGHWAYS': [h.strip() for h in self.highways_var.get().split(",") if h.strip()],
                'START_DATE': self.start_date_var.get(),
                'END_DATE': self.end_date_var.get(),
                'BATCH_SIZE_DAYS': int(self.batch_size_var.get()) if self.batch_size_var.get().isdigit() else 31,
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            
            self.log("配置已保存", 'success')
            messagebox.showinfo("成功", "配置已保存到 config.json")
        except Exception as e:
            self.log(f"保存配置失败: {e}", 'error')
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def load_config(self):
        """从文件加载配置"""
        try:
            config_file = os.path.join(os.path.dirname(__file__), "config.json")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # 检查变量是否已创建
                if hasattr(self, 'base_dir_var'):
                    self.base_dir_var.set(loaded_config.get('BASE_DIR', self.config['BASE_DIR']))
                    self.period_name_var.set(loaded_config.get('PERIOD_NAME', self.config['PERIOD_NAME']))
                    self.excel_path_var.set(loaded_config.get('EXCEL_PATH', ''))
                    self.template_path_var.set(loaded_config.get('TEMPLATE_PATH', ''))
                    highways = loaded_config.get('TARGET_HIGHWAYS', self.config['TARGET_HIGHWAYS'])
                    self.highways_var.set(", ".join(highways) if isinstance(highways, list) else highways)
                    self.start_date_var.set(loaded_config.get('START_DATE', self.config['START_DATE']))
                    self.end_date_var.set(loaded_config.get('END_DATE', self.config['END_DATE']))
                    self.batch_size_var.set(str(loaded_config.get('BATCH_SIZE_DAYS', self.config['BATCH_SIZE_DAYS'])))
                    
                    self.config.update(loaded_config)
                    self.log("配置已加载", 'success')
        except Exception as e:
            if hasattr(self, 'log'):
                self.log(f"加载配置失败: {e}", 'warn')
            else:
                print(f"加载配置失败: {e}")
    
    def reset_config(self):
        """重置为默认配置"""
        if messagebox.askyesno("确认", "确定要重置为默认配置吗？"):
            base_dir = self.config['BASE_DIR']
            self.base_dir_var.set(base_dir)
            self.period_name_var.set(self.config['PERIOD_NAME'])
            # 使用默认路径
            self.excel_path_var.set(os.path.join(base_dir, "基础资料", "1550通道ID测点完整表2026.01.15.xlsx"))
            self.template_path_var.set(os.path.join(base_dir, "基础资料", "云茂报告模版.docx"))
            self.highways_var.set(", ".join(self.config['TARGET_HIGHWAYS']))
            self.start_date_var.set(self.config['START_DATE'])
            self.end_date_var.set(self.config['END_DATE'])
            self.batch_size_var.set(str(self.config['BATCH_SIZE_DAYS']))
            self.log("配置已重置", 'info')
    
    # ==================== 功能执行方法 ====================
    
    def start_download(self):
        """启动数据下载"""
        if self.is_running:
            messagebox.showwarning("警告", "已有任务正在运行，请等待完成")
            return
        
        download_config, _ = self.get_config()
        
        # 验证配置
        excel_path = download_config['EXCEL_PATH']
        if not excel_path or not os.path.exists(excel_path):
            msg = f"Excel文件不存在:\n{excel_path}\n\n"
            msg += "请检查文件路径，或点击【浏览】按钮选择正确的Excel文件。"
            messagebox.showerror("错误", msg)
            return
        
        if not download_config['TARGET_HIGHWAYS']:
            messagebox.showerror("错误", "请配置目标高速公路")
            return
        
        self.is_running = True
        self.current_task = "下载"
        self.progress_var.set("正在下载数据...")
        self.download_progress_var.set("准备开始下载...")
        self.download_progress_value.set(0)
        self.status_var.set("正在下载数据...")
        
        thread = threading.Thread(target=self.run_download, args=(download_config,))
        thread.daemon = True
        thread.start()
    
    def start_analysis(self):
        """启动数据分析"""
        if self.is_running:
            messagebox.showwarning("警告", "已有任务正在运行，请等待完成")
            return
        
        _, analysis_config = self.get_config()
        
        # 验证配置
        if not os.path.exists(analysis_config['DATA_DIR']):
            messagebox.showerror("错误", f"数据目录不存在: {analysis_config['DATA_DIR']}\n请先下载数据")
            return
        
        self.is_running = True
        self.current_task = "分析"
        self.progress_var.set("正在分析数据...")
        self.analysis_progress_var.set("准备开始分析...")
        self.analysis_progress_value.set(0)
        self.status_var.set("正在分析数据...")
        
        thread = threading.Thread(target=self.run_analysis, args=(analysis_config,))
        thread.daemon = True
        thread.start()
    
    def start_download_and_analysis(self):
        """启动下载并分析"""
        if self.is_running:
            messagebox.showwarning("警告", "已有任务正在运行，请等待完成")
            return
        
        download_config, analysis_config = self.get_config()
        
        # 验证配置
        if not download_config['EXCEL_PATH'] or not os.path.exists(download_config['EXCEL_PATH']):
            messagebox.showerror("错误", "请先配置有效的Excel文件路径")
            return
        
        self.is_running = True
        self.current_task = "下载并分析"
        self.progress_var.set("正在下载数据...")
        self.download_progress_var.set("准备开始下载...")
        self.download_progress_value.set(0)
        self.analysis_progress_value.set(0)
        self.status_var.set("正在下载数据...")
        
        thread = threading.Thread(target=self.run_download_and_analysis, args=(download_config, analysis_config))
        thread.daemon = True
        thread.start()
    
    def open_plotter(self):
        """打开交互绘图器（集成到右侧面板）"""
        try:
            # 如果绘图器标签页不存在，创建它
            if self.plotter_container is None:
                self.plotter_container = ttk.Frame(self.right_notebook)
                self.right_notebook.add(self.plotter_container, text="交互绘图器")
            
            # 如果绘图器实例不存在，创建它
            if self.plotter_instance is None:
                self.plotter_instance = InteractivePlotter(parent=self.plotter_container, standalone=False)
            
            # 切换到绘图器标签页
            self.right_notebook.select(self.plotter_container)
            
        except Exception as e:
            self.log(f"打开交互绘图器失败: {e}", 'error')
            import traceback
            self.log(traceback.format_exc(), 'error')
            messagebox.showerror("错误", f"打开交互绘图器失败: {e}")
    
    def open_directory(self, path):
        """打开目录（跨平台）"""
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", path])
            else:  # Linux
                subprocess.Popen(["xdg-open", path])
            self.log(f"已打开目录: {path}", 'info')
        except Exception as e:
            self.log(f"打开目录失败: {e}", 'warn')
    
    def run_download(self, config):
        """执行数据下载"""
        try:
            self.log("开始数据下载...", 'info')
            self.download_progress_var.set("正在下载数据...")
            self.download_progress_value.set(10)
            
            # 创建进度监控线程
            progress_thread = threading.Thread(target=self._monitor_download_progress, args=(config,))
            progress_thread.daemon = True
            progress_thread.start()
            
            # 执行下载（不显示详细日志）
            highway_run_download(config)
            
            # 标记下载完成，停止进度监控
            self.download_completed = True
            self.download_progress_value.set(100)
            self.download_progress_var.set("下载完成！")
            self.log("数据下载完成！", 'success')
            self.status_var.set("数据下载完成")
            
            # 自动打开下载目录
            download_dir = config.get('ROAD', '')
            if download_dir and os.path.exists(download_dir):
                self.open_directory(download_dir)
            
            # 在主线程中显示消息框
            self.top_level.after(0, lambda: messagebox.showinfo("成功", "数据下载完成！\n已自动打开下载目录"))
        except Exception as e:
            self.log(f"数据下载失败: {e}", 'error')
            self.download_progress_var.set(f"下载失败: {str(e)}")
            self.status_var.set("数据下载失败")
            # 在主线程中显示错误框
            self.top_level.after(0, lambda: messagebox.showerror("错误", f"数据下载失败: {e}"))
        finally:
            self.is_running = False
            self.progress_var.set("等待操作...")
    
    def _monitor_download_progress(self, config):
        """监控下载进度（模拟进度更新）"""
        self.download_completed = False
        # 读取Excel文件获取总测点数
        try:
            import pandas as pd
            df = pd.read_excel(config.get('EXCEL_PATH', ''))
            total_sensors = len(df)
            
            # 模拟进度更新（每2秒更新一次，从10%到90%）
            for i in range(10, 90, 5):
                if not self.is_running or self.download_completed:
                    break
                self.download_progress_value.set(i)
                self.download_progress_var.set(f"正在下载数据... ({i}%)")
                time.sleep(2)
        except:
            # 如果无法获取总数，使用简单的时间进度
            for i in range(10, 90, 10):
                if not self.is_running or self.download_completed:
                    break
                self.download_progress_value.set(i)
                self.download_progress_var.set(f"正在下载数据... ({i}%)")
                time.sleep(3)
    
    def run_analysis(self, config):
        """执行数据分析"""
        try:
            self.log("开始数据分析...", 'info')
            self.analysis_progress_var.set("正在分析数据...")
            self.analysis_progress_value.set(10)
            
            success = self._run_trend_analysis(config)
            if success:
                self.analysis_progress_value.set(100)
                self.analysis_progress_var.set("分析完成！")
                self.log("数据分析完成！", 'success')
                self.status_var.set("数据分析完成")
                
                # 自动打开分析结果目录
                output_dir = config.get('OUTPUT_DIR', '')
                if output_dir and os.path.exists(output_dir):
                    self.open_directory(output_dir)
                
                # 在主线程中显示消息框
                self.top_level.after(0, lambda: messagebox.showinfo("成功", "数据分析完成！\n已自动打开结果目录"))
            else:
                self.analysis_progress_var.set("分析失败！")
                self.log("数据分析失败！", 'error')
                self.status_var.set("数据分析失败")
                # 在主线程中显示错误框
                self.top_level.after(0, lambda: messagebox.showerror("错误", "数据分析失败，请查看日志"))
        except Exception as e:
            self.analysis_progress_var.set(f"分析异常: {str(e)}")
            self.log(f"数据分析异常: {e}", 'error')
            import traceback
            self.log(traceback.format_exc(), 'error')
            self.status_var.set("数据分析失败")
            # 在主线程中显示错误框
            self.top_level.after(0, lambda: messagebox.showerror("错误", f"数据分析异常: {e}"))
        finally:
            self.is_running = False
            self.progress_var.set("等待操作...")
    
    def run_download_and_analysis(self, download_config, analysis_config):
        """执行下载并分析"""
        try:
            # 先下载
            self.log("开始数据下载...", 'info')
            self.progress_var.set("正在下载数据...")
            self.download_progress_var.set("正在下载数据...")
            self.download_progress_value.set(10)
            
            # 创建进度监控线程
            progress_thread = threading.Thread(target=self._monitor_download_progress, args=(download_config,))
            progress_thread.daemon = True
            progress_thread.start()
            
            highway_run_download(download_config)
            
            # 标记下载完成，停止进度监控
            self.download_completed = True
            self.download_progress_value.set(100)
            self.download_progress_var.set("下载完成！")
            self.log("数据下载完成！", 'success')
            
            # 再分析
            self.log("开始数据分析...", 'info')
            self.progress_var.set("正在分析数据...")
            self.analysis_progress_var.set("正在分析数据...")
            self.analysis_progress_value.set(10)
            
            success = self._run_trend_analysis(analysis_config)
            
            if success:
                self.analysis_progress_value.set(100)
                self.analysis_progress_var.set("分析完成！")
                self.log("所有任务完成！", 'success')
                self.status_var.set("所有任务完成")
                
                # 自动打开分析结果目录（优先显示分析结果）
                output_dir = analysis_config.get('OUTPUT_DIR', '')
                if output_dir and os.path.exists(output_dir):
                    self.open_directory(output_dir)
                
                # 在主线程中显示消息框
                self.top_level.after(0, lambda: messagebox.showinfo("成功", "数据下载和分析完成！\n已自动打开结果目录"))
            else:
                self.analysis_progress_var.set("分析失败！")
                self.log("数据分析失败！", 'error')
                self.status_var.set("数据分析失败")
                # 在主线程中显示警告框
                self.top_level.after(0, lambda: messagebox.showwarning("警告", "数据下载完成，但分析失败，请查看日志"))
        except Exception as e:
            self.log(f"执行失败: {e}", 'error')
            import traceback
            self.log(traceback.format_exc(), 'error')
            self.status_var.set("执行失败")
            # 在主线程中显示错误框
            self.top_level.after(0, lambda: messagebox.showerror("错误", f"执行失败: {e}"))
        finally:
            self.is_running = False
            self.progress_var.set("等待操作...")
    
    def _run_trend_analysis(self, config):
        """运行趋势分析（从main.py移植）"""
        try:
            t_total_start = time.perf_counter()
            
            set_template_path(config.get('TEMPLATE_PATH'))
            data_dir = config['DATA_DIR']
            output_dir = config['OUTPUT_DIR']
            
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(os.path.join(output_dir, "测点图表"), exist_ok=True)
            
            loader = DataLoader(data_dir)
            self.analysis_progress_var.set("正在扫描数据目录...")
            self.analysis_progress_value.set(15)
            bridge_files = loader.scan_data_directories()
            
            if not bridge_files:
                self.log("未找到任何桥梁数据", 'error')
                return False
            
            trend_analyzer = TrendAnalyzer()
            all_trend_results = {}
            all_bridges_data = {}
            manufacturers_map = {}
            total_bridges = len(bridge_files)
            current_bridge = 0
            total_sensors_all = sum(len(files) for files in bridge_files.values())
            processed_sensors_all = 0
            
            for bridge_name, txt_files in bridge_files.items():
                t_bridge_start = time.perf_counter()
                current_bridge += 1
                # 更新进度：桥梁处理进度（15% - 85%）
                bridge_progress = 15 + int((current_bridge - 1) / total_bridges * 70)
                self.analysis_progress_value.set(bridge_progress)
                self.analysis_progress_var.set(f"正在处理桥梁 ({current_bridge}/{total_bridges}): {bridge_name}")
                
                trend_results = {}
                bridge_data = {}
                critical_sensors_data = {}
                bridge_manufacturers = {}
                
                for fpath in txt_files:
                    info = loader.get_file_info(fpath)
                    if info is not None:
                        pier = info.get('pier_number') or loader.extract_sensor_id(fpath)
                        vendor = info.get('manufacturer', '')
                        if pier:
                            bridge_manufacturers[pier] = vendor
                
                total_sensors = len(txt_files)
                current_sensor = 0
                
                def _process_sensor(txt_file_path):
                    sensor_status = loader.get_sensor_status(txt_file_path)
                    if sensor_status == "离线":
                        sensor_id_local = loader.extract_sensor_id(txt_file_path)
                        return (txt_file_path, sensor_id_local, "OFFLINE")
                    
                    df_local = loader.load_single_file(txt_file_path, bridge_name)
                    if df_local is None:
                        return (txt_file_path, None, None)
                    result_local = trend_analyzer.analyze_trend(df_local)
                    if result_local is None:
                        return (txt_file_path, None, None)
                    sensor_id_local = str(df_local['sensor_id'].iloc[0])
                    return (txt_file_path, sensor_id_local, (df_local, result_local))
                
                base_workers = min(8, max(2, os.cpu_count() or 4))
                max_workers = max(1, min(base_workers, total_sensors))
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_file = {executor.submit(_process_sensor, fpath): fpath for fpath in txt_files}
                    for future in as_completed(future_to_file):
                        txt_file = future_to_file[future]
                        current_sensor += 1
                        processed_sensors_all += 1
                        try:
                            # 更新进度：测点处理进度
                            sensor_progress = 15 + int(processed_sensors_all / total_sensors_all * 70)
                            self.analysis_progress_value.set(sensor_progress)
                            self.analysis_progress_var.set(f"正在处理测点 ({processed_sensors_all}/{total_sensors_all}): {os.path.basename(txt_file)}")
                            txt_path, sensor_id, payload = future.result()
                        except Exception as e:
                            # 只记录严重错误
                            continue
                        if payload is None:
                            continue
                        
                        if payload == "OFFLINE":
                            trend_results[sensor_id] = "OFFLINE"
                            bridge_data[sensor_id] = "OFFLINE"
                            continue
                        
                        df, result = payload
                        trend_results[sensor_id] = result
                        bridge_data[sensor_id] = df
                        
                        h_trend = result['horizontal_angle_trend']
                        v_trend = result['vertical_angle_trend']
                        if h_trend['trend_strength'] != '正常' or v_trend['trend_strength'] != '正常':
                            chart_path = os.path.join(output_dir, "测点图表", f"{bridge_name}_{sensor_id}_趋势分析.png")
                            create_trend_chart(df, result, chart_path)
                        
                        if h_trend['trend_strength'] == '持续关注' or v_trend['trend_strength'] == '持续关注':
                            critical_sensors_data[sensor_id] = {
                                'timestamp': df['timestamp'],
                                'horizontal_angle': df['horizontal_angle'],
                                'vertical_angle': df['vertical_angle']
                            }
                
                if critical_sensors_data:
                    critical_chart_path = os.path.join(output_dir, "测点图表", f"{bridge_name}_持续关注测点.png")
                    create_critical_sensors_chart(bridge_name, critical_sensors_data, critical_chart_path)
                
                all_trend_results[bridge_name] = trend_results
                all_bridges_data[bridge_name] = bridge_data
                manufacturers_map[bridge_name] = bridge_manufacturers
            
            self.analysis_progress_value.set(85)
            self.analysis_progress_var.set("正在生成报告...")
            try:
                generate_month_report(all_trend_results, all_bridges_data, output_dir)
            except Exception as e:
                self.log(f"生成月报失败: {e}", 'error')
            
            self.analysis_progress_value.set(90)
            self.analysis_progress_var.set("正在生成季报...")
            try:
                generate_quarter_report(all_trend_results, all_bridges_data, output_dir)
            except Exception as e:
                self.log(f"生成季报失败: {e}", 'error')
            
            self.analysis_progress_value.set(95)
            self.analysis_progress_var.set("正在生成趋势图一览...")
            try:
                generate_all_trend_charts_report(all_trend_results, all_bridges_data, output_dir, manufacturers_map)
                self.log("所有桥梁测点趋势图一览生成完成", 'success')
            except Exception as e:
                self.log(f"生成趋势图一览失败: {e}", 'error')
                import traceback
                self.log(traceback.format_exc(), 'error')
            
            total_elapsed = time.perf_counter() - t_total_start
            self.log(f"数据分析完成，耗时: {total_elapsed:.2f}秒", 'success')
            return True
            
        except Exception as e:
            self.log(f"趋势分析异常: {e}", 'error')
            import traceback
            self.log(traceback.format_exc(), 'error')
            return False
    
    # ==================== 日志相关方法 ====================
    
    def log(self, message, level='info'):
        """添加日志"""
        prefix = {
            'info': '→',
            'warn': '!',
            'error': '×',
            'success': '√'
        }.get(level, '•')
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {prefix} {message}\n"
        
        # 添加到日志文本区域
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        
        # 同时输出到控制台（兼容原有的log函数）
        print(log_message.strip())
    
    def clear_log(self):
        """清空日志"""
        if messagebox.askyesno("确认", "确定要清空日志吗？"):
            self.log_text.delete(1.0, tk.END)
    
    def save_log(self):
        """保存日志到文件"""
        try:
            log_file = filedialog.asksaveasfilename(
                title="保存日志",
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            if log_file:
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("成功", f"日志已保存到: {log_file}")
        except Exception as e:
            messagebox.showerror("错误", f"保存日志失败: {e}")
    
    def run(self):
        """运行主界面"""
        if self.standalone:
            self.root.mainloop()
        # 嵌入模式下不需要调用mainloop，由父窗口管理


def main():
    """主函数"""
    try:
        app = MainUI()
        app.run()
    except Exception as e:
        messagebox.showerror("错误", f"程序启动失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

