"""
振动信号分析核心模块
将时程曲线和频谱图功能分离，支持独立调用
"""

import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.ticker import ScalarFormatter
from scipy.signal import welch, butter, sosfiltfilt, find_peaks, fftconvolve
import pandas as pd
import io

# ── 字体：中文宋体，数字与英文字母 Times New Roman ───────────────────────────
def _fp_tnr(size):
    """Times New Roman（坐标刻度、英文/数字标注）"""
    return fm.FontProperties(family='Times New Roman', size=size)


def _find_simsun_path():
    """查找宋体（SimSun）字体文件路径"""
    for name in ['SimSun', 'NSimSun', 'STSong', 'Songti SC']:
        try:
            p = fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
            if p and 'DejaVu' not in p:
                return p
        except Exception:
            pass
    return None


_SIMSUN_PATH = _find_simsun_path()


def _fp_simsun(size):
    """宋体（轴标题、图例、中文标题等）"""
    if _SIMSUN_PATH:
        return fm.FontProperties(fname=_SIMSUN_PATH, size=size)
    return fm.FontProperties(family='SimSun', size=size)


def _apply_ticks_tnr(ax):
    """坐标轴刻度数字、科学计数法指数：Times New Roman"""
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontfamily('Times New Roman')
    ax.yaxis.get_offset_text().set_fontfamily('Times New Roman')


def _apply_matlab_style(ax, tick_fontsize=18):
    """应用MATLAB风格的图表样式"""
    ax.set_facecolor('#EBEBEB')
    ax.grid(True, linestyle=':', color='white', linewidth=1.2, alpha=0.95)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_linewidth(1.5)
    ax.tick_params(labelsize=tick_fontsize, width=1.5, length=5)


def _parse_datetime(time_col):
    """尝试常见格式批量解析时间列"""
    sample = str(time_col.dropna().iloc[0])
    for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S",
                "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M",
                "%b %d, %H:%M"]:
        try:
            pd.to_datetime(sample, format=fmt)
            return pd.to_datetime(time_col, format=fmt, errors='coerce')
        except Exception:
            pass
    return pd.to_datetime(time_col, errors='coerce')


def load_vibration_data(filepath, separator=r'\s+'):
    """
    加载振动数据文件
    
    参数:
        filepath: 数据文件路径
        separator: 分隔符，默认空白字符
    
    返回:
        dict: {'time': 时间列, 'data': 数据数组, 'columns': 列名列表}
    """
    df_raw = pd.read_csv(filepath, sep=separator, header=0,
                         engine='c', on_bad_lines='skip')
    columns = list(df_raw.columns)
    time_col = df_raw.iloc[:, 0]
    data = df_raw.iloc[:, 1:].values.astype(float)
    
    return {
        'time': time_col,
        'data': data,
        'columns': columns,
        'filenames': columns[1:] if len(columns) > 1 else []
    }


def prepare_time_axis(time_col):
    """解析时间列为datetime格式"""
    return _parse_datetime(time_col)


# ═══════════════════════════════════════════════════════════════
# 时程曲线绘制模块
# ═══════════════════════════════════════════════════════════════

def plot_time_curve(time_dt, data, channel_index, label_mark,
                    fig=None, ax=None, figsize=(12, 6)):
    """
    绘制时程曲线
    
    参数:
        time_dt: datetime格式的时间数据
        data: 振动数据数组
        channel_index: 要绘制的通道索引（从0开始）
        label_mark: 曲线标签
        fig: 传入的Figure对象，如果为None则创建新的
        ax: 传入的Axes对象，如果为None则创建新的
    
    返回:
        fig, ax: 图形对象
    """
    if fig is None:
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor('white')
    
    channel_data = data[:, channel_index]
    ax.plot(time_dt, channel_data, linewidth=1, color='#2878B5')
    
    ax.set_xlabel('时间', fontproperties=_fp_simsun(16), labelpad=8)
    ax.set_ylabel('振幅（m/s²）', fontproperties=_fp_simsun(16), labelpad=8)
    # 标题：上行通道名（英文/数字）TNR，下行中文说明宋体
    ax.set_title('')
    ax.text(
        0.5, 1.04, str(label_mark), transform=ax.transAxes,
        ha='center', va='bottom', fontproperties=_fp_tnr(18), clip_on=False,
    )
    ax.text(
        0.5, 1.01, '加速度时程曲线', transform=ax.transAxes,
        ha='center', va='bottom', fontproperties=_fp_simsun(16), clip_on=False,
    )
    _apply_matlab_style(ax, 14)
    _apply_ticks_tnr(ax)
    fig.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.12)
    
    return fig, ax


# ═══════════════════════════════════════════════════════════════
# 频谱分析模块
# ═══════════════════════════════════════════════════════════════

def process_vibration_data(data, fs=50, highpass_cutoff=0.05):
    """
    处理振动数据：零均值化、归一化、高通滤波
    
    参数:
        data: 原始振动数据
        fs: 采样频率（Hz）
        highpass_cutoff: 高通滤波器截止频率（Hz）
    
    返回:
        处理后的数据
    """
    # 零均值化
    data = data - np.nanmean(data, axis=0)
    # 归一化
    data = data / 0.3
    
    # 高通滤波
    Wn = highpass_cutoff / (fs / 2)
    sos = butter(6, Wn, btype='high', output='sos')
    data = sosfiltfilt(sos, data, axis=0)
    
    return data


