import sys
import json
import requests
import logging
import time
from urllib.parse import quote, urlencode

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_ENGINES = ['baidu']

def get_baidu_suggestions(keyword):
    """获取百度搜索建议"""
    try:
        url = 'https://suggestion.baidu.com/su'
        params = {
            'wd': keyword,
            'action': 'opensearch'
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.json()
    except Exception as e:
        logger.error(f"获取搜索建议时出错: {str(e)}")
        return None

def get_baidu_related(keyword):
    """获取百度相关搜索"""
    try:
        url = 'https://www.baidu.com/sugrec'
        params = {
            'prod': 'pc',
            'wd': keyword
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        try:
            data = json.loads(response.text)
            if isinstance(data, dict) and 'g' in data:
                return data['g']
        except json.JSONDecodeError:
            pass
        
        return []
    except Exception as e:
        logger.error(f"获取相关搜索时出错: {str(e)}")
        return []

def search_baidu(keyword, page=1):
    """执行百度搜索"""
    try:
        results = []
        
        # 1. 获取搜索建议
        suggestions = get_baidu_suggestions(keyword)
        if suggestions and len(suggestions) > 1 and isinstance(suggestions[1], list):
            for suggestion in suggestions[1]:
                results.append({
                    'title': suggestion,
                    'link': f'https://www.baidu.com/s?wd={quote(suggestion)}',
                    'description': '搜索建议',
                    'type': 'suggestion'
                })
        
        # 2. 获取相关搜索
        related = get_baidu_related(keyword)
        for item in related:
            if isinstance(item, dict) and 'q' in item:
                results.append({
                    'title': item['q'],
                    'link': f'https://www.baidu.com/s?wd={quote(item["q"])}',
                    'description': '相关搜索',
                    'type': 'related'
                })
        
        # 去重
        seen = set()
        unique_results = []
        for item in results:
            if item['title'] not in seen:
                seen.add(item['title'])
                unique_results.append(item)
        
        # 分页
        start_idx = (page - 1) * 10
        end_idx = start_idx + 10
        paged_results = unique_results[start_idx:end_idx]
        
        return {
            'status': 'success',
            'data': {
                'keyword': keyword,
                'page': page,
                'total_found': len(unique_results),
                'results': paged_results
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

        result = search_baidu(keyword, page)
        
        response = {
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'no-cache'
            }
        }
        
        if result['status'] == 'error':
            response['statusCode'] = 500
            response['body'] = json.dumps(result, ensure_ascii=False)
        else:
            response['statusCode'] = 200
            response['body'] = json.dumps(result, ensure_ascii=False)
        
        return response
        
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