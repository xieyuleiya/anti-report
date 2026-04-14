# -*- coding: utf-8 -*-
"""
统一分析器入口 - 整合所有分析模块，提供统一的调用接口
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 兼容 Windows 控制台编码（避免 emoji 导致 gbk 编码失败）
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from utils.analyzer_utils import (
    AnalyzerPathManager, 
    DataDiscovery, 
    get_analyzer_info,
    DATA_TYPE_TO_ANALYZER
)
from config import BRIDGES_TO_DOWNLOAD


class UnifiedAnalyzer:
    """统一分析器管理器"""
    
    def __init__(self):
        self.path_manager = None
    
    def analyze_bridge(self, bridge_name: str, data_types: list = None):
        """
        分析指定桥梁的数据
        
        Args:
            bridge_name: 桥梁名称
            data_types: 数据类型列表，如果为None则分析所有可用类型
        """
        print(f"\n{'='*60}")
        print(f"开始分析桥梁: {bridge_name}")
        print(f"{'='*60}")
        
        # 创建路径管理器
        self.path_manager = AnalyzerPathManager(bridge_name)
        
        # 如果没有指定数据类型，则获取所有可用类型
        if data_types is None:
            data_types = DataDiscovery.get_bridge_data_types(bridge_name)
        
        if not data_types:
            print(f"⚠️ 桥梁 {bridge_name} 没有可用的数据")
            return False
        
        print(f"将分析以下数据类型: {', '.join(data_types)}\n")
        
        success_count = 0
        for data_type in data_types:
            print(f"\n{'─'*60}")
            print(f"分析 {data_type} 数据...")
            print(f"{'─'*60}")
            
            # 检查数据是否存在
            if not self.path_manager.has_data(data_type):
                print(f"⚠️ {data_type} 数据不存在，跳过")
                continue
            
            # 获取分析器信息
            analyzer_info = get_analyzer_info(data_type)
            if not analyzer_info:
                print(f"⚠️ 未找到 {data_type} 对应的分析器，跳过")
                continue
            
            # 运行分析器
            try:
                success = self._run_analyzer(bridge_name, data_type, analyzer_info)
                if success:
                    success_count += 1
                    print(f"✅ {data_type} 分析完成")
                else:
                    print(f"❌ {data_type} 分析失败")
            except Exception as e:
                print(f"❌ {data_type} 分析出错: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*60}")
        print(f"分析完成: {success_count}/{len(data_types)} 成功")
        print(f"{'='*60}\n")
        
        return success_count > 0
    
    def _run_analyzer(self, bridge_name: str, data_type: str, analyzer_info: dict) -> bool:
        """
        运行指定的分析器
        
        Args:
            bridge_name: 桥梁名称
            data_type: 数据类型
            analyzer_info: 分析器信息
        
        Returns:
            是否成功
        """
        module_name = analyzer_info["module"]
        class_name = analyzer_info["class"]
        
        try:
            # 动态导入模块
            module = __import__(module_name, fromlist=[class_name])
            analyzer_class = getattr(module, class_name)
            
            # 创建分析器实例（传入bridge_name参数）
            print(f"初始化分析器: {analyzer_info['description']}")
            
            # 尝试不同的初始化方式
            try:
                # 对于车辆荷载分析器，需要传递更多参数
                if data_type == "车辆荷载":
                    from utils.analyzer_utils import AnalyzerPathManager
                    path_mgr = AnalyzerPathManager(bridge_name)
                    data_dir = path_mgr.get_data_dir("车辆荷载")
                    output_dir = path_mgr.get_output_dir("车辆荷载")
                    # 尝试传入bridge_name和路径参数
                    try:
                        analyzer = analyzer_class(
                            bridge_name=bridge_name,
                            data_dir=str(data_dir),
                            output_dir=str(output_dir)
                        )
                    except TypeError:
                        # 如果失败，只传入bridge_name
                        analyzer = analyzer_class(bridge_name=bridge_name)
                elif data_type == "车辆荷载多年度":
                    # 多年度分析器：只从"车辆荷载多年度"目录读取（独立分析器）
                    from utils.analyzer_utils import AnalyzerPathManager
                    path_mgr = AnalyzerPathManager(bridge_name)
                    data_dir = path_mgr.get_data_dir("车辆荷载多年度")
                    output_dir = path_mgr.get_output_dir("车辆荷载多年度")
                    try:
                        analyzer = analyzer_class(
                            bridge_name=bridge_name,
                            data_dir=str(data_dir),
                            output_dir=str(output_dir)
                        )
                    except TypeError:
                        # 如果分析器不接受路径参数，只传 bridge_name
                        analyzer = analyzer_class(bridge_name=bridge_name)
                elif data_type == "船撞":
                    # 船撞：统一注入 data_dir/output_dir，避免分析器使用 chuanzhuang/<桥名>/数据 的旧路径
                    from utils.analyzer_utils import AnalyzerPathManager
                    path_mgr = AnalyzerPathManager(bridge_name)
                    data_dir = path_mgr.get_data_dir("船撞")
                    output_dir = path_mgr.get_output_dir("船撞")
                    try:
                        analyzer = analyzer_class(
                            bridge_name=bridge_name,
                            data_dir=str(data_dir),
                            output_dir=str(output_dir),
                        )
                    except TypeError:
                        # 如果分析器不接受路径参数，退回只传 bridge_name
                        analyzer = analyzer_class(bridge_name=bridge_name)
                elif data_type in ("温度", "温湿度", "风速"):
                    # 温度/温湿度/风速：统一注入 data_dir/output_dir，避免各分析器自带的旧路径
                    from utils.analyzer_utils import AnalyzerPathManager
                    from config import BRIDGE_CONFIG_EXCEL_PATH
                    import os
                    path_mgr = AnalyzerPathManager(bridge_name)
                    data_dir = path_mgr.get_data_dir(data_type)
                    output_dir = path_mgr.get_output_dir(data_type)
                    # 检查Excel文件是否存在，如果存在则传递，否则为None（分析器会尝试无Excel模式）
                    excel_path = BRIDGE_CONFIG_EXCEL_PATH if os.path.exists(BRIDGE_CONFIG_EXCEL_PATH) else None
                    try:
                        analyzer = analyzer_class(
                            bridge_name=bridge_name,
                            data_dir=str(data_dir),
                            output_dir=str(output_dir),
                            excel_path=excel_path,
                        )
                    except TypeError:
                        # 如果分析器不接受excel_path参数，只传基本参数
                        try:
                            analyzer = analyzer_class(
                                bridge_name=bridge_name,
                                data_dir=str(data_dir),
                                output_dir=str(output_dir),
                            )
                        except TypeError:
                            analyzer = analyzer_class(bridge_name=bridge_name)
                else:
                    # 其他分析器，优先尝试传入bridge_name参数
                    analyzer = analyzer_class(bridge_name=bridge_name)
            except TypeError:
                # 如果失败，尝试无参数初始化（某些分析器可能使用类属性）
                try:
                    analyzer = analyzer_class()
                    # 如果分析器有bridge_name属性，尝试设置
                    if hasattr(analyzer, 'bridge_name'):
                        analyzer.bridge_name = bridge_name
                    # 如果分析器有BRIDGE_NAME类属性，尝试设置
                    if hasattr(analyzer_class, 'BRIDGE_NAME'):
                        analyzer_class.BRIDGE_NAME = bridge_name
                except Exception as e:
                    print(f"⚠️ 无法初始化分析器: {e}")
                    return False
            
            # 运行分析（按优先级尝试不同的方法）
            if hasattr(analyzer, 'run_detailed_analysis'):
                # 车辆荷载分析器使用这个方法
                analyzer.run_detailed_analysis()
            elif hasattr(analyzer, 'run_analysis'):
                analyzer.run_analysis()
            elif hasattr(analyzer, 'run'):
                analyzer.run()
            elif hasattr(analyzer, 'analyze'):
                analyzer.analyze()
            elif hasattr(analyzer, 'generate_report'):
                analyzer.generate_report()
            elif hasattr(analyzer, 'run_multi_year_analysis'):
                # 多年度分析器
                analyzer.run_multi_year_analysis()
            else:
                # 如果没有标准方法，检查是否在初始化时已完成
                print(f"⚠️ 分析器没有标准的运行方法")
                # 某些分析器可能在初始化时就完成了分析
                if hasattr(analyzer, 'output_dir'):
                    print(f"   输出目录: {analyzer.output_dir}")
                return True
            
            return True
            
        except ImportError as e:
            print(f"❌ 无法导入分析器模块 {module_name}: {e}")
            print(f"💡 提示: 请检查是否安装了所有依赖包")
            print(f"   运行: pip install -r requirements.txt")
            return False
        except AttributeError as e:
            print(f"❌ 分析器类 {class_name} 不存在: {e}")
            return False
        except Exception as e:
            print(f"❌ 运行分析器时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def analyze_all_bridges(self, bridge_names: list = None, data_types: list = None):
        """
        分析所有桥梁的数据
        
        Args:
            bridge_names: 桥梁名称列表，如果为None则使用配置文件中的列表
            data_types: 数据类型列表，如果为None则分析所有可用类型
        """
        if bridge_names is None:
            bridge_names = BRIDGES_TO_DOWNLOAD
        
        print("开始批量分析...")
        print(f"目标桥梁: {bridge_names}")
        if data_types:
            print(f"数据类型: {data_types}")
        
        success_count = 0
        for bridge_name in bridge_names:
            if self.analyze_bridge(bridge_name, data_types):
                success_count += 1
        
        print(f"\n批量分析完成！成功: {success_count}/{len(bridge_names)}")


def main():
    """主函数"""
    analyzer = UnifiedAnalyzer()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'bridge':
            # 分析指定桥梁的所有数据
            if len(sys.argv) > 2:
                bridge_name = sys.argv[2]
                analyzer.analyze_bridge(bridge_name)
            else:
                # 兼容：不传桥名则使用配置文件第一个桥梁
                if BRIDGES_TO_DOWNLOAD:
                    bridge_name = BRIDGES_TO_DOWNLOAD[0]
                    print(f"未指定桥梁名称，使用配置中的桥梁: {bridge_name}")
                    analyzer.analyze_bridge(bridge_name)
                else:
                    print("❌ 请指定桥梁名称")
                    print("用法: python main_analyzer.py bridge <桥梁名称>")
                    print("或: python main_analyzer.py bridge_idx <序号> （从 list 输出中选择）")

        elif command == 'bridge_idx':
            # 按序号选择桥梁（避免终端编码导致中文参数乱码）
            if len(sys.argv) > 2:
                try:
                    idx = int(sys.argv[2])
                except ValueError:
                    print("❌ bridge_idx 参数必须是整数")
                    print("用法: python main_analyzer.py bridge_idx <序号>")
                    return
                bridges = DataDiscovery.get_all_bridges()
                if not bridges:
                    print("⚠️ 未找到任何可用桥梁，请先下载数据或检查目录")
                    return
                if idx < 1 or idx > len(bridges):
                    print(f"❌ 序号超出范围：1~{len(bridges)}")
                    print("先运行: python main_analyzer.py list 查看序号")
                    return
                bridge_name = bridges[idx - 1]
                print(f"按序号选择桥梁: {idx} -> {bridge_name}")
                analyzer.analyze_bridge(bridge_name)
            else:
                print("❌ 请指定桥梁序号")
                print("用法: python main_analyzer.py bridge_idx <序号>")
        
        elif command == 'type':
            # 分析指定类型的数据
            if len(sys.argv) > 3:
                bridge_name = sys.argv[2]
                data_type = sys.argv[3]
                analyzer.analyze_bridge(bridge_name, [data_type])
            else:
                print("❌ 请指定桥梁名称和数据类型")
                print("用法: python main_analyzer.py type <桥梁名称> <数据类型>")
        
        elif command == 'all':
            # 分析所有桥梁的所有数据
            analyzer.analyze_all_bridges()
        
        elif command == 'list':
            # 列出可用数据
            DataDiscovery.print_summary()
        
        elif command == 'help':
            # 显示帮助信息
            print("📖 使用说明:")
            print("  python main_analyzer.py bridge <桥梁名称>     # 分析指定桥梁的所有数据")
            print("  python main_analyzer.py bridge_idx <序号>     # 按序号选择桥梁（避免中文参数乱码）")
            print("  python main_analyzer.py type <桥梁名称> <数据类型>  # 分析指定类型的数据")
            print("  python main_analyzer.py all                    # 分析所有桥梁的所有数据")
            print("  python main_analyzer.py list                   # 列出可用的桥梁和数据类型")
            print("  python main_analyzer.py help                    # 显示帮助信息")
            print("\n支持的数据类型:")
            for data_type, info in DATA_TYPE_TO_ANALYZER.items():
                print(f"  {data_type:10s} - {info['description']}")
        
        else:
            print(f"❌ 未知命令: {command}")
            print("使用 'python main_analyzer.py help' 查看帮助信息")
    
    else:
        # 默认显示数据摘要
        print("未指定命令，显示数据摘要")
        print("使用 'python main_analyzer.py help' 查看帮助信息\n")
        DataDiscovery.print_summary()


if __name__ == "__main__":
    main()

