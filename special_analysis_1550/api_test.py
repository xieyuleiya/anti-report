import requests
import json
import os
import zipfile
import io
from datetime import datetime

# API_URL = 'http://128.21.9.139:8122/InternalData/DataExport'
API_URL = 'http://192.168.1.244:8122/InternalData/DataExport'
HEADERS = {'Content-Type': 'application/json'}
TEST_DATA = {
    # "ids": "13765",
    "ids": "13806",    
    "start": "2026-03-16 00:00:00",
    "end": "2026-03-16 23:59:59",
    "key": "337F11D3-7181-4570-9F44-CD42396BA266",
    "type": 1
}

def test_api(url, data, headers, save_file=True, preview_lines=20):
    """
    测试API并查看返回的文件内容
    
    Args:
        url: API地址
        data: 请求数据
        headers: 请求头
        save_file: 是否保存文件到本地
        preview_lines: 预览的行数（仅对文本文件有效）
    """
    try:
        response = requests.post(url, data=json.dumps(data), headers=headers, timeout=10)
        if response.status_code == 200:
            print("API连通性测试通过！")
            print(f"返回内容长度: {len(response.content)} 字节")
            
            # 获取Content-Type
            content_type = response.headers.get('Content-Type', 'unknown')
            print(f"Content-Type: {content_type}")
            
            # 尝试从Content-Disposition获取文件名
            content_disposition = response.headers.get('Content-Disposition', '')
            filename = None
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"\'')
            
            # 保存文件
            output_path = None
            if save_file:
                if not filename:
                    # 根据Content-Type推断文件扩展名
                    if 'zip' in content_type.lower() or 'application/zip' in content_type.lower():
                        filename = f'api_response_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
                    elif 'json' in content_type.lower():
                        filename = 'api_response.json'
                    elif 'csv' in content_type.lower() or 'text/csv' in content_type.lower():
                        filename = 'api_response.csv'
                    elif 'excel' in content_type.lower() or 'spreadsheet' in content_type.lower():
                        filename = 'api_response.xlsx'
                    else:
                        filename = f'api_response_{datetime.now().strftime("%Y%m%d_%H%M%S")}.dat'
                
                # 保存到当前目录
                output_dir = os.path.dirname(os.path.abspath(__file__))
                output_path = os.path.join(output_dir, filename)
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"文件已保存到: {output_path}")
            
            # 尝试预览内容
            print("\n" + "="*50)
            print("响应内容预览:")
            print("="*50)
            
            # 首先检查是否是ZIP文件
            is_zip = False
            try:
                zip_file = zipfile.ZipFile(io.BytesIO(response.content))
                is_zip = True
                zip_file.close()
            except:
                pass
            
            if is_zip:
                # 处理ZIP文件
                print("响应格式: ZIP压缩包")
                try:
                    zip_file = zipfile.ZipFile(io.BytesIO(response.content))
                    file_list = zip_file.namelist()
                    print(f"ZIP文件包含 {len(file_list)} 个文件:")
                    for i, file_name in enumerate(file_list, 1):
                        file_info = zip_file.getinfo(file_name)
                        print(f"  {i}. {file_name} ({file_info.file_size} 字节)")
                    
                    print("\n" + "-"*50)
                    print("ZIP文件内容预览:")
                    print("-"*50)
                    
                    # 查找并读取txt文件
                    txt_files = [f for f in file_list if f.lower().endswith('.txt')]
                    if txt_files:
                        for txt_file in txt_files:
                            print(f"\n文件: {txt_file}")
                            print("-"*50)
                            try:
                                content = zip_file.read(txt_file)
                                # 尝试解码为文本（尝试UTF-8，如果失败则用GBK）
                                try:
                                    text_content = content.decode('utf-8')
                                except:
                                    try:
                                        text_content = content.decode('gbk')
                                    except:
                                        text_content = content.decode('utf-8', errors='ignore')
                                
                                lines = text_content.split('\n')
                                print(f"总行数: {len(lines)}")
                                print(f"文件大小: {len(content)} 字节")
                                print("\n文件内容预览:")
                                print("-"*50)
                                preview = '\n'.join(lines[:preview_lines])
                                print(preview)
                                if len(lines) > preview_lines:
                                    print(f"\n... (仅显示前 {preview_lines} 行，完整内容在ZIP文件中)")
                            except Exception as e:
                                print(f"读取文件 {txt_file} 时出错: {e}")
                    else:
                        print("\nZIP文件中没有找到.txt文件")
                        # 如果有其他文本文件，尝试读取第一个
                        text_extensions = ['.csv', '.json', '.xml', '.log']
                        for ext in text_extensions:
                            text_files = [f for f in file_list if f.lower().endswith(ext)]
                            if text_files:
                                print(f"\n找到 {ext} 文件: {text_files[0]}")
                                try:
                                    content = zip_file.read(text_files[0])
                                    try:
                                        text_content = content.decode('utf-8')
                                    except:
                                        text_content = content.decode('gbk', errors='ignore')
                                    lines = text_content.split('\n')
                                    print(f"总行数: {len(lines)}")
                                    preview = '\n'.join(lines[:preview_lines])
                                    print(preview)
                                    if len(lines) > preview_lines:
                                        print(f"\n... (仅显示前 {preview_lines} 行)")
                                except Exception as e:
                                    print(f"读取文件出错: {e}")
                                break
                    
                    # 如果需要保存解压后的文件
                    if save_file and output_path:
                        extract_dir = output_path.replace('.zip', '_extracted')
                        os.makedirs(extract_dir, exist_ok=True)
                        zip_file.extractall(extract_dir)
                        print(f"\nZIP文件已解压到: {extract_dir}")
                    
                    zip_file.close()
                except Exception as e:
                    print(f"处理ZIP文件时出错: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                # 尝试作为文本预览（JSON、CSV等文本格式）
                try:
                    # 先尝试JSON
                    try:
                        json_data = response.json()
                        print("响应格式: JSON")
                        print(json.dumps(json_data, ensure_ascii=False, indent=2)[:2000])
                        if len(str(json_data)) > 2000:
                            print("\n... (内容已截断，完整内容已保存到文件)")
                    except:
                        # 不是JSON，尝试作为文本
                        text_content = response.text
                        lines = text_content.split('\n')
                        print(f"响应格式: 文本 (共 {len(lines)} 行)")
                        preview = '\n'.join(lines[:preview_lines])
                        print(preview)
                        if len(lines) > preview_lines:
                            print(f"\n... (仅显示前 {preview_lines} 行，完整内容已保存到文件)")
                except Exception as e:
                    print(f"无法以文本格式预览，可能是二进制文件: {e}")
                    print(f"前100个字节 (十六进制): {response.content[:100].hex()}")
            
            print("="*50)
            
            return True, response
        else:
            print(f"API连通性测试失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            return False, None
    except Exception as e:
        print(f"API连通性测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == "__main__":
    print("正在测试API连通性并查看返回文件...")
    result, response = test_api(API_URL, TEST_DATA, HEADERS, save_file=True, preview_lines=20)
    if not result:
        print("API不可用，请检查网络或接口状态。")
    else:
        print("\nAPI可用，返回的文件内容已查看并保存。") 