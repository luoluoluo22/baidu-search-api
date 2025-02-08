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
REQUEST_TIMEOUT = 5

# 请求头信息
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

def clean_text(text: str) -> str:
    """清理文本内容"""
    if not text:
        return ""
    return ' '.join(text.strip().split())

def search_baidu(keyword: str, page: int = 1) -> Dict:
    """执行百度搜索"""
    try:
        # 编码关键词
        encoded_keyword = urllib.parse.quote(keyword)
        
        # 构建搜索URL
        params = {
            'wd': encoded_keyword,
            'pn': str((page - 1) * 10),
            'rn': '10',  # 每页结果数
            'ie': 'utf-8'
        }
        
        with requests.Session() as session:
            session.headers.update(HEADERS)
            
            # 执行搜索
            response = session.get('https://www.baidu.com/s', params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # 解析结果
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 查找搜索结果
            containers = soup.select('#content_left .result, #content_left .result-op')
            
            for idx, container in enumerate(containers, start=(page-1)*10+1):
                try:
                    # 提取标题和链接
                    title_elem = container.select_one('h3')
                    if not title_elem:
                        continue
                        
                    link_elem = title_elem.select_one('a')
                    if not link_elem:
                        continue
                    
                    title = clean_text(link_elem.get_text())
                    link = link_elem.get('href', '')
                    
                    if not title or not link:
                        continue
                    
                    # 处理链接
                    if not link.startswith(('http://', 'https://')):
                        link = 'https://www.baidu.com' + link
                    
                    # 提取摘要
                    abstract = ''
                    abstract_elem = container.select_one('.c-abstract, .content-right')
                    if abstract_elem:
                        abstract = clean_text(abstract_elem.get_text())
                    
                    # 如果没找到摘要，尝试使用其他元素
                    if not abstract:
                        content_elems = container.select('div > *:not(h3)')
                        for elem in content_elems:
                            if elem.get_text().strip():
                                abstract = clean_text(elem.get_text())
                                break
                    
                    # 处理摘要长度
                    if abstract and len(abstract) > ABSTRACT_MAX_LENGTH:
                        abstract = abstract[:ABSTRACT_MAX_LENGTH] + '...'
                    
                    results.append({
                        'title': title,
                        'link': link,
                        'description': abstract,
                        'rank': idx,
                        'source': 'baidu'
                    })
                    
                except Exception as e:
                    logger.error(f"解析结果时出错: {str(e)}")
                    continue
            
            # 检查是否有下一页
            next_page = bool(soup.select_one('a.n:contains("下一页")'))
            
            return {
                'status': 'success',
                'data': {
                    'keyword': keyword,
                    'page': page,
                    'total_found': len(results),
                    'results': results,
                    'has_next': next_page
                }
            }
            
    except requests.Timeout:
        return {
            'status': 'error',
            'message': '搜索请求超时'
        }
    except requests.RequestException as e:
        return {
            'status': 'error',
            'message': f'网络请求错误: {str(e)}'
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