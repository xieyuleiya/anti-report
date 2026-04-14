# -*- coding: utf-8 -*-
"""
其他数据下载模块 - 重构版本
基于原有的optimized_download.py，使用统一配置
"""

import json
import requests
import calendar
import zipfile
import os
import re
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import shutil
import time

from config import (
    HEADERS, API_KEY, BATCH_SIZE_DAYS, WAIT_SECONDS,
    OTHER_DATA_EXCEL_PATH, get_other_data_categories,
    START_DATE, END_DATE, create_output_dirs, OTHER_DATA_SHEET_NAME
)

class OtherDataDownloader:
    """其他数据下载器（温湿度、温度等）"""

    def __init__(self, data_type=1):
        self.headers = HEADERS
        self.api_key = API_KEY
        self.batch_size_days = BATCH_SIZE_DAYS
        self.wait_seconds = WAIT_SECONDS
        self.excel_path = OTHER_DATA_EXCEL_PATH
        self.target_categories = get_other_data_categories()
        self.start_date = START_DATE
        self.end_date = END_DATE
        self.data_type = data_type  # 数据类型：0-秒，1-分钟，2-十分钟，3-小时

    def download_bridge_data(self, bridge_name: str) -> bool:
        """下载指定桥梁的其他数据"""
        print(f"🚀 开始下载 {bridge_name} 的其他数据...")
        print(f"📋 配置信息:")
        print(f"  - Excel文件: {self.excel_path}")
        print(f"  - 目标桥梁: {bridge_name}")
        print(f"  - 下载时间范围: {self.start_date} 到 {self.end_date}")
        print(f"  - 批量大小: {self.batch_size_days} 天")
        if self.target_categories is None:
            print(f"  - 测点种类: 全部")
        else:
            print(f"  - 测点种类: {self.target_categories}")

        # 读取Excel文件
        try:
            df = pd.read_excel(self.excel_path, sheet_name=OTHER_DATA_SHEET_NAME)
            print(f"✅ 成功读取Excel文件，共 {len(df)} 行数据")
        except Exception as e:
            print(f"❌ 读取Excel文件失败: {str(e)}")
            return False

        # 过滤指定桥梁的数据
        bridge_data = df[df['桥名'] == bridge_name]
        print(f"📊 找到 {len(bridge_data)} 条 {bridge_name} 的数据")
        if bridge_data.empty:
            print(f"❌ 未找到 {bridge_name} 的数据")
            return False

        # 按种类筛选
        filtered_data = bridge_data
        if self.target_categories is not None:
            if isinstance(self.target_categories, str):
                filtered_data = bridge_data[bridge_data.iloc[:, 4] == self.target_categories]
            elif isinstance(self.target_categories, (list, tuple, set)):
                filtered_data = bridge_data[bridge_data.iloc[:, 4].isin(self.target_categories)]
            print(f"📊 筛选后剩余 {len(filtered_data)} 条数据")
            if filtered_data.empty:
                print(f"❌ 未找到指定种类的数据")
                return False
        else:
            print(f"📊 未指定种类，下载全部种类")

        # 按所属测点分组
        categories = filtered_data.iloc[:, 4].unique()
        print(f"📊 找到的测点种类: {list(categories)}")

        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        success_count = 0
        # 为每个种类下载数据
        for category in categories:
            if pd.isna(category) or category == '':
                continue
            print(f"\n🔧 处理种类: {category}")

            category_data = filtered_data[filtered_data.iloc[:, 4] == category]

            # 创建输出目录
            output_dir = create_output_dirs(bridge_name, category)

            category_success_count = 0
            # 为每个ID单独下载数据
            for idx, row in category_data.iterrows():
                download_id = str(row.iloc[1])  # B列：通道ID
                if not download_id or download_id == 'nan':
                    continue
                
                # 组合B、A、E、F、D、C、G列的值作为文件名
                col_b = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ''  # 通道ID
                col_a = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''  # 桥名
                col_e = str(row.iloc[4]) if pd.notna(row.iloc[4]) else ''  # 类型
                col_f = str(row.iloc[5]) if pd.notna(row.iloc[5]) else ''  # 左右幅
                col_d = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ''  # 所属测点
                col_c = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ''  # 通道名称
                col_g = str(row.iloc[6]) if pd.notna(row.iloc[6]) else ''  # 位置
                file_name = f'{col_b}_{col_a}_{col_e}_{col_f}_{col_d}_{col_c}_{col_g}'.replace('__', '_').strip('_')
                
                print(f'\n🔧 处理ID: {download_id}')
                print(f'📝 文件名组合: {file_name}')

                # 单独下载该ID的数据
                success = self._download_single_id_data(category, download_id, file_name, output_dir, timestamp)
                if success:
                    category_success_count += 1
                    print(f'✅ ID {download_id} 的数据下载完成')
                else:
                    print(f'❌ ID {download_id} 的数据下载失败')
            
            if category_success_count > 0:
                success_count += 1
                print(f'✅ 种类 {category} 的数据下载完成 ({category_success_count} 个ID)')
            else:
                print(f'❌ 种类 {category} 的数据下载失败')

        print(f"\n🎉 {bridge_name} 的其他数据下载完成！成功下载 {success_count}/{len(categories)} 个种类")
        return success_count > 0

    def _download_single_id_data(self, category_name, download_id, file_name, output_dir, timestamp):
        """下载单个ID的数据"""
        url = 'http://192.168.1.244:8122/InternalData/DataExport'

        print(f'   开始下载ID {download_id} 的数据...')
        print(f'   下载范围: {self.start_date} 到 {self.end_date}')

        # 计算总天数
        start_dt = datetime.strptime(self.start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(self.end_date, '%Y-%m-%d')
        total_days = (end_dt - start_dt).days + 1

        print(f'   总天数: {total_days} 天')

        # 如果时间范围太大，分批下载
        if total_days > self.batch_size_days:
            print(f'   时间范围较大，将分批下载（每批 {self.batch_size_days} 天）')
            return self._download_single_id_in_batches(category_name, download_id, file_name, output_dir, timestamp, start_dt, end_dt)
        else:
            # 小时间范围，直接下载
            return self._download_single_id_batch(category_name, download_id, file_name, output_dir, timestamp, self.start_date, self.end_date)

    def _download_single_id_in_batches(self, category_name, download_id, file_name, output_dir, timestamp, start_dt, end_dt):
        """分批下载单个ID的大数据量"""
        current_start = start_dt
        batch_count = 0
        total_downloaded = 0

        while current_start <= end_dt:
            # 计算当前批次的结束日期
            current_end = min(current_start + timedelta(days=self.batch_size_days - 1), end_dt)

            batch_count += 1
            print(f'     批次 {batch_count}: {current_start.strftime("%Y-%m-%d")} 到 {current_end.strftime("%Y-%m-%d")}')

            # 下载当前批次
            success = self._download_single_id_batch(
                category_name, download_id, file_name, output_dir, timestamp,
                current_start.strftime('%Y-%m-%d'),
                current_end.strftime('%Y-%m-%d'),
                batch_suffix=f'_batch{batch_count:02d}'
            )

            if success:
                batch_days = (current_end - current_start).days + 1
                total_downloaded += batch_days
                print(f'     ✅ 批次 {batch_count} 完成: {batch_days} 天')
            else:
                print(f'     ❌ 批次 {batch_count} 失败')

            # 移动到下一批次
            current_start = current_end + timedelta(days=1)

            # 避免API频率限制
            if current_start <= end_dt and self.wait_seconds > 0:
                print(f'     ⏳ 等待{self.wait_seconds}秒...')
                time.sleep(self.wait_seconds)

        print(f'   🎉 单个ID批量下载完成！共下载 {total_downloaded} 天数据')
        return total_downloaded > 0

    def _download_single_id_batch(self, category_name, download_id, file_name, output_dir, timestamp, start_date, end_date, batch_suffix=''):
        """下载单个ID的单个批次数据"""
        url = 'http://192.168.1.244:8122/InternalData/DataExport'

        data = {
            'ids': download_id,
            'start': f'{start_date} 00:00:00',
            'end': f'{end_date} 23:59:59',
            'key': self.api_key,
            'type': self.data_type
        }

        try:
            print(f'     🔄 API请求: {start_date} 00:00:00 到 {end_date} 23:59:59')

            response = requests.post(url, data=json.dumps(data), headers=self.headers, timeout=60)

            if response.status_code == 200:
                # 生成文件名
                filename = f'{timestamp}_{category_name}_{download_id}_{start_date}_{end_date}{batch_suffix}.zip'
                save_path = os.path.join(output_dir, filename)

                with open(save_path, 'wb') as file:
                    file.write(response.content)

                file_size_mb = len(response.content) / (1024 * 1024)
                print(f'     ✅ 下载成功: {filename}')
                print(f'     📁 文件大小: {file_size_mb:.2f} MB')
                print(f'     ⏱️  响应时间: {response.elapsed.total_seconds():.2f}秒')

                # 处理并重命名文件
                self._process_single_id_files(output_dir, timestamp, category_name, download_id, file_name)
                return True
            else:
                print(f'     ❌ 下载失败: HTTP {response.status_code}')
                return False

        except Exception as e:
            print(f'     ❌ 下载异常: {str(e)}')
            return False

    def _process_single_id_files(self, output_dir, timestamp, category_name, download_id, file_name):
        """处理单个ID下载的文件并重命名"""
        print(f'   🔧 开始处理ID {download_id} 的文件...')

        # 创建数据目录
        data_dir = os.path.join(output_dir, '数据')
        os.makedirs(data_dir, exist_ok=True)

        # 解压所有zip文件
        zip_files = [f for f in os.listdir(output_dir) if f.endswith('.zip') and download_id in f]
        if not zip_files:
            print('   没有找到对应的zip文件，跳过解压步骤')
            return

        print(f'   📦 找到 {len(zip_files)} 个zip文件，开始解压...')

        all_data = []
        header_added = False

        for filename in zip_files:
            zip_path = os.path.join(output_dir, filename)
            try:
                with zipfile.ZipFile(zip_path, 'r') as f:
                    print(f'     📂 解压: {filename}')
                    for fn in f.namelist():
                        if fn.endswith('.txt'):
                            # 直接读取文件内容
                            with f.open(fn) as txt_file:
                                content = txt_file.read().decode('gb18030', errors='ignore')
                                lines = content.splitlines()
                                
                                if len(lines) > 1:
                                    if not header_added:
                                        all_data.append(lines[0])
                                        header_added = True
                                    all_data.extend(lines[1:])

                print(f'     ✅ 解压完成: {filename}')
            except Exception as e:
                print(f'     ❌ 解压失败: {filename}, 错误: {str(e)}')

        # 处理数据并保存
        if all_data:
            try:
                # 处理数据格式
                processed_lines = []
                for line in all_data:
                    line = line.replace('\t\t', ',')
                    line = line.replace('\t', ',')
                    line = line.replace('\n', '')
                    line = line.replace('\r', '')
                    processed_lines.append(line)

                # 创建DataFrame并排序
                df = pd.DataFrame([x.split(',') for x in processed_lines])
                if not df.empty:
                    if len(df) > 1:
                        df.columns = df.iloc[0]
                        df.columns = [col.replace('\ufeff', '').strip() for col in df.columns]
                        df = df.iloc[1:]

                    # 时间排序
                    if len(df.columns) > 0:
                        time_column = df.columns[0]
                        try:
                            df[time_column] = df[time_column].astype(str).str.replace('\ufeff', '').str.strip()

                            def parse_time_series(s: pd.Series) -> pd.Series:
                                parsed = pd.to_datetime(s, format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
                                mask = parsed.isna()
                                if mask.any():
                                    parsed2 = pd.to_datetime(s[mask], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                                    parsed.loc[mask] = parsed2
                                    mask = parsed.isna()
                                if mask.any():
                                    parsed3 = pd.to_datetime(s[mask], infer_datetime_format=True, errors='coerce')
                                    parsed.loc[mask] = parsed3
                                return parsed

                            parsed_time = parse_time_series(df[time_column])
                            df = df.assign(__time=parsed_time)
                            before_drop = len(df)
                            df = df.dropna(subset=['__time'])
                            if len(df) < before_drop:
                                print(f'     ⚠️  丢弃了 {before_drop - len(df)} 行无法解析时间的数据')
                            df.sort_values(by='__time', inplace=True, ascending=True)
                            df.drop(columns=['__time'], inplace=True)

                        except Exception as e:
                            print(f'     ⚠️  时间排序失败，使用字符串排序: {str(e)}')
                            df.sort_values(by=time_column, inplace=True, ascending=True)

                    # 生成输出文件
                    def sanitize_filename(name: str) -> str:
                        return re.sub(r'[\\/:*?"<>|]', '_', name)

                    safe_name = sanitize_filename(file_name)
                    output_filename = f'{safe_name}.txt'
                    output_path = os.path.join(output_dir, output_filename)
                    df.to_csv(output_path, sep='\t', index=False, header=False)
                    print(f'     ✅ 已保存 {len(df)} 条记录到: {output_filename}')
                else:
                    print(f'     ⚠️  ID {download_id} 的数据为空')

            except Exception as e:
                print(f'     ❌ 处理ID {download_id} 数据时出错: {str(e)}')
        else:
            print(f'     ⚠️  ID {download_id} 没有有效数据')

        # 清理临时文件
        try:
            for file_name in os.listdir(output_dir):
                if file_name.endswith('.zip'):
                    os.remove(os.path.join(output_dir, file_name))
                    print(f'   🗑️  删除zip包: {file_name}')
        except Exception as e:
            print(f'   删除zip包时出错: {str(e)}')

        try:
            if os.path.exists(data_dir):
                shutil.rmtree(data_dir)
                print(f'   🗑️  已删除过程文件夹: {data_dir}')
        except Exception as e:
            print(f'   删除过程文件夹时出错: {str(e)}') 