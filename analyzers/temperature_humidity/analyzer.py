import os
from pathlib import Path
from config import get_analyzer_data_dir, get_analyzer_output_dir
from .processor import TemperatureHumidityProcessor
from .plotter import TemperatureHumidityPlotter
from .reporter import TemperatureHumidityReporter

BRIDGE_NAME = "金马大桥"

class TemperatureHumidityAnalyzer:
    def __init__(self, bridge_name=None, data_dir=None, output_dir=None, template_path=None):
        self.bridge_name = bridge_name if bridge_name else BRIDGE_NAME
        
        if data_dir is None or output_dir is None:
            try:
                from utils.analyzer_utils import AnalyzerPathManager
                path_mgr = AnalyzerPathManager(self.bridge_name)
                data_dir = data_dir or path_mgr.get_data_dir("温湿度")
                output_dir = output_dir or path_mgr.get_output_dir("温湿度")
            except Exception:
                DATA_ROOT = Path("D:/useful/03-chengxu/report_gen/数据下载")
                data_dir = data_dir or (DATA_ROOT / self.bridge_name / "原始数据" / "温湿度")
                output_dir = output_dir or (Path(__file__).parent / "分析结果" / self.bridge_name)

        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template_path = str(template_path) if template_path else ""

    def run(self):
        return self.run_analysis()
        
    def run_analysis(self):
        print(f"🌡️ 开始分析 {self.bridge_name} 温湿度数据...")
        
        processor = TemperatureHumidityProcessor(self.bridge_name, self.data_dir)
        th_data = processor.load_data()
        
        if not th_data:
            print("没有可用的数据进行分析")
            return False
            
        processor.preprocess_data()
        stats_summary = processor.analyze_basic_stats()
        humidity_threshold = processor.get_humidity_threshold()
        
        plotter = TemperatureHumidityPlotter(self.bridge_name, self.output_dir, th_data, humidity_threshold)
        plotter.plot_all_stations_temperature_humidity()
        plotter.plot_temperature_humidity_distribution()
        plotter.plot_humidity_exceedance_bar_chart()
        df_temp = plotter.create_temperature_statistics_table(stats_summary)
        df_hum = plotter.create_humidity_statistics_table(stats_summary)
        
        reporter = TemperatureHumidityReporter(self.bridge_name, self.output_dir, th_data, stats_summary, humidity_threshold, df_temp, df_hum)
        report_path = reporter.generate_word_report()
        
        if report_path:
            print(f"✅ {self.bridge_name} 温湿度分析完成！结果保存在: {self.output_dir}")
            return True
        return False
