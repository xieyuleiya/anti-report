import os
from pathlib import Path
try:
    from docxtpl import DocxTemplate, InlineImage
    from docx.shared import Mm
except ImportError:
    pass
import numpy as np
from datetime import datetime

class TemperatureHumidityReporter:
    def __init__(self, bridge_name: str, output_dir: Path, data: dict, stats_summary: dict, humidity_threshold: int, df_temp, df_hum):
        self.bridge_name = bridge_name
        self.output_dir = output_dir
        self.data = data
        self.stats_summary = stats_summary
        self.humidity_threshold = humidity_threshold
        self.df_temp = df_temp
        self.df_hum = df_hum

    def _build_report_context(self):
        now = datetime.now()
        context = {
            'bridge_name': self.bridge_name,
            'humidity_threshold': self.humidity_threshold,
            'report_gen_time': now.strftime('%Y年%m月%d日 %H:%M:%S'),
            'report_year': now.strftime('%Y'),
            'report_month': now.strftime('%m'),
            'report_day': now.strftime('%d'),
            'report_date': now.strftime('%Y年%m月%d日'),
        }
        
        all_dates = []
        for d in self.data.values():
            if d is not None and not d.empty:
                all_dates.extend([d['Date'].min(), d['Date'].max()])
                
        if all_dates:
            context['start_date_str'] = min(all_dates).strftime('%Y年%m月%d日')
            context['end_date_str'] = max(all_dates).strftime('%Y年%m月%d日')
        else:
            context['start_date_str'] = "未知"
            context['end_date_str'] = "未知"
            
        stats_list = []
        if self.stats_summary:
            for station, stats in self.stats_summary.items():
                stats_list.append({
                    'station': station,
                    'records': stats['records'],
                    'temp_mean': f"{stats['temp_mean']:.2f}",
                    'temp_min': f"{stats['temp_min']:.2f}",
                    'temp_max': f"{stats['temp_max']:.2f}",
                    'temp_range': f"{stats['temp_range']:.2f}",
                    'hum_mean': f"{stats['humidity_mean']:.2f}",
                    'hum_min': f"{stats['humidity_min']:.2f}",
                    'hum_max': f"{stats['humidity_max']:.2f}",
                    'hum_range': f"{stats['humidity_range']:.2f}",
                    'hum_over_limit_rate': f"{stats['over_limit_rate']:.2f}"
                })
        context['stats_list'] = stats_list
        context['has_stats'] = len(stats_list) > 0
        
        # Temp Table
        temp_table = []
        if self.df_temp is not None and not self.df_temp.empty:
            for _, row in self.df_temp.iterrows():
                temp_table.append({
                    'station': row['测点名称'],
                    'mean': str(row['温度平均值(°C)']),
                    'max': str(row['温度最大值(°C)']),
                    'min': str(row['温度最小值(°C)']),
                    'range': str(row['温度差值(°C)']),
                    'std': str(row['温度标准差(°C)'])
                })
        context['temp_table'] = temp_table
        
        # Hum Table
        hum_table = []
        if self.df_hum is not None and not self.df_hum.empty:
            for _, row in self.df_hum.iterrows():
                hum_table.append({
                    'station': row['测点名称'],
                    'mean': str(row['湿度平均值(%)']),
                    'max': str(row['湿度最大值(%)']),
                    'min': str(row['湿度最小值(%)']),
                    'range': str(row['湿度差值(%)']),
                    'std': str(row['湿度标准差(%)']),
                    'rate': str(row['湿度超限记录频率(%)'])
                })
        context['hum_table'] = hum_table
        
        # Conclusions
        if self.stats_summary:
            temp_means = [s['temp_mean'] for s in self.stats_summary.values()]
            temp_ranges = [s['temp_range'] for s in self.stats_summary.values()]
            hum_means = [s['humidity_mean'] for s in self.stats_summary.values()]
            hum_rates = [s['over_limit_rate'] for s in self.stats_summary.values()]
            
            context['conc_temp_min'] = f"{min(temp_means):.2f}"
            context['conc_temp_max'] = f"{max(temp_means):.2f}"
            context['conc_temp_avg'] = f"{np.mean(temp_means):.2f}"
            context['conc_temp_range'] = f"{max(temp_ranges):.2f}"
            
            context['conc_hum_min'] = f"{min(hum_means):.2f}"
            context['conc_hum_max'] = f"{max(hum_means):.2f}"
            context['conc_hum_avg'] = f"{np.mean(hum_means):.2f}"
            
            context['conc_rate_min'] = f"{min(hum_rates):.2f}"
            context['conc_rate_max'] = f"{max(hum_rates):.2f}"
            context['conc_rate_avg'] = f"{np.mean(hum_rates):.2f}"

        return context

    def generate_word_report(self):
        print("正在生成Word格式报告...")
        try:
            from docxtpl import DocxTemplate, InlineImage
            from docx.shared import Mm
        except ImportError:
            print("❌ 缺少 docxtpl 库，请先运行: pip install docxtpl")
            return None
        
        template_file = os.path.join(str(Path(__file__).parent.parent.parent), "templates", "温湿度分析模版_docxtpl.docx")
        if not os.path.exists(template_file):
            print(f"模板文件不存在: {template_file}")
            return None
            
        doc = DocxTemplate(template_file)
        context = self._build_report_context()
        
        for img_key, img_file in [
            ('img_temp_series', '各测点温度时序图.png'),
            ('img_hum_series', '各测点湿度时序图.png'),
            ('img_dist', '各测点温湿度频数分布图.png'),
            ('img_exceed', '湿度超限记录数统计图.png')
        ]:
            img_path = self.output_dir / img_file
            if img_path.exists():
                context[img_key] = InlineImage(doc, str(img_path), width=Mm(140))
            else:
                context[img_key] = '[图表缺失]'
                
        try:
            doc.render(context)
            report_path = self.output_dir / f'{self.bridge_name}温湿度数据分析报告.docx'
            doc.save(str(report_path))
            print(f"✅ Word报告已生成并尝试打开: {report_path}")
            
            # 自动打开文档
            try:
                os.startfile(str(report_path))
            except Exception as e_open:
                print(f"无法自动打开文档: {e_open}")
                
            return str(report_path)
        except Exception as e:
            print(f"❌ 保存Word报告失败: {e}")
            try:
                fallback_path = f'{self.bridge_name}温湿度数据分析报告.docx'
                doc.save(fallback_path)
                print(f"✅ Word报告已保存到备用位置: {fallback_path}")
                try:
                    os.startfile(fallback_path)
                except:
                    pass
                return fallback_path
            except Exception as e2:
                print(f"备用保存失败: {e2}")
                return None