def compute_cross_correlation(data, ch1, ch2):
    """
    计算两个通道的互相关（FFT法）
    
    参数:
        data: 振动数据数组
        ch1: 第一个通道索引
        ch2: 第二个通道索引
    
    返回:
        互相关结果
    """
    s1 = data[:, ch1].copy()
    s1 -= s1.mean()
    s2 = data[:, ch2].copy()
    s2 -= s2.mean()
    return fftconvolve(s1, s2[::-1], mode='full') / len(s1)


def compute_spectrum(data, fs=50):
    """
    计算功率谱密度（Welch方法）
    
    参数:
        data: 振动数据（单通道）
        fs: 采样频率
    
    返回:
        f: 频率数组
        Pxx: 功率谱密度数组
    """
    data = np.asarray(data, dtype=float).ravel()
    N = len(data)
    
    nperseg = min(1 << (max(256, N // 8) - 1).bit_length(), N)
    noverlap = nperseg // 2
    f, Pxx = welch(data, fs=fs, window='hamming',
                   nperseg=nperseg, noverlap=noverlap, nfft=nperseg,
                   return_onesided=True, scaling='density')
    
    return f, Pxx


def find_spectrum_peaks(Pxx, f, height_ratio=50, distance_ratio=100):
    """
    查找频谱中的峰值
    
    参数:
        Pxx: 功率谱密度
        f: 频率数组
        height_ratio: 峰值高度阈值（最大值除以该值）
        distance_ratio: 峰值间最小距离（频率点数除以该值）
    
    返回:
        peaks_f: 峰值频率数组
        peaks_pxx: 峰值功率数组
    """
    height_threshold = max(Pxx) / height_ratio
    distance = max(1, math.ceil(len(f) / distance_ratio))
    
    locs, _ = find_peaks(Pxx, height=height_threshold, distance=distance)
    peaks_f = f[locs]
    peaks_pxx = Pxx[locs]
    
    return peaks_f, peaks_pxx


def plot_spectrum(f, Pxx, peaks_f, peaks_pxx, label_mark,
                  fig=None, ax=None, figsize=(16, 9), xlim_hz=3.0,
                  analyze_date=None):
    """
    绘制频谱图

    参数:
        f: 频率数组
        Pxx: 功率谱密度数组
        peaks_f: 峰值频率数组
        peaks_pxx: 峰值功率数组
        label_mark: 曲线标签
        fig: 传入的Figure对象，如果为None则创建新的
        ax: 传入的Axes对象，如果为None则创建新的
        figsize: 图形尺寸（默认 16:9）
        xlim_hz: X轴显示范围（Hz）
        analyze_date: 分析日期字符串，以小号字显示在图外右下角边距处

    返回:
        fig, ax: 图形对象
    """
    if fig is None:
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor('white')

    # 裁剪绘图数据
    mask = f <= (xlim_hz + 0.5)
    f_p = f[mask]
    P_p = Pxx[mask]

    peaks_f = np.asarray(peaks_f)
    peaks_pxx = np.asarray(peaks_pxx)
    pm = peaks_f <= xlim_hz
    mf_p = peaks_f[pm]
    mp_p = peaks_pxx[pm]

    # 绘制频谱曲线
    ax.plot(f_p, P_p, color='#2878B5', linewidth=1.5,
            label='频谱', zorder=2)

    # 绘制峰值点
    ax.plot(
        mf_p, mp_p, linestyle='none', marker='o', markersize=9,
        markerfacecolor='none', markeredgecolor='red',
        markeredgewidth=1.8,
        label='峰值', zorder=3,
    )

    # 标注峰值频率
    for xp, yp in zip(mf_p, mp_p):
        ax.text(xp + 0.008, yp, f'{xp:.4f}',
                fontproperties=_fp_tnr(20), ha='left', va='bottom')

    ax.set_xlim([0, xlim_hz])
    ax.set_ylim([0, max(P_p) * 1.10])

    # 设置Y轴格式
    exp_val = int(np.floor(np.log10(max(Pxx)))) if max(Pxx) > 0 else -4
    fmt = ScalarFormatter(useMathText=False)
    fmt.set_scientific(True)
    fmt.set_powerlimits((exp_val, exp_val))
    ax.yaxis.set_major_formatter(fmt)
    ax.yaxis.get_offset_text().set_fontsize(16)

    ax.set_xlabel('频率（Hz）', fontproperties=_fp_simsun(20), labelpad=8)
    ax.set_ylabel('PSD (dB/Hz)', fontproperties=_fp_tnr(20), labelpad=8)

    # 标题：仅通道名
    ax.set_title('')
    ax.text(
        0.5, 1.04, str(label_mark), transform=ax.transAxes,
        ha='center', va='bottom', fontproperties=_fp_tnr(20), clip_on=False,
    )

    ax.legend(prop=_fp_simsun(18), loc='best',
              frameon=True, edgecolor='#AAAAAA', facecolor='white')
    _apply_matlab_style(ax, 18)
    _apply_ticks_tnr(ax)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.14)
    # 日期画在坐标系内右下角
    if analyze_date:
        ax.text(
            0.99, 0.02, str(analyze_date).strip(),
            transform=ax.transAxes,
            ha='right', va='bottom',
            fontsize=10,
            color='#333333',
            clip_on=False,
        )

    return fig, ax


# ═══════════════════════════════════════════════════════════════
# 完整分析流程
# ═══════════════════════════════════════════════════════════════

def analyze_vibration(filepath, channel_index, reference_channel=None,
                      fs=50, highpass_cutoff=0.05, xlim_hz=3.0):
    """
    完整的振动信号分析流程
    
    参数:
        filepath: 数据文件路径
        channel_index: 分析通道索引（从1开始，与原代码一致）
        reference_channel: 参考通道索引（用于互相关，可选，0 或 None 表示不用）
        fs: 采样频率
        highpass_cutoff: 高通滤波截止频率 (Hz)
        xlim_hz: 频谱图X轴范围（仅用于后续绘图参考）
    
    返回:
        dict: 包含分析结果的字典
        - data_raw: 原始数值列（时程图与原版一致，用滤波前数据）
        - data: 滤波后的全部通道数据（频谱基于此通道）
    """
    # 加载数据
    result = load_vibration_data(filepath)
    time_col = result['time']
    data_raw = np.asarray(result['data'], dtype=float)
    columns = result['columns']
    
    n_ch = data_raw.shape[1]
    ch = int(channel_index) - 1  # 转换为0索引
    if ch < 0 or ch >= n_ch:
        raise ValueError(f"分析通道必须在 1～{n_ch} 之间，当前为 {channel_index}")
    
    # 提取标签
    label_mark = []
    for name in columns[1:]:
        idx = name.find('【')
        label_mark.append(name[:idx] if idx != -1 else name)
    
    # 解析时间
    time_dt = _parse_datetime(time_col)
    # 日期标记：直接从文件第二行（首行数据）取前10位，避免 pandas 解析差异
    analyze_date_str = ''
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            _ = f.readline()  # 跳过表头
            first_data = f.readline().strip()
        if first_data and len(first_data) >= 10 and first_data[:4].isdigit():
            analyze_date_str = first_data[:10].replace('-', '.').replace('/', '.')
    except Exception:
        pass
    
    # 参考通道互相关（在滤波后的数据上计算，与原版一致）
    data_proc = process_vibration_data(data_raw.copy(), fs, highpass_cutoff)
    ref_ch = None
    if reference_channel is not None and int(reference_channel) > 0:
        ref_ch = int(reference_channel) - 1
        if ref_ch < 0 or ref_ch >= n_ch:
            raise ValueError(f"参考通道必须在 1～{n_ch} 之间或为 0，当前为 {reference_channel}")
        if ref_ch == ch:
            raise ValueError("参考通道不能与分析通道相同")
        _ = compute_cross_correlation(data_proc, ch, ref_ch)
    
    # 频谱用滤波后的当前通道
    channel_data = data_proc[:, ch]
    
    # 计算频谱
    f, Pxx = compute_spectrum(channel_data, fs)
    peaks_f, peaks_pxx = find_spectrum_peaks(Pxx, f)
    
    # 计算能量比
    energy_ratio = 0.0
    if len(peaks_f) > 1:
        s = np.argsort(peaks_pxx)[::-1]
        energy_ratio = float(peaks_pxx[s[0]] / peaks_pxx[s[1]])
    
    return {
        'time': time_dt,
        'data_raw': data_raw,
        'data': data_proc,
        'channel_index': int(channel_index),
        'label': label_mark[ch] if ch < len(label_mark) else f"通道{channel_index}",
        'columns': columns[1:],          # 数据列名（不含时间列）
        'columns_raw': columns,           # 含时间列的完整列名
        'analyze_date': analyze_date_str,
        'f': f,
        'Pxx': Pxx,
        'peaks_f': peaks_f,
        'peaks_pxx': peaks_pxx,
        'energy_ratio': energy_ratio,
    }


def create_figure_from_result(result, plot_type='spectrum', xlim_hz=3.0):
    """
    根据分析结果创建图形
    
    参数:
        result: analyze_vibration返回的结果
        plot_type: 'time' 或 'spectrum'
        xlim_hz: 频谱图X轴范围
    
    返回:
        fig, ax: 图形对象
    """
    if plot_type == 'time':
        return plot_time_curve(
            result['time'],
            result.get('data_raw', result['data']),
            result['channel_index'] - 1,
            result['label']
        )
    elif plot_type == 'spectrum':
        return plot_spectrum(
            result['f'],
            result['Pxx'],
            result['peaks_f'],
            result['peaks_pxx'],
            result['label'],
            xlim_hz=xlim_hz,
            analyze_date=result.get('analyze_date')
        )
    else:
        raise ValueError(f"未知的绘图类型: {plot_type}")