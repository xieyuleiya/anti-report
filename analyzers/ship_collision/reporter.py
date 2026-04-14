import os
from pathlib import Path
try:
    from docxtpl import DocxTemplate, InlineImage
    from docx.shared import Mm
except ImportError:
    pass
import numpy as np
from datetime import datetime

HEAVY_DEVIATION_THRESHOLD = 4500

class ShipCollisionReporter:
    def __init__(self, bridge_name: str, output_dir: Path, navigation_data, deviation_data):
        self.bridge_name = bridge_name
        self.output_dir = output_dir
        self.navigation_data = navigation_data
        self.deviation_data = deviation_data

    def _build_report_context(self):
        """计算并准备所有填入 Word 模板的数据上下文"""
        now = datetime.now()
        context = {
            'bridge_name': self.bridge_name,
            'report_gen_time': now.strftime('%Y年%m月%d日 %H:%M:%S'),
            'report_year': now.strftime('%Y'),
            'report_month': now.strftime('%m'),
            'report_day': now.strftime('%d'),
            'report_date': now.strftime('%Y年%m月%d日'),
        }
        
        nav_count = len(self.navigation_data) if self.navigation_data is not None else 0
        dev_count = len(self.deviation_data) if self.deviation_data is not None else 0
        total_count = nav_count + dev_count
        context['nav_count'] = nav_count
        context['dev_count'] = dev_count
        context['deviation_rate'] = f"{(dev_count / total_count * 100):.2f}" if total_count > 0 else "0.00"
        
        if self.navigation_data is not None and not self.navigation_data.empty:
            start_date = self.navigation_data['EnterTime'].min()
            end_date = self.navigation_data['EnterTime'].max()
            context['start_date_str'] = start_date.strftime('%Y年%m月%d日')
            context['end_date_str'] = end_date.strftime('%Y年%m月%d日')
            
            nav_daily_counts = self.navigation_data.groupby('Date').size()
            context['avg_daily_nav'] = f"{nav_daily_counts.mean():.1f}"
            
            nav_ship_types = self.navigation_data['ShipType'].value_counts()
            context['nav_main_type'] = nav_ship_types.index[0]
            context['nav_main_type_count'] = nav_ship_types.iloc[0]
            context['nav_main_type_percentage'] = f"{(nav_ship_types.iloc[0] / nav_count * 100):.1f}"
            
            nav_direction = self.navigation_data['FromUpDown'].value_counts()
            context['nav_main_direction'] = nav_direction.index[0]
            context['nav_main_direction_count'] = nav_direction.iloc[0]
            context['nav_main_direction_percentage'] = f"{(nav_direction.iloc[0] / nav_count * 100):.1f}"
            
            if 'Tonnage' in self.navigation_data.columns:
                nav_tonnage = self.navigation_data['Tonnage'].dropna()
                if len(nav_tonnage) > 0:
                    context['nav_avg_tonnage'] = f"{nav_tonnage.mean():.1f}"
                    context['nav_max_tonnage'] = f"{nav_tonnage.max():.1f}"
                else:
                    context['nav_avg_tonnage'] = "0"
                    context['nav_max_tonnage'] = "0"
            else:
                context['nav_avg_tonnage'] = "0"
                context['nav_max_tonnage'] = "0"
        else:
            context.update({
                'start_date_str': '未知', 'end_date_str': '未知',
                'avg_daily_nav': '0', 'nav_main_type': '未知', 'nav_main_type_count': '0',
                'nav_main_type_percentage': '0', 'nav_main_direction': '未知',
                'nav_main_direction_count': '0', 'nav_main_direction_percentage': '0',
                'nav_avg_tonnage': '0', 'nav_max_tonnage': '0'
            })
            
        if self.deviation_data is not None and not self.deviation_data.empty:
            dev_daily_counts = self.deviation_data.groupby('Date').size()
            context['avg_daily_dev'] = f"{dev_daily_counts.mean():.1f}"
            
            dev_ship_types = self.deviation_data['ShipType'].value_counts()
            context['dev_main_type'] = dev_ship_types.index[0]
            context['dev_main_type_count'] = dev_ship_types.iloc[0]
            context['dev_main_type_percentage'] = f"{(dev_ship_types.iloc[0] / dev_count * 100):.1f}"
            
            dev_direction = self.deviation_data['FromUpDown'].value_counts()
            context['dev_main_direction'] = dev_direction.index[0]
            context['dev_main_direction_count'] = dev_direction.iloc[0]
            context['dev_main_direction_percentage'] = f"{(dev_direction.iloc[0] / dev_count * 100):.1f}"
            
            if 'Tonnage' in self.deviation_data.columns:
                dev_tonnage = self.deviation_data['Tonnage'].dropna()
                if len(dev_tonnage) > 0:
                    context['dev_avg_tonnage'] = f"{dev_tonnage.mean():.1f}"
                    context['dev_max_tonnage'] = f"{dev_tonnage.max():.1f}"
                else:
                    context['dev_avg_tonnage'] = "0"
                    context['dev_max_tonnage'] = "0"
            else:
                context['dev_avg_tonnage'] = "0"
                context['dev_max_tonnage'] = "0"
        else:
            context.update({
                'avg_daily_dev': '0', 'dev_main_type': '未知', 'dev_main_type_count': '0',
                'dev_main_type_percentage': '0', 'dev_main_direction': '未知',
                'dev_main_direction_count': '0', 'dev_main_direction_percentage': '0',
                'dev_avg_tonnage': '0', 'dev_max_tonnage': '0'
            })
            
        context['heavy_threshold'] = HEAVY_DEVIATION_THRESHOLD
        heavy_list = []
        if self.deviation_data is not None and not self.deviation_data.empty and 'Tonnage' in self.deviation_data.columns:
            heavy_deviation = self.deviation_data[self.deviation_data['Tonnage'] > HEAVY_DEVIATION_THRESHOLD]
            context['heavy_count'] = len(heavy_deviation)
            context['heavy_percentage'] = f"{(len(heavy_deviation)/len(self.deviation_data)*100):.1f}" if len(self.deviation_data)>0 else "0.0"
            if not heavy_deviation.empty:
                context['heavy_avg'] = f"{heavy_deviation['Tonnage'].mean():.1f}"
                context['heavy_max'] = f"{heavy_deviation['Tonnage'].max():.1f}"
                context['heavy_min'] = f"{heavy_deviation['Tonnage'].min():.1f}"
                
                for i, (_, row) in enumerate(heavy_deviation.iterrows(), 1):
                    heavy_list.append({
                        'idx': i,
                        'mmsi': str(row['MMSI']),
                        'name': str(row.get('ChineseName', row.get('EnglishName', '未知'))),
                        'tonnage': f"{row['Tonnage']:.1f}",
                        'enter_time': str(row['EnterTime']),
                        'direction': str(row['FromUpDown'])
                    })
            else:
                context['heavy_avg'], context['heavy_max'], context['heavy_min'] = "0", "0", "0"
        else:
            context['heavy_count'] = 0
            context['heavy_percentage'] = "0.0"
            context['heavy_avg'], context['heavy_max'], context['heavy_min'] = "0", "0", "0"
            
        context['heavy_deviation_list'] = heavy_list
        return context

    def generate_word_report(self):
        print("正在生成Word格式报告...")
        try:
            from docxtpl import DocxTemplate, InlineImage
            from docx.shared import Mm
        except ImportError:
            print("❌ 缺少 docxtpl 库，请先运行: pip install docxtpl")
            return None

        template_file = os.path.join(str(Path(__file__).parent.parent.parent), "templates", "船撞分析模版_docxtpl.docx")
        if not os.path.exists(template_file):
            print(f"模板文件不存在: {template_file}")
            return None
            
        doc = DocxTemplate(template_file)
        context = self._build_report_context()
        
        for img_key, img_file in [
            ('plot_daily_nav', '每日助航船舶数量统计.png'),
            ('plot_daily_dev', '每日偏航船舶数量统计.png'),
            ('plot_ship_type', '船舶类型分布.png'),
            ('plot_direction', '航行方向分布.png'),
            ('plot_nav_tonnage', '助航船舶吨位分布.png'),
            ('plot_dev_tonnage', '偏航船舶吨位分布.png')
        ]:
            img_path = self.output_dir / img_file
            if img_path.exists():
                context[img_key] = InlineImage(doc, str(img_path), width=Mm(140))
            else:
                context[img_key] = '[图表缺失]'

        try:
            doc.render(context)
            report_path = self.output_dir / f'{self.bridge_name}船撞数据分析报告.docx'
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
                fallback_path = f'{self.bridge_name}船撞数据分析报告.docx'
                doc.save(fallback_path)
                print(f"Word报告已保存到备用位置: {fallback_path}")
                try:
                    os.startfile(fallback_path)
                except:
                    pass
                return fallback_path
            except Exception as e2:
                print(f"备用保存失败: {e2}")
                return None
