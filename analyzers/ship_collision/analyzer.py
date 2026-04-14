import os
from pathlib import Path
from config import get_analyzer_data_dir, get_analyzer_output_dir
from .processor import ShipCollisionProcessor
from .plotter import ShipCollisionPlotter
from .reporter import ShipCollisionReporter

BRIDGE_NAME = "观音沙大桥"

class ShipCollisionAnalyzer:
    def __init__(self, bridge_name=None, data_dir=None, output_dir=None):
        self.bridge_name = bridge_name if bridge_name else BRIDGE_NAME
        
        if data_dir is None:
            self.data_dir = Path(get_analyzer_data_dir(self.bridge_name, "船撞"))
        else:
            self.data_dir = Path(data_dir)

        if output_dir is None:
            self.output_dir = Path(get_analyzer_output_dir(self.bridge_name, "船撞"))
        else:
            self.output_dir = Path(output_dir)
            
        if not self.data_dir.exists():
            print(f"缺少目录: {self.data_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_analysis(self):
        print(f"开始分析 {self.bridge_name} 船撞数据...")
        
        processor = ShipCollisionProcessor(self.bridge_name, self.data_dir)
        nav_data, dev_data = processor.load_data()
        processor.preprocess_data()
        processor.analyze_basic_stats()
        
        plotter = ShipCollisionPlotter(self.bridge_name, self.output_dir, nav_data, dev_data)
        plotter.generate_charts()
        
        reporter = ShipCollisionReporter(self.bridge_name, self.output_dir, nav_data, dev_data)
        report_path = reporter.generate_word_report()
        
        if report_path:
            return True
        return False
