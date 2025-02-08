import sys
import json
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional, Tuple
import urllib.parse

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

def clean_text(text: str) -> str:
    """清理文本内容"""
    if not text:
        return ""
    return ' '.join(text.strip().split())

def get_text_content(elem) -> str:
    """获取元素的文本内容"""
    return clean_text(elem.get_text()) if elem else ""

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
                
                # 尝试不同的摘要容器类
                abstract_classes = ['c-abstract', 'content-right', 'c-span-last', 'c-color-text']
                for class_name in abstract_classes:
                    abstract_elem = div.find(['div', 'span'], class_=class_name)
                    if abstract_elem:
                        abstract = get_text_content(abstract_elem)
                        break
                
                # 如果还没找到摘要，尝试其他方法
                if not abstract:
                    # 尝试获取第一个非空的div文本
                    for elem in div.find_all(['div', 'p']):
                        if elem.get_text().strip() and elem != title_elem:
                            abstract = get_text_content(elem)
                            break
                
                # 如果还是没有摘要，使用整个容器的文本
                if not abstract:
                    text = get_text_content(div)
                    if text != title:
                        abstract = text
                
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
        
        # 编码关键词
        encoded_keyword = urllib.parse.quote(keyword)
        
        # 构建搜索URL
        search_url = f'https://www.baidu.com/s?ie=utf-8&wd={encoded_keyword}&pn={(page-1)*10}'
        logger.info(f"搜索URL: {search_url}")
        
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