"""
数据加载模块（data_loader.py）

该模块提供 `DataLoader` 类，用于：
- 扫描数据目录，按"桥梁名称 -> 测点txt文件列表"的结构收集数据文件；
- 加载单个测点数据文件，解析为结构化的 `pandas.DataFrame`；
- 从文件名中提取测点编号：直接解析文件名格式，获取墩号作为测点编号。

设计要点：
- 解析鲁棒性：
  - 读入时忽略注释行（以 `#` 或 `//` 开头）和空行；
  - 自动适配"任意数量空白字符"的定界（`\s+`），以兼容制表符/多个空格；
  - 时间戳解析提供兜底格式 `%Y-%m-%d %H:%M:%S.%f`；
- 失败可恢复：
  - 任一阶段失败均记录日志（`utils.log`），并在必要时返回 `None`，避免影响批处理；
- 目录扫描策略：
  - 扫描高速文件夹下的桥梁文件夹，每个桥梁文件夹下直接包含测点txt文件；
- 文件名解析策略：
  - 支持格式：ID_测点编号_高速名称_桥梁名称_墩号_厂家_状态
  - 直接提取墩号作为测点编号，无需Excel对照表；

注意：
- 该模块依赖 `utils.log` 进行信息、警告和错误日志输出；
- 文件名格式为硬编码，不符合格式的文件名将记录警告并使用文件名作为测点编号。
"""

import os
import glob
import re
import pandas as pd
from .utils import log


