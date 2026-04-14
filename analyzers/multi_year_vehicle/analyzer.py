import os
from pathlib import Path
from .processor import MultiYearVehicleProcessor
from .plotter import MultiYearVehiclePlotter
from .reporter import MultiYearVehicleReporter

class MultiYearVehicleAnalyzer:
    def __init__(self, bridge_name, data_dir=None, output_dir=None):
        self.bridge_name = bridge_name
        
        # Default path handling
        if data_dir is None or output_dir is None:
            try:
                from utils.analyzer_utils import AnalyzerPathManager
                path_mgr = AnalyzerPathManager(bridge_name)
                data_dir = data_dir or path_mgr.get_data_dir("车辆荷载多年度")
                output_dir = output_dir or path_mgr.get_output_dir("车辆荷载多年度")
            except Exception:
                BASE_PATH = r"D:\useful\01-work file\07.报告\00-自动报告目录"
                data_dir = data_dir or os.path.join(BASE_PATH, bridge_name, "原始数据", "车辆荷载多年度")
                output_dir = output_dir or os.path.join(BASE_PATH, bridge_name, "分析结果", "车辆荷载多年度")

        self.data_dir = data_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def run(self):
        print(f"🚀 开始分析 {self.bridge_name} 多年度车辆荷载对比...")
        
        # 1. Process
        processor = MultiYearVehicleProcessor(self.bridge_name, self.data_dir)
        try:
            years, directions = processor.scan_data_structure()
            processor.load_yearly_data()
            stats = processor.analyze_yearly_stats()
        except Exception as e:
            print(f"❌ 数据处理失败: {e}")
            return False
            
        # 2. Plot
        plotter = MultiYearVehiclePlotter(self.bridge_name, self.output_dir, years, directions)
        plotter.plot_all(stats)
        
        # 3. Report
        reporter = MultiYearVehicleReporter(self.bridge_name, self.output_dir, stats)
        report_path = reporter.generate_report()
        
        if report_path:
            print(f"✅ 分析完成！报告位于: {report_path}")
            return True
        return False
