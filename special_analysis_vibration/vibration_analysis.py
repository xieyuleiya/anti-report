"""
振动信号频谱分析模块（Pwelch法）
移植自 MATLAB mainfun.m + pwelch_fun.m

已解决的性能问题：
  1. xcorr: np.correlate O(N²) → fftconvolve O(N logN)，42秒→<1秒
  2. 时间解析: 自动推断格式后批量解析，3秒→<0.1秒
  3. 绘图: Agg后端 + 保存PNG + os.startfile，彻底避免Windows GUI卡死
"""

import math, time, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.ticker import ScalarFormatter
from scipy.signal import welch, butter, sosfiltfilt, find_peaks, fftconvolve
import pandas as pd

# ── 计时工具 ──────────────────────────────────────────────────
class _Timer:
    def __init__(self, label): self.label = label
    def __enter__(self):       self._t = time.perf_counter(); return self
    def __exit__(self, *_):    print(f"  [{(time.perf_counter()-self._t)*1000:7.1f} ms]  {self.label}")
def _t(label): return _Timer(label)

# ── 输出目录 ──────────────────────────────────────────────────
_OUT_DIR = os.path.dirname(os.path.abspath(__file__))

def _save_and_open(fig, filename):
    path = os.path.join(_OUT_DIR, filename)
    with _t(f"保存图片 → {filename}"):
        fig.savefig(path, dpi=120, bbox_inches='tight')
    plt.close(fig)
    with _t("系统打开图片（非阻塞）"):
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}" &')
    print(f"  图片路径: {path}")

# ── 中文字体（模块加载时查找一次）───────────────────────────
print("[初始化] 查找中文字体...", end=" ", flush=True)
_t0 = time.perf_counter()
def _find_chinese_font():
    for name in ['SimSun','SimHei','Microsoft YaHei','STSong','STHeiti',
                 'PingFang SC','WenQuanYi Micro Hei','Noto Sans CJK SC']:
        try:
            p = fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
            if p and 'DejaVu' not in p: return p
        except: pass
    return None
_CHINESE_FONT_PATH = _find_chinese_font()
print(f"{(time.perf_counter()-_t0)*1000:.1f} ms  →  "
      f"{'找到: '+_CHINESE_FONT_PATH if _CHINESE_FONT_PATH else '未找到，使用英文'}")
matplotlib.rcParams['axes.unicode_minus'] = False

def _fp(size):
    if _CHINESE_FONT_PATH: return fm.FontProperties(fname=_CHINESE_FONT_PATH, size=size)
    return fm.FontProperties(size=size)

def _apply_matlab_style(ax, tick_fontsize=18):
    ax.set_facecolor('#EBEBEB')
    ax.grid(True, linestyle=':', color='white', linewidth=1.2, alpha=0.95)
    ax.set_axisbelow(True)
    for s in ax.spines.values(): s.set_linewidth(1.5)
    ax.tick_params(labelsize=tick_fontsize, width=1.5, length=5)

def _parse_datetime(time_col):
    """尝试常见格式批量解析，避免逐行推断（快10x）。"""
    sample = str(time_col.dropna().iloc[0])
    for fmt in ["%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S",
                "%Y/%m/%d %H:%M",    "%Y-%m-%d %H:%M",
                "%b %d, %H:%M"]:
        try:
            pd.to_datetime(sample, format=fmt)
            return pd.to_datetime(time_col, format=fmt, errors='coerce')
        except Exception:
            pass
    # 最后兜底：不指定格式（会慢，但不报警告）
    return pd.to_datetime(time_col, errors='coerce')


