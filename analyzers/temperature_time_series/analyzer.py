import os
from pathlib import Path
from .processor import TemperatureTimeSeriesProcessor
from .plotter import TemperatureTimeSeriesPlotter
from .reporter import TemperatureTimeSeriesReporter
#123345667
class TemperatureTimeSeriesAnalyzer:
    BRIDGE_NAME = "崖门大桥"
    
    def __init__(self, bridge_name=None, data_dir=None, output_dir=None):
        self.bridge_name = bridge_name or self.BRIDGE_NAME
        
        if data_dir is None or output_dir is None:
            try:
                from utils.analyzer_utils import AnalyzerPathManager
                path_mgr = AnalyzerPathManager(self.bridge_name)
                data_dir = data_dir or path_mgr.get_data_dir("温度")
                output_dir = output_dir or path_mgr.get_output_dir("温度")
            except Exception:
                DATA_ROOT = Path("D:/useful/03-chengxu/report_gen/数据下载")
                data_dir = data_dir or (DATA_ROOT / self.bridge_name / "温度" / "数据")
                output_dir = output_dir or (Path(__file__).parent / "temperature_time_series" / self.bridge_name)

        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        print(f"🌡️ 开始分析 {self.bridge_name} 温度数据...")
        
        processor = TemperatureTimeSeriesProcessor(self.bridge_name, self.data_dir, self.output_dir)
        if not processor.build_file_mapping():
            return False
            
        processor.load_temperature_data()
        processor.preprocess_data()
        stats_summary, global_stats = processor.analyze_basic_stats()
        temperature_data, original_data, grouped_data, file_mapping = processor.get_data()
        
        plotter = TemperatureTimeSeriesPlotter(self.bridge_name, self.output_dir, temperature_data, original_data, file_mapping)
        plotter.plot_temperature_time_series_original()
        df_temp_table = plotter.create_temperature_statistics_table(stats_summary)
        
        reporter = TemperatureTimeSeriesReporter(self.bridge_name, self.output_dir, stats_summary, global_stats, grouped_data, file_mapping)
        report_path = reporter.generate_word_report()
        
        if report_path:
            print(f"✅ {self.bridge_name} 温度分析完成！结果保存在: {self.output_dir}")
            return True
        return False
