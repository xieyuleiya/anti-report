"""
振动信号分析交互式UI
支持时程曲线/频谱图分离绘制、通道自动识别、复制到Word
"""

import json
import os
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import io
from PIL import Image

# 不在此强制全局英文字体，由 vibration_analyzer 按元素分别指定宋体 / Times New Roman
plt.rcParams['axes.unicode_minus'] = False

# 尝试导入剪贴板相关库
try:
    import win32clipboard
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# 导入振动分析核心模块
from vibration_analyzer import (
    load_vibration_data, process_vibration_data,
    compute_cross_correlation, compute_spectrum, find_spectrum_peaks,
    plot_time_curve, plot_spectrum,     analyze_vibration
)

# 界面默认数据目录（与脚本同目录下的配置文件）
GUI_CONFIG_FILENAME = "vibration_gui_defaults.json"


class VibrationAnalyzerUI:

    def __init__(self, parent=None, standalone=True):
        if standalone or parent is None:
            self.root = tk.Tk()
            self.root.title("振动信号分析")
            self.root.geometry("1300x720")
            self.parent = self.root
            self.standalone = True
        else:
            self.root = parent.winfo_toplevel() if hasattr(parent, 'winfo_toplevel') else parent
            self.parent = parent
            self.standalone = False

        # 分析结果存储
        self.current_result = None
        self.figure_objects = []
        self._columns = []          # 当前文件的通道列表（含标签）
        self.default_dir_var = tk.StringVar(value="")

        self.create_widgets()
        self._load_gui_config()
        # 注册 trace
        self.plot_type_var.trace_add('write', self._on_plot_type_trace)

    # ── 界面构建 ────────────────────────────────────────────────────────────

    def create_widgets(self):
        main_frame = ttk.Frame(self.parent, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.pack_propagate(False)

        if hasattr(self.parent, 'columnconfigure'):
            self.parent.columnconfigure(0, weight=1)
            self.parent.rowconfigure(0, weight=1)

        # 左侧控制面板：固定宽度 280px
        control_panel = ttk.LabelFrame(main_frame, text="参数", padding="10", width=280)
        control_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        control_panel.pack_propagate(False)
        control_panel.columnconfigure(0, weight=1)

        self.create_control_panel(control_panel)

        # 右侧绘图面板：填满剩余空间（16:9）
        plot_panel = ttk.LabelFrame(main_frame, text="图形显示", padding="5")
        plot_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        plot_panel.columnconfigure(0, weight=1)
        plot_panel.rowconfigure(0, weight=1)

        self.create_plot_panel(plot_panel)

    def create_control_panel(self, parent):
        """控制面板"""
        # ── 文件选择 ───────────────────────────────────────────────────────
        file_frame = ttk.LabelFrame(parent, text="数据文件", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        default_dir_row = ttk.Frame(file_frame)
        default_dir_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(default_dir_row, text="默认目录：").pack(side=tk.LEFT)
        self._default_dir_entry = ttk.Entry(
            default_dir_row, textvariable=self.default_dir_var, width=18)
        self._default_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        self._default_dir_entry.bind('<FocusOut>', lambda _e: self._on_default_dir_focus_out())
        ttk.Button(default_dir_row, text="选择目录", width=8,
                   command=self.select_default_dir).pack(side=tk.RIGHT)

        path_row = ttk.Frame(file_frame)
        path_row.pack(fill=tk.X)
        self.filepath_var = tk.StringVar(value="")
        fp_entry = ttk.Entry(path_row, textvariable=self.filepath_var, width=25)
        fp_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(path_row, text="浏览…", command=self.select_file,
                   width=8).pack(side=tk.RIGHT)

        # ── 通道选择 ───────────────────────────────────────────────────────
        channel_frame = ttk.LabelFrame(parent, text="通道选择", padding="5")
        channel_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(channel_frame, text="数据通道：").grid(
            row=0, column=0, sticky=tk.W, pady=2)
        self.channel_var = tk.StringVar(value="")
        self.channel_combo = ttk.Combobox(
            channel_frame, textvariable=self.channel_var,
            state='readonly', width=22
        )
        self.channel_combo.grid(row=0, column=1, pady=2, padx=5, sticky=tk.W)
        ttk.Label(channel_frame, text="（从文件头读取）",
                  font=("SimSun", 8)).grid(
                      row=0, column=2, sticky=tk.W, padx=2)

        ttk.Label(channel_frame, text="参考通道：").grid(
            row=1, column=0, sticky=tk.W, pady=2)
        self.ref_channel_var = tk.StringVar(value="0")
        tk.Spinbox(channel_frame, from_=0, to=99, increment=1, width=8,
                   textvariable=self.ref_channel_var,
                   justify=tk.CENTER).grid(row=1, column=1, pady=2, padx=5, sticky=tk.W)
        ttk.Label(channel_frame, text="（0 表示无，用于互相关）",
                  font=("SimSun", 8)).grid(
                      row=1, column=2, sticky=tk.W, padx=2)

        # ── 分析参数 ───────────────────────────────────────────────────────
        param_frame = ttk.LabelFrame(parent, text="分析参数", padding="5")
        param_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(param_frame, text="采样频率 (Hz)：").grid(
            row=0, column=0, sticky=tk.W, pady=2)
        self.fs_var = tk.StringVar(value="50")
        tk.Spinbox(param_frame, from_=1, to=2000, increment=1, width=8,
                   textvariable=self.fs_var, justify=tk.CENTER
                   ).grid(row=0, column=1, pady=2, padx=5, sticky=tk.W)

        ttk.Label(param_frame, text="高通截止 (Hz)：").grid(
            row=1, column=0, sticky=tk.W, pady=2)
        self.cutoff_var = tk.StringVar(value="0.05")
        tk.Spinbox(param_frame, from_=0.001, to=10.0, increment=0.01, width=10,
                   textvariable=self.cutoff_var, justify=tk.CENTER
                   ).grid(row=1, column=1, pady=2, padx=5, sticky=tk.W)

        ttk.Label(param_frame, text="频谱横轴上限 (Hz)：").grid(
            row=2, column=0, sticky=tk.W, pady=2)
        self.xlim_var = tk.StringVar(value="3.0")
        tk.Spinbox(param_frame, from_=0.1, to=25.0, increment=0.1, width=10,
                   textvariable=self.xlim_var, justify=tk.CENTER
                   ).grid(row=2, column=1, pady=2, padx=5, sticky=tk.W)

        # ── 绘图类型 ───────────────────────────────────────────────────────
        plot_type_frame = ttk.LabelFrame(parent, text="绘图类型", padding="5")
        plot_type_frame.pack(fill=tk.X, pady=(0, 10))

        self.plot_type_var = tk.StringVar(value="spectrum")
        ttk.Radiobutton(plot_type_frame, text="时程曲线",
                        variable=self.plot_type_var, value="time"
                        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(plot_type_frame, text="频谱",
                        variable=self.plot_type_var, value="spectrum"
                        ).pack(anchor=tk.W, pady=2)

        # ── 操作按钮 ───────────────────────────────────────────────────────
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(button_frame, text="分析",
                   command=self.analyze, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="新窗口",
                   command=self.plot_in_new_window, width=12).pack(side=tk.LEFT, padx=2)

        # ── 导出 ───────────────────────────────────────────────────────────
        copy_frame = ttk.LabelFrame(parent, text="导出", padding="5")
        copy_frame.pack(fill=tk.X, pady=(0, 0))

        ttk.Button(copy_frame, text="复制到剪贴板",
                   command=self.copy_to_clipboard, width=15).pack(pady=2)
        ttk.Button(copy_frame, text="保存图像",
                   command=self.save_image, width=15).pack(pady=2)

    def create_plot_panel(self, parent):
        """绘图面板（16:9，随面板自动扩展）"""
        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self._reset_axes_placeholder()

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

    # ── 文件选择 & 通道解析 ───────────────────────────────────────────────────

    def _gui_config_path(self):
        return Path(__file__).resolve().parent / GUI_CONFIG_FILENAME

    def _load_gui_config(self):
        p = self._gui_config_path()
        if not p.is_file():
            return
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            dd = (data.get('default_dir') or '').strip()
            if dd and os.path.isdir(dd):
                self.default_dir_var.set(dd)
        except Exception:
            pass

    def _save_gui_config(self):
        try:
            with open(self._gui_config_path(), 'w', encoding='utf-8') as f:
                json.dump(
                    {'default_dir': (self.default_dir_var.get() or '').strip()},
                    f, ensure_ascii=False, indent=2,
                )
        except Exception:
            pass

    def _on_default_dir_focus_out(self):
        p = (self.default_dir_var.get() or '').strip()
        if p and os.path.isdir(p):
            self._save_gui_config()

    def select_default_dir(self):
        init = (self.default_dir_var.get() or '').strip()
        if not init or not os.path.isdir(init):
            init = os.path.expanduser('~')
        if not os.path.isdir(init):
            init = None
        d = filedialog.askdirectory(
            parent=self.root,
            title="选择默认数据目录",
            initialdir=init,
        )
        if d:
            self.default_dir_var.set(d)
            self._save_gui_config()

    def select_file(self):
        init_dir = (self.default_dir_var.get() or '').strip()
        if not init_dir or not os.path.isdir(init_dir):
            init_dir = None
        filepath = filedialog.askopenfilename(
            parent=self.root,
            title="选择振动数据文件",
            initialdir=init_dir,
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filepath:
            self.filepath_var.set(filepath)
            self._load_channel_list(filepath)

    def _load_channel_list(self, filepath):
        """读取文件列头，填充通道下拉列表"""
        try:
            from vibration_analyzer import load_vibration_data
            result = load_vibration_data(filepath)
            columns = result.get('columns', [])
            if len(columns) <= 1:
                messagebox.showwarning("提示", "文件中未找到数据列。")
                return
            data_cols = columns[1:]          # 去掉时间列
            # 清理标签
            labels = []
            for name in data_cols:
                idx = name.find('【')
                labels.append(name[:idx] if idx != -1 else name)
            self._columns = labels
            self.channel_combo['values'] = labels
            if labels:
                self.channel_var.set(labels[0])   # 默认选第1个
        except Exception as e:
            messagebox.showerror("错误", f"读取文件列头失败：\n{e}")

    # ── 分析 & 绘图 ──────────────────────────────────────────────────────────

    def _on_plot_type_trace(self, *_):
        if self.current_result is not None:
            self.root.after_idle(self.update_plot)

    def _parse_positive_int(self, s, name, default=None, allow_zero=False):
        s = (s or "").strip()
        if not s and default is not None:
            return default
        try:
            v = int(float(s))
        except ValueError:
            raise ValueError(f"{name}须为整数，当前为：{s!r}")
        lo = 0 if allow_zero else 1
        if v < lo:
            raise ValueError(f"{name}须不小于 {lo}")
        return v

    def _parse_float(self, s, name):
        s = (s or "").strip()
        try:
            return float(s)
        except ValueError:
            raise ValueError(f"{name}须为数字，当前为：{s!r}")

    def analyze(self):
        filepath = (self.filepath_var.get() or "").strip()
        if not filepath or not os.path.isfile(filepath):
            messagebox.showwarning("提示", "请选择有效的数据文件。")
            return

        channel_name = (self.channel_var.get() or "").strip()
        if not channel_name:
            messagebox.showwarning("提示", "请选择数据通道。")
            return
        # 从列名反查索引（从1开始）
        if channel_name not in self._columns:
            messagebox.showwarning("提示", f"未找到通道「{channel_name}」。")
            return
        channel_index = self._columns.index(channel_name) + 1

        try:
            ref_channel = self._parse_positive_int(
                self.ref_channel_var.get(), "参考通道",
                default=0, allow_zero=True
            )
            fs = self._parse_positive_int(self.fs_var.get(), "采样频率")
            cutoff = self._parse_float(self.cutoff_var.get(), "高通截止频率")
            if not (0 < cutoff < fs / 2):
                raise ValueError(f"高通截止频率须在 (0, {fs/2}) Hz 内。")

            ref_arg = None if ref_channel == 0 else ref_channel
            self.current_result = analyze_vibration(
                filepath, channel_index,
                reference_channel=ref_arg,
                fs=fs, highpass_cutoff=cutoff
            )

            self.update_plot()
            pf = self.current_result['peaks_f']
            er = self.current_result['energy_ratio']
            date_str = self.current_result.get('analyze_date', '')
            msg = f"分析完成（通道：{channel_name}）"
            if date_str:
                msg += f"\n数据日期：{date_str}"
            msg += f"\n峰值频率：{pf}\n能量占比：{er:.4f}"
            messagebox.showinfo("完成", msg)

        except Exception as e:
            messagebox.showerror("错误", f"分析失败：\n{e}")
            import traceback
            traceback.print_exc()

    def update_plot(self):
        if self.current_result is None:
            return

        plot_type = (self.plot_type_var.get() or "spectrum").strip()
        xlim = self._parse_float(self.xlim_var.get(), "频谱横轴上限")
        if xlim <= 0:
            raise ValueError("频谱横轴上限须大于 0")

        self.ax.clear()
        ch0 = self.current_result['channel_index'] - 1
        data_time = self.current_result.get('data_raw', self.current_result['data'])
        analyze_date = self.current_result.get('analyze_date')

        if plot_type == 'time':
            plot_time_curve(
                self.current_result['time'],
                data_time,
                ch0,
                self.current_result['label'],
                fig=self.fig, ax=self.ax
            )
        else:
            plot_spectrum(
                self.current_result['f'],
                self.current_result['Pxx'],
                self.current_result['peaks_f'],
                self.current_result['peaks_pxx'],
                self.current_result['label'],
                fig=self.fig, ax=self.ax,
                xlim_hz=xlim,
                analyze_date=analyze_date
            )
        self.fig.tight_layout()
        self.canvas.draw()

    def _reset_axes_placeholder(self):
        self.ax.text(0.5, 0.5, '请点击「分析」按钮加载数据并绘图',
                     ha='center', va='center', transform=self.ax.transAxes,
                     fontsize=14, color='gray', fontfamily='SimSun')
        self.ax.set_xticks([])
        self.ax.set_yticks([])

    # ── 导出 ─────────────────────────────────────────────────────────────────

    def copy_to_clipboard(self):
        if self.current_result is None:
            messagebox.showwarning("提示", "请先完成分析并显示图形。")
            return
        try:
            buf = io.BytesIO()
            self.fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            img = Image.open(buf)
            if HAS_WIN32:
                output = io.BytesIO()
                img.convert('RGB').save(output, 'BMP')
                data = output.getvalue()[14:]
                output.close()
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
                messagebox.showinfo("成功", "图像已复制到剪贴板（可在 Word 中 Ctrl+V）。")
            else:
                messagebox.showwarning("提示", "未安装 pywin32，无法复制到剪贴板。")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败：\n{e}")

    def save_image(self):
        if self.current_result is None:
            messagebox.showwarning("提示", "请先完成分析并显示图形。")
            return
        filepath = filedialog.asksaveasfilename(
            parent=self.root,
            title="保存图像",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("所有文件", "*.*")]
        )
        if filepath:
            try:
                self.fig.savefig(filepath, dpi=300, bbox_inches='tight')
                messagebox.showinfo("成功", f"已保存到：\n{filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败：\n{e}")

    # ── 新窗口绘图 ────────────────────────────────────────────────────────────

    def plot_in_new_window(self):
        if self.current_result is None:
            messagebox.showwarning("提示", "请先完成分析并显示图形。")
            return

        new_window = tk.Toplevel(self.root)
        new_window.title("振动分析 - 频谱图")
        new_window.geometry("1300x720")

        main_frame = ttk.Frame(new_window, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        new_window.columnconfigure(0, weight=0)
        new_window.columnconfigure(1, weight=1)
        new_window.rowconfigure(0, weight=1)

        # 左侧占位面板（与主窗口控制面板同宽）
        left_panel = ttk.LabelFrame(main_frame, text="图形选项", padding="10", width=280)
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_panel.pack_propagate(False)

        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)

        plot_type = (self.plot_type_var.get() or "spectrum").strip()
        xlim = self._parse_float(self.xlim_var.get(), "频谱横轴上限")
        if xlim <= 0:
            raise ValueError("频谱横轴上限须大于 0")
        ch0 = self.current_result['channel_index'] - 1
        data_time = self.current_result.get('data_raw', self.current_result['data'])
        analyze_date = self.current_result.get('analyze_date')

        if plot_type == 'time':
            plot_time_curve(
                self.current_result['time'],
                data_time,
                ch0,
                self.current_result['label'],
                fig=fig, ax=ax
            )
        else:
            plot_spectrum(
                self.current_result['f'],
                self.current_result['Pxx'],
                self.current_result['peaks_f'],
                self.current_result['peaks_pxx'],
                self.current_result['label'],
                fig=fig, ax=ax,
                xlim_hz=xlim,
                analyze_date=analyze_date
            )

        # 右侧绘图区
        right_panel = ttk.Frame(main_frame)
        right_panel.pack_propagate(False)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_panel.rowconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=0)
        right_panel.rowconfigure(2, weight=0)
        right_panel.columnconfigure(0, weight=1)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=right_panel)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky=tk.NSEW)

        toolbar = NavigationToolbar2Tk(canvas, right_panel)
        toolbar.grid(row=1, column=0, sticky=tk.W)

        btn_frame = ttk.Frame(right_panel)
        btn_frame.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Button(btn_frame, text="复制到剪贴板",
                   command=lambda: self._copy_fig_to_clipboard(fig)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="保存图像",
                   command=lambda: self._save_fig(fig)).pack(side=tk.LEFT, padx=2)

        self.figure_objects.append({'window': new_window, 'fig': fig, 'ax': ax, 'canvas': canvas})
        new_window.protocol("WM_DELETE_WINDOW",
                            lambda: self._close_figure_window(new_window))

    def _copy_fig_to_clipboard(self, fig):
        try:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            img = Image.open(buf)
            if HAS_WIN32:
                output = io.BytesIO()
                img.convert('RGB').save(output, 'BMP')
                data = output.getvalue()[14:]
                output.close()
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
                messagebox.showinfo("成功", "图像已复制到剪贴板。")
            else:
                messagebox.showwarning("提示", "未安装 pywin32。")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败：\n{e}")

    def _save_fig(self, fig):
        filepath = filedialog.asksaveasfilename(
            parent=self.root,
            title="保存图像",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("所有文件", "*.*")]
        )
        if filepath:
            try:
                fig.savefig(filepath, dpi=300, bbox_inches='tight')
                messagebox.showinfo("成功", f"已保存到：\n{filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败：\n{e}")

    def _close_figure_window(self, window):
        self.figure_objects = [obj for obj in self.figure_objects if obj['window'] != window]
        window.destroy()


def main():
    app = VibrationAnalyzerUI(standalone=True)
    app.root.mainloop()


if __name__ == "__main__":
    main()
