from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

class BaiduSearchClient:
    def __init__(self):
        options = webdriver.EdgeOptions()
        options.add_argument('--headless')
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

    def search(self, keyword, page=1):
        """
        执行百度搜索并返回结构化结果
        :param keyword: 搜索关键词
        :param page: 页码（目前暂未实现分页）
        :return: 搜索结果字典
        """
        try:
            # 访问百度首页
            self.driver.get(self.base_url)
            
            # 等待搜索框加载并输入关键词
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "kw"))
            )
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)
            
            # 等待搜索结果加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "result"))
            )
            
            # 等待动态内容加载
            time.sleep(2)
            
            # 查找所有搜索结果
            results = []
            result_containers = self.driver.find_elements(By.CLASS_NAME, "result")
            
            for container in result_containers:
                try:
                    result = {}
                    
                    # 获取标题和链接
                    title_element = container.find_element(By.CSS_SELECTOR, "h3 a")
                    result['title'] = self.clean_text(title_element.text)
                    result['link'] = title_element.get_attribute('href')
                    
                    # 获取描述
                    desc_selectors = ['.content-right', '.c-abstract', '.content', '.c-row']
                    description = ""
                    for selector in desc_selectors:
                        try:
                            desc_element = container.find_element(By.CSS_SELECTOR, selector)
                            description = self.clean_text(desc_element.text)
                            if description:
                                break
                        except:
                            continue
                    result['description'] = description
                    
                    # 获取来源信息
                    try:
                        source_element = container.find_element(By.CSS_SELECTOR, '.c-showurl, .source')
                        result['source'] = self.clean_text(source_element.text)
                    except:
                        result['source'] = ""
                        
                    # 获取发布时间
                    try:
                        time_element = container.find_element(By.CSS_SELECTOR, '.c-color-gray2')
                        result['publish_time'] = self.clean_text(time_element.text)
                    except:
                        result['publish_time'] = ""
                    
                    results.append(result)
                    
                except Exception as e:
                    continue
            
            return {
                'status': 'success',
                'data': {
                    'keyword': keyword,
                    'page': page,
                    'total_found': len(results),
                    'results': results
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

def handler(event, context):
    """Netlify function handler"""
    # 解析查询参数
    params = event.get('queryStringParameters', {})
    keyword = params.get('q', '')
    page = int(params.get('page', '1'))
    
    if not keyword:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'status': 'error',
                'message': '请提供搜索关键词(q参数)'
            }, ensure_ascii=False)
        }
    
    # 执行搜索
    client = BaiduSearchClient()
    result = client.search(keyword, page)
    
    # 设置CORS头
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    # 返回结果
    return {
        'statusCode': 200 if result['status'] == 'success' else 500,
        'headers': headers,
        'body': json.dumps(result, ensure_ascii=False)
    }