from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import asyncio
from datetime import datetime
import os
from pyppeteer import launch
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if os.environ.get('DEBUG') == 'true' else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # 确保日志输出到stdout
)
logger = logging.getLogger(__name__)

# 浏览器实例缓存
browser_instance = None
last_browser_launch_time = None
BROWSER_REFRESH_INTERVAL = 3600  # 每小时刷新浏览器实例

async def get_browser():
    global browser_instance, last_browser_launch_time
    current_time = datetime.now()
    
    logger.debug(f"获取浏览器实例，当前时间: {current_time}")
    logger.debug(f"现有实例: {browser_instance}, 上次启动时间: {last_browser_launch_time}")
    
    if (browser_instance is None or 
        last_browser_launch_time is None or 
        (current_time - last_browser_launch_time).total_seconds() > BROWSER_REFRESH_INTERVAL):
        
        if browser_instance:
            logger.debug("关闭旧的浏览器实例")
            await browser_instance.close()
        
        logger.debug("启动新的浏览器实例")
        chrome_path = os.environ.get('CHROME_PATH', "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
        logger.debug(f"Chrome路径: {chrome_path}")
        
        browser_instance = await launch(
            executablePath=chrome_path,
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
        logger.debug("浏览器实例启动成功")
        
    return browser_instance

async def search_zhihu(query: str):
    logger.debug(f"开始知乎搜索，关键词: {query}")
    try:
        browser = await get_browser()
        page = await browser.newPage()
        
        # 设置浏览器特征
        logger.debug("设置浏览器特征")
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        await page.setViewport({'width': 1920, 'height': 1080})
        
        # 注入反检测代码
        logger.debug("注入反检测代码")
        await page.evaluateOnNewDocument('''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        ''')
        
        # 读取并设置cookies
        logger.debug("设置cookies")
        if os.environ.get('ZHIHU_COOKIE'):
            cookies = []
            cookie_str = os.environ['ZHIHU_COOKIE']
            logger.debug(f"Cookie字符串长度: {len(cookie_str)}")
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
            logger.debug(f"成功解析 {len(cookies)} 个cookies")
            await page.setCookie(*cookies)
        else:
            logger.warning("未找到ZHIHU_COOKIE环境变量")
        
        # 存储API响应数据
        api_data = None
        api_response_received = asyncio.Event()
        
        async def intercept_response(response):
            nonlocal api_data
            url = response.url()
            if 'api/v4/search_v3?' in url:
                logger.debug(f"捕获到API响应: {url}")
                try:
                    data = await response.json()
                    logger.debug(f"API响应数据: {json.dumps(data, ensure_ascii=False)}")
                    if 'error' not in data:
                        api_data = data
                        api_response_received.set()
                except Exception as e:
                    logger.error(f"解析API响应时出错: {e}")
        
        page.on('response', lambda res: asyncio.ensure_future(intercept_response(res)))
        
        # 访问搜索页面
        search_url = f'https://www.zhihu.com/search?type=content&q={query}'
        logger.debug(f"访问搜索页面: {search_url}")
        await page.goto(search_url, {
            'waitUntil': 'networkidle0',
            'timeout': 30000
        })
        
        # 等待API响应
        try:
            logger.debug("等待API响应...")
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
            
            logger.debug(f"成功获取 {len(results)} 条搜索结果")
            return results
        
        logger.warning("API数据中没有搜索结果")
        return []
        
    except Exception as e:
        logger.error(f"搜索过程中出错: {e}")
        raise e
    
    finally:
        if page:
            await page.close()
            logger.debug("已关闭页面")

async def handler_async(event, context):
    logger.debug(f"收到请求: {json.dumps(event)}")
    # 设置响应头
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    # 处理预检请求
    if event['httpMethod'] == 'OPTIONS':
        logger.debug("处理OPTIONS预检请求")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # 获取查询参数
    params = event.get('queryStringParameters', {})
    query = params.get('q', '')
    logger.debug(f"搜索关键词: {query}")
    
    if not query:
        logger.warning("未提供搜索关键词")
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
        logger.debug(f"搜索完成，返回 {len(results)} 条结果")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'status': 'success',
                'data': results,
                'total': len(results),
                'query': query,
                'engine': 'zhihu'
            }, ensure_ascii=False)
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
    logger.debug("函数入口点被调用")
    return asyncio.get_event_loop().run_until_complete(handler_async(event, context)) 