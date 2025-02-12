from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import asyncio
from datetime import datetime
import os
from pyppeteer import launch
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 浏览器实例缓存
browser_instance = None
last_browser_launch_time = None
BROWSER_REFRESH_INTERVAL = 3600  # 每小时刷新浏览器实例

async def get_browser():
    global browser_instance, last_browser_launch_time
    current_time = datetime.now()
    
    if (browser_instance is None or 
        last_browser_launch_time is None or 
        (current_time - last_browser_launch_time).total_seconds() > BROWSER_REFRESH_INTERVAL):
        
        if browser_instance:
            await browser_instance.close()
            
        browser_instance = await launch(
            executablePath=os.environ.get('CHROME_PATH', "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"),
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized',
                '--disable-gpu',
                '--disable-dev-shm-usage'
            ],
            ignoreHTTPSErrors=True,
            userDataDir='./user_data'
        )
        last_browser_launch_time = current_time
        
    return browser_instance

async def search_zhihu(query: str):
    try:
        browser = await get_browser()
        page = await browser.newPage()
        
        # 设置浏览器特征
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        await page.setViewport({'width': 1920, 'height': 1080})
        
        # 注入反检测代码
        await page.evaluateOnNewDocument('''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        ''')
        
        # 读取并设置cookies
        if os.environ.get('ZHIHU_COOKIE'):
            cookies = []
            cookie_str = os.environ['ZHIHU_COOKIE']
            for cookie_part in cookie_str.split('; '):
                try:
                    name, value = cookie_part.split('=', 1)
                    cookies.append({
                        'name': name,
                        'value': value,
                        'domain': '.zhihu.com',
                        'path': '/'
                    })
                except ValueError as e:
                    logger.error(f"解析cookie时出错: {cookie_part}, 错误: {e}")
            await page.setCookie(*cookies)
        
        # 存储API响应数据
        api_data = None
        api_response_received = asyncio.Event()
        
        async def intercept_response(response):
            nonlocal api_data
            if 'api/v4/search_v3?' in response.url:
                try:
                    data = await response.json()
                    if 'error' not in data:
                        api_data = data
                        api_response_received.set()
                except Exception as e:
                    logger.error(f"解析API响应时出错: {e}")
        
        page.on('response', lambda res: asyncio.ensure_future(intercept_response(res)))
        
        # 访问搜索页面
        search_url = f'https://www.zhihu.com/search?type=content&q={query}'
        await page.goto(search_url, {
            'waitUntil': 'networkidle0',
            'timeout': 30000
        })
        
        # 等待API响应
        try:
            await asyncio.wait_for(api_response_received.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.warning("获取API数据超时")
            return []
        
        # 处理搜索结果
        if api_data and 'data' in api_data:
            results = []
            for item in api_data['data']:
                try:
                    if 'object' in item:
                        obj = item['object']
                        result = {
                            'title': obj.get('title', ''),
                            'content': obj.get('excerpt', ''),
                            'author': obj.get('author', {}).get('name', '') if obj.get('author') else '',
                            'link': f"https://www.zhihu.com/question/{obj.get('question', {}).get('id', '')}/answer/{obj.get('id', '')}" if 'question' in obj else obj.get('url', ''),
                            'source': 'zhihu',
                            'timestamp': datetime.now().isoformat()
                        }
                        results.append(result)
                except Exception as e:
                    logger.error(f"处理搜索结果时出错: {e}")
                    continue
            
            return results
        
        return []
        
    except Exception as e:
        logger.error(f"搜索过程中出错: {e}")
        raise e
    
    finally:
        if page:
            await page.close()

async def handler_async(event, context):
    # 设置响应头
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    # 处理预检请求
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # 获取查询参数
    params = event.get('queryStringParameters', {})
    query = params.get('q', '')
    
    if not query:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'status': 'error',
                'message': '请提供搜索关键词'
            })
        }
    
    try:
        results = await search_zhihu(query)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'status': 'success',
                'data': results,
                'total': len(results),
                'query': query,
                'engine': 'zhihu'
            })
        }
        
    except Exception as e:
        logger.error(f"处理请求时出错: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'status': 'error',
                'message': f'搜索失败: {str(e)}'
            })
        }

def handler(event, context):
    return asyncio.get_event_loop().run_until_complete(handler_async(event, context)) 