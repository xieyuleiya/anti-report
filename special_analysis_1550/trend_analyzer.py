import numpy as np
from scipy import stats

class TrendAnalyzer:
    """
    趋势分析类，负责对单个测点数据进行线性趋势分析
    """
    def analyze_trend(self, df):
        # 分析单个测点的趋势（归一化：减去首值）
        if df is None or len(df) == 0:
            return None
        
        # 如果传入的是离线标记，返回离线结果
        if isinstance(df, str) and df == "OFFLINE":
            return "OFFLINE"
        sensor_id = df['sensor_id'].iloc[0]
        bridge_name = df['bridge_name'].iloc[0]
        time_numeric = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds() / 3600
        analysis_result = {
            'sensor_id': sensor_id,
            'bridge_name': bridge_name,
            'data_count': len(df),
            'time_span_hours': time_numeric.max(),
            'time_span_days': time_numeric.max() / 24,
            'start_time': df['timestamp'].min(),
            'end_time': df['timestamp'].max()
        }
        for angle_type in ['horizontal_angle', 'vertical_angle']:
            angle_data = df[angle_type] - df[angle_type].iloc[0]
            stats_data = {
                'max_value': angle_data.max(),
                'min_value': angle_data.min(),
                'value_range': angle_data.max() - angle_data.min(),
                'mean_value': angle_data.mean(),
                'std_value': angle_data.std(),
                'initial_value': angle_data.iloc[0],
                'final_value': angle_data.iloc[-1],
                'total_change': angle_data.iloc[-1] - angle_data.iloc[0],
                'max_time': df.loc[angle_data.idxmax(), 'timestamp'],
                'min_time': df.loc[angle_data.idxmin(), 'timestamp']
            }
            # 线性趋势分析（基于归一化数据）
            slope, intercept, r_value, p_value, std_err = stats.linregress(time_numeric, angle_data)
            trend_per_day = slope * 24
            trend_per_month = slope * 24 * 30
            is_significant = p_value < 0.05
            trend_strength = ('持续关注' if abs(trend_per_month) > 0.09 else
                            # '持续关注' if abs(trend_per_month) > 0.08 else
                            '正常')
            risk_level = ('高' if is_significant and abs(trend_per_month) > 0.09 else
                        #  '中' if is_significant and abs(trend_per_month) > 0.08 else
                         '低')
            analysis_result[f'{angle_type}_trend'] = {
                **stats_data,
                'slope_per_hour': slope,
                'slope_per_day': trend_per_day,
                'slope_per_month': trend_per_month,
                'slope_per_year': slope * 24 * 365,
                'intercept': intercept,
                'r_squared': r_value**2,
                'p_value': p_value,
                'std_error': std_err,
                'is_significant': is_significant,
                'trend_strength': trend_strength,
                'risk_level': risk_level
            }
        return analysis_result 