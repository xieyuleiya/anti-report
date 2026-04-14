import requests
import json

API_URL = 'http://128.21.9.139:28122/InternalData/DataExport'
HEADERS = {'Content-Type': 'application/json'}
TEST_DATA = {
    # "ids": "13765",
    "ids": "13766",    
    "start": "2024-01-01 00:00:00",
    "end": "2024-01-01 23:59:59",
    "key": "337F11D3-7181-4570-9F44-CD42396BA266",
    "type": 3
}

def test_api(url, data, headers):
    try:
        response = requests.post(url, data=json.dumps(data), headers=headers, timeout=10)
        if response.status_code == 200:
            print("API连通性测试通过！")
            print(f"返回内容长度: {len(response.content)} 字节")
            return True
        else:
            print(f"API连通性测试失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"API连通性测试异常: {e}")
        return False

if __name__ == "__main__":
    print("正在测试API连通性...")
    result = test_api(API_URL, TEST_DATA, HEADERS)
    if not result:
        print("API不可用，请检查网络或接口状态。")
    else:
        print("API可用，可以开始下载数据。") 