# ═══════════════════════════════════════════════════════════════
def pwelch_fun(fs, data, label_mark="", plotcnt=0, xlim_hz=3.0):
    print(f"\n── pwelch_fun 开始（N={len(data)} 点）──")
    data = np.asarray(data, dtype=float).ravel()
    N    = len(data)

    with _t("Welch 计算"):
        nperseg  = min(1 << (max(256, N//8)-1).bit_length(), N)
        noverlap = nperseg // 2
        f, Pxx   = welch(data, fs=fs, window='hamming',
                         nperseg=nperseg, noverlap=noverlap, nfft=nperseg,
                         return_onesided=True, scaling='density')
        print(f"         nperseg={nperseg}, f点数={len(f)}")

    with _t("寻峰"):
        locs, _ = find_peaks(Pxx,
                             height=max(Pxx)/50,
                             distance=max(1, math.ceil(len(f)/100)))
        max_pxx = Pxx[locs]
        max_f   = f[locs]
        print(f"         找到 {len(max_f)} 个峰: {np.round(max_f,4)}")

    energy_ratio = 0.0
    if len(max_f) > 1:
        s = np.argsort(max_pxx)[::-1]
        energy_ratio = float(max_pxx[s[0]] / max_pxx[s[1]])

    if plotcnt == 1:
        print(f"\n── 绘制频谱图 ──")
        FS = 20

        with _t("裁剪绘图数据"):
            mask = f <= (xlim_hz + 0.5)
            f_p  = f[mask];    P_p  = Pxx[mask]
            pm   = max_f <= xlim_hz
            mf_p = max_f[pm];  mp_p = max_pxx[pm]
            print(f"         {len(f)} → {len(f_p)} 点")

        with _t("构建图形对象"):
            fig, ax = plt.subplots(figsize=(12, 7))
            fig.patch.set_facecolor('white')
            ax.plot(f_p, P_p, color='#2878B5', linewidth=1.5,
                    label='频谱' if _CHINESE_FONT_PATH else 'Spectrum', zorder=2)
            ax.plot(mf_p, mp_p, linestyle='none', marker='o', markersize=9,
                    markerfacecolor='none', markeredgecolor='red',
                    markeredgewidth=1.8,
                    label='峰值' if _CHINESE_FONT_PATH else 'Peak', zorder=3)
            for xp, yp in zip(mf_p, mp_p):
                ax.text(xp+0.008, yp, f'{xp:.4f}',
                        fontproperties=_fp(FS), ha='left', va='bottom')
            ax.set_xlim([0, xlim_hz])
            ax.set_ylim([0, max(P_p)*1.10])
            exp_val = int(np.floor(np.log10(max(Pxx)))) if max(Pxx) > 0 else -4
            fmt = ScalarFormatter(useMathText=False)
            fmt.set_scientific(True)
            fmt.set_powerlimits((exp_val, exp_val))
            ax.yaxis.set_major_formatter(fmt)
            ax.yaxis.get_offset_text().set_fontsize(FS-4)
            ax.set_xlabel('频率/Hz' if _CHINESE_FONT_PATH else 'Frequency/Hz',
                          fontproperties=_fp(FS), labelpad=8)
            ax.set_ylabel('PSD (dB/Hz)', fontproperties=_fp(FS), labelpad=8)
            ax.set_title(
                f'{label_mark}频谱分析' if _CHINESE_FONT_PATH else f'{label_mark} Spectrum',
                fontproperties=_fp(FS+4), pad=12)
            ax.legend(prop=_fp(FS-2), loc='upper right',
                      frameon=True, edgecolor='#AAAAAA', facecolor='white')
            _apply_matlab_style(ax, FS-2)
            fig.subplots_adjust(left=0.12, right=0.97, top=0.93, bottom=0.10)

        safe = label_mark.replace(' ','_').replace('/','').replace('[','').replace(']','')
        _save_and_open(fig, f"{safe}_频谱.png")

    return max_pxx, max_f, energy_ratio


# ═══════════════════════════════════════════════════════════════
def main(filepath='2024-10-10-12-LabViewData--jsd.txt',
         ii=3, cori=3, plotcnt=1):

    T0 = time.perf_counter()
    print(f"\n{'='*52}")
    print(f"  振动信号分析  通道={ii}  文件={filepath}")
    print(f"{'='*52}")

    with _t("读取文件（c引擎）"):
        df_raw  = pd.read_csv(filepath, sep=r'\s+', header=0,
                              engine='c', on_bad_lines='skip')
        point_m = list(df_raw.columns)
        time_col= df_raw.iloc[:, 0]
        Data    = df_raw.iloc[:, 1:].values.astype(float)
        print(f"         数据形状: {Data.shape}")

    label_mark = []
    for name in point_m[1:]:
        idx = name.find('【')
        label_mark.append(name[:idx] if idx != -1 else name)
    ch = ii - 1

    # ── 时程曲线 ──────────────────────────────────────────────
    if plotcnt == 1:
        with _t("时间列解析（格式匹配，快速）"):
            time_dt = _parse_datetime(time_col)

        print(f"\n── 绘制时程曲线 ──")
        with _t("构建图形对象"):
            fig0, ax0 = plt.subplots(figsize=(12, 6))
            fig0.patch.set_facecolor('white')
            ax0.plot(time_dt, Data[:, ch], linewidth=1, color='#2878B5')
            ax0.set_xlabel('时间' if _CHINESE_FONT_PATH else 'Time',
                           fontproperties=_fp(16))
            ax0.set_ylabel('振幅 m/s²' if _CHINESE_FONT_PATH else 'Amp m/s²',
                           fontproperties=_fp(16))
            ax0.set_title(
                f'{label_mark[ch]}加速度时程曲线' if _CHINESE_FONT_PATH
                else f'{label_mark[ch]} Acc.',
                fontproperties=_fp(20))
            _apply_matlab_style(ax0, 14)
            fig0.subplots_adjust(left=0.10, right=0.97, top=0.92, bottom=0.12)

        safe = label_mark[ch].replace(' ','_').replace('/','').replace('[','').replace(']','')
        _save_and_open(fig0, f"{safe}_时程.png")

    with _t("零均值化 + 归一化"):
        Data = Data - np.nanmean(Data, axis=0)
        Data = Data / 0.3

    with _t("butter SOS 滤波器构造"):
        fs  = 50
        Wn  = 0.05 / (fs / 2)
        sos = butter(6, Wn, btype='high', output='sos')

    with _t("sosfiltfilt 高通滤波"):
        Data = sosfiltfilt(sos, Data, axis=0)

    # ★ xcorr: fftconvolve O(N logN)，原来 np.correlate O(N²) 要42秒
    if cori > 0:
        with _t("xcorr 互相关（FFT法）"):
            s1 = Data[:, ch].copy();       s1 -= s1.mean()
            s2 = Data[:, cori-1].copy();   s2 -= s2.mean()
            _ = fftconvolve(s1, s2[::-1], mode='full') / len(s1)
    data = Data[:, ch]

    max_pxx, max_f, energy_ratio = pwelch_fun(fs, data, label_mark[ch], plotcnt)

    print(f"\n{'='*52}")
    print(f"  总耗时    : {(time.perf_counter()-T0)*1000:.0f} ms")
    print(f"  通道      : {label_mark[ch]}")
    print(f"  峰值频率  : {np.round(max_f,4)} Hz")
    print(f"  能量比    : {energy_ratio:.4f}")
    print(f"{'='*52}\n")

    return max_pxx, max_f, energy_ratio


if __name__ == '__main__':
    main(filepath='2024-10-10-12-LabViewData--jsd.txt', ii=3, cori=3, plotcnt=1)