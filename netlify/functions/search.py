import sys
import json
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional, Tuple

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_ENGINES = ['baidu']
ABSTRACT_MAX_LENGTH = 300

# 请求头信息
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
    "Referer": "https://www.baidu.com/",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

def create_session() -> requests.Session:
    """创建会话"""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session

def parse_search_page(html: str, rank_start: int = 0) -> Tuple[List[Dict], Optional[str]]:
    """解析百度搜索结果页面"""
    try:
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找搜索结果容器
        content_left = soup.find('div', id='content_left')
        if not content_left:
            return [], None
            
        # 遍历搜索结果
        for div in content_left.find_all(['div', 'article'], class_=['result', 'c-container', 'result-op']):
            try:
                # 提取标题
                h3 = div.find(['h3', 'article'])
                if not h3:
                    continue
                    
                a_tag = h3.find('a')
                if not a_tag:
                    continue
                
                title = a_tag.get_text().strip()
                url = a_tag.get('href', '')
                
                # 提取摘要
                abstract_div = div.find(['div', 'span'], class_=['c-abstract', 'content-right'])
                abstract = ''
                if abstract_div:
                    abstract = abstract_div.get_text().strip()
                else:
                    # 尝试获取其他可能包含摘要的元素
                    for elem in div.find_all(['div', 'p']):
                        if elem.get('class') and any(c in ['content-right', 'c-span-last'] for c in elem['class']):
                            abstract = elem.get_text().strip()
                            break
                
                if abstract and len(abstract) > ABSTRACT_MAX_LENGTH:
                    abstract = abstract[:ABSTRACT_MAX_LENGTH] + '...'
                
                rank_start += 1
                results.append({
                    'title': title,
                    'url': url,
                    'description': abstract,
                    'rank': rank_start,
                    'source': 'baidu'
                })
                
            except Exception as e:
                logger.error(f"解析结果项时出错: {str(e)}")
                continue
        
        # 查找下一页链接
        next_page = None
        page_links = soup.find_all('a', class_='n')
        for link in page_links:
            if link.get_text().strip() == '下一页>':
                next_page = 'https://www.baidu.com' + link.get('href')
                break
        
        return results, next_page
        
    except Exception as e:
        logger.error(f"解析页面时出错: {str(e)}")
        return [], None

def search_baidu(keyword: str, page: int = 1) -> Dict:
    """执行百度搜索"""
    try:
        session = create_session()
        
        # 访问百度首页获取Cookie
        session.get('https://www.baidu.com/', timeout=10)
        
        # 构建搜索URL
        search_url = f'https://www.baidu.com/s?ie=utf-8&wd={keyword}&pn={(page-1)*10}'
        
        # 执行搜索
        response = session.get(search_url, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        # 解析结果
        results, next_page = parse_search_page(response.text)
        
        return {
            'status': 'success',
            'data': {
                'keyword': keyword,
                'page': page,
                'total_found': len(results),
                'results': results,
                'has_next': bool(next_page)
            }
        }
        
    except Exception as e:
        logger.error(f"搜索过程中出错: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

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