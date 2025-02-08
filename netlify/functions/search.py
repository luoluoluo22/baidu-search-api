import json
import requests
import logging
from typing import Dict, List, Optional
import urllib.parse

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_ENGINES = ['baidu']
REQUEST_TIMEOUT = 3  # 降低超时时间到3秒

# 请求头信息
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

def search_baidu(keyword: str, page: int = 1) -> Dict:
    """执行百度搜索"""
    try:
        # 编码关键词
        encoded_keyword = urllib.parse.quote(keyword)
        
        # 使用搜索建议API
        suggest_url = 'https://suggestion.baidu.com/su'
        params = {
            'wd': encoded_keyword,
            'action': 'opensearch',
            'ie': 'utf-8',
            'from': 'mobile'
        }
        
        # 执行请求
        response = requests.get(
            suggest_url,
            params=params,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        # 解析结果
        suggestions = response.json()
        results = []
        
        if len(suggestions) > 1 and isinstance(suggestions[1], list):
            for idx, sugg in enumerate(suggestions[1], start=1):
                results.append({
                    'title': sugg,
                    'link': f'https://m.baidu.com/s?word={urllib.parse.quote(sugg)}',
                    'description': f'搜索建议: {sugg}',
                    'rank': idx,
                    'source': 'baidu'
                })
        
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
        logger.error("搜索请求超时")
        return {
            'status': 'error',
            'message': '搜索请求超时'
        }
    except requests.RequestException as e:
        logger.error(f"网络请求错误: {str(e)}")
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