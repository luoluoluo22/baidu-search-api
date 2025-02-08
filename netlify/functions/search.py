import sys
import json
import requests
from bs4 import BeautifulSoup

SEARCH_ENGINES = ['baidu', 'bing', 'google']

def clean_text(text):
    """清理文本内容"""
    if not text:
        return ""
    return ' '.join(text.split())

def search_baidu(keyword, page=1):
    """执行百度搜索"""
    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        session.headers.update(headers)
        
        # 访问首页获取cookie
        session.get('https://www.baidu.com')
        
        # 执行搜索
        params = {
            'wd': keyword,
            'pn': str((page - 1) * 10),
            'rn': '10',
            'ie': 'utf-8'
        }
        
        response = session.get('https://www.baidu.com/s', params=params)
        response.raise_for_status()
        
        # 解析结果
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # 查找搜索结果
        for container in soup.select('.result, .result-op, .c-container'):
            try:
                # 提取标题和链接
                h3 = container.select_one('h3')
                if not h3:
                    continue
                    
                a_tag = h3.select_one('a')
                if not a_tag:
                    continue
                
                title = clean_text(a_tag.get_text())
                link = a_tag.get('href', '')
                
                # 提取描述
                abstract = container.select_one('.content-right, .c-abstract')
                description = clean_text(abstract.get_text()) if abstract else ""
                
                # 提取来源
                source = container.select_one('.c-showurl, .source')
                source_text = clean_text(source.get_text()) if source else ""
                
                # 提取时间
                time_elem = container.select_one('.c-color-gray2')
                publish_time = clean_text(time_elem.get_text()) if time_elem else ""
                
                results.append({
                    'title': title,
                    'link': link,
                    'description': description,
                    'source': source_text,
                    'publish_time': publish_time
                })
                
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

def search_google(keyword, page=1):
    """执行Google搜索"""
    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        session.headers.update(headers)
        
        params = {
            'q': keyword,
            'start': str((page - 1) * 10),
            'num': '10',
        }
        
        response = session.get('https://www.google.com/search', params=params)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for div in soup.select('div.g'):
            try:
                title_element = div.select_one('h3')
                if not title_element:
                    continue
                    
                link_element = div.select_one('a')
                if not link_element:
                    continue
                    
                title = clean_text(title_element.get_text())
                link = link_element.get('href', '')
                
                snippet = div.select_one('.VwiC3b')
                description = clean_text(snippet.get_text()) if snippet else ""
                
                results.append({
                    'title': title,
                    'link': link,
                    'description': description,
                    'source': 'google',
                })
                
            except Exception:
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

def search_bing(keyword, page=1):
    """执行Bing搜索"""
    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        session.headers.update(headers)
        
        params = {
            'q': keyword,
            'first': str((page - 1) * 10 + 1),
            'count': '10',
        }
        
        response = session.get('https://www.bing.com/search', params=params)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for li in soup.select('.b_algo'):
            try:
                title_element = li.select_one('h2')
                if not title_element:
                    continue
                    
                link_element = title_element.select_one('a')
                if not link_element:
                    continue
                    
                title = clean_text(title_element.get_text())
                link = link_element.get('href', '')
                
                snippet = li.select_one('.b_caption p')
                description = clean_text(snippet.get_text()) if snippet else ""
                
                results.append({
                    'title': title,
                    'link': link,
                    'description': description,
                    'source': 'bing',
                })
                
            except Exception:
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
    # 获取查询参数
    try:
        params = event.get('queryStringParameters', {})
        keyword = params.get('q')
        engine = params.get('engine', 'baidu').lower()
        page = int(params.get('page', '1'))

        if not keyword:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'status': 'error',
                    'message': '请提供搜索关键词 (使用q参数)'
                }, ensure_ascii=False)
            }

        if engine not in SEARCH_ENGINES:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'status': 'error',
                    'message': f'不支持的搜索引擎。支持的引擎: {", ".join(SEARCH_ENGINES)}'
                }, ensure_ascii=False)
            }

        # 根据选择的搜索引擎调用对应的函数
        search_functions = {
            'baidu': search_baidu,
            'bing': search_bing,
            'google': search_google
        }

        search_function = search_functions[engine]
        result = search_function(keyword, page)

        result['data']['engine'] = engine
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as e:
        result = {
            'status': 'error',
            'message': str(e)
        }
        return {
            'statusCode': 500,
            'body': json.dumps(result, ensure_ascii=False)
        }

if __name__ == "__main__":
    # 用于本地测试
    test_event = {
        'queryStringParameters': {
            'q': 'python',
            'engine': 'baidu',
            'page': '1'
        }
    }
    response = handler(test_event, None)
    print(response['body'])