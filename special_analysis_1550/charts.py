import matplotlib
# 使用非交互式后端，避免多线程下 Tkinter 报错（main thread is not in main loop）
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from .utils import setup_chinese_fonts

# 关闭交互模式，减少与 GUI 后端的耦合
plt.ioff()

def create_trend_chart(df, trend_result, output_path):
    """
    创建长期趋势分析图表（归一化），分横向/纵向两子图
    """
    if df is None or trend_result is None:
        return
    setup_chinese_fonts()
    sensor_id = trend_result['sensor_id']
    bridge_name = trend_result['bridge_name']
    df = df.copy()
    df['horizontal_angle'] = df['horizontal_angle'] - df['horizontal_angle'].iloc[0]
    df['vertical_angle'] = df['vertical_angle'] - df['vertical_angle'].iloc[0]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
    fig.suptitle(f'{bridge_name} - {sensor_id} 趋势分析', fontsize=18, fontweight='bold', y=0.95)
    timestamps = df['timestamp']
    time_numeric = (timestamps - timestamps.min()).dt.total_seconds() / 3600
    # 横向倾角散点图
    ax1.scatter(timestamps, df['horizontal_angle'], alpha=0.6, s=4, color='green', label='横向数据', zorder=2)
    h_trend = trend_result['horizontal_angle_trend']
    h_trend_values = h_trend['slope_per_hour'] * time_numeric + h_trend['intercept']
    ax1.plot(timestamps, h_trend_values, color='darkgreen', linewidth=3, 
             label=f"横向趋势 ({h_trend['slope_per_day']:.6f}°/天)", zorder=3)
    ax1.set_title('横向倾角趋势', fontsize=14)
    ax1.set_xlabel('时间', fontsize=12)
    ax1.set_ylabel('倾角 (°)', fontsize=12)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    # 纵向倾角散点图
    ax2.scatter(timestamps, df['vertical_angle'], alpha=0.6, s=4, color='red', label='纵向数据', zorder=2)
    v_trend = trend_result['vertical_angle_trend']
    v_trend_values = v_trend['slope_per_hour'] * time_numeric + v_trend['intercept']
    ax2.plot(timestamps, v_trend_values, color='darkred', linewidth=3, 
             label=f"纵向趋势 ({v_trend['slope_per_day']:.6f}°/天)", zorder=3)
    ax2.set_title('纵向倾角趋势', fontsize=14)
    ax2.set_xlabel('时间', fontsize=12)
    ax2.set_ylabel('倾角 (°)', fontsize=12)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    import matplotlib.dates as mdates
    time_span_hours = (timestamps.max() - timestamps.min()).total_seconds() / 3600
    if time_span_hours <= 2:
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax1.xaxis.set_major_locator(mdates.MinuteLocator(interval=10))
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax2.xaxis.set_major_locator(mdates.MinuteLocator(interval=10))
    elif time_span_hours <= 24:
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax1.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax2.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    elif time_span_hours <= 168:
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    else:
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator())
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax2.xaxis.set_major_locator(mdates.WeekdayLocator())
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    start_time = timestamps.min().strftime('%Y-%m-%d %H:%M')
    end_time = timestamps.max().strftime('%Y-%m-%d %H:%M')
    info_text = f"""数据统计:\n• 监测时段: {start_time}\n          至 {end_time}\n• 监测时长: {trend_result['time_span_days']:.1f} 天\n• 数据点数: {trend_result['data_count']} 个\n\n横向趋势:\n• 变化率: {h_trend['slope_per_month']:.6f}°/月\n• 趋势强度: {h_trend['trend_strength']}\n• 风险等级: {h_trend['risk_level']}\n• R² = {h_trend['r_squared']:.4f}\n\n纵向趋势:\n• 变化率: {v_trend['slope_per_month']:.6f}°/月\n• 趋势强度: {v_trend['trend_strength']}\n• 风险等级: {v_trend['risk_level']}\n• R² = {v_trend['r_squared']:.4f}"""
    ax1.text(0.02, 0.98, info_text, transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    plt.tight_layout()
    try:
        plt.savefig(output_path, dpi=50, bbox_inches='tight', facecolor='white')
    except Exception as e:
        # 如果保存失败，尝试降低DPI
        try:
            plt.savefig(output_path, dpi=30, bbox_inches='tight', facecolor='white')
        except Exception as e2:
            raise e2
    finally:
        # 确保关闭figure并清理内存
        plt.close(fig)
        import gc
        gc.collect()


def create_critical_sensors_chart(bridge_name, critical_sensors_data, output_path):
    """
    创建重点关注测点的组合图表（归一化）
    
    Args:
        bridge_name: 桥梁名称
        critical_sensors_data: 重点关注测点数据字典，格式为 {sensor_id: {'timestamp': [...], 'horizontal_angle': [...], 'vertical_angle': [...]}}
        output_path: 输出图片路径
    
    Returns:
        str: 生成的图片路径，如果失败返回None
    """
    if not critical_sensors_data:
        return None
    
    setup_chinese_fonts()
    
    plt.figure(figsize=(12, 6))
    ax1 = plt.subplot(211)
    ax2 = plt.subplot(212)
    
    for sensor_id, sensor_data in critical_sensors_data.items():
        if sensor_data is not None:
            timestamps = sensor_data['timestamp']
            horizontal_angle = sensor_data['horizontal_angle']
            vertical_angle = sensor_data['vertical_angle']
            
            # 归一化处理
            h_angle = np.array(horizontal_angle) - horizontal_angle.iloc[0]
            v_angle = np.array(vertical_angle) - vertical_angle.iloc[0]
            
            ax1.plot(timestamps, h_angle, label=sensor_id)
            ax2.plot(timestamps, v_angle, label=sensor_id)
    
    ax1.set_title('横向倾角')
    ax1.set_ylabel('倾角(°)')
    ax1.grid(True)
    ax1.legend()
    
    ax2.set_title('纵向倾角')
    ax2.set_xlabel('时间')
    ax2.set_ylabel('倾角(°)')
    ax2.grid(True)
    ax2.legend()
    
    plt.tight_layout()
    try:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
    except Exception as e:
        # 如果保存失败，尝试降低DPI
        try:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        except Exception as e2:
            raise e2
    finally:
        # 确保关闭figure并清理内存
        plt.close()
        import gc
        gc.collect()
    
    return output_path