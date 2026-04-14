# -*- coding: utf-8 -*-
"""
船撞数据下载模块 - 重构版本
基于原有的ship_collision_batch_downloader.py，使用统一配置
"""

import json
import requests
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
import time

from config import (
    HEADERS, API_KEY, BATCH_SIZE_DAYS, WAIT_SECONDS,
    BRIDGE_CONFIG_EXCEL_PATH, START_DATE, END_DATE, create_output_dirs
)

class ShipCollisionDownloader:
    """船撞数据下载器（按固定30天批次）"""

    def __init__(self):
        self.headers = HEADERS
        self.api_key = API_KEY
        self.batch_size_days = BATCH_SIZE_DAYS
        self.wait_seconds = WAIT_SECONDS
        self.excel_path = BRIDGE_CONFIG_EXCEL_PATH
        self.start_date = START_DATE
        self.end_date = END_DATE
        self.ship_data_url = 'http://192.168.1.244:8122/InternalData/GetShipData'

    def download_bridge_data(self, bridge_name: str) -> bool:
        """下载指定桥梁的船撞数据（30天批次）"""
        print(f"🚀 开始下载 {bridge_name} 的船撞数据...")
        print(f"📋 配置信息:")
        print(f"  - Excel文件: {self.excel_path}")
        print(f"  - 目标桥梁: {bridge_name}")
        print(f"  - 下载时间范围: {self.start_date} 到 {self.end_date}")
        print(f"  - 批量大小: {self.batch_size_days} 天")
        print(f"  - 等待时间: {self.wait_seconds} 秒")

        total_start = time.perf_counter()

        # 读取桥梁配置
        try:
            old_df = pd.read_excel(self.excel_path, sheet_name="船撞")
            bridge_config = old_df[old_df['桥梁名称'] == bridge_name]
            if bridge_config.empty:
                print(f"⚠️ 未找到桥梁 {bridge_name} 的船撞配置")
                return False
            bridge_id = int(bridge_config.iloc[0, 0])
            print(f"✅ 找到桥梁ID: {bridge_id}")
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            return False

        # 创建输出目录
        output_dir = create_output_dirs(bridge_name, "船撞")

        # 计算日期范围
        try:
            start_dt = datetime.strptime(self.start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                print(f"❌ 开始日期 {self.start_date} 不能晚于结束日期 {self.end_date}")
                return False
            print(f"📅 下载时间范围: {self.start_date} 至 {self.end_date}")
        except ValueError as e:
            print(f"❌ 日期格式错误: {e}")
            return False

        # 下载两类事件
        success = False

        print("📥 批次下载 助航数据(eventTypeId=1)...")
        nav_start = time.perf_counter()
        navigation_df = self._download_event_in_batches(bridge_id, event_type_id=1, start_dt=start_dt, end_dt=end_dt)
        nav_elapsed = time.perf_counter() - nav_start
        nav_count = len(navigation_df)
        print(f"⏱️ 助航数据下载耗时: {nav_elapsed:.2f}s")
        if nav_count > 0:
            print(f"📊 助航数据获取到 {nav_count} 条记录")
        else:
            print(f"⚠️ 助航数据未获取到任何记录")

        print("📥 批次下载 偏航数据(eventTypeId=4)...")
        dev_start = time.perf_counter()
        deviation_df = self._download_event_in_batches(bridge_id, event_type_id=4, start_dt=start_dt, end_dt=end_dt)
        dev_elapsed = time.perf_counter() - dev_start
        dev_count = len(deviation_df)
        print(f"⏱️ 偏航数据下载耗时: {dev_elapsed:.2f}s")
        if dev_count > 0:
            print(f"📊 偏航数据获取到 {dev_count} 条记录")
        else:
            print(f"⚠️ 偏航数据未获取到任何记录")

        # 保存
        print("\n💾 保存数据文件...")
        if not navigation_df.empty:
            navigation_file = os.path.join(output_dir, "助航统计.txt")
            navigation_df.to_csv(navigation_file, sep='\t', index=False)
            print(f"✅ 助航数据已保存: {navigation_file} (共 {nav_count} 条记录)")
            success = True
        else:
            print(f"⚠️ 助航数据为空，未生成文件")
            
        if not deviation_df.empty:
            deviation_file = os.path.join(output_dir, "偏航统计.txt")
            deviation_df.to_csv(deviation_file, sep='\t', index=False)
            print(f"✅ 偏航数据已保存: {deviation_file} (共 {dev_count} 条记录)")
            success = True
        else:
            print(f"⚠️ 偏航数据为空，未生成文件")

        total_elapsed = time.perf_counter() - total_start
        print(f"\n⏱️ 总耗时: {total_elapsed:.2f}s")

        # 最终总结
        print("\n" + "="*60)
        if success:
            print(f"✅ {bridge_name} 船撞数据下载完成！")
            print(f"📋 数据统计:")
            print(f"  - 助航数据: {nav_count} 条")
            print(f"  - 偏航数据: {dev_count} 条")
        else:
            print(f"⚠️ {bridge_name} 未获取到任何船撞数据")
            print(f"📋 数据统计:")
            print(f"  - 助航数据: 0 条")
            print(f"  - 偏航数据: 0 条")
            print(f"💡 提示: 请检查时间范围 {self.start_date} 至 {self.end_date} 内是否有数据")
        print("="*60)
        return success

    def get_available_bridges(self):
        """获取可用的桥梁列表"""
        try:
            old_df = pd.read_excel(self.excel_path, sheet_name="船撞")
            return old_df['桥梁名称'].unique().tolist()
        except Exception as e:
            print(f"❌ 读取桥梁列表失败: {e}")
            return []

    def _iter_batches(self, start_dt: datetime, end_dt: datetime):
        """生成30天批次时间范围"""
        current = start_dt
        while current <= end_dt:
            batch_end = min(current + timedelta(days=self.batch_size_days - 1), end_dt)
            yield current, batch_end
            current = batch_end + timedelta(days=1)

    def _download_event_in_batches(self, bridge_id: int, event_type_id: int, start_dt: datetime, end_dt: datetime):
        """按30天批次下载指定事件类型的数据"""
        all_df = pd.DataFrame()
        batch_index = 0

        for b_start, b_end in self._iter_batches(start_dt, end_dt):
            batch_index += 1
            # 注意：接口字段使用 startTime/endTime，否则可能返回空数据
            payload = {
                "bridgeId": bridge_id,
                "startTime": f"{b_start.strftime('%Y-%m-%d')} 00:00:00",
                "endTime": f"{b_end.strftime('%Y-%m-%d')} 23:59:59",
                "eventTypeId": event_type_id,
                "key": self.api_key,
            }
            batch_t0 = time.perf_counter()
            try:
                print(f"   🔄 批次{batch_index:03d} [{event_type_id}] {payload['startTime']} → {payload['endTime']}")
                resp = requests.post(self.ship_data_url, data=json.dumps(payload), headers=self.headers, timeout=60)
                if resp.status_code == 200:
                    try:
                        data_list = resp.json().get('list', [])
                        df = pd.DataFrame(data_list)
                        if not df.empty:
                            # 与原逻辑保持一致：构造 var1 并去掉最后一列
                            df['var1'] = df.iloc[:, -1] * 2
                            df = df.iloc[:, :-1]
                            all_df = pd.concat([all_df, df], ignore_index=True)
                    except (json.JSONDecodeError, ValueError, KeyError):
                        pass
                else:
                    print(f"   ⚠️ HTTP {resp.status_code}")
            except Exception as e:
                print(f"   ❌ 批次请求异常: {e}")
            finally:
                batch_elapsed = time.perf_counter() - batch_t0
                print(f"   ⏱️ 批次{batch_index:03d} 耗时: {batch_elapsed:.2f}s")
            # 轻微等待，避免频控
            if self.wait_seconds > 0:
                try:
                    time.sleep(self.wait_seconds)
                except Exception:
                    pass
        return all_df 