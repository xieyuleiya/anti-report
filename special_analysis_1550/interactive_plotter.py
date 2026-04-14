# -*- coding: utf-8 -*-
"""
交互式绘图器 (interactive_plotter.py)

该模块提供交互式文件选择界面，允许用户：
- 通过文件选择对话框选择测点文件（支持多选）
- 动态添加/删除测点
- 实时预览选中的测点信息
- 生成组合图表

使用说明：
1. 运行 interactive_plotter.py
2. 点击【选择文件】按钮，选择一个或多个测点数据文件（.txt格式）
3. 文件会自动添加到绘图列表
4. 使用复选框选择要绘制的测点
5. 可以随时删除已添加的测点
6. 点击"生成图表"创建组合图表（或文件添加后自动生成）
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
try:
    from .data_loader import DataLoader
    from .utils import log, setup_chinese_fonts
except ImportError:
    from data_loader import DataLoader
    from utils import log, setup_chinese_fonts
import matplotlib
matplotlib.use('TkAgg')  # 使用TkAgg后端以支持在tkinter中显示图表
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


class InteractivePlotter:
    """交互式绘图器主类"""
    
    def __init__(self, parent=None, standalone=True):
        """
        初始化交互式绘图器
        
        Args:
            parent: 父容器（用于嵌入模式），如果提供则嵌入到parent中
            standalone: 是否为独立窗口模式（默认True）
        """
        self.standalone = standalone
        self.parent = parent
        
        if standalone:
            # 独立窗口模式
            self.root = tk.Tk()
            self.root.title("桥梁测点数据交互式绘图器")
            self.root.geometry("1600x700")  # 增加窗口尺寸，确保图表完整显示
            # 固定窗口大小，禁止调整
            self.root.resizable(False, False)
        else:
            # 嵌入模式：使用parent作为容器
            if parent is None:
                raise ValueError("嵌入模式需要提供parent参数")
            self.root = parent
        
        # 图表相关
        self.current_figure = None
        self.canvas = None
        self.toolbar = None
        
        # 数据相关
        self.data_loader = None
        self.data_dir = None
        self.dir_var = tk.StringVar()  # 目录变量（用于内部使用）
        self.uploaded_files = []   # 已上传的文件列表
        self.file_checkboxes = {}  # 文件复选框字典 {file_path: checkbox_var}
        self.file_data = {}        # 文件数据缓存
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重 - 根据图表实际尺寸设置
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=2)  # 左侧控制面板 (增加占比)
        main_frame.columnconfigure(1, weight=3)  # 右侧图表区域 (减少占比)
        main_frame.rowconfigure(0, weight=1)
        
        # 1. 左侧控制面板
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        control_frame.columnconfigure(0, weight=1)
        control_frame.rowconfigure(0, weight=1)  # 文件选择区域
        control_frame.rowconfigure(1, weight=4)  # 已选择文件区域（增加占比）
        control_frame.rowconfigure(2, weight=1)  # 按钮区域
        
        # 文件选择区域
        self.file_select_frame = ttk.LabelFrame(control_frame, text="文件选择", padding="5")
        self.file_select_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 提示文本区域
        info_area = tk.Frame(self.file_select_frame, bg='lightgray', relief=tk.RAISED, bd=2, height=60)
        info_area.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        info_area.grid_propagate(False)
        
        # 提示文本
        info_label = tk.Label(
            info_area, 
            text="点击下方【选择文件】按钮选择测点数据文件\n支持 .txt 文件，可多选", 
            bg='lightgray', 
            font=('Arial', 9), 
            justify=tk.CENTER
        )
        info_label.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        # 文件选择按钮
        dir_button_frame = ttk.Frame(self.file_select_frame)
        dir_button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 主要按钮：选择文件（支持多选）
        ttk.Button(dir_button_frame, text="选择文件", command=self.select_files, width=20).grid(row=0, column=0)
        
        self.file_select_frame.columnconfigure(0, weight=1)
        
        # 2. 右侧图表预览区域（固定尺寸，完全按照图片尺寸）
        chart_frame = ttk.LabelFrame(main_frame, text="图表预览", padding="5")
        chart_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)
        # 设置图表区域固定尺寸，确保完整显示
        chart_frame.configure(width=1250, height=650)  # 增加尺寸，确保图表完整显示
        
        # 创建matplotlib图表区域
        self.create_chart_area(chart_frame)
        
        # 3. 左侧文件管理区域
        file_frame = ttk.LabelFrame(control_frame, text="测点文件管理", padding="5")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        file_frame.columnconfigure(0, weight=1)
        file_frame.rowconfigure(0, weight=1)
        
        # 已上传文件列表（带复选框）
        uploaded_list_frame = ttk.Frame(file_frame)
        uploaded_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 创建Canvas用于滚动
        self.files_canvas = tk.Canvas(uploaded_list_frame, height=300)  # 增加高度，显示更多文件
        self.files_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        uploaded_scrollbar = ttk.Scrollbar(uploaded_list_frame, orient=tk.VERTICAL, command=self.files_canvas.yview)
        uploaded_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.files_canvas.configure(yscrollcommand=uploaded_scrollbar.set)
        
        # 创建Frame用于放置复选框
        self.uploaded_files_frame = tk.Frame(self.files_canvas)
        self.files_canvas.create_window((0, 0), window=self.uploaded_files_frame, anchor="nw")
        
        uploaded_list_frame.columnconfigure(0, weight=1)
        uploaded_list_frame.rowconfigure(0, weight=1)
        
        # 文件操作按钮 - 分为两行
        file_ops_frame = ttk.Frame(file_frame)
        file_ops_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # 第一行：选择操作
        select_frame = ttk.Frame(file_ops_frame)
        select_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 3))
        ttk.Label(select_frame, text="选择操作:", font=("Arial", 9, "bold")).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(select_frame, text="全选", command=self.select_all_files).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(select_frame, text="全不选", command=self.deselect_all_files).grid(row=0, column=2, padx=(0, 5))
        
        # 第二行：删除操作
        delete_frame = ttk.Frame(file_ops_frame)
        delete_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        ttk.Label(delete_frame, text="删除操作:", font=("Arial", 9, "bold")).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(delete_frame, text="删除选中", command=self.remove_selected_files).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(delete_frame, text="清空全部", command=self.clear_selection).grid(row=0, column=2)
        
        # 第三行：状态显示
        status_frame = ttk.Frame(file_ops_frame)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        self.selection_status_label = ttk.Label(status_frame, text="已选择: 0 个文件用于绘图", font=("Arial", 9))
        self.selection_status_label.grid(row=0, column=0)
        
        # 文件信息模块已删除，为左侧功能区腾出更多空间
        
        # 绑定选择事件（现在通过复选框处理）
        
        # 5. 底部操作按钮区域
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Button(button_frame, text="生成图表", command=self.generate_chart).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="保存图表", command=self.save_chart).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(button_frame, text="复制图表", command=self.copy_chart).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(button_frame, text="退出程序", command=self.root.quit).grid(row=0, column=3)
        
        # 6. 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("请点击【选择文件】按钮选择测点数据文件")
        status_bar = ttk.Label(control_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def create_chart_area(self, parent):
        """创建matplotlib图表区域"""
        # 创建matplotlib图形，完全按照参考代码的figsize
        self.current_figure = Figure(figsize=(12, 6), dpi=100)
        
        # 创建画布
        self.canvas = FigureCanvasTkAgg(self.current_figure, parent)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 设置画布固定大小，完全按照参考代码的比例
        # 12英寸 * 100 DPI = 1200像素宽度
        # 6英寸 * 100 DPI = 600像素高度
        # 画布尺寸与图表区域匹配，确保完整显示
        self.canvas.get_tk_widget().configure(width=1200, height=600)  # 恢复完整尺寸，确保图表完整显示
        
        # 创建工具栏容器
        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 创建工具栏
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        
        # 显示初始提示
        self.show_chart_placeholder()
        
    def show_chart_placeholder(self):
        """显示图表占位符"""
        self.current_figure.clear()
        ax = self.current_figure.add_subplot(111)
        ax.text(0.5, 0.5, '请选择文件并点击"生成图表"按钮\n\n支持的功能：\n• 点击【选择文件】按钮选择文件\n• 实时预览图表\n• 缩放、平移、保存、复制', 
                ha='center', va='center', fontsize=14, 
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        self.canvas.draw()
        
    def process_selected_files(self, file_paths):
        """处理选择的文件"""
        print(f"[PROCESS] ========== 开始处理选择的文件 ==========")
        print(f"[PROCESS] 文件数量: {len(file_paths)}")
        print(f"[PROCESS] 文件列表: {file_paths}")
        
        try:
            added_count = 0
            bridge_name = None
            skipped_count = 0
            error_count = 0
            
            for i, file_path in enumerate(file_paths, 1):
                print(f"[PROCESS] 处理文件 {i}/{len(file_paths)}: {file_path}")
                
                if not os.path.exists(file_path):
                    print(f"[PROCESS]   ✗ 文件不存在，跳过")
                    skipped_count += 1
                    continue
                
                # 检查文件是否已经添加
                if file_path in self.uploaded_files:
                    print(f"[PROCESS]   ⚠ 文件已添加，跳过")
                    skipped_count += 1
                    continue
                
                # 创建临时的DataLoader来解析文件信息
                if not self.data_loader:
                    print(f"[PROCESS]   创建 DataLoader...")
                    # 从文件路径推断数据目录
                    parent_dir = os.path.dirname(file_path)
                    print(f"[PROCESS]   文件所在目录: {parent_dir}")
                    
                    # 尝试查找包含特定桥梁名称的目录
                    search_dirs = ['云茂', '广佛肇']
                    found_dir = None
                    original_parent = parent_dir
                    
                    while parent_dir and parent_dir != os.path.dirname(parent_dir):
                        print(f"[PROCESS]   检查目录: {parent_dir}")
                        for d in search_dirs:
                            check_path = os.path.join(parent_dir, d)
                            if os.path.exists(check_path):
                                found_dir = parent_dir
                                print(f"[PROCESS]   ✓ 找到桥梁目录: {check_path}")
                                break
                        if found_dir:
                            break
                        parent_dir = os.path.dirname(parent_dir)
                    
                    if found_dir:
                        try:
                            self.data_loader = DataLoader(found_dir)
                            self.data_dir = found_dir
                            self.dir_var.set(found_dir)
                            print(f"[PROCESS]   ✓ DataLoader 创建成功: {found_dir}")
                        except Exception as e:
                            print(f"[PROCESS]   ✗ DataLoader 创建失败: {e}")
                            # 如果失败，使用文件所在目录
                            self.data_loader = DataLoader(original_parent)
                            self.data_dir = original_parent
                            self.dir_var.set(original_parent)
                            print(f"[PROCESS]   使用文件所在目录: {original_parent}")
                    else:
                        # 如果无法推断，使用文件所在目录
                        print(f"[PROCESS]   未找到桥梁目录，使用文件所在目录: {original_parent}")
                        try:
                            self.data_loader = DataLoader(original_parent)
                            self.data_dir = original_parent
                            self.dir_var.set(original_parent)
                            print(f"[PROCESS]   ✓ DataLoader 创建成功: {original_parent}")
                        except Exception as e:
                            print(f"[PROCESS]   ✗ DataLoader 创建失败: {e}")
                            print(f"[PROCESS]   ⚠ 继续处理文件，但不解析文件信息")
                            # 不跳过文件，即使DataLoader创建失败也继续处理
                            # error_count += 1
                            # continue
                
                # 获取文件信息
                file_info = None
                if self.data_loader:
                    print(f"[PROCESS]   获取文件信息...")
                    try:
                        file_info = self.data_loader.get_file_info(file_path)
                        print(f"[PROCESS]   文件信息: {file_info}")
                    except Exception as e:
                        print(f"[PROCESS]   ✗ 获取文件信息失败: {e}")
                        file_info = None
                else:
                    print(f"[PROCESS]   ⚠ DataLoader 未初始化，跳过文件信息解析")
                
                if file_info:
                    pier_number = file_info.get('pier_number', '未知')
                    current_bridge = file_info.get('bridge_name', '未知')
                    status = file_info.get('status', '')
                    
                    print(f"[PROCESS]   墩号: {pier_number}, 桥梁: {current_bridge}, 状态: {status}")
                    
                    # 检查桥梁一致性
                    if bridge_name is None:
                        bridge_name = current_bridge
                    elif bridge_name != current_bridge and current_bridge != '未知':
                        print(f"[PROCESS]   ⚠ 桥梁不一致: {bridge_name} vs {current_bridge}")
                        messagebox.showwarning("警告", f"所选文件来自不同桥梁：{bridge_name} 和 {current_bridge}\n请选择同一桥梁的文件")
                        return
                    
                    display_name = f"{pier_number} - {os.path.basename(file_path)}"
                    if status:
                        display_name += f" ({status})"
                    
                    print(f"[PROCESS]   显示名称: {display_name}")
                else:
                    print(f"[PROCESS]   ⚠ 无法解析文件信息，使用默认名称")
                    display_name = os.path.basename(file_path)
                
                # 添加到上传文件列表
                print(f"[PROCESS]   添加到文件列表...")
                try:
                    self.add_file_to_list(file_path)
                    added_count += 1
                    print(f"[PROCESS]   ✓ 文件添加成功")
                except Exception as e:
                    print(f"[PROCESS]   ✗ 文件添加失败: {e}")
                    import traceback
                    traceback.print_exc()
                    error_count += 1
            
            print(f"[PROCESS] ========== 处理完成 ==========")
            print(f"[PROCESS] 成功: {added_count}, 跳过: {skipped_count}, 错误: {error_count}")
            
            if added_count > 0:
                status_msg = f"已添加 {added_count} 个文件，共 {len(self.uploaded_files)} 个文件"
                if bridge_name and bridge_name != '未知':
                    status_msg += f" (桥梁: {bridge_name})"
                if hasattr(self, 'status_var'):
                    self.status_var.set(status_msg)
                print(f"[PROCESS] ✓ {status_msg}")
            else:
                if skipped_count > 0:
                    msg = f"所选文件已全部添加或无效\n\n跳过: {skipped_count} 个文件"
                    if error_count > 0:
                        msg += f"\n错误: {error_count} 个文件"
                    messagebox.showinfo("提示", msg)
                else:
                    messagebox.showwarning("警告", f"没有成功添加任何文件\n\n请检查文件格式和路径\n\n错误: {error_count} 个文件")
                print(f"[PROCESS] ⚠ 没有添加任何文件")
                
        except Exception as e:
            print(f"[PROCESS] ========== 处理异常 ==========")
            print(f"[PROCESS] 异常类型: {type(e).__name__}")
            print(f"[PROCESS] 异常信息: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("错误", f"处理选择的文件时出错: {str(e)}\n\n请查看控制台获取详细信息")
            if hasattr(self, 'status_var'):
                self.status_var.set("处理文件失败")
            
    def select_files(self):
        """选择文件（支持多选）"""
        files = filedialog.askopenfilenames(
            title="选择测点数据文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialdir=self.data_dir if self.data_dir else None
        )
        print(f"[SELECT] 文件选择对话框返回: {files}")
        print(f"[SELECT] 文件数量: {len(files)}")
        
        if files:
            # 过滤 .txt 文件（更宽松的检查）
            txt_files = []
            for f in files:
                f_lower = f.lower()
                # 检查多种可能的txt扩展名格式
                if f_lower.endswith('.txt') or f_lower.endswith('.txt '):
                    txt_files.append(f)
                    print(f"[SELECT] ✓ 识别为txt文件: {f}")
                else:
                    print(f"[SELECT] ✗ 不是txt文件: {f} (扩展名: {os.path.splitext(f)[1]})")
            
            print(f"[SELECT] 识别到的txt文件数量: {len(txt_files)}")
            
            if txt_files:
                # 直接处理文件，不依赖DataLoader
                self.process_selected_files(txt_files)
            else:
                # 即使不是.txt，也尝试处理（可能是文件选择器的问题）
                print(f"[SELECT] 警告: 没有识别到.txt文件，但尝试处理所有文件")
                messagebox.showwarning("警告", f"选择的文件可能不是 .txt 格式\n\n已选择的文件:\n{chr(10).join([os.path.basename(f) for f in files[:3]])}\n\n将尝试处理这些文件")
                self.process_selected_files(list(files))
    
    def add_file_to_list(self, file_path):
        """添加文件到上传列表并创建复选框"""
        print(f"[ADD] 添加文件到列表: {file_path}")
        try:
            if file_path not in self.uploaded_files:
                self.uploaded_files.append(file_path)
                print(f"[ADD] ✓ 文件已添加到列表")
                
                # 创建复选框变量
                checkbox_var = tk.BooleanVar(value=True)  # 默认选中
                self.file_checkboxes[file_path] = checkbox_var
                print(f"[ADD] ✓ 复选框变量已创建")
                
                # 绑定复选框变化事件
                try:
                    checkbox_var.trace('w', lambda *args, path=file_path: self.on_checkbox_change(path))
                    print(f"[ADD] ✓ 复选框事件已绑定")
                except Exception as e:
                    print(f"[ADD] ⚠ 复选框事件绑定失败: {e}")
                
                # 更新文件列表显示
                try:
                    if hasattr(self, 'uploaded_files_frame'):
                        self.update_files_display()
                        print(f"[ADD] ✓ 文件列表显示已更新")
                    else:
                        print(f"[ADD] ⚠ uploaded_files_frame 尚未初始化，跳过显示更新")
                except Exception as e:
                    print(f"[ADD] ✗ 文件列表显示更新失败: {e}")
                    import traceback
                    traceback.print_exc()
                
                # 自动生成图表（不阻塞，即使失败也不影响文件添加）
                try:
                    if hasattr(self, 'current_figure') and self.current_figure:
                        self.generate_chart()
                        print(f"[ADD] ✓ 图表已生成")
                    else:
                        print(f"[ADD] ⚠ 图表区域尚未初始化，跳过图表生成")
                except Exception as e:
                    print(f"[ADD] ⚠ 图表生成失败: {e}")
                    # 不抛出异常，文件已经添加成功
            else:
                print(f"[ADD] ⚠ 文件已在列表中，跳过")
        except Exception as e:
            print(f"[ADD] ✗ 添加文件时发生异常: {e}")
            import traceback
            traceback.print_exc()
            raise  # 重新抛出异常，让调用者知道失败
    
    def update_files_display(self):
        """更新文件列表显示"""
        # 清除现有内容
        for widget in self.uploaded_files_frame.winfo_children():
            widget.destroy()
        
        # 重新创建文件项
        for i, file_path in enumerate(self.uploaded_files):
            try:
                # 创建每个文件项的容器
                file_item_frame = tk.Frame(self.uploaded_files_frame, relief="solid", bd=1)
                file_item_frame.grid(row=i, column=0, sticky=(tk.W, tk.E), padx=2, pady=1)
                
                # 获取文件名和测点信息
                filename = os.path.basename(file_path)
                display_name = filename  # 默认使用文件名
                
                if self.data_loader:
                    try:
                        sensor_id = self.data_loader.extract_sensor_id(filename)
                        if sensor_id:
                            display_name = f"{sensor_id} - {filename}"
                    except Exception as e:
                        print(f"[UPDATE] 提取传感器ID失败: {e}，使用默认名称")
                        display_name = filename
                else:
                    display_name = filename
                
                # 创建复选框
                checkbox = tk.Checkbutton(
                    file_item_frame,
                    text=display_name,
                    variable=self.file_checkboxes[file_path],
                    command=lambda path=file_path: self.on_checkbox_change(path),
                    anchor="w"
                )
                checkbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
                
                # 添加删除按钮
                delete_btn = tk.Button(
                    file_item_frame,
                    text="删除",
                    command=lambda path=file_path: self.remove_file(path),
                    width=6,
                    height=1,
                    bg="#ff6b6b",
                    fg="white",
                    font=("Arial", 8)
                )
                delete_btn.pack(side=tk.RIGHT, padx=5, pady=2)
            except Exception as e:
                print(f"[UPDATE] 创建文件项失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 更新Canvas滚动区域
        self.uploaded_files_frame.update_idletasks()
        self.files_canvas.configure(scrollregion=self.files_canvas.bbox("all"))
    
    def on_checkbox_change(self, file_path):
        """处理复选框状态变化"""
        # 更新选择状态显示
        self.update_selection_status()
        # 自动重新生成图表
        self.generate_chart()
    
    def update_selection_status(self):
        """更新选择状态显示"""
        selected_count = sum(1 for var in self.file_checkboxes.values() if var.get())
        total_count = len(self.uploaded_files)
        self.selection_status_label.config(text=f"已选择: {selected_count}/{total_count} 个文件用于绘图")
    
    def remove_file(self, file_path):
        """删除单个文件"""
        if file_path in self.uploaded_files:
            self.uploaded_files.remove(file_path)
            if file_path in self.file_checkboxes:
                del self.file_checkboxes[file_path]
            if file_path in self.file_data:
                del self.file_data[file_path]
            self.update_files_display()
            self.update_selection_status()
            self.generate_chart()
    
    def select_all_files(self):
        """全选所有文件"""
        for checkbox_var in self.file_checkboxes.values():
            checkbox_var.set(True)
        self.update_selection_status()
        self.generate_chart()
        
    def deselect_all_files(self):
        """全不选所有文件"""
        for checkbox_var in self.file_checkboxes.values():
            checkbox_var.set(False)
        self.update_selection_status()
        self.generate_chart()
            
    def remove_selected_files(self):
        """删除选中的文件（基于复选框状态）"""
        # 获取选中的文件
        selected_files = [path for path, var in self.file_checkboxes.items() if var.get()]
        
        if not selected_files:
            messagebox.showinfo("提示", "请先勾选要删除的文件")
            return
        
        # 确认删除
        if messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selected_files)} 个文件吗？\n\n注意：删除后这些文件将不再显示在列表中，也无法用于绘图。"):
            for file_path in selected_files:
                self.remove_file(file_path)
            
            self.status_var.set(f"已删除选中文件，剩余 {len(self.uploaded_files)} 个文件")
        
    def clear_selection(self):
        """清空所有选择"""
        if self.uploaded_files and messagebox.askyesno("确认清空", "确定要清空所有文件吗？\n\n注意：清空后所有文件都将从列表中移除，无法恢复。"):
            self.uploaded_files = []
            self.file_checkboxes = {}
            self.file_data = {}
            self.update_files_display()
            self.update_selection_status()
            # 文件信息模块已删除
            self.status_var.set("已清空所有选择")
            # 显示空图表
            self.display_chart_in_interface("", {})
        
    def generate_chart(self):
        """生成图表并在界面中显示"""
        # 获取选中的文件
        selected_files = [path for path, var in self.file_checkboxes.items() if var.get()]
        
        if not selected_files:
            # 如果没有选中的文件，显示空图表
            self.display_chart_in_interface("", {})
            return
            
        try:
            self.status_var.set("正在加载数据...")
            self.root.update()
            
            # 准备数据
            critical_sensors_data = {}
            bridge_name = None
            
            for file_path in selected_files:
                # 获取文件信息
                if self.data_loader:
                    file_info = self.data_loader.get_file_info(file_path)
                    if file_info:
                        current_bridge = file_info.get('bridge_name', '未知')
                    else:
                        current_bridge = '未知'
                else:
                    current_bridge = '未知'
                
                # 确保所有文件来自同一桥梁
                if bridge_name is None:
                    bridge_name = current_bridge
                elif bridge_name != current_bridge and current_bridge != '未知':
                    messagebox.showwarning("警告", f"所选文件来自不同桥梁：{bridge_name} 和 {current_bridge}\n请选择同一桥梁的文件")
                    return
                
                # 加载文件数据
                self.status_var.set(f"正在加载文件: {os.path.basename(file_path)}")
                self.root.update()
                
                if self.data_loader:
                    df = self.data_loader.load_single_file(file_path, bridge_name)
                    if df is not None:
                        # 提取墩号作为传感器ID
                        sensor_id = self.data_loader.extract_sensor_id(file_path)
                        critical_sensors_data[sensor_id] = {
                            'timestamp': df['timestamp'],
                            'horizontal_angle': df['horizontal_angle'],
                            'vertical_angle': df['vertical_angle']
                        }
                    else:
                        log(f"文件 {file_path} 数据加载失败", 'warn')
            
            if not critical_sensors_data:
                messagebox.showerror("错误", "没有成功加载任何数据文件")
                self.status_var.set("数据加载失败")
                return
                
            self.status_var.set("正在生成图表...")
            self.root.update()
            
            # 在界面中显示图表
            self.display_chart_in_interface(bridge_name, critical_sensors_data)
            
            self.status_var.set(f"图表已生成 (桥梁: {bridge_name}, 测点数: {len(critical_sensors_data)})")
                
        except Exception as e:
            messagebox.showerror("错误", f"生成图表时出错: {str(e)}")
            self.status_var.set("生成图表失败")
            log(f"生成图表错误: {e}", 'error')
            
    def display_chart_in_interface(self, bridge_name, critical_sensors_data):
        """在界面中显示图表"""
        try:
            # 设置中文字体
            setup_chinese_fonts()
            
            # 清除当前图表
            self.current_figure.clear()
            
            # 完全按照参考代码的方式创建图表
            # 使用与参考代码完全相同的figsize
            self.current_figure.set_size_inches(12, 6)
            
            # 创建子图，完全按照参考代码的格式
            ax1 = self.current_figure.add_subplot(211)
            ax2 = self.current_figure.add_subplot(212)
            
            # 绘制图表，完全按照参考代码的格式
            for sensor_id, sensor_data in critical_sensors_data.items():
                if sensor_data is not None:
                    timestamps = sensor_data['timestamp']
                    horizontal_angle = sensor_data['horizontal_angle']
                    vertical_angle = sensor_data['vertical_angle']
                    
                    # 归一化处理
                    h_angle = np.array(horizontal_angle) - horizontal_angle.iloc[0]
                    v_angle = np.array(vertical_angle) - vertical_angle.iloc[0]
                    
                    # 严格按照参考代码，使用默认线条粗细
                    ax1.plot(timestamps, h_angle, label=sensor_id)
                    ax2.plot(timestamps, v_angle, label=sensor_id)
            
            # 设置图表属性，完全按照参考代码的格式
            ax1.set_title('横向倾角')
            ax1.set_ylabel('倾角(°)')
            ax1.grid(True)
            ax1.legend()
            
            ax2.set_title('纵向倾角')
            ax2.set_xlabel('时间')
            ax2.set_ylabel('倾角(°)')
            ax2.grid(True)
            ax2.legend()
            
            # 智能分配X轴标签间距，避免重叠（保持原始字体大小）
            for ax in [ax1, ax2]:
                # 获取当前标签
                labels = ax.get_xticklabels()
                if len(labels) > 1:
                    # 计算标签数量，智能调整显示间隔
                    total_labels = len(labels)
                    if total_labels > 20:
                        # 如果标签太多，只显示部分标签
                        step = max(1, total_labels // 15)
                        for i, label in enumerate(labels):
                            if i % step != 0:
                                label.set_visible(False)
                    elif total_labels > 10:
                        # 中等数量标签，适当减少显示
                        step = max(1, total_labels // 10)
                        for i, label in enumerate(labels):
                            if i % step != 0:
                                label.set_visible(False)
                
                # 保持原始字体大小，不修改labelsize
            
            # 调整布局，完全按照参考代码的格式
            self.current_figure.tight_layout()
            
            # 刷新画布
            self.canvas.draw()
            
        except Exception as e:
            log(f"显示图表错误: {e}", 'error')
            messagebox.showerror("错误", f"显示图表时出错: {str(e)}")
            
    def save_chart(self):
        """保存图表到文件"""
        if self.current_figure is None or not self.uploaded_files:
            messagebox.showwarning("警告", "请先生成图表")
            return
            
        try:
            # 选择保存路径
            bridge_name = "桥梁"
            if self.uploaded_files and self.data_loader:
                file_info = self.data_loader.get_file_info(self.uploaded_files[0])
                if file_info:
                    bridge_name = file_info.get('bridge_name', '桥梁')
            
            output_path = filedialog.asksaveasfilename(
                title="保存图表",
                defaultextension=".png",
                filetypes=[("PNG图片", "*.png"), ("PDF文件", "*.pdf"), ("SVG文件", "*.svg"), ("所有文件", "*.*")],
                initialfile=f"{bridge_name}_自定义测点组合图.png"
            )
            
            if output_path:
                self.current_figure.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
                self.status_var.set(f"图表已保存到: {output_path}")
                messagebox.showinfo("成功", f"图表已保存到:\n{output_path}")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存图表时出错: {str(e)}")
            log(f"保存图表错误: {e}", 'error')
            
    def copy_chart(self):
        """复制图表到剪贴板"""
        if self.current_figure is None or not self.uploaded_files:
            messagebox.showwarning("警告", "请先生成图表")
            return
            
        try:
            # 将图表保存到内存缓冲区
            import io
            buf = io.BytesIO()
            self.current_figure.savefig(buf, format='png', dpi=300, bbox_inches='tight', 
                                      facecolor='white', edgecolor='none')
            buf.seek(0)
            
            # 使用PIL处理图像并复制到剪贴板
            try:
                from PIL import Image
                import win32clipboard
                
                # 打开图像
                image = Image.open(buf)
                
                # 将图像转换为RGB模式（如果需要）
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # 将图像保存到内存
                output = io.BytesIO()
                image.save(output, 'BMP')
                data = output.getvalue()[14:]  # 去掉BMP文件头
                output.close()
                
                # 复制到剪贴板
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
                
                self.status_var.set("图表已复制到剪贴板")
                messagebox.showinfo("成功", "图表已复制到剪贴板，可以在Word等应用程序中粘贴")
                
            except ImportError:
                # 如果没有win32clipboard，尝试使用tkinter的剪贴板
                try:
                    from PIL import Image
                    image = Image.open(buf)
                    
                    # 将图像转换为tkinter可用的格式
                    import tkinter as tk
                    from PIL import ImageTk
                    
                    # 创建tkinter图像
                    photo = ImageTk.PhotoImage(image)
                    
                    # 复制到剪贴板
                    self.root.clipboard_clear()
                    self.root.clipboard_append("图表已复制到剪贴板")
                    
                    self.status_var.set("图表已复制到剪贴板（文本格式）")
                    messagebox.showinfo("成功", "图表已复制到剪贴板（文本格式），建议使用保存功能")
                    
                except Exception as e:
                    self.status_var.set("复制失败，请使用保存功能")
                    messagebox.showwarning("警告", f"复制失败: {str(e)}\n请使用保存功能保存图表")
            
        except Exception as e:
            messagebox.showerror("错误", f"复制图表时出错: {str(e)}")
            log(f"复制图表错误: {e}", 'error')
            
    def run(self):
        """运行程序"""
        if self.standalone:
            self.root.mainloop()
        # 嵌入模式下不需要调用mainloop，由父窗口管理


def main():
    """主函数"""
    try:
        app = InteractivePlotter()
        app.run()
    except Exception as e:
        log(f"程序运行出错: {e}", 'error')
        messagebox.showerror("错误", f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()
