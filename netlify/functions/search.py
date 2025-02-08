import json
import requests
import logging
from typing import Dict, List, Optional
import urllib.parse
import html

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_ENGINES = ['baidu']
REQUEST_TIMEOUT = 2  # 缩短超时时间到2秒

# 请求头信息
HEADERS = {
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
    "Referer": "https://m.baidu.com/"
}

def clean_text(text: str) -> str:
    """清理文本内容"""
    if not text:
        return ""
    # 解码HTML实体
    text = html.unescape(text)
    # 移除多余空白
    return ' '.join(text.strip().split())

def parse_jsonp(jsonp_str: str) -> Dict:
    """解析JSONP响应"""
    try:
        # 移除JSONP包装
        json_str = jsonp_str.strip()
        if json_str.startswith('window.baidu.sug('):
            json_str = json_str[len('window.baidu.sug('):-1]
        elif json_str.startswith('{'):
            return json.loads(json_str)
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"解析JSONP失败: {str(e)}")
        return {}

def search_baidu(keyword: str, page: int = 1) -> Dict:
    """使用百度JSONP搜索建议API"""
    try:
        # 构建请求
        params = {
            'wd': keyword,
            'cb': 'window.baidu.sug',
            'ie': 'utf-8',
            'prod': 'wise'  # 使用移动版API
        }
        
        # 执行请求
        response = requests.get(
            'https://suggestion.baidu.com/su',
            params=params,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        # 解析JSONP响应
        data = parse_jsonp(response.text)
        results = []
        
        if isinstance(data, dict) and 's' in data:
            suggestions = data['s']
            start_idx = (page - 1) * 10
            end_idx = start_idx + 10
            
            # 只处理当前页的内容
            for idx, sugg in enumerate(suggestions[start_idx:end_idx], start=start_idx+1):
                # 清理文本
                cleaned_sugg = clean_text(sugg)
                if not cleaned_sugg:
                    continue
                    
                results.append({
                    'title': cleaned_sugg,
                    'link': f'https://m.baidu.com/s?word={urllib.parse.quote(cleaned_sugg)}',
                    'description': f'相关搜索',
                    'rank': idx,
                    'source': 'baidu'
                })
        
        return {
            'status': 'success',
            'data': {
                'keyword': keyword,
                'page': page,
                'total_found': len(data.get('s', [])),
                'results': results,
                'has_next': len(data.get('s', [])) > end_idx
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
        # 获取请求参数
        params = event.get('queryStringParameters', {})
        keyword = params.get('q', '').strip()
        engine = params.get('engine', 'baidu').lower().strip()
        page = int(params.get('page', '1'))
        
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
            
        # 执行搜索
        result = search_baidu(keyword, page)
        
        # 返回结果，添加缓存控制
        return {
            'statusCode': 200 if result['status'] == 'success' else 500,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=60',  # 缓存1分钟
                'Vary': 'Accept-Encoding'
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