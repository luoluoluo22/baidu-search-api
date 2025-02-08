import sys
import json
import requests
from bs4 import BeautifulSoup
import logging
import time
import os
from urllib.parse import urlencode

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_ENGINES = ['baidu', 'bing', 'google']

# 代理服务配置
PROXY_URLS = {
    'baidu': 'http://api.scrapeops.io/v1/browser',
    'google': 'http://api.scrapeops.io/v1/browser',
    'bing': 'http://api.scrapeops.io/v1/browser'
}

def clean_text(text):
    """清理文本内容"""
    if not text:
        return ""
    return ' '.join(text.split())

def get_scrapeops_url(url, params=None):
    """构建ScrapeOps代理URL"""
    scrapeops_params = {
        'api_key': os.environ.get('SCRAPEOPS_API_KEY', ''),
        'url': url
    }
    if params:
        scrapeops_params['url'] += '?' + urlencode(params)
    
    return PROXY_URLS['baidu'], scrapeops_params

def search_baidu(keyword, page=1):
    """执行百度搜索"""
    try:
        session = requests.Session()
        base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1'
        }
        session.headers.update(base_headers)
        
        # 使用代理服务访问首页
        logger.info("正在通过代理访问百度首页...")
        proxy_url, proxy_params = get_scrapeops_url('https://www.baidu.com')
        index_response = session.get(proxy_url, params=proxy_params, timeout=30)
        index_response.raise_for_status()
        
        # 添加延迟
        time.sleep(2)
        
        # 执行搜索
        search_params = {
            'wd': keyword,
            'pn': str((page - 1) * 10),
            'rn': '10',
            'ie': 'utf-8'
        }
        
        logger.info(f"正在搜索关键词: {keyword}")
        proxy_url, proxy_params = get_scrapeops_url('https://www.baidu.com/s', search_params)
        response = session.get(proxy_url, params=proxy_params, timeout=30)
        response.raise_for_status()
        
        # 记录响应内容
        logger.info(f"响应状态码: {response.status_code}")
        
        # 解析结果
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # 查找搜索结果
        containers = soup.select('.result, .result-op, .c-container')
        logger.info(f"找到 {len(containers)} 个搜索结果容器")
        
        for container in containers:
            try:
                h3 = container.select_one('h3')
                if not h3:
                    continue
                    
                a_tag = h3.select_one('a')
                if not a_tag:
                    continue
                
                title = clean_text(a_tag.get_text())
                link = a_tag.get('href', '')
                
                abstract = container.select_one('.content-right, .c-abstract')
                description = clean_text(abstract.get_text()) if abstract else ""
                
                source = container.select_one('.c-showurl, .source')
                source_text = clean_text(source.get_text()) if source else ""
                
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
        session = requests.Session()
        base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1'
        }
        session.headers.update(base_headers)
        
        search_params = {
            'q': keyword,
            'start': str((page - 1) * 10),
            'num': '10',
            'hl': 'en',
            'gl': 'us'
        }
        
        logger.info(f"正在执行Google搜索: {keyword}")
        proxy_url, proxy_params = get_scrapeops_url('https://www.google.com/search', search_params)
        response = session.get(proxy_url, params=proxy_params, timeout=30)
        response.raise_for_status()
        
        logger.info(f"Google响应状态码: {response.status_code}")
        
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
                
            except Exception as e:
                logger.error(f"解析Google结果时出错: {str(e)}")
                continue
        
        logger.info(f"Google搜索成功解析 {len(results)} 个结果")
        
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
        session = requests.Session()
        base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1'
        }
        session.headers.update(base_headers)
        
        search_params = {
            'q': keyword,
            'first': str((page - 1) * 10 + 1),
            'count': '10',
            'setlang': 'en'
        }
        
        logger.info(f"正在执行Bing搜索: {keyword}")
        proxy_url, proxy_params = get_scrapeops_url('https://www.bing.com/search', search_params)
        response = session.get(proxy_url, params=proxy_params, timeout=30)
        response.raise_for_status()
        
        logger.info(f"Bing响应状态码: {response.status_code}")
        
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
                
            except Exception as e:
                logger.error(f"解析Bing结果时出错: {str(e)}")
                continue
        
        logger.info(f"Bing搜索成功解析 {len(results)} 个结果")
        
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

        if not os.environ.get('SCRAPEOPS_API_KEY'):
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'status': 'error',
                    'message': '缺少必要的API密钥配置'
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
    os.environ['SCRAPEOPS_API_KEY'] = 'your-api-key-here'  # 仅用于本地测试
    test_event = {
        'queryStringParameters': {
            'q': 'python',
            'engine': 'baidu',
            'page': '1'
        }
    }
    response = handler(test_event, None)
    print(json.dumps(json.loads(response['body']), ensure_ascii=False, indent=2))