import sys
import json
import requests
import logging
import time
import urllib.parse
from typing import Dict, List, Optional

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_ENGINES = ['baidu']

def safe_request(url: str, params: Dict = None, timeout: int = 5) -> Optional[requests.Response]:
    """安全的HTTP请求，带重试机制"""
    tries = 3
    while tries > 0:
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            tries -= 1
            if tries == 0:
                logger.error(f"请求失败: {str(e)}")
                return None
            time.sleep(1)
    return None

def get_baidu_suggestions(keyword: str) -> List[Dict]:
    """获取百度搜索建议"""
    results = []
    try:
        encoded_keyword = urllib.parse.quote(keyword)
        url = 'https://suggestion.baidu.com/su'
        params = {
            'wd': encoded_keyword,
            'action': 'opensearch'
        }
        
        response = safe_request(url, params=params)
        if not response:
            return results
            
        data = response.json()
        if len(data) > 1 and isinstance(data[1], list):
            for suggestion in data[1]:
                results.append({
                    'title': suggestion,
                    'link': f'https://www.baidu.com/s?wd={urllib.parse.quote(suggestion)}',
                    'description': '搜索建议',
                    'type': 'suggestion'
                })
    except Exception as e:
        logger.error(f"获取搜索建议时出错: {str(e)}")
    return results

def get_baidu_related(keyword: str) -> List[Dict]:
    """获取百度相关搜索"""
    results = []
    try:
        encoded_keyword = urllib.parse.quote(keyword)
        url = 'https://www.baidu.com/sugrec'
        params = {
            'prod': 'pc',
            'wd': encoded_keyword,
            'cb': 'null'
        }
        
        response = safe_request(url, params=params)
        if not response:
            return results
            
        # 移除JSONP包装
        text = response.text.strip('null()')
        if not text:
            return results
            
        try:
            data = json.loads(text)
            if isinstance(data, dict) and 'g' in data:
                for item in data['g']:
                    if isinstance(item, dict) and 'q' in item:
                        results.append({
                            'title': item['q'],
                            'link': f'https://www.baidu.com/s?wd={urllib.parse.quote(item["q"])}',
                            'description': '相关搜索',
                            'type': 'related'
                        })
        except json.JSONDecodeError:
            logger.error("解析相关搜索结果失败")
    except Exception as e:
        logger.error(f"获取相关搜索时出错: {str(e)}")
    return results

def search_baidu(keyword: str, page: int = 1) -> Dict:
    """执行百度搜索"""
    try:
        results = []
        
        # 1. 获取搜索建议
        suggestions = get_baidu_suggestions(keyword)
        results.extend(suggestions)
        
        # 2. 获取相关搜索
        related = get_baidu_related(keyword)
        results.extend(related)
        
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
        
        status_code = 200 if result['status'] == 'success' else 500
        return {
            'statusCode': status_code,
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