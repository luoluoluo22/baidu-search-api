import sys
import json
import requests
from bs4 import BeautifulSoup
import logging
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_ENGINES = ['baidu', 'bing', 'google']

MOBILE_USER_AGENT = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1'

def create_session():
    """创建一个带重试机制的会话"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def clean_text(text):
    """清理文本内容"""
    if not text:
        return ""
    return ' '.join(text.split())

def search_baidu(keyword, page=1):
    """执行百度搜索"""
    try:
        session = create_session()
        headers = {
            'User-Agent': MOBILE_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        session.headers.update(headers)
        
        # 访问移动版百度
        logger.info("正在访问百度移动版...")
        index_response = session.get('https://m.baidu.com/', timeout=10)
        index_response.raise_for_status()
        
        # 添加延迟
        time.sleep(1)
        
        # 执行搜索
        params = {
            'word': keyword,
            'pn': str((page - 1) * 10),
            'rn': '10'
        }
        
        logger.info(f"正在搜索关键词: {keyword}")
        response = session.get('https://m.baidu.com/s', params=params, timeout=10)
        response.raise_for_status()
        
        # 解析结果
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # 查找搜索结果
        for div in soup.select('.c-result'):
            try:
                title_elem = div.select_one('.c-title')
                if not title_elem:
                    continue
                    
                a_tag = title_elem.select_one('a')
                if not a_tag:
                    continue
                
                title = clean_text(a_tag.get_text())
                link = a_tag.get('href', '')
                
                desc_elem = div.select_one('.c-abstract')
                description = clean_text(desc_elem.get_text()) if desc_elem else ""
                
                results.append({
                    'title': title,
                    'link': link,
                    'description': description,
                    'source': 'baidu'
                })
                
            except Exception as e:
                logger.error(f"解析结果时出错: {str(e)}")
                continue
        
        logger.info(f"成功解析 {len(results)} 个搜索结果")
        
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
        logger.error(f"搜索过程中出错: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

def search_google(keyword, page=1):
    """执行Google搜索"""
    try:
        session = create_session()
        headers = {
            'User-Agent': MOBILE_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br'
        }
        session.headers.update(headers)
        
        params = {
            'q': keyword,
            'start': str((page - 1) * 10),
            'num': '10'
        }
        
        logger.info(f"正在执行Google搜索: {keyword}")
        response = session.get('https://www.google.com/search', params=params, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for div in soup.select('div.xpd'):
            try:
                title_element = div.select_one('div[role="heading"]')
                if not title_element:
                    continue
                    
                link_element = div.select_one('a')
                if not link_element:
                    continue
                    
                title = clean_text(title_element.get_text())
                link = link_element.get('href', '')
                
                snippet = div.select_one('div.BNeawe')
                description = clean_text(snippet.get_text()) if snippet else ""
                
                results.append({
                    'title': title,
                    'link': link,
                    'description': description,
                    'source': 'google'
                })
                
            except Exception as e:
                logger.error(f"解析Google结果时出错: {str(e)}")
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
        logger.error(f"Google搜索过程中出错: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

def search_bing(keyword, page=1):
    """执行Bing搜索"""
    try:
        session = create_session()
        headers = {
            'User-Agent': MOBILE_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br'
        }
        session.headers.update(headers)
        
        params = {
            'q': keyword,
            'first': str((page - 1) * 10 + 1),
            'count': '10'
        }
        
        logger.info(f"正在执行Bing搜索: {keyword}")
        response = session.get('https://www.bing.com/search', params=params, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for li in soup.select('li.b_algo'):
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
                    'source': 'bing'
                })
                
            except Exception as e:
                logger.error(f"解析Bing结果时出错: {str(e)}")
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
        logger.error(f"Bing搜索过程中出错: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

def handler(event, context):
    """Netlify function handler"""
    try:
        params = event.get('queryStringParameters', {})
        keyword = params.get('q')
        engine = params.get('engine', 'baidu').lower()
        page = int(params.get('page', '1'))

        logger.info(f"收到搜索请求 - 引擎: {engine}, 关键词: {keyword}, 页码: {page}")

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
        
        if result['status'] == 'error':
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result, ensure_ascii=False)
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"处理请求时出错: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': str(e)
            }, ensure_ascii=False)
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
    print(json.dumps(json.loads(response['body']), ensure_ascii=False, indent=2))