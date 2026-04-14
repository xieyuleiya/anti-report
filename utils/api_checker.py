# -*- coding: utf-8 -*-
"""
API连通性检查模块
在下载前检查各个API接口是否可用
"""

import requests
import json
import time
from typing import Dict, List, Tuple
from config import HEADERS, API_KEY

class APIConnectivityChecker:
    """API连通性检查器"""
    
    def __init__(self):
        self.headers = HEADERS
        self.api_key = API_KEY
        self.timeout = 10  # 超时时间（秒）
        
        # 定义需要检查的API接口
        self.api_endpoints = {
            "其他数据": {
                "url": "http://192.168.1.244:8122/InternalData/DataExport",
                "test_data": {
                    "ids": "13766",
                    "start": "2024-01-01 00:00:00",
                    "end": "2024-01-01 23:59:59",
                    "key": self.api_key,
                    "type": 3
                }
            },
            "船撞数据": {
                "url": "http://192.168.1.244:8122/InternalData/GetShipData",
                "test_data": {
                    "bridgeId": 1,
                    "eventTypeId": 1,
                    "startTime": "2024-01-01 00:00:00",
                    "endTime": "2024-01-01 23:59:59",
                    "key": self.api_key
                }
            },
            "车辆荷载数据": {
                "url": "http://192.168.1.244:8122/InternalData/GetEctData",
                "test_data": {
                    "gantryId": 1,
                    "startTime": "2024-01-01 00:00:00",
                    "endTime": "2024-01-01 23:59:59",
                    "key": self.api_key
                }
            }
        }
    
    def check_single_api(self, api_name: str, url: str, test_data: dict) -> Tuple[bool, str]:
        """
        检查单个API接口的连通性
        
        Args:
            api_name: API名称
            url: API地址
            test_data: 测试数据
            
        Returns:
            (是否连通, 详细信息)
        """
        try:
            print(f"🔍 正在检查 {api_name} API连通性...")
            start_time = time.perf_counter()
            
            response = requests.post(
                url, 
                data=json.dumps(test_data), 
                headers=self.headers, 
                timeout=self.timeout
            )
            
            elapsed_time = time.perf_counter() - start_time
            
            if response.status_code == 200:
                content_length = len(response.content)
                return True, f"✅ {api_name} API连通正常 (响应时间: {elapsed_time:.2f}s, 数据大小: {content_length} 字节)"
            else:
                return False, f"❌ {api_name} API响应异常 (状态码: {response.status_code})"
                
        except requests.exceptions.Timeout:
            return False, f"⏰ {api_name} API连接超时 (超过{self.timeout}秒)"
        except requests.exceptions.ConnectionError:
            return False, f"🔌 {api_name} API连接失败 (网络或服务器问题)"
        except requests.exceptions.RequestException as e:
            return False, f"⚠️ {api_name} API请求异常: {str(e)}"
        except Exception as e:
            return False, f"💥 {api_name} API检查出现未知错误: {str(e)}"
    
    def check_all_apis(self) -> Dict[str, Tuple[bool, str]]:
        """
        检查所有API接口的连通性
        
        Returns:
            字典，键为API名称，值为(是否连通, 详细信息)的元组
        """
        print("🚀 开始检查所有API接口连通性...")
        print("=" * 60)
        
        results = {}
        
        for api_name, config in self.api_endpoints.items():
            is_connected, message = self.check_single_api(
                api_name, 
                config["url"], 
                config["test_data"]
            )
            results[api_name] = (is_connected, message)
            print(message)
            print("-" * 40)
        
        return results
    
    def check_specific_apis(self, api_names: List[str]) -> Dict[str, Tuple[bool, str]]:
        """
        检查指定API接口的连通性
        
        Args:
            api_names: 要检查的API名称列表
            
        Returns:
            字典，键为API名称，值为(是否连通, 详细信息)的元组
        """
        print(f"🔍 开始检查指定API接口连通性: {api_names}")
        print("=" * 60)
        
        results = {}
        
        for api_name in api_names:
            if api_name in self.api_endpoints:
                config = self.api_endpoints[api_name]
                is_connected, message = self.check_single_api(
                    api_name, 
                    config["url"], 
                    config["test_data"]
                )
                results[api_name] = (is_connected, message)
                print(message)
                print("-" * 40)
            else:
                error_msg = f"❌ 未知的API接口: {api_name}"
                results[api_name] = (False, error_msg)
                print(error_msg)
                print("-" * 40)
        
        return results
    
    def get_summary(self, results: Dict[str, Tuple[bool, str]]) -> str:
        """
        生成连通性检查摘要
        
        Args:
            results: 检查结果字典
            
        Returns:
            摘要信息
        """
        total_apis = len(results)
        connected_apis = sum(1 for is_connected, _ in results.values() if is_connected)
        failed_apis = total_apis - connected_apis
        
        summary = f"\n📊 API连通性检查摘要:\n"
        summary += f"  - 总接口数: {total_apis}\n"
        summary += f"  - 连通正常: {connected_apis}\n"
        summary += f"  - 连通失败: {failed_apis}\n"
        
        if failed_apis > 0:
            summary += f"  - 失败接口:\n"
            for api_name, (is_connected, message) in results.items():
                if not is_connected:
                    summary += f"    • {api_name}: {message.split(')')[0]})\n"
        
        return summary
    
    def is_all_apis_connected(self, results: Dict[str, Tuple[bool, str]]) -> bool:
        """
        检查是否所有API都连通
        
        Args:
            results: 检查结果字典
            
        Returns:
            是否全部连通
        """
        return all(is_connected for is_connected, _ in results.values())

def main():
    """测试函数"""
    checker = APIConnectivityChecker()
    
    # 检查所有API
    results = checker.check_all_apis()
    
    # 显示摘要
    summary = checker.get_summary(results)
    print(summary)
    
    # 检查是否全部连通
    if checker.is_all_apis_connected(results):
        print("🎉 所有API接口连通正常，可以开始下载数据！")
    else:
        print("⚠️ 部分API接口连通异常，请检查网络或联系管理员。")

if __name__ == "__main__":
    main() 