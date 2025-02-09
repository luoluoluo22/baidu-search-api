import json
import logging
import sys
from search_engines import Bing, Yahoo
from typing import Dict, List
from random import choice
from time import sleep

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_ENGINES = ['bing', 'yahoo']

# 随机 User-Agent
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
]

def get_search_engine(engine_name: str):
    """获取搜索引擎实例"""
    engines = {
        "bing": Bing(),
        "yahoo": Yahoo(),
    }
    return engines.get(engine_name)

def search_with_engine(engine_name: str, keyword: str, page: int = 1) -> Dict:
    """使用指定搜索引擎搜索"""
    try:
        engine = get_search_engine(engine_name)
        if not engine:
            return {
                'status': 'error',
                'message': f'不支持的搜索引擎: {engine_name}'
            }

        # 设置请求头
        engine.set_headers({'User-Agent': choice(USER_AGENTS)})
        
        # 执行搜索，固定搜索2页
        results = engine.search(keyword, pages=2)
        search_results = []
        
        for i, result in enumerate(results.results(), 1):
            search_results.append({
                'title': result.get('title', 'No Title'),
                'link': result.get('link', 'No Link'),
                'description': result.get('text', 'No Description'),
                'rank': i,
                'source': engine_name
            })
        
        return {
            'status': 'success',
            'data': {
                'keyword': keyword,
                'engine': engine_name,
                'results': search_results,
                'total_found': len(search_results)
            }
        }
        
    except Exception as e:
        logger.error(f"搜索过程中出错: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

def handler(event):
    """处理搜索请求"""
    try:
        # 获取请求参数
        params = event.get('queryStringParameters', {})
        keyword = params.get('q', '').strip()
        engines = params.get('engines', 'bing,yahoo').lower().strip().split(',')
        
        # 验证参数
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

        # 验证搜索引擎
        engines = [e for e in engines if e in SEARCH_ENGINES]
        if not engines:
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
            
        # 执行多引擎搜索
        all_results = []
        for engine in engines:
            result = search_with_engine(engine, keyword)
            if result['status'] == 'success':
                all_results.extend(result['data']['results'])
            sleep(2)  # 避免请求过快
        
        # 返回结果
        response_data = {
            'status': 'success',
            'data': {
                'keyword': keyword,
                'engines': engines,
                'results': all_results,
                'total_found': len(all_results)
            }
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=60',  # 缓存1分钟
                'Vary': 'Accept-Encoding'
            },
            'body': json.dumps(response_data, ensure_ascii=False)
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
    # 从标准输入读取参数
    event = json.load(sys.stdin)
    response = handler(event)
    print(json.dumps(response, ensure_ascii=False))
