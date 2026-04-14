import os
from pathlib import Path
from config import get_analyzer_data_dir, get_analyzer_output_dir
from .processor import WindSpeedProcessor
from .plotter import WindSpeedPlotter
from .reporter import WindSpeedReporter

BRIDGE_NAME = "乌石北江特大桥"

class WindSpeedAnalyzer:
    def __init__(self, bridge_name=None, data_dir=None, output_dir=None, excel_path=None):
        self.bridge_name = bridge_name if bridge_name else BRIDGE_NAME
        
        if data_dir is None or output_dir is None:
            try:
                from utils.analyzer_utils import AnalyzerPathManager
                path_mgr = AnalyzerPathManager(self.bridge_name)
                data_dir = data_dir or path_mgr.get_data_dir("风速")
                output_dir = output_dir or path_mgr.get_output_dir("风速")
            except Exception:
                DATA_ROOT = Path("D:/useful/03-chengxu/report_gen/数据下载")
                data_dir = data_dir or (DATA_ROOT / self.bridge_name / "风速" / "数据")
                output_dir = output_dir or (Path(__file__).parent / "fengsu" / self.bridge_name)

        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.excel_path = excel_path or Path("D:/useful/01-work file/07.报告/00-自动报告目录/00-基础资料/桥梁测点通道.xlsx")

    def run(self):
        return self.run_analysis()
        
    def run_analysis(self):
        print(f"🌪️ 开始分析 {self.bridge_name} 风速数据...")
        
        processor = WindSpeedProcessor(
            bridge_name=self.bridge_name, 
            data_dir=self.data_dir, 
            output_dir=self.output_dir, 
            excel_path=self.excel_path
        )
        if not processor.load_excel_data(): return False
        
        # 筛选特定桥梁
        filtered_data = processor.excel_data[processor.excel_data.iloc[:, 0] == self.bridge_name]
        if len(filtered_data) == 0:
            print(f"❌ 未找到桥名 {self.bridge_name} 的数据")
            return False
            
        if not processor.build_file_mapping(filtered_data): return False
        
        processor.load_wind_data()
        stats_summary, global_stats = processor.analyze_wind_statistics()
        wind_data = processor.get_wind_data()
        orig_data = processor.get_original_data()
        
        plotter = WindSpeedPlotter(self.bridge_name, self.output_dir, orig_data, wind_data)
        plotter.plot_wind_time_series()
        plotter.plot_comprehensive_wind_analysis()
        plotter.plot_wind_rose()
        df_wind = plotter.create_wind_statistics_table(stats_summary)
        
        reporter = WindSpeedReporter(self.bridge_name, self.output_dir, wind_data, orig_data, stats_summary, global_stats, df_wind)
        report_path = reporter.generate_word_report()
        
        if report_path:
            print(f"✅ {self.bridge_name} 风速分析完成！结果保存在: {self.output_dir}")
            return True
        return False
