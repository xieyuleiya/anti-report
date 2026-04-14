import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 简单记忆：避免多次重复扫描字体与重复设置 rcParams
_FONT_SETUP_DONE = False
_SELECTED_FONT = None

def log(msg, level='info', progress=False):
    """
    统一日志输出函数，方便管理输出信息
    msg: 要输出的信息
    level: 信息级别（info普通，warn警告，error错误，success成功）
    progress: 是否为进度条内输出
    """
    if not progress:
        prefix = {
            'info': '→',
            'warn': '!',
            'error': '×',
            'success': '√'
        }.get(level, '•')
        print(f"{prefix} {msg}")
    else:
        print(msg)

def setup_chinese_fonts():
    """
    设置matplotlib的中文字体，优先宋体
    只影响图表显示，不影响Word
    返回选中的字体名
    """
    global _FONT_SETUP_DONE, _SELECTED_FONT
    if _FONT_SETUP_DONE:
        return _SELECTED_FONT
    try:
        font_candidates = ['SimSun', 'NSimSun', '宋体', 'Microsoft YaHei', 'SimHei']
        available_fonts = set([f.name for f in fm.fontManager.ttflist])
        selected_font = next((font for font in font_candidates if font in available_fonts), None)
        if selected_font:
            plt.rcParams.update({
                'font.sans-serif': [selected_font, 'Times New Roman'],
                'font.family': 'sans-serif',
                'axes.unicode_minus': False,
                'font.size': 12,
                'axes.titlesize': 16,
                'axes.labelsize': 14,
                'xtick.labelsize': 12,
                'ytick.labelsize': 12,
                'legend.fontsize': 12
            })
        else:
            plt.rcParams['axes.unicode_minus'] = False
        _SELECTED_FONT = selected_font
        _FONT_SETUP_DONE = True
        return selected_font
    except Exception:
        plt.rcParams['axes.unicode_minus'] = False
        _SELECTED_FONT = None
        _FONT_SETUP_DONE = True
        return None 