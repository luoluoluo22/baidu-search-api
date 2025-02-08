from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

class BaiduSearchClient:
    def __init__(self):
        print("初始化Edge浏览器...")
        options = webdriver.EdgeOptions()
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Edge(options=options)
        self.base_url = 'https://www.baidu.com'

    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

    def clean_text(self, text):
        """清理文本内容"""
        if not text:
            return ""
        return ' '.join(text.split())

    def search(self, keyword):
        try:
            print(f"正在访问百度首页...")
            self.driver.get(self.base_url)
            
            print(f"等待搜索框加载...")
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "kw"))
            )
            
            print(f"输入搜索关键词: {keyword}")
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)
            
            # 等待搜索结果加载
            print("等待搜索结果加载...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "result"))
            )
            
            # 等待一下以确保动态内容加载完成
            time.sleep(2)
            
            # 保存页面源码以供调试
            with open('selenium_response.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print("\n页面源码已保存到 selenium_response.html")
            
            # 查找所有搜索结果
            results = []
            print("\n开始解析搜索结果:")
            
            # 查找所有结果容器
            result_containers = self.driver.find_elements(By.CLASS_NAME, "result")
            print(f"找到 {len(result_containers)} 个结果容器")
            
            for i, container in enumerate(result_containers, 1):
                try:
                    result = {}
                    
                    # 获取标题和链接
                    title_element = container.find_element(By.CSS_SELECTOR, "h3 a")
                    result['title'] = self.clean_text(title_element.text)
                    result['link'] = title_element.get_attribute('href')
                    
                    # 获取描述（尝试多个可能的选择器）
                    description = ""
                    desc_selectors = [
                        '.content-right',    # 标准描述
                        '.c-abstract',       # 摘要
                        '.content',          # 内容
                        '.c-row'            # 行内容
                    ]
                    
                    for selector in desc_selectors:
                        try:
                            desc_element = container.find_element(By.CSS_SELECTOR, selector)
                            description = self.clean_text(desc_element.text)
                            if description:
                                break
                        except:
                            continue
                    
                    result['description'] = description
                    
                    # 获取来源和时间信息
                    try:
                        source_element = container.find_element(By.CSS_SELECTOR, '.c-showurl, .source')
                        result['source'] = self.clean_text(source_element.text)
                    except:
                        result['source'] = ""
                        
                    try:
                        time_element = container.find_element(By.CSS_SELECTOR, '.c-color-gray2')
                        result['publish_time'] = self.clean_text(time_element.text)
                    except:
                        result['publish_time'] = ""
                    
                    print(f"\n结果 {i}:")
                    print(f"标题: {result['title']}")
                    print(f"链接: {result['link']}")
                    print(f"描述: {result['description'][:200]}...")
                    if result['source']:
                        print(f"来源: {result['source']}")
                    if result['publish_time']:
                        print(f"发布时间: {result['publish_time']}")
                    
                    results.append(result)
                    
                except Exception as e:
                    print(f"解析结果 {i} 时出错: {str(e)}")
                    continue
            
            print(f"\n总共解析出 {len(results)} 条结果")
            
            return {
                'status': 'success',
                'data': {
                    'keyword': keyword,
                    'total_found': len(results),
                    'results': results
                }
            }
            
        except Exception as e:
            error_msg = f"搜索过程中出错: {str(e)}"
            print(error_msg)
            return {
                'status': 'error',
                'message': error_msg
            }

def main():
    client = BaiduSearchClient()
    keyword = 'Python编程'
    print(f"\n{'='*50}")
    print(f"测试关键词: {keyword}")
    print('='*50)
    
    try:
        result = client.search(keyword)
        if result['status'] == 'success':
            print(f"\n搜索成功，找到 {result['data']['total_found']} 条结果")
            print("\n搜索结果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n搜索失败: {result['message']}")
    finally:
        del client  # 确保浏览器被关闭

if __name__ == "__main__":
    main()