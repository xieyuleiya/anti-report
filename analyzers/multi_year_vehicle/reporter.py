import os
from pathlib import Path
from datetime import datetime
try:
    from docxtpl import DocxTemplate, InlineImage
    from docx.shared import Mm
except ImportError:
    pass

class MultiYearVehicleReporter:
    def __init__(self, bridge_name, output_dir, stats):
        self.bridge_name = bridge_name
        self.output_dir = Path(output_dir)
        self.stats = stats

    def _build_context(self):
        s = self.stats
        years = s['years']
        directions = s['directions']
        
        now = datetime.now()
        c = {
            'bridge_name': self.bridge_name,
            'report_gen_time': now.strftime('%Y年%m月%d日 %H:%M:%S'),
            'report_year': now.strftime('%Y'),
            'report_month': now.strftime('%m'),
            'report_day': now.strftime('%d'),
            'report_date': now.strftime('%Y年%m月%d日'),
            'years': years,
            'years_str': "、".join(years),
            'directions': directions,
            'yearly_summaries': []
        }
        
        # Build yearly summaries for text
        for y in years:
            sum_y = s['yearly_summary'][y]
            c['yearly_summaries'].append({
                'year': y,
                'total_vehicles_wan': f"{sum_y['total_vehicles']/10000:.1f}"
            })
            
        # Direction summaries
        direction_infos = []
        for d in directions:
            d_years = []
            for y in years:
                cnt = s['yearly_summary'][y]['direction_counts'][d]
                d_years.append({'year': y, 'count_wan': f"{cnt}/10000:.1f"})
            direction_infos.append({'name': d, 'years': d_years})
        c['direction_infos'] = direction_infos
        
        # Trend Analysis
        total_counts = [s['yearly_summary'][y]['total_vehicles'] for y in years]
        if len(total_counts) > 1:
            if total_counts[-1] > total_counts[0]:
                trend = "呈上升趋势"
                rate = ((total_counts[-1] - total_counts[0]) / total_counts[0]) * 100
                c['traffic_trend'] = f'从整体车流量来看，{years[0]}年到{years[-1]}年{trend}，增长率约{rate:.1f}%。'
            elif total_counts[-1] < total_counts[0]:
                trend = "呈下降趋势"
                rate = ((total_counts[0] - total_counts[-1]) / total_counts[0]) * 100
                c['traffic_trend'] = f'从整体车流量来看，{years[0]}年到{years[-1]}年{trend}，下降率约{rate:.1f}%。'
            else:
                c['traffic_trend'] = '从整体车流量来看，各年度基本保持稳定。'
        else:
            c['traffic_trend'] = '由于只有一个年度的数据，无法进行趋势分析。'

        # Overweight trend
        overweight_trends = []
        for y in years:
            total_ow = sum(s['yearly_direction_stats'][y][d]['overweight_stats']['over_51_45_count'] for d in directions)
            total_v = sum(s['yearly_direction_stats'][y][d]['count'] for d in directions)
            rate = (total_ow / total_v * 100) if total_v > 0 else 0
            overweight_trends.append({'year': y, 'rate': f"{rate:.2f}%", 'raw_rate': rate})
        c['overweight_trends'] = overweight_trends
        
        if len(overweight_trends) > 1:
            if overweight_trends[-1]['raw_rate'] > overweight_trends[0]['raw_rate']:
                c['overweight_trend_summary'] = '整体呈上升趋势。'
            elif overweight_trends[-1]['raw_rate'] < overweight_trends[0]['raw_rate']:
                c['overweight_trend_summary'] = '整体呈下降趋势。'
            else:
                c['overweight_trend_summary'] = '基本保持稳定。'
        else:
            c['overweight_trend_summary'] = ''
            
        return c

    def generate_report(self):
        print("正在生成Word格式报告...")
        try:
            from docxtpl import DocxTemplate, InlineImage
            from docx.shared import Mm
        except ImportError:
            print("❌ 缺少 docxtpl 库，请先运行: pip install docxtpl")
            return None
            
        template_path = Path(__file__).parent.parent.parent / "templates" / "多年度车辆对比分析模版_docxtpl.docx"
        if not template_path.exists():
            print(f"❌ 模板不存在: {template_path}")
            return None
            
        doc = DocxTemplate(str(template_path))
        context = self._build_context()
        
        # Inject images
        images = {}
        chart_files = [
            '年度总车流量对比.png', '各方向年度车流量对比.png', '轴数统计年度对比.png',
            '车牌颜色统计年度对比.png', '车重分布年度对比.png',
            '分时流量年度综合对比.png', '随时间日流量年度综合对比.png'
        ]
        
        for cf in chart_files:
            img_path = self.output_dir / cf
            if img_path.exists():
                tag = cf.split('.')[0]
                key = f"img_{tag.replace('对比', '').replace('统计', '')}"
                images[key] = InlineImage(doc, str(img_path), width=Mm(140))
        
        context.update(images)
        
        try:
            doc.render(context)
            report_path = self.output_dir / f"{self.bridge_name}多年度车辆对比报告.docx"
            doc.save(str(report_path))
            print(f"✅ Word报告已生成并尝试打开: {report_path}")
            
            # 自动打开文档
            try:
                os.startfile(str(report_path))
            except Exception as e_open:
                print(f"无法自动打开文档: {e_open}")
                
            return str(report_path)
        except Exception as e:
            print(f"❌ 生成报告失败: {e}")
            try:
                fallback_path = f"{self.bridge_name}多年度车辆对比报告.docx"
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
