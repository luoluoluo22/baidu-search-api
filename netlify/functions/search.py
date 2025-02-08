import sys
import json
import requests
import logging
from typing import Dict, List, Optional
import urllib.parse

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_ENGINES = ['baidu']
REQUEST_TIMEOUT = 5

# 请求头信息
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://m.baidu.com/"
}

def search_baidu(keyword: str, page: int = 1) -> Dict:
    """执行百度搜索"""
    try:
        # 编码关键词
        encoded_keyword = urllib.parse.quote(keyword)
        
        # 构建搜索URL
        params = {
            'word': encoded_keyword,
            'pn': str((page - 1) * 10),
            'rn': '10',
            'ie': 'utf-8',
            'tn': 'baiduhome_pg',
            'ct': '201326592',
            'lm': '-1',
            'si': 'm.baidu.com',
            'rsv_pq': '1',
            'sa': 'i_1'
        }
        
        with requests.Session() as session:
            session.headers.update(HEADERS)
            
            # 获取搜索建议
            suggest_url = f'https://m.baidu.com/su'
            suggest_params = {
                'wd': keyword,
                'action': 'opensearch',
                'ie': 'utf-8'
            }
            
            suggest_response = session.get(
                suggest_url, 
                params=suggest_params, 
                timeout=REQUEST_TIMEOUT
            )
            suggest_response.raise_for_status()
            suggestions = suggest_response.json()
            
            # 转换建议为结果格式
            results = []
            
            # 处理搜索建议
            if len(suggestions) > 1 and isinstance(suggestions[1], list):
                for idx, sugg in enumerate(suggestions[1], start=1):
                    results.append({
                        'title': sugg,
                        'link': f'https://m.baidu.com/s?word={urllib.parse.quote(sugg)}',
                        'description': f'搜索建议: {sugg}',
                        'rank': idx,
                        'source': 'baidu',
                        'type': 'suggestion'
                    })
            
            # 获取相关搜索
            related_url = 'https://m.baidu.com/rec'
            related_params = {
                'platform': 'wise',
                'word': keyword,
                'qid': '',
                'rtt': '1'
            }
            
            related_response = session.get(
                related_url, 
                params=related_params, 
                timeout=REQUEST_TIMEOUT
            )
            related_response.raise_for_status()
            
            try:
                related_data = related_response.json()
                if isinstance(related_data, dict) and 'data' in related_data:
                    for item in related_data['data']:
                        if isinstance(item, dict) and 'query' in item:
                            results.append({
                                'title': item['query'],
                                'link': f'https://m.baidu.com/s?word={urllib.parse.quote(item["query"])}',
                                'description': f'相关搜索: {item["query"]}',
                                'rank': len(results) + 1,
                                'source': 'baidu',
                                'type': 'related'
                            })
            except:
                pass
            
            # 分页处理
            start_idx = (page - 1) * 10
            end_idx = start_idx + 10
            paged_results = results[start_idx:end_idx]
            
            return {
                'status': 'success',
                'data': {
                    'keyword': keyword,
                    'page': page,
                    'total_found': len(results),
                    'results': paged_results,
                    'has_next': len(results) > end_idx
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