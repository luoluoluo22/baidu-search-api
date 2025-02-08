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

def search_baidu(keyword, page=1):
    """执行百度搜索"""
    try:
        # 首先获取搜索建议
        logger.info(f"正在获取搜索建议: {keyword}")
        suggest_url = f'https://suggestion.baidu.com/su?wd={quote(keyword)}&action=opensearch'
        response = requests.get(suggest_url, timeout=10)
        response.raise_for_status()
        
        suggestions = response.json()
        suggest_results = []
        
        # 处理搜索建议结果
        if len(suggestions) > 1 and isinstance(suggestions[1], list):
            for suggestion in suggestions[1]:
                suggest_results.append({
                    'title': suggestion,
                    'link': f'https://www.baidu.com/s?wd={quote(suggestion)}',
                    'description': f'搜索建议: {suggestion}',
                    'type': 'suggestion'
                })
        
        # 然后获取相关搜索
        logger.info(f"正在获取相关搜索: {keyword}")
        related_url = 'https://www.baidu.com/sugrec'
        params = {
            'prod': 'pc',
            'wd': keyword,
            'cb': 'null'
        }
        
        response = requests.get(related_url, params=params, timeout=10)
        response.raise_for_status()
        
        # 移除 "null(" 和最后的 ")"
        related_data = response.text.strip('null()')
        related_json = json.loads(related_data)
        
        # 处理相关搜索结果
        if 'g' in related_json:
            for item in related_json['g']:
                if 'q' in item:
                    suggest_results.append({
                        'title': item['q'],
                        'link': f'https://www.baidu.com/s?wd={quote(item["q"])}',
                        'description': f'相关搜索: {item["q"]}',
                        'type': 'related'
                    })
        
        # 对结果进行排序和去重
        seen = set()
        unique_results = []
        for item in suggest_results:
            if item['title'] not in seen:
                seen.add(item['title'])
                unique_results.append(item)
        
        # 分页处理
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

        # 目前只支持百度搜索
        result = search_baidu(keyword, page)
        
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