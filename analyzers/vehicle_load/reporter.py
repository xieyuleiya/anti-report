import os
from pathlib import Path
try:
    from docxtpl import DocxTemplate, InlineImage
    from docx.shared import Mm
except ImportError:
    pass
from datetime import datetime

class VehicleLoadReporter:
    def __init__(self, bridge_name: str, output_dir: Path, direction1_name: str, direction2_name: str, stats: dict, df1, df2, df_combined):
        self.bridge_name = bridge_name
        self.output_dir = output_dir
        self.direction1_name = direction1_name
        self.direction2_name = direction2_name
        self.stats = stats
        self.df1 = df1
        self.df2 = df2
        self.df_combined = df_combined
        
    def find_two_peaks(self, daily_stats):
        sorted_data = daily_stats.sort_index()
        mean_traffic = sorted_data.mean()
        std_traffic = sorted_data.std()
        threshold = mean_traffic + 1.0 * std_traffic
        high_traffic_days = sorted_data[sorted_data > threshold]
        
        if len(high_traffic_days) == 0:
            sorted_values = sorted_data.sort_values(ascending=False)
            peak1_date = sorted_values.index[0]
            peak1_val = sorted_values.iloc[0]
            peak2_date = sorted_values.index[1] if len(sorted_values) > 1 else peak1_date
            peak2_val = sorted_values.iloc[1] if len(sorted_values) > 1 else peak1_val
            return peak1_date, peak2_date, peak1_val, peak2_val
        
        peak_groups = []
        current_group = [high_traffic_days.index[0]]
        for i in range(1, len(high_traffic_days)):
            current_date = high_traffic_days.index[i]
            prev_date = current_group[-1]
            if (current_date - prev_date).days <= 7:
                current_group.append(current_date)
            else:
                peak_groups.append(current_group)
                current_group = [current_date]
        if current_group:
            peak_groups.append(current_group)
        
        peak_maxes = []
        for group in peak_groups:
            group_data = sorted_data[group]
            max_date = group_data.idxmax()
            max_val = group_data.max()
            peak_maxes.append((max_date, max_val))
        
        peak_maxes.sort(key=lambda x: x[1], reverse=True)
        if len(peak_maxes) >= 2:
            peak1_date, peak1_val = peak_maxes[0]
            peak2_date, peak2_val = None, None
            for i in range(1, len(peak_maxes)):
                candidate_date, candidate_val = peak_maxes[i]
                if abs((peak1_date - candidate_date).days) >= 30:
                    peak2_date, peak2_val = candidate_date, candidate_val
                    break
            if peak2_date is None:
                peak2_date, peak2_val = peak_maxes[1] if len(peak_maxes) > 1 else peak_maxes[0]
            return peak1_date, peak2_date, peak1_val, peak2_val
        else:
            if len(peak_maxes) == 1:
                peak1_date, peak1_val = peak_maxes[0]
                sorted_values = sorted_data.sort_values(ascending=False)
                peak2_date = sorted_values.index[1] if len(sorted_values) > 1 else peak1_date
                peak2_val = sorted_values.iloc[1] if len(sorted_values) > 1 else peak1_val
                return peak1_date, peak2_date, peak1_val, peak2_val
            else:
                sorted_values = sorted_data.sort_values(ascending=False)
                peak1_date = sorted_values.index[0]
                peak1_val = sorted_values.iloc[0]
                peak2_date = sorted_values.index[1] if len(sorted_values) > 1 else peak1_date
                peak2_val = sorted_values.iloc[1] if len(sorted_values) > 1 else peak1_val
                return peak1_date, peak2_date, peak1_val, peak2_val

    def _build_report_context(self):
        s = self.stats
        total_vehicles = s['total_vehicles']
        direction1_count = s['direction1_count']
        direction2_count = s['direction2_count']
        
        now = datetime.now()
        c = {
            'bridge_name': self.bridge_name,
            'report_gen_time': now.strftime('%Y年%m月%d日 %H:%M:%S'),
            'report_year': now.strftime('%Y'),
            'report_month': now.strftime('%m'),
            'report_day': now.strftime('%d'),
            'report_date': now.strftime('%Y年%m月%d日'),
            'start_date_str': s['start_date'].strftime('%Y年%m月%d日'),
            'end_date_str': s['end_date'].strftime('%Y年%m月%d日'),
            'total_vehicles': f"{total_vehicles}",
            'total_vehicles_w': f"{total_vehicles/10000:.1f}",
            'direction1_name': self.direction1_name,
            'direction2_name': self.direction2_name,
            'direction1_count': f"{direction1_count}",
            'direction2_count': f"{direction2_count}",
            'direction1_count_w': f"{direction1_count/10000:.1f}",
            'direction2_count_w': f"{direction2_count/10000:.1f}",
            'direction1_ratio': f"{(direction1_count/total_vehicles*100):.1f}" if total_vehicles > 0 else "0",
            'direction2_ratio': f"{(direction2_count/total_vehicles*100):.1f}" if total_vehicles > 0 else "0",
        }
        
        # DIR1 Stats
        c['d1_main_axle'] = s['axle_stats1'].index[0]
        c['d1_sec_axle'] = s['axle_stats1'].index[1] if len(s['axle_stats1']) > 1 else ""
        top_colors1 = s['color_stats1'].head(2)
        c['d1_main_colors'] = "、".join(list(top_colors1.index))
        c['d1_colors_pct'] = f"{(top_colors1.sum() / len(self.df1) * 100):.1f}"
        top_provinces1 = list(s['province_stats1'].head(3).index)
        c['d1_main_provinces'] = ", ".join(top_provinces1)
        c['d1_main_type'] = s['type_stats1'].index[0]
        c['d1_type_pct'] = f"{(s['type_stats1'].iloc[0] / len(self.df1) * 100):.1f}"
        c['d1_w_under_10_pct'] = f"{s['weight_stats1']['percentages']['10吨以下']:.1f}"
        c['d1_w_40_50_count'] = s['weight_stats1']['counts']['40-51.45吨']
        c['d1_w_40_50_pct'] = f"{(c['d1_w_40_50_count'] / len(self.df1) * 100):.1f}"
        c['d1_w_over_51_count'] = s['overweight_stats1']['over_51_45_count']
        c['d1_w_over_51_pct'] = f"{s['overweight_stats1']['over_51_45_percentage']:.2f}"
        c['d1_max_weight'] = f"{s['weight_stats1']['max_weight']:.1f}"
        
        d1_p1_d, d1_p2_d, d1_p1_v, d1_p2_v = self.find_two_peaks(s['daily_stats1'])
        avg_d1 = s['daily_stats1'].mean()
        c.update({
            'd1_peak1_date': d1_p1_d.strftime('%m月%d日'),
            'd1_peak2_date': d1_p2_d.strftime('%m月%d日'),
            'd1_peak1_val': d1_p1_v,
            'd1_peak2_val': d1_p2_v,
            'd1_peak1_ratio': f"{d1_p1_v / avg_d1:.1f}" if avg_d1 > 0 else "1.0",
            'd1_peak2_ratio': f"{d1_p2_v / avg_d1:.1f}" if avg_d1 > 0 else "1.0"
        })

        # DIR2 Stats
        c['d2_main_axle'] = s['axle_stats2'].index[0]
        c['d2_sec_axle'] = s['axle_stats2'].index[1] if len(s['axle_stats2']) > 1 else ""
        top_colors2 = s['color_stats2'].head(2)
        c['d2_main_colors'] = "、".join(list(top_colors2.index))
        c['d2_colors_pct'] = f"{(top_colors2.sum() / len(self.df2) * 100):.1f}"
        top_provinces2 = list(s['province_stats2'].head(3).index)
        c['d2_main_provinces'] = ", ".join(top_provinces2)
        c['d2_main_type'] = s['type_stats2'].index[0]
        c['d2_type_pct'] = f"{(s['type_stats2'].iloc[0] / len(self.df2) * 100):.1f}"
        c['d2_w_under_10_pct'] = f"{s['weight_stats2']['percentages']['10吨以下']:.1f}"
        c['d2_w_40_50_count'] = s['weight_stats2']['counts']['40-51.45吨']
        c['d2_w_40_50_pct'] = f"{(c['d2_w_40_50_count'] / len(self.df2) * 100):.1f}"
        c['d2_w_over_51_count'] = s['overweight_stats2']['over_51_45_count']
        c['d2_w_over_51_pct'] = f"{s['overweight_stats2']['over_51_45_percentage']:.2f}"
        c['d2_max_weight'] = f"{s['weight_stats2']['max_weight']:.1f}"
        
        d2_p1_d, d2_p2_d, d2_p1_v, d2_p2_v = self.find_two_peaks(s['daily_stats2'])
        avg_d2 = s['daily_stats2'].mean()
        c.update({
            'd2_peak1_date': d2_p1_d.strftime('%m月%d日'),
            'd2_peak2_date': d2_p2_d.strftime('%m月%d日'),
            'd2_peak1_val': d2_p1_v,
            'd2_peak2_val': d2_p2_v,
            'd2_peak1_ratio': f"{d2_p1_v / avg_d2:.1f}" if avg_d2 > 0 else "1.0",
            'd2_peak2_ratio': f"{d2_p2_v / avg_d2:.1f}" if avg_d2 > 0 else "1.0"
        })

        # Global analysis
        avg_weight_under_10 = (s['weight_stats1']['percentages']['10吨以下'] + s['weight_stats2']['percentages']['10吨以下']) / 2
        total_weight_40_51_45 = c['d1_w_40_50_count'] + c['d2_w_40_50_count']
        weight_40_51_45_pct = (total_weight_40_51_45 / total_vehicles) * 100
        over_51_45_count = c['d1_w_over_51_count'] + c['d2_w_over_51_count']
        over_51_45_pct = (over_51_45_count / total_vehicles) * 100
        over_60_count = s['overweight_stats1']['over_60_count'] + s['overweight_stats2']['over_60_count']
        c.update({
            'g_w_under_10_pct': f"{avg_weight_under_10:.1f}",
            'g_w_40_50_count': total_weight_40_51_45,
            'g_w_40_50_pct': f"{weight_40_51_45_pct:.1f}",
            'g_w_over_51_count': over_51_45_count,
            'g_w_over_51_pct': f"{over_51_45_pct:.2f}",
            'g_w_over_60_count': over_60_count
        })

        # Hourly Analysis
        hourly1 = s['hourly_stats1']
        hourly2 = s['hourly_stats2']
        max_hourly_traffic = max(hourly1.max(), hourly2.max())
        peak_hours = (hourly1 + hourly2).nlargest(3)
        c['peak_hours_text'] = "、".join([f"{hour}点" for hour in peak_hours.index])
        c['max_hourly_traffic'] = f"{max_hourly_traffic:.0f}"
        
        if max_hourly_traffic < 100: c['traffic_level'] = "整体车流量较小"
        elif max_hourly_traffic < 500: c['traffic_level'] = "整体车流量中等"
        else: c['traffic_level'] = "整体车流量较大"

        daytime1, daytime2 = hourly1[6:19].sum(), hourly2[6:19].sum()
        daytime_diff = abs(daytime1 - daytime2) / max(daytime1, daytime2) * 100 if max(daytime1, daytime2) > 0 else 0
        if daytime_diff > 20: c['traffic_diff_desc'] = "左右两幅白天车流量相差较大"
        elif daytime_diff > 10: c['traffic_diff_desc'] = "左右两幅白天车流量存在一定差异"
        else: c['traffic_diff_desc'] = "左右两幅白天车流量基本平衡"

        nighttime1 = hourly1[0:6].sum() + hourly1[19:24].sum()
        nighttime2 = hourly2[0:6].sum() + hourly2[19:24].sum()
        nighttime_diff = abs(nighttime1 - nighttime2) / max(nighttime1, nighttime2) * 100 if max(nighttime1, nighttime2) > 0 else 0
        c['night_desc'] = "凌晨时段存在差异" if nighttime_diff > 20 else "凌晨时段基本持平"

        avg_night_heavy = (s.get('night_heavy_ratio1', 0) + s.get('night_heavy_ratio2', 0)) / 2
        c['heavy_desc'] = "夜间0点到清晨8点重车行驶较多" if avg_night_heavy > 0.3 else "夜间重车行驶相对较少"

        # Balance Analysis
        weight_under_10_diff = abs(s['weight_stats1']['percentages']['10吨以下'] - s['weight_stats2']['percentages']['10吨以下'])
        weight_40_51_diff = abs(c['d1_w_40_50_count']/len(self.df1)*100 - c['d2_w_40_50_count']/len(self.df2)*100)
        c['balance_desc_weight'] = "存在一定的偏载现象" if (weight_under_10_diff > 5 or weight_40_51_diff > 5) else "左右幅通行车辆吨位基本持平，不存在较明显的偏载现象"

        c['axle_range_desc'] = "2~6轴"
        c['axle_desc_list'] = "0~10t、10~30t、20~40t、20~50t、40~60t"
        
        traffic_diff_all = abs(direction1_count - direction2_count) / total_vehicles * 100
        if traffic_diff_all < 5: c['balance_desc_traffic'] = "左右幅车流基本平衡"
        elif traffic_diff_all < 15: c['balance_desc_traffic'] = "左右幅车流存在一定差异"
        else: c['balance_desc_traffic'] = "左右幅车流差异较大"

        main_axle1, main_axle2 = s['axle_stats1'].index[0], s['axle_stats2'].index[0]
        c['final_axle_desc'] = f"{main_axle1}轴" if main_axle1 == main_axle2 else f"{main_axle1}轴和{main_axle2}轴"
        main_type1, main_type2 = s['type_stats1'].index[0], s['type_stats2'].index[0]
        c['final_type_desc'] = main_type1 if main_type1 == main_type2 else f"{main_type1}和{main_type2}"
        
        set1, set2 = set(list(top_colors1.index)), set(list(top_colors2.index))
        if set1 == set2: c['final_color_desc'] = "、".join(set1)
        else: c['final_color_desc'] = f"{'、'.join(set1)}和{'、'.join(set2)}"
        
        all_provinces = list(set(top_provinces1 + top_provinces2))[:5]
        c['final_provinces_desc'] = ", ".join(all_provinces)

        return c

    def generate_word_report(self):
        print("正在生成Word格式报告...")
        try:
            from docxtpl import DocxTemplate, InlineImage
            from docx.shared import Mm
        except ImportError:
            print("❌ 缺少 docxtpl 库，请先运行: pip install docxtpl")
            return None
            
        template_file = os.path.join(str(Path(__file__).parent.parent.parent), "templates", "车辆荷载分析模版_docxtpl.docx")
        if not os.path.exists(template_file):
            print(f"模板文件不存在: {template_file}")
            return None
            
        doc = DocxTemplate(template_file)
        context = self._build_report_context()
        
        # Inject standard charts
        for img_key, img_file in [
            ('plot_axle_stats', '轴数统计结果.png'),
            ('plot_color_stats', '车牌颜色统计结果.png'),
            ('plot_type_stats', '车型统计结果.png'),
            ('plot_province_stats', '归属地统计结果.png'),
            ('plot_weight_stats', '车重统计结果.png'),
            ('plot_daily_traffic', '每日车流量统计结果.png'),
            ('plot_hourly_traffic', '分时流量统计结果.png'),
            ('plot_dual_hourly', '双向分时流量对比.png'),
            ('plot_dual_weight', '双向车辆平均重量统计.png')
        ]:
            img_path = self.output_dir / img_file
            if img_path.exists():
                context[img_key] = InlineImage(doc, str(img_path), width=Mm(140))
            else:
                context[img_key] = '[图表缺失]'

        # Inject dynamic axle distributions
        axle_images = []
        for axle in range(2, 7):
            axle_path = self.output_dir / f'{axle}轴车车重分布.png'
            if axle_path.exists():
                axle_images.append({
                    'name': f'{axle}轴车车重分布',
                    'image': InlineImage(doc, str(axle_path), width=Mm(140))
                })
        context['axle_images'] = axle_images

        try:
            doc.render(context)
            report_path = self.output_dir / f'{self.bridge_name}车辆荷载分析报告.docx'
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
                fallback_path = f'{self.bridge_name}车辆荷载分析报告.docx'
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