class DataLoader:
    """
    数据加载类，负责：
    1) 扫描数据目录，按桥梁维度汇总测点txt文件；
    2) 从单个测点文件解析结构化数据；
    3) 根据文件名提取测点编号（直接解析文件名格式）。

    参数
    - data_dir: str
        包含多个高速文件夹的数据根目录。结构通常为：
        data_dir/
          ├─ 云茂/
          │   ├─ 倒流大桥/
          │   │   ├─ 13761_xxx_云茂_倒流大桥_左幅3#_博远.txt
          │   │   └─ 13762_xxx_云茂_倒流大桥_左幅4#_博远_空文件.txt
          │   └─ 华南口大桥/
          │       └─ 13889_xxx_云茂_华南口大桥_左幅0#_博远.txt
          └─ 广佛肇/
              └─ ...
    """

    def __init__(self, data_dir):
        # 保存数据根目录路径，不做存在性校验（由调用者或后续流程决定）。
        self.data_dir = data_dir
        # 轻量缓存：避免重复解析同名文件的传感器编号和文件信息
        self._sensor_id_cache = {}  # dict[str_base_name, str_sensor_id]
        self._file_info_cache = {}  # dict[str_base_name, dict] 存储文件的完整解析信息

    def extract_sensor_id(self, filename):
        """
        从文件名中提取测点编号和所有相关信息。

        新的文件名格式：13925_BJDQ-INC-P01-001-01_云茂_白鸡大桥_左幅0#_博远_少量缺失
        对应：ID_测点编号_高速名称_桥梁名称_墩号_厂家_状态

        参数
        - filename: str
            文件完整路径或仅文件名字符串。

        返回
        - str: 提取到的测点编号（墩号部分）
        """
        # 仅取文件名部分，避免目录前缀干扰
        base_name = os.path.basename(filename)

        # 命中缓存则直接返回，避免重复解析
        cached = self._sensor_id_cache.get(base_name)
        if cached is not None:
            return cached

        # 解析文件名格式：ID_测点编号_高速名称_桥梁名称_墩号_厂家_状态
        # 先去除扩展名，然后使用下划线分割
        name_without_ext = os.path.splitext(base_name)[0]
        parts = name_without_ext.split('_')
        
        if len(parts) >= 6:  # 至少需要6个部分
            try:
                # 提取各个部分
                sensor_id = parts[0]  # ID
                sensor_code = parts[1]  # 测点编号
                highway_name = parts[2]  # 高速名称
                bridge_name = parts[3]  # 桥梁名称
                pier_number = parts[4]  # 墩号（这就是我们需要的测点名称）
                manufacturer = parts[5]  # 厂家
                status = parts[6] if len(parts) > 6 else ""  # 状态（可选）
                
                # 存储完整信息到缓存中，供后续使用
                file_info = {
                    'sensor_id': sensor_id,
                    'sensor_code': sensor_code,
                    'highway_name': highway_name,
                    'bridge_name': bridge_name,
                    'pier_number': pier_number,
                    'manufacturer': manufacturer,
                    'status': status
                }
                
                # 将完整信息存储到缓存中，键为文件名，值为墩号（测点名称）
                self._sensor_id_cache[base_name] = pier_number
                
                # 同时存储完整信息到另一个缓存中，供后续使用
                if not hasattr(self, '_file_info_cache'):
                    self._file_info_cache = {}
                self._file_info_cache[base_name] = file_info
                
                log(f"成功解析文件名: {base_name} -> 墩号: {pier_number}, 状态: {status}", 'info')
                return pier_number
                
            except Exception as e:
                log(f"解析文件名失败: {base_name}, 错误: {e}", 'warn')
        
        # 如果解析失败，记录警告并返回文件名（去扩展名）
        log(f"文件名格式不符合预期: {base_name}", 'warn')
        fallback = os.path.splitext(base_name)[0]
        self._sensor_id_cache[base_name] = fallback
        return fallback

    def get_file_info(self, filename):
        """
        获取文件的完整解析信息。
        
        参数
        - filename: str
            文件完整路径或仅文件名字符串。
            
        返回
        - dict: 包含文件所有解析信息的字典，如果解析失败返回None
        """
        # 确保已经解析过这个文件
        self.extract_sensor_id(filename)
        
        # 获取文件名部分
        base_name = os.path.basename(filename)
        
        # 从缓存中获取完整信息
        if hasattr(self, '_file_info_cache') and base_name in self._file_info_cache:
            return self._file_info_cache[base_name]
        
        return None

    def get_sensor_status(self, filename):
        """
        获取传感器的状态信息。
        
        参数
        - filename: str
            文件完整路径或仅文件名字符串。
            
        返回
        - str: 传感器状态
            - "离线": 如果文件状态为"空文件"
            - "在线": 其他状态（包括正常、少量缺失、大量缺失等）
            - "未知": 如果无法获取状态信息
        """
        file_info = self.get_file_info(filename)
        if file_info:
            status = file_info.get('status', '')
            if status == '空文件':
                return "离线"
            else:
                return "在线"
        return "未知"

    def scan_data_directories(self):
        """
        扫描数据根目录，按桥梁文件夹聚合测点txt文件。

        规则（适配新数据结构）：
        - 数据根目录下包含高速名文件夹（如"云茂"、"广佛肇"）
        - 每个高速文件夹下包含桥梁文件夹
        - 每个桥梁文件夹下直接包含测点txt文件
        - 扫描所有高速下的所有桥梁

        返回
        - dict[str, list[str]]: {桥梁名称: [该桥梁下收集到的测点txt文件路径列表]}。
        - 若未发现任何桥梁数据，返回空字典，并记录错误日志。
        """
        bridge_files = {}
        total_files = 0

        log("扫描数据目录...")
        
        # 遍历数据根目录下的高速文件夹
        for highway_folder in os.listdir(self.data_dir):
            highway_path = os.path.join(self.data_dir, highway_folder)
            if not os.path.isdir(highway_path):
                # 跳过非目录项
                continue
                
            log(f"  扫描高速: {highway_folder}")
            
            # 遍历高速文件夹下的桥梁文件夹
            for bridge_folder in os.listdir(highway_path):
                bridge_path = os.path.join(highway_path, bridge_folder)
                if not os.path.isdir(bridge_path):
                    # 跳过非目录项
                    continue
                
                # 扫描桥梁文件夹下的txt文件
                txt_files = glob.glob(os.path.join(bridge_path, "*.txt"))
                
                if txt_files:
                    # 直接使用桥名作为桥梁标识
                    bridge_key = bridge_folder
                    bridge_files[bridge_key] = txt_files
                    total_files += len(txt_files)
                    log(f"    - {bridge_key}: {len(txt_files)} 个测点")

        if bridge_files:
            log(f"总计: {len(bridge_files)} 座桥梁, {total_files} 个测点", 'success')
            log("==================================================================")
        else:
            log("未找到任何桥梁数据", 'error')

        return bridge_files

    def load_single_file(self, file_path, bridge_name):
        """
        加载并解析单个测点数据文件，返回按时间升序的 `DataFrame`。

        解析规则
        - 首先检查文件状态：如果状态为"空文件"，直接返回None并标记为"离线"；
        - 忽略：空行、以 `#` 或 `//` 开头的注释行；
        - 拆分：使用通用空白正则 `\s+` 进行字段分割，以兼容多空格/制表符；
        - 字段：至少4段，前两段拼接为时间戳字符串，随后两段分别为水平角、竖直角；
        - 类型：角度字段转为 `float`，时间戳尝试自动解析，失败则尝试格式`%Y-%m-%d %H:%M:%S.%f`；
        - 清洗：丢弃解析失败或缺失时间戳的记录，最终按时间排序并重建索引；

        参数
        - file_path: str
            待解析的测点txt文件路径；
        - bridge_name: str
            该测点所属的桥梁名称（外部传入，用于标注列）。

        返回
        - pandas.DataFrame | None
            成功时返回包含如下列的DataFrame：
            - 'timestamp': pandas.Timestamp
            - 'horizontal_angle': float
            - 'vertical_angle': float
            - 'sensor_id': str
            - 'bridge_name': str
            若文件无法解析或无有效记录，返回 None。
        """
        try:
            # 预先提取测点编号（包含Excel映射/正则回退/兜底）
            sensor_id = self.extract_sensor_id(file_path)
            
            # 检查文件状态，如果为空文件则直接返回None
            file_info = self.get_file_info(file_path)
            if file_info and file_info.get('status') == '空文件':
                log(f"文件 {file_path} 状态为空文件，标记为离线", 'info')
                return None

            # 累积解析出的记录（逐行解析）
            data = []
            # 尝试多种编码方式读取文件
            encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']
            file_content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        file_content = f.readlines()
                    break
                except UnicodeDecodeError:
                    continue
            
            if file_content is None:
                log(f"文件 {file_path} 编码无法识别", 'error')
                return None
            
            for line_num, line in enumerate(file_content, 1):
                line = line.strip()

                # 跳过空行与注释行（`#` 或 `//`）
                if not line or line.startswith(('#', '//')):
                    continue

                try:
                    # 使用正则 `\s+` 拆分任意数量的空白字符
                    parts = re.split(r'\s+', line.strip())

                    # 期望至少4段：日期、时间、水平角、竖直角
                    if len(parts) >= 4:
                        # 清理时间戳字符串，去除可能的特殊字符
                        timestamp_str = f"{parts[0]} {parts[1]}".strip()
                        
                        # 验证时间戳格式
                        if not re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?', timestamp_str):
                            continue
                        
                        data.append({
                            'timestamp': timestamp_str,
                            'horizontal_angle': float(parts[2].strip()),
                            'vertical_angle': float(parts[3].strip()),
                            'sensor_id': sensor_id,
                            'bridge_name': bridge_name
                        })
                except (ValueError, IndexError) as e:
                    # 单行解析失败（如角度非数/字段缺失），忽略该行继续
                    if line_num <= 5:  # 只在前5行显示错误，避免刷屏
                        log(f"文件 {file_path} 第{line_num}行解析失败: {line[:50]}...", 'warn')
                    continue

            if not data:
                # 未解析到任何有效数据，返回 None 以便调用方跳过
                log(f"文件 {file_path} 未能解析到有效数据", 'warn')
                return None

            # 构建DataFrame
            df = pd.DataFrame(data)

            # 时间戳解析：尝试多种格式
            timestamp_formats = [
                '%Y-%m-%d %H:%M:%S.%f',  # 2025-08-01 02:03:00.000
                '%Y-%m-%d %H:%M:%S',     # 2025-08-01 02:03:00
                '%Y/%m/%d %H:%M:%S.%f',  # 2025/08/01 02:03:00.000
                '%Y/%m/%d %H:%M:%S',     # 2025/08/01 02:03:00
            ]
            
            timestamp_parsed = False
            for fmt in timestamp_formats:
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], format=fmt)
                    timestamp_parsed = True
                    break
                except:
                    continue
            
            if not timestamp_parsed:
                # 如果所有格式都失败，尝试自动推断
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    timestamp_parsed = True
                except Exception as e:
                    # 若仍失败，记录错误并返回None
                    log(f"文件 {file_path} 时间戳格式无法解析: {e}", 'error')
                    # 显示前几个时间戳样本用于调试
                    if len(df) > 0:
                        sample_timestamps = df['timestamp'].head(3).tolist()
                        log(f"时间戳样本: {sample_timestamps}", 'error')
                    return None

            # 清洗并排序：去除缺失时间戳记录，按时间升序排列，重置索引
            df = df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)

            if len(df) == 0:
                log(f"文件 {file_path} 没有有效的数据记录", 'warn')
                return None

            # 成功返回结果（不在此处输出成功日志，避免批量时刷屏）
            return df
        except Exception as e:
            # 顶层保护：任何未捕获异常均记录错误并返回 None，保障批处理稳定
            log(f"加载文件 {file_path} 失败: {e}", 'error')
            return None 