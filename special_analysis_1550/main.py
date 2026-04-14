# -*- coding: utf-8 -*-
"""
快速运行指引（每月仅需改两处）：
1. 修改 BASE_DIR 与 PERIOD_NAME
   - BASE_DIR: 报告根目录（不含月份）
   - PERIOD_NAME: 本期名称，如 "9月月报"
   程序会自动生成：
     - 原始数据目录:  BASE_DIR/PERIOD_NAME/原始数据（下载保存 & 分析读取）
     - 结果输出目录:  BASE_DIR/PERIOD_NAME/趋势分析结果
     - 模板路径:      BASE_DIR/基础资料/云茂报告模版.docx

2. 配置下载时间范围（DOWNLOAD_CONFIG 的 START_DATE / END_DATE）
   - 仅改日期，其他路径会自动随 PERIOD_NAME 调整

3. 运行 main.py，菜单选择：
   - 1 仅下载数据（使用 highway_downloader，下载到“原始数据”）
   - 2 仅进行趋势分析（从“原始数据”读取并生成报告）
   - 3 下载+分析（先下载再自动分析）

注意：所有路径在 Windows 上按 BASE_DIR + PERIOD_NAME 自动拼装；
      若需切换工程根目录，只改 BASE_DIR 一处。
"""

import os
import sys
import traceback
import pandas as pd
from .utils import log
from data_loader import DataLoader
from trend_analyzer import TrendAnalyzer
from charts import create_trend_chart, create_critical_sensors_chart
from report_generator import generate_month_report, generate_quarter_report, generate_all_trend_charts_report, set_template_path
from highway_downloader import run_download as highway_run_download
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


# ---------------- 用户仅需改动以下两个参数 ----------------
BASE_DIR = r"D:\useful\01-work file\07.报告\20250801-报告-云茂1550报告"  # 报告根目录（不含月份）
PERIOD_NAME = "1月月报"  # 每月只改这里和时间范围，如 "9月月报"
# -------------------------------------------------------

# 统一构建本期目录结构
PERIOD_ROOT = os.path.join(BASE_DIR, PERIOD_NAME)
RAW_DIR = os.path.join(PERIOD_ROOT, "原始数据")           # 下载器保存目录 == 分析器数据源目录
RESULT_DIR = os.path.join(PERIOD_ROOT, "趋势分析结果")    # 分析输出目录
TEMPLATE_PATH_DEFAULT = os.path.join(BASE_DIR, "基础资料", "云茂报告模版.docx")

# 下载器统一配置
DOWNLOAD_CONFIG = {
    'EXCEL_PATH': os.path.join(BASE_DIR, "基础资料", "1550通道ID测点完整表2026.01.15.xlsx"),
    'ROAD': RAW_DIR,  # 与分析器的数据目录保持一致
    'TARGET_HIGHWAYS': ["云茂"],
    'TARGET_HIGHWAY_BRIDGES': [],  # e.g. [("云茂", "倒流大桥")]
    'START_DATE': "2025-12-01",
    'END_DATE': "2025-12-31",
    'BATCH_SIZE_DAYS': 31,
}


# 分析配置（趋势分析与报告）
ANALYSIS_CONFIG = {
    'DATA_DIR': RAW_DIR,          # 与下载器同一路径
    'OUTPUT_DIR': RESULT_DIR,
    'TEMPLATE_PATH': TEMPLATE_PATH_DEFAULT,
}


def show_menu():
    """显示用户选择菜单"""
    print("\n" + "="*60)
    print("          桥梁趋势分析系统")
    print("="*60)
    print("请选择要执行的操作：")
    print("1. 仅下载数据")
    print("2. 仅进行趋势分析")
    print("3. 下载数据并进行趋势分析")
    print("4. 退出程序")
    print("="*60)


def get_user_choice():
    """获取用户选择"""
    while True:
        try:
            choice = input("请输入选择 (1-4, 回车默认2): ").strip()
            if choice == '':
                return '2'
            if choice in ['1', '2', '3', '4']:
                return choice
            else:
                print("❌ 无效选择，请输入 1-4 之间的数字")
        except KeyboardInterrupt:
            print("\n\n程序被用户中断")
            sys.exit(0)
        except Exception as e:
            print(f"❌ 输入错误: {e}")


