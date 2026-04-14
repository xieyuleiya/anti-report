# -*- coding: utf-8 -*-
"""
车辆荷载数据下载模块 - 重构版本
基于原有的vehicle_load_downloader.py，升级为批次下载模式，使用统一配置
"""

import json
import requests
import calendar
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
import time

from config import (
    HEADERS, API_KEY, BATCH_SIZE_DAYS, WAIT_SECONDS,
    BRIDGE_CONFIG_EXCEL_PATH, START_DATE, END_DATE, create_output_dirs
)

class VehicleLoadDownloader:
    """车辆荷载数据下载器（升级为批次下载模式）"""

    def __init__(self):
        self.headers = HEADERS
        self.api_key = API_KEY
        self.batch_size_days = BATCH_SIZE_DAYS
        self.wait_seconds = WAIT_SECONDS
        self.excel_path = BRIDGE_CONFIG_EXCEL_PATH
        self.start_date = START_DATE
        self.end_date = END_DATE
        self.vehicle_data_url = 'http://192.168.1.244:8122/InternalData/GetEctData'

    def download_bridge_data(self, bridge_name: str) -> bool:
        """下载指定桥梁的车辆荷载数据"""
        print(f"🚀 开始下载 {bridge_name} 的车辆荷载数据...")
        print(f"📋 配置信息:")
        print(f"  - Excel文件: {self.excel_path}")
        print(f"  - 目标桥梁: {bridge_name}")
        print(f"  - 下载时间范围: {self.start_date} 到 {self.end_date}")
        print(f"  - 批量大小: {self.batch_size_days} 天")
        print(f"  - 等待时间: {self.wait_seconds} 秒")

        # 读取车辆荷载配置
        try:
            old_df1 = pd.read_excel(self.excel_path, sheet_name="车辆荷载")
            number1 = old_df1[old_df1['桥梁名称'] == bridge_name]
            if number1.empty:
                print(f'⚠️ 桥梁 {bridge_name} 没有车辆荷载配置')
                return False
            print(f"✅ 找到 {len(number1)} 个车辆荷载测点")
        except Exception as e:
            print(f"❌ 读取车辆荷载配置文件失败: {e}")
            return False

        # 创建输出目录
        output_dir = create_output_dirs(bridge_name, "车辆荷载")

        success_count = 0
        # 下载每个测点的数据
        for idx in range(len(number1)):
            gantry_id = number1.iloc[idx, 0]
            gantry_name = number1.iloc[idx, 1]
            # 组合A、C、D、E列的值作为文件名
            col_a = str(number1.iloc[idx, 0]) if pd.notna(number1.iloc[idx, 0]) else ""
            col_c = str(number1.iloc[idx, 2]) if pd.notna(number1.iloc[idx, 2]) else ""
            col_d = str(number1.iloc[idx, 3]) if pd.notna(number1.iloc[idx, 3]) else ""
            col_e = str(number1.iloc[idx, 4]) if pd.notna(number1.iloc[idx, 4]) else ""
            file_name = f"{col_a}_{col_c}_{col_d}_{col_e}".replace("__", "_").strip("_")

            print(f"\n🔧 处理测点: {gantry_name} (ID: {gantry_id})")
            print(f"📝 文件名组合: {file_name}")

            # 批量下载该测点的数据
            success = self._download_gantry_data(gantry_id, gantry_name, file_name, output_dir)
            if success:
                success_count += 1
                print(f"✅ 测点 {gantry_name} 的数据下载完成")
            else:
                print(f"❌ 测点 {gantry_name} 的数据下载失败")

        print(f"\n🎉 {bridge_name} 的车辆荷载数据下载完成！成功下载 {success_count}/{len(number1)} 个测点")
        return success_count > 0

    def get_available_bridges(self):
        """获取可用的桥梁列表"""
        try:
            old_df = pd.read_excel(self.excel_path, sheet_name="车辆荷载")
            return old_df['桥梁名称'].unique().tolist()
        except Exception as e:
            print(f"❌ 读取桥梁列表失败: {e}")
            return []

    def _download_gantry_data(self, gantry_id, gantry_name, file_name, output_dir):
        """批量下载指定测点的车辆荷载数据"""
        print(f"📥 开始批量下载测点 {gantry_name} 的数据...")

        # 计算日期范围
        try:
            start_dt = datetime.strptime(self.start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                print(f"❌ 开始日期 {self.start_date} 不能晚于结束日期 {self.end_date}")
                return False
        except ValueError as e:
            print(f"❌ 日期格式错误: {e}")
            return False

        # 使用批次下载
        all_data = pd.DataFrame()
        batch_count = 0
        current_start = start_dt

        while current_start <= end_dt:
            # 计算当前批次的结束日期
            current_end = min(current_start + timedelta(days=self.batch_size_days - 1), end_dt)
            batch_count += 1

            print(f"   📦 批次 {batch_count}: {current_start.strftime('%Y-%m-%d')} 到 {current_end.strftime('%Y-%m-%d')}")

            # 下载当前批次
            batch_data = self._download_batch_data(gantry_id, current_start, current_end)
            if not batch_data.empty:
                all_data = pd.concat([all_data, batch_data], ignore_index=True)
                print(f"   ✅ 批次 {batch_count} 完成: {len(batch_data)} 条记录")
            else:
                print(f"   ⚠️ 批次 {batch_count} 无数据")

            # 移动到下一批次
            current_start = current_end + timedelta(days=1)

            # 避免API频率限制
            if current_start <= end_dt and self.wait_seconds > 0:
                print(f"   ⏳ 等待{self.wait_seconds}秒...")
                time.sleep(self.wait_seconds)

        # 保存数据
        if not all_data.empty:
            output_file = os.path.join(output_dir, f"{file_name}.txt")
            all_data.to_csv(output_file, sep='\t', index=False)
            print(f"✅ 已保存 {len(all_data)} 条记录到: {output_file}")
            return True
        else:
            print(f"⚠️ 测点 {gantry_name} 没有数据")
            return False

    def _download_batch_data(self, gantry_id, start_dt, end_dt):
        """下载指定时间范围的批次数据"""
        batch_data = pd.DataFrame()
        current_date = start_dt

        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            data = {
                "gantryId": gantry_id,
                "start": f"{date_str} 00:00:00",
                "end": f"{date_str} 23:59:59",
                "key": self.api_key
            }

            try:
                response = requests.post(self.vehicle_data_url, data=json.dumps(data), headers=self.headers, timeout=30)
                if response.status_code == 200:
                    data_daochu = response.json().get('list', [])
                    if data_daochu:
                        data2 = pd.DataFrame(data_daochu)
                        if not data2.empty:
                            data2['var1'] = data2.iloc[:, -1] * 2
                            data1 = data2.iloc[:, :-1]
                            batch_data = pd.concat([batch_data, data1], ignore_index=True)
            except Exception as e:
                print(f"   ❌ 下载数据时出错: {e}, 日期: {date_str}")

            current_date += timedelta(days=1)

        return batch_data 