"""
交互式周聚合数据绘图器
支持拖拽文件、自定义时间段、编辑图表属性，并复制图片到剪贴板
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 尝试导入拖拽支持
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    # 如果没有tkinterdnd2，使用普通Tk
    TkinterDnD = tk.Tk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from pathlib import Path
import io
from PIL import Image
import sys

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 尝试导入剪贴板相关库
try:
    import win32clipboard
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    try:
        import pyperclip
        HAS_PYPERCLIP = True
    except ImportError:
        HAS_PYPERCLIP = False


class InteractivePlotter:
    """交互式绘图器类"""
    
    def __init__(self, parent=None, standalone=True):
        """
        初始化交互式绘图器
        
        Args:
            parent: 父容器（如果为None或standalone=True，则创建独立窗口）
            standalone: 是否为独立窗口模式
        """
        if standalone or parent is None:
            # 独立窗口模式
            self.root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
            self.root.title("周聚合数据交互式绘图器")
            self.root.geometry("1400x900")
            self.parent = self.root
            self.standalone = True
        else:
            # 嵌入模式
            self.root = parent.winfo_toplevel() if hasattr(parent, 'winfo_toplevel') else parent
            self.parent = parent
            self.standalone = False
            # 检查根窗口是否是 TkinterDnD 实例（如果主窗口支持拖拽）
            try:
                # 尝试检查根窗口是否有 drop_target_register 方法
                if HAS_DND and hasattr(self.root, 'drop_target_register'):
                    self.supports_dnd = True
                else:
                    self.supports_dnd = False
            except:
                self.supports_dnd = False
        
        # 数据存储 - 改为字典，支持多个测点
        self.data_dict = {}  # {测点名称: {'data': DataFrame, 'type': 'displacement'/'tilt', 'filepath': Path}}
        self.weekly_data_dict = {}  # {测点名称: 周聚合数据}
        self.data_type = None  # 当前数据类型（所有测点应该一致）
        
        # 颜色列表
        self.colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                      '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        """创建界面组件"""
        # 创建样式用于设置字体（ttk组件不支持font参数）
        style = ttk.Style()
        try:
            style.configure("Small.TLabel", font=("Arial", 9))
            style.configure("Small.TEntry", font=("Arial", 9))
            style.configure("Small.TCheckbutton", font=("Arial", 9))
            style.configure("Small.TRadiobutton", font=("Arial", 9))
        except:
            pass  # 如果样式设置失败，使用默认样式
        
        # 主框架（减少padding）
        main_frame = ttk.Frame(self.parent, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重（如果是独立窗口）
        if hasattr(self.parent, 'columnconfigure'):
            self.parent.columnconfigure(0, weight=1)
            self.parent.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 左侧控制面板（减小宽度，减少padding）
        control_panel = ttk.LabelFrame(main_frame, text="控制面板", padding="5")
        control_panel.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        control_panel.columnconfigure(0, weight=1)
        
        # 文件选择区域（更紧凑）
        file_frame = ttk.LabelFrame(control_panel, text="文件选择", padding="3")
        file_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.file_count_label = ttk.Label(file_frame, text="已加载: 0 个测点", style="Small.TLabel")
        self.file_count_label.pack(fill=tk.X, pady=2)
        
        # 按钮使用更紧凑的布局（水平排列）
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="添加文件", command=self.select_file, width=10).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="添加多个", command=self.select_files, width=10).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="清空", command=self.clear_data, width=8).pack(side=tk.LEFT, padx=1)
        
        # 拖拽区域（更小更紧凑）
        drop_frame = ttk.Frame(file_frame)
        drop_frame.pack(fill=tk.X, pady=2)
        drop_label = tk.Label(drop_frame, text="拖拽文件到此处", 
                             bg="lightgray", relief=tk.SUNKEN, padx=5, pady=8, font=("Arial", 8))
        drop_label.pack(fill=tk.X)
        # 尝试启用拖拽功能（独立模式或嵌入模式但根窗口支持）
        if HAS_DND:
            try:
                # 尝试注册拖拽功能
                drop_label.drop_target_register(DND_FILES)
                drop_label.dnd_bind('<<Drop>>', self.on_drop)
                # 如果成功，恢复原始提示文本
                drop_label.config(text="拖拽文件到此处\n(或使用上方'选择文件'按钮)")
            except Exception as e:
                # 如果拖拽注册失败，降级为普通模式
                if self.standalone:
                    drop_label.config(text="请使用'选择文件'按钮\n(拖拽功能不可用)")
                else:
                    drop_label.config(text="请使用'选择文件'按钮\n(嵌入模式下不支持拖拽)")
        else:
            drop_label.config(text="请使用'选择文件'按钮\n(安装tkinterdnd2以支持拖拽)")
        
        # 时间段选择（更紧凑）
        time_frame = ttk.LabelFrame(control_panel, text="时间段选择", padding="3")
        time_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(time_frame, text="开始:", style="Small.TLabel").grid(row=0, column=0, sticky=tk.W, pady=1)
        self.start_date_var = tk.StringVar(value="")
        ttk.Entry(time_frame, textvariable=self.start_date_var, width=12, style="Small.TEntry").grid(row=0, column=1, pady=1, padx=2)
        
        ttk.Label(time_frame, text="结束:", style="Small.TLabel").grid(row=1, column=0, sticky=tk.W, pady=1)
        self.end_date_var = tk.StringVar(value="")
        ttk.Entry(time_frame, textvariable=self.end_date_var, width=12, style="Small.TEntry").grid(row=1, column=1, pady=1, padx=2)
        
        # 测点选择区域（更紧凑）
        point_frame = ttk.LabelFrame(control_panel, text="测点选择", padding="3")
        point_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 全选/全不选按钮（更紧凑）
        select_frame = ttk.Frame(point_frame)
        select_frame.pack(fill=tk.X, pady=(0, 2))
        ttk.Button(select_frame, text="全选", command=self.select_all_points, width=8).pack(side=tk.LEFT, padx=1)
        ttk.Button(select_frame, text="全不选", command=self.deselect_all_points, width=8).pack(side=tk.LEFT, padx=1)
        
        # 测点复选框容器（带滚动条）
        canvas_frame = ttk.Frame(point_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Canvas和Scrollbar用于滚动
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.point_checkbox_frame = ttk.Frame(canvas)
        
        self.point_checkbox_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.point_checkbox_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 测点复选框字典
        self.point_vars = {}  # {测点名称: BooleanVar}
        self.point_checkboxes = {}  # {测点名称: Checkbutton}
        
        # 图表属性设置（更紧凑）
        plot_frame = ttk.LabelFrame(control_panel, text="图表属性", padding="3")
        plot_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(plot_frame, text="标题:", style="Small.TLabel").grid(row=0, column=0, sticky=tk.W, pady=1)
        self.title_var = tk.StringVar(value="")
        ttk.Entry(plot_frame, textvariable=self.title_var, width=15, style="Small.TEntry").grid(row=0, column=1, pady=1, padx=2)
        
        ttk.Label(plot_frame, text="X轴:", style="Small.TLabel").grid(row=1, column=0, sticky=tk.W, pady=1)
        self.xlabel_var = tk.StringVar(value="时间（周）")
        ttk.Entry(plot_frame, textvariable=self.xlabel_var, width=15, style="Small.TEntry").grid(row=1, column=1, pady=1, padx=2)
        
        ttk.Label(plot_frame, text="Y轴:", style="Small.TLabel").grid(row=2, column=0, sticky=tk.W, pady=1)
        self.ylabel_var = tk.StringVar(value="")
        ttk.Entry(plot_frame, textvariable=self.ylabel_var, width=15, style="Small.TEntry").grid(row=2, column=1, pady=1, padx=2)
        
        # 绘图选项（更紧凑）
        option_frame = ttk.LabelFrame(control_panel, text="绘图选项", padding="3")
        option_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.show_grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(option_frame, text="显示网格", variable=self.show_grid_var, style="Small.TCheckbutton").pack(anchor=tk.W, pady=1)
        
        self.show_marker_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(option_frame, text="显示标记点", variable=self.show_marker_var, style="Small.TCheckbutton").pack(anchor=tk.W, pady=1)
        
        # 数据预处理选项
        self.subtract_first_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(option_frame, text="减去首值（归一化）", 
                      variable=self.subtract_first_var, style="Small.TCheckbutton").pack(anchor=tk.W, pady=1)
        
        # 倾角方向选择（更紧凑）
        tilt_direction_frame = ttk.Frame(option_frame)
        tilt_direction_frame.pack(fill=tk.X, pady=2)
        ttk.Label(tilt_direction_frame, text="倾角方向:", style="Small.TLabel").pack(side=tk.LEFT, padx=(0, 3))
        self.tilt_direction_var = tk.StringVar(value="X")
        ttk.Radiobutton(tilt_direction_frame, text="X", variable=self.tilt_direction_var, 
                       value="X", style="Small.TRadiobutton").pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(tilt_direction_frame, text="Y", variable=self.tilt_direction_var, 
                       value="Y", style="Small.TRadiobutton").pack(side=tk.LEFT, padx=2)
        
        # 按钮区域（更紧凑，水平排列）
        button_frame = ttk.Frame(control_panel)
        button_frame.pack(fill=tk.X, pady=(0, 0))
        
        ttk.Button(button_frame, text="绘制", command=self.plot_data, width=8).pack(side=tk.LEFT, padx=1, pady=2)
        ttk.Button(button_frame, text="复制", command=self.copy_to_clipboard, width=8).pack(side=tk.LEFT, padx=1, pady=2)
        ttk.Button(button_frame, text="保存", command=self.save_image, width=8).pack(side=tk.LEFT, padx=1, pady=2)
        
        # 右侧图表显示区域（减少padding）
        plot_panel = ttk.LabelFrame(main_frame, text="图表预览", padding="5")
        plot_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        plot_panel.columnconfigure(0, weight=1)
        plot_panel.rowconfigure(0, weight=1)
        
        # 创建matplotlib图形（稍微减小尺寸以适应紧凑布局）
        self.fig = Figure(figsize=(9, 5.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.text(0.5, 0.5, '请选择数据文件开始绘图', 
                    ha='center', va='center', transform=self.ax.transAxes,
                    fontsize=14, color='gray')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        # 创建canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_panel)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 工具栏
        toolbar_frame = ttk.Frame(plot_panel)
        toolbar_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        
    def load_displacement_file(self, filepath):
        """加载位移数据文件"""
        try:
            df = pd.read_csv(filepath, sep='\t', header=None, 
                           usecols=[0, 1],
                           names=['时间', '位移值'], 
                           engine='python', encoding='utf-8',
                           skipinitialspace=True)
            
            df = df.dropna()
            df['时间'] = df['时间'].astype(str).str.strip()
            df['时间'] = pd.to_datetime(df['时间'], format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
            df = df.dropna(subset=['时间'])
            df['位移值'] = pd.to_numeric(df['位移值'], errors='coerce')
            df = df.dropna()
            
            return df
        except Exception as e:
            messagebox.showerror("错误", f"加载位移文件失败: {e}")
            return None
    
    def load_tilt_file(self, filepath):
        """加载倾角数据文件"""
        try:
            df = pd.read_csv(filepath, sep='\t', header=None, 
                           names=['时间', '列1', '倾角X', '倾角Y'], 
                           engine='python', encoding='utf-8')
            
            df['时间'] = pd.to_datetime(df['时间'], format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
            df = df.dropna(subset=['时间'])
            df['倾角X'] = pd.to_numeric(df['倾角X'], errors='coerce')
            df['倾角Y'] = pd.to_numeric(df['倾角Y'], errors='coerce')
            df = df.dropna()
            
            return df
        except Exception as e:
            messagebox.showerror("错误", f"加载倾角文件失败: {e}")
            return None
    
    def aggregate_by_week(self, df, value_columns):
        """按周聚合数据，只返回平均值"""
        if df is None or df.empty:
            return None
        
        df_indexed = df.set_index('时间').copy()
        
        weekly_data = {}
        for col in value_columns:
            if col in df_indexed.columns:
                weekly_data[f'{col}_平均值'] = df_indexed[col].resample('W').mean()
        
        weekly_df = pd.DataFrame(weekly_data)
        weekly_df.index.name = '周'
        
        return weekly_df
    
    def select_file(self):
        """选择单个文件"""
        filepath = filedialog.askopenfilename(
            title="选择数据文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filepath:
            self.load_file(filepath)
    
    def select_files(self):
        """选择多个文件"""
        filepaths = filedialog.askopenfilenames(
            title="选择数据文件（可多选）",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        for filepath in filepaths:
            self.load_file(filepath)
    
    def on_drop(self, event):
        """处理文件拖拽"""
        if HAS_DND:
            files = self.root.tk.splitlist(event.data)
            for filepath in files:
                self.load_file(filepath)
        else:
            self.select_file()
    
    def load_file(self, filepath):
        """加载文件"""
        filepath = Path(filepath)
        point_name = filepath.stem  # 使用文件名（不含扩展名）作为测点名称
        
        # 如果已存在同名测点，添加序号
        if point_name in self.data_dict:
            counter = 1
            while f"{point_name}_{counter}" in self.data_dict:
                counter += 1
            point_name = f"{point_name}_{counter}"
        
        # 根据文件名判断数据类型
        data_type = None
        data = None
        
        if '位移' in filepath.name:
            data_type = 'displacement'
            data = self.load_displacement_file(filepath)
        elif '倾角' in filepath.name:
            data_type = 'tilt'
            data = self.load_tilt_file(filepath)
        else:
            # 尝试自动检测
            data = self.load_displacement_file(filepath)
            if data is not None:
                data_type = 'displacement'
            else:
                data = self.load_tilt_file(filepath)
                if data is not None:
                    data_type = 'tilt'
        
        if data is not None and not data.empty:
            # 检查数据类型一致性（位移和倾角不能混在一起）
            if self.data_type is None:
                self.data_type = data_type
                # 自动设置Y轴标签
                if data_type == 'displacement':
                    if not self.ylabel_var.get():
                        self.ylabel_var.set("位移值 (mm)")
                elif data_type == 'tilt':
                    # 根据选择的方向设置Y轴标签
                    tilt_direction = self.tilt_direction_var.get()
                    if not self.ylabel_var.get():
                        if tilt_direction == 'X':
                            self.ylabel_var.set("倾角X (度)")
                        else:
                            self.ylabel_var.set("倾角Y (度)")
            elif self.data_type != data_type:
                messagebox.showwarning("警告", f"文件 {filepath.name} 的数据类型({data_type})与已加载的测点类型({self.data_type})不一致，已跳过\n注意：位移和倾角数据不能混在一起绘制")
                return
            else:
                # 数据类型一致，如果是倾角，更新Y轴标签
                if data_type == 'tilt':
                    tilt_direction = self.tilt_direction_var.get()
                    current_ylabel = self.ylabel_var.get()
                    if '倾角' in current_ylabel:
                        # 更新Y轴标签以匹配当前选择的方向
                        if tilt_direction == 'X':
                            self.ylabel_var.set("倾角X (度)")
                        else:
                            self.ylabel_var.set("倾角Y (度)")
            
            # 存储数据
            self.data_dict[point_name] = {
                'data': data,
                'type': data_type,
                'filepath': filepath
            }
            
            # 更新界面
            self.update_point_list()
            
            # 自动设置时间范围（使用所有数据的范围）
            all_dates = []
            for point_data in self.data_dict.values():
                all_dates.extend([point_data['data']['时间'].min(), point_data['data']['时间'].max()])
            if all_dates:
                min_date = min(all_dates)
                max_date = max(all_dates)
                if not self.start_date_var.get():
                    self.start_date_var.set(min_date.strftime('%Y-%m-%d'))
                if not self.end_date_var.get():
                    self.end_date_var.set(max_date.strftime('%Y-%m-%d'))
            
            # 自动设置标题
            if not self.title_var.get():
                if len(self.data_dict) == 1:
                    self.title_var.set(f"{point_name} - 周聚合平均值")
                else:
                    self.title_var.set("多测点周聚合平均值对比")
            
            self.file_count_label.config(text=f"已加载: {len(self.data_dict)} 个测点")
        else:
            messagebox.showerror("错误", f"无法加载数据文件: {filepath.name}")
    
    def update_point_list(self):
        """更新测点列表"""
        # 清空现有复选框
        for widget in self.point_checkbox_frame.winfo_children():
            widget.destroy()
        self.point_vars.clear()
        self.point_checkboxes.clear()
        
        # 添加测点复选框
        for point_name in sorted(self.data_dict.keys()):
            # 创建复选框变量（默认选中）
            var = tk.BooleanVar(value=True)
            self.point_vars[point_name] = var
            
            # 创建复选框
            checkbox = ttk.Checkbutton(
                self.point_checkbox_frame, 
                text=point_name[:40] + ('...' if len(point_name) > 40 else ''), 
                variable=var
            )
            checkbox.pack(anchor=tk.W, padx=5, pady=2)
            self.point_checkboxes[point_name] = checkbox
    
    def select_all_points(self):
        """全选所有测点"""
        for var in self.point_vars.values():
            var.set(True)
    
    def deselect_all_points(self):
        """全不选所有测点"""
        for var in self.point_vars.values():
            var.set(False)
    
    def clear_data(self):
        """清空所有数据"""
        self.data_dict.clear()
        self.weekly_data_dict.clear()
        self.data_type = None
        self.file_count_label.config(text="已加载: 0 个测点")
        self.update_point_list()
        self.ax.clear()
        self.ax.text(0.5, 0.5, '请选择数据文件开始绘图', 
                    ha='center', va='center', transform=self.ax.transAxes,
                    fontsize=14, color='gray')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()
    
    def plot_data(self):
        """绘制图表"""
        if not self.data_dict:
            messagebox.showwarning("警告", "请先加载数据文件")
            return
        
        # 获取选中的测点
        selected_points = [name for name, var in self.point_vars.items() if var.get()]
        if not selected_points:
            messagebox.showwarning("警告", "请至少选择一个测点")
            return
        
        # 检查数据类型一致性（确保同一图表只显示一种数据类型）
        selected_types = set()
        for point_name in selected_points:
            if point_name in self.data_dict:
                data_type = self.data_dict[point_name]['type']
                if data_type == 'tilt':
                    # 对于倾角，需要区分X和Y
                    tilt_direction = self.tilt_direction_var.get()
                    selected_types.add(f"tilt_{tilt_direction}")
                else:
                    selected_types.add(data_type)
        
        if len(selected_types) > 1:
            messagebox.showerror("错误", "同一图表中只能显示一种数据类型！\n请确保所有选中的测点都是同一种类型（位移、倾角X或倾角Y）")
            return
        
        # 获取时间段
        start_date = self.start_date_var.get().strip()
        end_date = self.end_date_var.get().strip()
        
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = pd.to_datetime(start_date)
            except:
                messagebox.showwarning("警告", "开始日期格式错误，将使用全部数据")
        if end_date:
            try:
                end_dt = pd.to_datetime(end_date)
            except:
                messagebox.showwarning("警告", "结束日期格式错误，将使用全部数据")
        
        # 处理每个选中的测点
        self.weekly_data_dict.clear()
        color_idx = 0
        
        for point_name in selected_points:
            if point_name not in self.data_dict:
                continue
            
            point_info = self.data_dict[point_name]
            df = point_info['data'].copy()
            data_type = point_info['type']
            
            # 过滤时间段
            if start_dt is not None:
                df = df[df['时间'] >= start_dt]
            if end_dt is not None:
                df = df[df['时间'] <= end_dt]
            
            if df.empty:
                continue
            
            # 按周聚合
            if data_type == 'displacement':
                value_columns = ['位移值']
            elif data_type == 'tilt':
                # 根据用户选择的方向，只聚合对应的列
                tilt_direction = self.tilt_direction_var.get()
                if tilt_direction == 'X':
                    value_columns = ['倾角X']
                else:
                    value_columns = ['倾角Y']
            else:
                continue
            
            weekly_data = self.aggregate_by_week(df, value_columns)
            if weekly_data is not None and not weekly_data.empty:
                # 数据预处理：减去区间内第一个周聚合的首值（如果启用）
                if self.subtract_first_var.get():
                    # 按时间排序，确保首值是第一个周的平均值
                    weekly_data = weekly_data.sort_index()
                    
                    # 根据数据类型处理对应的列
                    if data_type == 'displacement':
                        col_name = '位移值_平均值'
                        if col_name in weekly_data.columns and len(weekly_data) > 0:
                            first_week_value = weekly_data[col_name].iloc[0]
                            weekly_data[col_name] = weekly_data[col_name] - first_week_value
                    elif data_type == 'tilt':
                        tilt_direction = self.tilt_direction_var.get()
                        if tilt_direction == 'X':
                            col_name = '倾角X_平均值'
                            if col_name in weekly_data.columns and len(weekly_data) > 0:
                                first_week_value = weekly_data[col_name].iloc[0]
                                weekly_data[col_name] = weekly_data[col_name] - first_week_value
                        else:  # Y方向
                            col_name = '倾角Y_平均值'
                            if col_name in weekly_data.columns and len(weekly_data) > 0:
                                first_week_value = weekly_data[col_name].iloc[0]
                                weekly_data[col_name] = weekly_data[col_name] - first_week_value
                
                self.weekly_data_dict[point_name] = {
                    'data': weekly_data,
                    'type': data_type,
                    'tilt_direction': tilt_direction if data_type == 'tilt' else None
                }
        
        if not self.weekly_data_dict:
            messagebox.showerror("错误", "选择的时间段内没有数据")
            return
        
        # 绘制图表
        self.ax.clear()
        
        # 获取图表属性
        title = self.title_var.get() or "周聚合平均值"
        xlabel = self.xlabel_var.get() or "时间（周）"
        ylabel = self.ylabel_var.get() or "数值"
        show_grid = self.show_grid_var.get()
        show_marker = self.show_marker_var.get()
        
        # 绘制每个测点的数据
        for point_name, weekly_info in self.weekly_data_dict.items():
            weekly_data = weekly_info['data']
            data_type = weekly_info['type']
            color = self.colors[color_idx % len(self.colors)]
            color_idx += 1
            
            marker = 'o' if show_marker else None
            
            # 从测点名称提取简短标识
            short_name = point_name.split('_')[-1] if '_' in point_name else point_name[:30]
            
            if data_type == 'displacement':
                col_name = '位移值_平均值'
                if col_name in weekly_data.columns:
                    self.ax.plot(weekly_data.index, weekly_data[col_name],
                               marker=marker, linewidth=2, markersize=6, 
                               label=short_name, color=color)
            elif data_type == 'tilt':
                # 根据用户选择的方向绘制
                tilt_direction = weekly_info.get('tilt_direction', 'X')
                if tilt_direction == 'X':
                    col_name = '倾角X_平均值'
                    if col_name in weekly_data.columns:
                        self.ax.plot(weekly_data.index, weekly_data[col_name],
                                   marker=marker, linewidth=2, markersize=6, 
                                   label=short_name, color=color)
                else:  # Y方向
                    col_name = '倾角Y_平均值'
                    if col_name in weekly_data.columns:
                        self.ax.plot(weekly_data.index, weekly_data[col_name],
                                   marker=marker, linewidth=2, markersize=6, 
                                   label=short_name, color=color)
        
        # 设置图表属性
        self.ax.set_title(title, fontsize=14, fontweight='bold')
        self.ax.set_xlabel(xlabel, fontsize=12)
        self.ax.set_ylabel(ylabel, fontsize=12)
        
        if show_grid:
            self.ax.grid(True, alpha=0.3)
        
        # 显示图例
        if len(selected_points) > 0:
            self.ax.legend(fontsize=9, loc='best')
        
        self.ax.tick_params(axis='x', rotation=45)
        
        self.fig.tight_layout()
        self.canvas.draw()
    
    def copy_to_clipboard(self):
        """复制图片到剪贴板"""
        if not self.weekly_data_dict:
            messagebox.showwarning("警告", "请先绘制图表")
            return
        
        try:
            # 将图形保存到内存
            buf = io.BytesIO()
            self.fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            
            # 使用PIL打开图片
            img = Image.open(buf)
            
            # 复制到剪贴板
            if HAS_WIN32:
                # Windows系统使用win32clipboard
                output = io.BytesIO()
                img.convert('RGB').save(output, 'BMP')
                data = output.getvalue()[14:]  # 跳过BMP头
                output.close()
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
                messagebox.showinfo("成功", "图片已复制到剪贴板，可以在Word中直接粘贴（Ctrl+V）")
            elif HAS_PYPERCLIP:
                # 使用pyperclip（需要安装pyperclip和Pillow）
                img.save('temp_clipboard.png')
                # pyperclip需要特殊处理，这里简化处理
                messagebox.showinfo("提示", "请安装pywin32以支持剪贴板功能\n图片已保存为temp_clipboard.png")
            else:
                messagebox.showwarning("警告", "无法复制到剪贴板，请安装pywin32库\n使用命令: pip install pywin32")
        except Exception as e:
            messagebox.showerror("错误", f"复制到剪贴板失败: {e}")
    
    def save_image(self):
        """保存图片"""
        if not self.weekly_data_dict:
            messagebox.showwarning("警告", "请先绘制图表")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="保存图片",
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png"), ("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        
        if filepath:
            try:
                self.fig.savefig(filepath, dpi=300, bbox_inches='tight')
                messagebox.showinfo("成功", f"图片已保存到: {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"保存图片失败: {e}")


def main():
    """主函数 - 独立运行模式"""
    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    app = InteractivePlotter(parent=None, standalone=True)
    root.mainloop()


if __name__ == "__main__":
    main()