def _format_duration(seconds: float) -> str:
    """将秒数格式化为易读字符串，如 1h 02m 03.456s / 12.345s"""
    if seconds >= 3600:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}h {m:02d}m {s:06.3f}s"
    if seconds >= 60:
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m}m {s:06.3f}s"
    return f"{seconds:.3f}s"


def run_trend_analysis():
    
    """运行趋势分析功能"""
    t_total_start = time.perf_counter()
    log("=== 桥梁趋势分析模块 ===", 'info')
    # 固定数据目录和输出目录（来自 ANALYSIS_CONFIG）
    set_template_path(ANALYSIS_CONFIG.get('TEMPLATE_PATH'))
    data_dir = ANALYSIS_CONFIG['DATA_DIR']
    output_dir = ANALYSIS_CONFIG['OUTPUT_DIR']
    log("桥梁趋势分析系统")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "测点图表"), exist_ok=True)
    loader = DataLoader(data_dir)

    t_scan_start = time.perf_counter()
    bridge_files = loader.scan_data_directories()
    t_scan = time.perf_counter() - t_scan_start
    log(f"扫描数据目录耗时: {_format_duration(t_scan)}", 'info')

    if not bridge_files:
        log("未找到任何桥梁数据，程序退出", 'error')
        return False
    trend_analyzer = TrendAnalyzer()
    all_trend_results = {}
    all_bridges_data = {}
    manufacturers_map = {}
    total_bridges = len(bridge_files)
    current_bridge = 0
    
    for bridge_name, txt_files in bridge_files.items():
        t_bridge_start = time.perf_counter()
        current_bridge += 1
        log(f"处理桥梁 ({current_bridge}/{total_bridges}): {bridge_name}")
        trend_results = {}
        bridge_data = {}
        critical_sensors_data = {}
        # 预提取本桥“墩号 -> 厂家”映射
        bridge_manufacturers = {}
        for fpath in txt_files:
            info = loader.get_file_info(fpath)
            if info is not None:
                pier = info.get('pier_number') or loader.extract_sensor_id(fpath)
                vendor = info.get('manufacturer', '')
                if pier:
                    bridge_manufacturers[pier] = vendor
        
        total_sensors = len(txt_files)
        current_sensor = 0

        # 定义单测点处理函数（加载+趋势分析）
        def _process_sensor(txt_file_path):
            # 首先检查传感器状态
            sensor_status = loader.get_sensor_status(txt_file_path)
            
            if sensor_status == "离线":
                # 对于离线传感器，返回特殊标记
                sensor_id_local = loader.extract_sensor_id(txt_file_path)
                return (txt_file_path, sensor_id_local, "OFFLINE")
            
            # 对于在线传感器，进行正常的数据加载和趋势分析
            df_local = loader.load_single_file(txt_file_path, bridge_name)
            if df_local is None:
                return (txt_file_path, None, None)
            result_local = trend_analyzer.analyze_trend(df_local)
            if result_local is None:
                return (txt_file_path, None, None)
            sensor_id_local = str(df_local['sensor_id'].iloc[0])
            return (txt_file_path, sensor_id_local, (df_local, result_local))

        # 线程池并行处理单桥的所有测点
        base_workers = min(8, max(2, os.cpu_count() or 4))
        # 若测点数更少，则以测点数为准，避免创建闲置线程；至少为1
        max_workers = max(1, min(base_workers, total_sensors))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(_process_sensor, fpath): fpath for fpath in txt_files}
            for future in as_completed(future_to_file):
                txt_file = future_to_file[future]
                current_sensor += 1
                try:
                    log(f"  处理测点 ({current_sensor}/{total_sensors}): {os.path.basename(txt_file)}")
                    txt_path, sensor_id, payload = future.result()
                except Exception as e:
                    log(f"    ❌ 处理失败: {e}", 'error')
                    continue
                if payload is None:
                    log(f"    ❌ 数据加载或趋势分析失败")
                    continue
                
                # 处理离线传感器
                if payload == "OFFLINE":
                    log(f"    📴 传感器离线: {sensor_id}")
                    trend_results[sensor_id] = "OFFLINE"
                    bridge_data[sensor_id] = "OFFLINE"
                    continue
                
                # 处理正常传感器
                df, result = payload
                trend_results[sensor_id] = result
                bridge_data[sensor_id] = df

                # 仅对“非正常”测点生成单点趋势图（减少绘图开销）
                h_trend = result['horizontal_angle_trend']
                v_trend = result['vertical_angle_trend']
                if h_trend['trend_strength'] != '正常' or v_trend['trend_strength'] != '正常':
                    chart_path = os.path.join(output_dir, "测点图表", f"{bridge_name}_{sensor_id}_趋势分析.png")
                    create_trend_chart(df, result, chart_path)

                # 收集重点关注测点数据用于合并图
                if h_trend['trend_strength'] == '持续关注' or v_trend['trend_strength'] == '持续关注':
                    critical_sensors_data[sensor_id] = {
                        'timestamp': df['timestamp'],
                        'horizontal_angle': df['horizontal_angle'],
                        'vertical_angle': df['vertical_angle']
                    }
        if critical_sensors_data:
            critical_chart_path = os.path.join(output_dir, "测点图表", f"{bridge_name}_持续关注测点.png")
            create_critical_sensors_chart(bridge_name, critical_sensors_data, critical_chart_path)
        
        # 将当前桥梁的数据添加到总数据中
        all_trend_results[bridge_name] = trend_results
        all_bridges_data[bridge_name] = bridge_data
        manufacturers_map[bridge_name] = bridge_manufacturers

        t_bridge = time.perf_counter() - t_bridge_start
        log(f"桥梁 {bridge_name} 处理耗时: {_format_duration(t_bridge)} (测点数: {total_sensors}, 并发: {max_workers})", 'info')
    
    # 在所有桥梁数据处理完毕后，生成报告
    log("📄 开始生成月报...", 'info')
    t_month_start = time.perf_counter()
    generate_month_report(all_trend_results, all_bridges_data, output_dir)
    log(f"月报生成耗时: {_format_duration(time.perf_counter() - t_month_start)}", 'info')

    log("📄 开始生成季报...", 'info')
    t_quarter_start = time.perf_counter()
    generate_quarter_report(all_trend_results, all_bridges_data, output_dir)
    log(f"季报生成耗时: {_format_duration(time.perf_counter() - t_quarter_start)}", 'info')

    log("📄 开始生成所有测点趋势图一览...", 'info')
    t_allcharts_start = time.perf_counter()
    generate_all_trend_charts_report(all_trend_results, all_bridges_data, output_dir, manufacturers_map)
    log(f"所有测点趋势图一览生成耗时: {_format_duration(time.perf_counter() - t_allcharts_start)}", 'info')
    
    total_elapsed = time.perf_counter() - t_total_start
    log(f"分析完成，总耗时: {_format_duration(total_elapsed)}，结果已保存至: {output_dir}", 'success')
    return True


