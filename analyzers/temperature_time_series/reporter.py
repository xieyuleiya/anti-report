import os
from pathlib import Path
from datetime import datetime
import re

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

class TemperatureTimeSeriesReporter:
    def __init__(self, bridge_name: str, output_dir: Path, stats_summary: dict, global_stats: dict, grouped_data: dict, file_mapping: dict):
        self.bridge_name = bridge_name
        self.output_dir = output_dir
        self.stats_summary = stats_summary
        self.global_stats = global_stats
        self.grouped_data = grouped_data
        self.file_mapping = file_mapping

    def _build_report_context(self):
        now = datetime.now()
        c = {
            'bridge_name': self.bridge_name,
            'report_gen_time': now.strftime('%Y年%m月%d日 %H:%M:%S'),
            'report_year': now.strftime('%Y'),
            'report_month': now.strftime('%m'),
            'report_day': now.strftime('%d'),
            'report_date': now.strftime('%Y年%m月%d日'),
            'total_sensors': len(self.stats_summary),
            'total_groups': len(self.grouped_data)
        }
        
        c['groups_info'] = [{'name': k, 'count': len(v)} for k, v in self.grouped_data.items()]
        
        if self.global_stats:
            c['has_extremes'] = True
            c['max_temp'] = f"{self.global_stats['max_temp']:.2f}"
            c['max_temp_time'] = self.global_stats['max_temp_time'].strftime('%Y年%m月%d日 %H:%M:%S')
            c['max_group'] = self.global_stats['max_temp_group']
            c['max_sensor'] = self.global_stats['max_temp_sensor'].split('（')[0]
            
            c['min_temp'] = f"{self.global_stats['min_temp']:.2f}"
            c['min_temp_time'] = self.global_stats['min_temp_time'].strftime('%Y年%m月%d日 %H:%M:%S')
            c['min_group'] = self.global_stats['min_temp_group']
            c['min_sensor'] = self.global_stats['min_temp_sensor'].split('（')[0]
            c['temp_range'] = f"{self.global_stats['max_temp'] - self.global_stats['min_temp']:.2f}"
        else:
            c['has_extremes'] = False
            
        location_groups = {}
        for sensor_name in self.stats_summary.keys():
            location_info = "未知"
            for _, attrs in self.file_mapping.items():
                if attrs.get('sensor_name') == sensor_name:
                    location_info = attrs.get('group_key', "未知")
                    break
            if location_info not in location_groups:
                location_groups[location_info] = []
            location_groups[location_info].append(sensor_name)
            
        table_rows = []
        sorted_locations = sorted(location_groups.keys(), key=natural_sort_key)
        for location_info in sorted_locations:
            sensor_names = location_groups[location_info]
            sorted_sensor_names = sorted(sensor_names, key=natural_sort_key)
            for sensor_name in sorted_sensor_names:
                stats = self.stats_summary[sensor_name]
                simplified_name = sensor_name.split('（')[0]
                table_rows.append({
                    'location': location_info, # 每一行都填充位置
                    'sensor': simplified_name,
                    'mean': f"{stats['temp_mean']:.2f}",
                    'max': f"{stats['temp_max']:.2f}",
                    'min': f"{stats['temp_min']:.2f}",
                    'range': f"{stats['temp_range']:.2f}"
                })
        c['table_rows'] = table_rows
        return c

    def _merge_vertical_cells(self, doc_obj):
        """对文档中包含'位置'列的所有表格执行垂直合并"""
        if not doc_obj.tables:
            return
            
        from docx.enum.table import WD_ALIGN_VERTICAL
        
        merged_any = False
        for i, table in enumerate(doc_obj.tables):
            # 1. 查找包含“位置”关键字的列索引
            target_col_idx = -1
            if len(table.rows) > 0:
                for j, cell in enumerate(table.rows[0].cells):
                    if "位置" in cell.text:
                        target_col_idx = j
                        break
            
            if target_col_idx == -1:
                continue
            
            print(f"DEBUG: 正在对表格 {i+1} 的第 {target_col_idx+1} 列 ('%s') 执行自动合并..." % table.rows[0].cells[target_col_idx].text.strip())
            
            rows = table.rows
            start_row_idx = 1 # 跳过标题行
            while start_row_idx < len(rows):
                current_text = rows[start_row_idx].cells[target_col_idx].text.strip()
                if not current_text:
                    start_row_idx += 1
                    continue
                
                # 向下寻找相同的内容
                end_row_idx = start_row_idx + 1
                while end_row_idx < len(rows):
                    next_text = rows[end_row_idx].cells[target_col_idx].text.strip()
                    if next_text == current_text:
                        end_row_idx += 1
                    else:
                        break
                
                # 如果发现连续相同的内容，执行合并
                if end_row_idx - start_row_idx > 1:
                    try:
                        starting_cell = rows[start_row_idx].cells[target_col_idx]
                        ending_cell = rows[end_row_idx - 1].cells[target_col_idx]
                        # 执行合并
                        combined = starting_cell.merge(ending_cell)
                        combined.text = current_text # 重新设置文本确保干净
                        combined.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                        merged_any = True
                    except Exception as e_inner:
                        print(f"DEBUG: 合并单元格时发生微调异常: {e_inner}")
                
                start_row_idx = end_row_idx
        
        if not merged_any:
            print("DEBUG: 扫描完毕，未发现可合并的内容。")

    def generate_word_report(self):
        print("📄 正在准备Word报告...")
        try:
            from docxtpl import DocxTemplate, InlineImage
            from docx.shared import Mm
        except ImportError:
            print("❌ 缺少 docxtpl 库")
            return None
            
        template_file = os.path.join(str(Path(__file__).parent.parent.parent), "templates", "温度时序图分析模版_docxtpl.docx")
        if not os.path.exists(template_file):
            print(f"模板文件不存在: {template_file}")
            return None
            
        doc = DocxTemplate(template_file)
        context = self._build_report_context()
        
        group_images = []
        for group_key in sorted(self.grouped_data.keys(), key=natural_sort_key):
            image_path = self.output_dir / f"{group_key}温度时序图.png"
            if image_path.exists():
                group_images.append({
                    'name': group_key,
                    'image': InlineImage(doc, str(image_path), width=Mm(140))
                })
        context['group_images'] = group_images

        try:
            doc.render(context)
            
            # 重要：在 render 之后，doc 对象内部的 XML 已更新。直接操作 doc.get_docx()
            try:
                # docxtpl 的 DocxTemplate 本身就持有 docx 文档的所有方法
                self._merge_vertical_cells(doc)
            except Exception as e_merge:
                print(f"⚠️ 自动处理表格样式失败: {e_merge}")
            
            report_path = self.output_dir / f'{self.bridge_name}温度时间序列分析报告.docx'
            doc.save(str(report_path))
            print(f"✅ Word报告已生成并尝试打开: {report_path}")
            
            try:
                os.startfile(str(report_path))
            except:
                pass
                
            return str(report_path)
        except Exception as e:
            print(f"❌ 保存Word报告失败: {e}")
            try:
                fallback_path = f'{self.bridge_name}温度时间序列分析报告.docx'
                doc.save(fallback_path)
                os.startfile(fallback_path)
                return fallback_path
            except:
                return None
