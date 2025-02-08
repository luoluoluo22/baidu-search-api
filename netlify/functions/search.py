import sys
import json
import requests
import logging
import time
from urllib.parse import quote

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_ENGINES = ['baidu']

def search_baidu(keyword, page=1):
    """执行百度搜索"""
    try:
        params = {
            'wd': keyword,
            'pn': str((page - 1) * 10),
            'rn': '10',
            'ie': 'utf-8',
            'format': 'json',
            'rsv_sug4': 1,
            'from': 'api'
        }
        
        # 使用百度搜索建议API获取相关结果
        logger.info(f"正在搜索关键词: {keyword}")
        url = f'https://suggestion.baidu.com/su?wd={quote(keyword)}&action=opensearch'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        suggestions = response.json()
        results = []
        
        # 处理搜索建议结果
        if len(suggestions) > 1 and isinstance(suggestions[1], list):
            for suggestion in suggestions[1][:10]:  # 取前10个结果
                results.append({
                    'title': suggestion,
                    'link': f'https://www.baidu.com/s?wd={quote(suggestion)}',
                    'description': f'搜索建议: {suggestion}',
                    'source': 'baidu'
                })
        
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