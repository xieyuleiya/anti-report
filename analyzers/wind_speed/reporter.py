import os
from pathlib import Path
try:
    from docxtpl import DocxTemplate, InlineImage
    from docx.shared import Mm
except ImportError:
    pass
import numpy as np
from datetime import datetime

class WindSpeedReporter:
    def __init__(self, bridge_name: str, output_dir: Path, wind_data: dict, original_data: dict, stats_summary: dict, global_stats: dict, df_wind):
        self.bridge_name = bridge_name
        self.output_dir = output_dir
        self.wind_data = wind_data
        self.original_data = original_data
        self.stats_summary = stats_summary
        self.global_stats = global_stats
        self.df_wind = df_wind

    def _natural_sort_key(self, text):
        import re
        return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', text)]

    def _build_report_context(self):
        now = datetime.now()
        context = {
            'bridge_name': self.bridge_name,
            'report_gen_time': now.strftime('%Y年%m月%d日 %H:%M:%S'),
            'report_year': now.strftime('%Y'),
            'report_month': now.strftime('%m'),
            'report_day': now.strftime('%d'),
            'report_date': now.strftime('%Y年%m月%d日'),
        }
        
        # Calculate start and end global date if not in global_stats
        if self.stats_summary:
            min_avg_speed = min([stats['wind_speed_mean'] for stats in self.stats_summary.values()])
            max_avg_speed = max([stats['wind_speed_mean'] for stats in self.stats_summary.values()])
            min_max_speed = min([stats['wind_speed_max'] for stats in self.stats_summary.values()])
            max_max_speed = max([stats['wind_speed_max'] for stats in self.stats_summary.values()])
            avg_wind_speed = np.mean([stats['wind_speed_mean'] for stats in self.stats_summary.values()])
            min_wind_speed = min([stats['wind_speed_min'] for stats in self.stats_summary.values()])
            max_wind_speed = max([stats['wind_speed_max'] for stats in self.stats_summary.values()])
            
            context.update({
                'has_stats': True,
                'min_avg_speed': f"{min_avg_speed:.2f}",
                'max_avg_speed': f"{max_avg_speed:.2f}",
                'min_max_speed': f"{min_max_speed:.2f}",
                'max_max_speed': f"{max_max_speed:.2f}",
                'overall_avg_speed': f"{avg_wind_speed:.2f}",
                'overall_min_speed': f"{min_wind_speed:.2f}",
                'overall_max_speed': f"{max_wind_speed:.2f}",
            })
            
            if self.global_stats:
                max_time_str = self.global_stats['max_wind_speed_time'].strftime('%Y年%m月%d日 %H:%M:%S')
                context.update({
                    'global_max_speed': f"{self.global_stats['max_wind_speed']:.2f}",
                    'global_max_sensor': self.global_stats['max_wind_speed_sensor'],
                    'global_max_time': max_time_str
                })
        else:
            context['has_stats'] = False

        # Build wind table
        wind_table = []
        if self.df_wind is not None and not self.df_wind.empty:
            for _, row in self.df_wind.iterrows():
                wind_table.append({
                    'station': row['测点名称'],
                    'mean': str(row['平均风速(m/s)']),
                    'max': str(row['最大风速(m/s)']),
                    'min': str(row['最小风速(m/s)']),
                    'std': str(row['风速标准差(m/s)']),
                    'dir': str(row['平均风向(°)']),
                    'records': str(row['记录数量'])
                })
        context['wind_table'] = wind_table
        
        # Build comprehensive sensor list for doc template text
        direction_chinese = {
            'N': '北风', 'NNE': '东北风', 'NE': '东北风', 'ENE': '东北风',
            'E': '东风', 'ESE': '东南风', 'SE': '东南风', 'SSE': '东南风',
            'S': '南风', 'SSW': '西南风', 'SW': '西南风', 'WSW': '西南风',
            'W': '西风', 'WNW': '西北风', 'NW': '西北风', 'NNW': '西北风'
        }
        
        sensor_analysis_list = []
        sorted_sensor_names = sorted(self.stats_summary.keys(), key=self._natural_sort_key)
        for sensor_name in sorted_sensor_names:
            stats = self.stats_summary[sensor_name]
            main_speed_text = "2-6"
            if 'wind_speed_distribution' in stats:
                dist = sorted(stats['wind_speed_distribution'].items(), key=lambda x: x[1], reverse=True)
                if dist and dist[0][1] > 0:
                    main_speed_text = dist[0][0]
                    
            main_dir_text = "东南风"
            if 'wind_direction_distribution' in stats:
                dist2 = sorted(stats['wind_direction_distribution'].items(), key=lambda x: x[1], reverse=True)
                if dist2 and dist2[0][1] > 0:
                    raw_dir = dist2[0][0]
                    main_dir_text = direction_chinese.get(raw_dir, raw_dir)
                    
            sensor_analysis_list.append({
                'name': sensor_name,
                'main_speed': main_speed_text,
                'main_dir': main_dir_text
            })
        context['sensor_analysis_list'] = sensor_analysis_list
        return context

    def generate_word_report(self):
        print("正在生成Word格式报告...")
        try:
            from docxtpl import DocxTemplate, InlineImage
            from docx.shared import Mm
        except ImportError:
            print("❌ 缺少 docxtpl 库，请先运行: pip install docxtpl")
            return None
            
        template_file = os.path.join(str(Path(__file__).parent.parent.parent), "templates", "风速分析模版_docxtpl.docx")
        if not os.path.exists(template_file):
            print(f"模板文件不存在: {template_file}")
            return None
            
        doc = DocxTemplate(template_file)
        context = self._build_report_context()
        
        # Inject dynamic images per sensor
        time_series_images = []
        comprehensive_images = []
        sorted_sensor_names = sorted(self.wind_data.keys(), key=self._natural_sort_key)
        
        for sensor_name in sorted_sensor_names:
            # Time Series
            ts_path = self.output_dir / f"{sensor_name}风速风向时序图.png"
            if ts_path.exists():
                time_series_images.append({
                    'name': sensor_name,
                    'image': InlineImage(doc, str(ts_path), width=Mm(140))
                })
            # Comprehensive
            comp_path = self.output_dir / f"{sensor_name}综合分析图.png"
            if comp_path.exists():
                comprehensive_images.append({
                    'name': sensor_name,
                    'image': InlineImage(doc, str(comp_path), width=Mm(140))
                })
                
        context['time_series_images'] = time_series_images
        context['comprehensive_images'] = comprehensive_images
        
        try:
            doc.render(context)
            report_path = self.output_dir / f'{self.bridge_name}风速数据分析报告.docx'
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
                fallback_path = f'{self.bridge_name}风速数据分析报告.docx'
                doc.save(fallback_path)
                print(f"Word报告已保存到备用位置: {fallback_path}")
                # 备用位置也要尝试打开
                try:
                    os.startfile(fallback_path)
                except:
                    pass
                return fallback_path
            except Exception as e2:
                print(f"备用保存也失败: {e2}")
                return None
