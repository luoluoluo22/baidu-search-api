import sys
import json
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional, Tuple
import urllib.parse
import asyncio
import aiohttp
import concurrent.futures

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_ENGINES = ['baidu']
ABSTRACT_MAX_LENGTH = 300
REQUEST_TIMEOUT = 5  # 请求超时时间（秒）

# 请求头信息
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

def create_session() -> requests.Session:
    """创建会话"""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session

def clean_text(text: str) -> str:
    """清理文本内容"""
    if not text:
        return ""
    return ' '.join(text.strip().split())

def get_text_content(elem) -> str:
    """获取元素的文本内容"""
    return clean_text(elem.get_text()) if elem else ""

async def fetch_url(session: aiohttp.ClientSession, url: str, params: Optional[Dict] = None) -> str:
    """异步获取URL内容"""
    try:
        async with session.get(url, params=params, timeout=REQUEST_TIMEOUT) as response:
            return await response.text()
    except Exception as e:
        logger.error(f"获取URL失败: {url}, 错误: {str(e)}")
        return ""

def parse_search_results(html: str, rank_start: int = 0) -> List[Dict]:
    """解析搜索结果HTML"""
    results = []
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找搜索结果容器
        content_left = soup.find('div', id='content_left')
        if not content_left:
            return results
            
        # 遍历搜索结果
        for div in content_left.find_all(['div', 'article'], class_=['result', 'c-container', 'result-op']):
            try:
                # 提取标题和链接
                title_elem = div.find(['h3', 'h2', 'article'])
                if not title_elem:
                    continue
                
                link_elem = title_elem.find('a')
                if not link_elem:
                    continue
                
                title = get_text_content(link_elem)
                link = link_elem.get('href', '')
                
                if not title or not link:
                    continue
                
                # 处理链接
                if not link.startswith(('http://', 'https://')):
                    link = 'https://www.baidu.com' + link
                
                # 提取摘要
                abstract = ''
                abstract_elem = div.find(['div', 'span'], class_=['c-abstract', 'content-right'])
                if abstract_elem:
                    abstract = get_text_content(abstract_elem)
                
                if not abstract:
                    # 尝试其他可能包含摘要的元素
                    for elem in div.find_all(['div', 'p']):
                        if elem != title_elem and elem.get_text().strip():
                            abstract = get_text_content(elem)
                            break
                
                # 处理摘要长度
                if abstract and len(abstract) > ABSTRACT_MAX_LENGTH:
                    abstract = abstract[:ABSTRACT_MAX_LENGTH] + '...'
                
                rank_start += 1
                results.append({
                    'title': title,
                    'link': link,
                    'description': abstract,
                    'rank': rank_start,
                    'source': 'baidu'
                })
                
            except Exception as e:
                logger.error(f"解析结果项时出错: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"解析搜索结果时出错: {str(e)}")
        
    return results

async def search_baidu_async(keyword: str, page: int = 1) -> Dict:
    """异步执行百度搜索"""
    try:
        # 编码关键词
        encoded_keyword = urllib.parse.quote(keyword)
        
        # 构建搜索URL
        search_url = f'https://www.baidu.com/s'
        params = {
            'ie': 'utf-8',
            'wd': encoded_keyword,
            'pn': (page-1) * 10
        }
        
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            html = await fetch_url(session, search_url, params)
            if not html:
                return {
                    'status': 'error',
                    'message': '搜索请求失败'
                }
            
            results = parse_search_results(html)
            
            return {
                'status': 'success',
                'data': {
                    'keyword': keyword,
                    'page': page,
                    'total_found': len(results),
                    'results': results,
                    'has_next': len(results) >= 10
                }
            }
            
    except Exception as e:
        logger.error(f"搜索过程中出错: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

def search_baidu(keyword: str, page: int = 1) -> Dict:
    """同步执行百度搜索（包装异步函数）"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(search_baidu_async(keyword, page))
    finally:
        loop.close()

def handler(event, context):
    """Netlify function handler"""
    try:
        params = event.get('queryStringParameters', {})
        keyword = params.get('q', '').strip()
        engine = params.get('engine', 'baidu').lower().strip()
        page = int(params.get('page', '1'))

        logger.info(f"收到搜索请求 - 引擎: {engine}, 关键词: {keyword}, 页码: {page}")

        if not keyword:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json; charset=utf-8',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'error',
                    'message': '请提供搜索关键词 (使用q参数)'
                }, ensure_ascii=False)
            }

        if engine not in SEARCH_ENGINES:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json; charset=utf-8',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'error',
                    'message': f'不支持的搜索引擎。支持的引擎: {", ".join(SEARCH_ENGINES)}'
                }, ensure_ascii=False)
            }

        result = search_baidu(keyword, page)
        
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'no-cache'
            },
            'body': json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"处理请求时出错: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
            },
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