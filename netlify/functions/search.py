import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, unquote

class BaiduSearchClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = 'https://www.baidu.com/s'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(self.headers)

    def _clean_text(self, text):
        """清理文本内容"""
        if not text:
            return ""
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        # 移除特殊字符
        text = text.replace('\n', ' ').replace('\r', '')
        return text

    def _extract_search_results(self, html_content):
        """解析搜索结果HTML，提取结构化数据"""
        soup = BeautifulSoup(html_content, 'html.parser')  # 使用内置解析器
        results = []
        
        # 查找所有搜索结果容器
        containers = soup.find_all(['div', 'article'], class_=['result', 'result-op', 'c-container'])
        
        for container in containers:
            try:
                result = {}
                
                # 提取标题和链接
                title_element = container.find(['h3', 'h2'])
                if title_element:
                    a_tag = title_element.find('a')
                    if a_tag:
                        result['title'] = self._clean_text(a_tag.get_text())
                        result['link'] = a_tag.get('href', '')
                    else:
                        continue

                # 提取描述
                content_element = container.find(['div', 'span'], class_=['content-right', 'c-abstract'])
                if content_element:
                    result['description'] = self._clean_text(content_element.get_text())
                else:
                    # 备选描述提取
                    abstract = container.find(['div', 'span'], class_=['abstract', 'content'])
                    result['description'] = self._clean_text(abstract.get_text()) if abstract else ""

                # 提取来源和时间
                source_element = container.find(['span', 'a'], class_=['c-showurl', 'source'])
                result['source'] = self._clean_text(source_element.get_text()) if source_element else ""

                time_element = container.find('span', class_=['c-color-gray2', 'time'])
                result['publish_time'] = self._clean_text(time_element.get_text()) if time_element else ""

                results.append(result)

            except Exception as e:
                print(f"解析结果错误: {str(e)}")
                continue

        return results

    def search(self, keyword, page=1):
        """执行搜索并返回结构化结果"""
        offset = (page - 1) * 10
        params = {
            'wd': keyword,
            'pn': str(offset),
            'rn': '10',
            'ie': 'utf-8'
        }
        
        try:
            # 获取初始cookie
            self.session.get('https://www.baidu.com')
            
            # 执行搜索
            response = self.session.get(
                self.base_url,
                params=params,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # 解析搜索结果
                results = self._extract_search_results(response.text)
                
                return {
                    'status': 'success',
                    'data': {
                        'keyword': keyword,
                        'page': page,
                        'total_found': len(results),
                        'results': results
                    }
                }
            else:
                return {
                    'status': 'error',
                    'message': f'搜索失败，状态码: {response.status_code}'
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
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'error',
                'message': '请提供搜索关键词(q参数)'
            }, ensure_ascii=False)
        }
    
    # 执行搜索
    client = BaiduSearchClient()
    result = client.search(keyword, page)
    
    # 返回结果
    return {
        'statusCode': 200 if result['status'] == 'success' else 500,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET, OPTIONS'
        },
        'body': json.dumps(result, ensure_ascii=False)
    }