def main():
    """
    主函数
    """
    try:
        show_menu()
        choice = get_user_choice()
        
        if choice == '1':
            # 仅下载数据（使用 highway_downloader）
            log("开始执行数据下载...", 'info')
            try:
                highway_run_download(DOWNLOAD_CONFIG)
                log("数据下载完成！", 'success')
            except SystemExit:
                # highway_downloader 可能调用了 sys.exit；忽略以保持主程序不退出
                log("数据下载流程已结束。", 'info')
            except Exception as e:
                log(f"数据下载失败: {e}", 'error')
        elif choice == '2':
            # 仅进行趋势分析
            success = run_trend_analysis()
            if not success:
                log("趋势分析失败！", 'error')
        elif choice == '3':
            # 下载数据并进行趋势分析（使用 highway_downloader）
            log("开始执行数据下载...", 'info')
            try:
                highway_run_download(DOWNLOAD_CONFIG)
                log("数据下载完成！开始进行趋势分析...", 'success')
                analysis_success = run_trend_analysis()
                if analysis_success:
                    log("所有任务完成！", 'success')
                else:
                    log("趋势分析失败！", 'error')
            except SystemExit:
                log("数据下载流程已结束。", 'info')
                analysis_success = run_trend_analysis()
                if analysis_success:
                    log("所有任务完成！", 'success')
                else:
                    log("趋势分析失败！", 'error')
            except Exception as e:
                log(f"数据下载失败，无法进行趋势分析: {e}", 'error')
        elif choice == '4':
            # 退出程序
            log("程序退出", 'info')
            return
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        log(f"程序运行出错: {e}", 'error')
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
