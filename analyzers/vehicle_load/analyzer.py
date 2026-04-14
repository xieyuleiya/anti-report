import os
from pathlib import Path
from .processor import VehicleLoadProcessor
from .plotter import VehicleLoadPlotter
from .reporter import VehicleLoadReporter

class VehicleLoadAnalyzer:
    def __init__(self, bridge_name="崖门大桥", data_dir=None, output_dir=None):
        self.bridge_name = bridge_name
        
        if data_dir is None or output_dir is None:
            try:
                from utils.analyzer_utils import AnalyzerPathManager
                path_mgr = AnalyzerPathManager(self.bridge_name)
                data_dir = data_dir or path_mgr.get_data_dir("车辆荷载")
                output_dir = output_dir or path_mgr.get_output_dir("车辆荷载")
            except Exception:
                DATA_ROOT = Path("D:/useful/03-chengxu/report_gen/数据下载")
                data_dir = data_dir or (DATA_ROOT / self.bridge_name / "车辆荷载" / "数据")
                output_dir = output_dir or (Path(__file__).parent / "vehicle_load" / self.bridge_name)

        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        print(f"🚛 开始分析 {self.bridge_name} 车辆荷载数据...")
        
        processor = VehicleLoadProcessor(self.bridge_name, self.data_dir, self.output_dir)
        try:
            processor.load_data()
        except FileNotFoundError as e:
            print(f"❌ 车辆荷载加载数据失败: {e}")
            return False
            
        stats = processor.analyze_detailed_stats()
        df1, df2, df_combined = processor.get_dfs()
        direction1_name = processor.direction1_name
        direction2_name = processor.direction2_name
        
        plotter = VehicleLoadPlotter(self.bridge_name, self.output_dir, direction1_name, direction2_name, df1, df2, df_combined)
        plotter.create_enhanced_charts(stats)
        
        reporter = VehicleLoadReporter(self.bridge_name, self.output_dir, direction1_name, direction2_name, stats, df1, df2, df_combined)
        report_path = reporter.generate_word_report()
        
        if report_path:
            print(f"✅ {self.bridge_name} 车辆荷载分析完成！结果保存在: {self.output_dir}")
            return True
        return False
