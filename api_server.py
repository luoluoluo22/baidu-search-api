from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from typing import Optional, List
from pydantic import BaseModel
import uvicorn
from pyppeteer import launch
import os
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('search_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="搜索聚合API",
    description="整合多个搜索引擎的搜索结果",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义响应模型
class SearchResult(BaseModel):
    title: str
    content: Optional[str] = None
    author: Optional[str] = None
    link: Optional[str] = None
    source: str = "zhihu"
    timestamp: str = None

class SearchResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[List[SearchResult]] = None
    total: Optional[int] = 0
    query: Optional[str] = None
    engine: Optional[str] = None

# 浏览器实例缓存
browser_instance = None
last_browser_launch_time = None
BROWSER_REFRESH_INTERVAL = 3600  # 每小时刷新浏览器实例

async def get_browser():
    global browser_instance, last_browser_launch_time
    current_time = datetime.now()
    
    # 检查是否需要刷新浏览器实例
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

async def search_zhihu(query: str) -> List[SearchResult]:
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
        if os.path.exists('cookies.txt'):
            cookies = []
            with open('cookies.txt', 'r', encoding='utf-8') as f:
                cookie_str = f.read().strip()
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
                        result = SearchResult(
                            title=obj.get('title', ''),
                            content=obj.get('excerpt', ''),
                            author=obj.get('author', {}).get('name', '') if obj.get('author') else '',
                            link=f"https://www.zhihu.com/question/{obj.get('question', {}).get('id', '')}/answer/{obj.get('id', '')}" if 'question' in obj else obj.get('url', ''),
                            timestamp=datetime.now().isoformat()
                        )
                        results.append(result)
                except Exception as e:
                    logger.error(f"处理搜索结果时出错: {e}")
                    continue
            
            return results
        
        return []
        
    except Exception as e:
        logger.error(f"搜索过程中出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if page:
            await page.close()

@app.get("/search", response_model=SearchResponse)
async def search(q: str, engine: str = "zhihu"):
    """
    搜索接口
    
    - **q**: 搜索关键词
    - **engine**: 搜索引擎 (目前支持: zhihu)
    """
    try:
        if not q:
            return SearchResponse(
                status="error",
                message="请提供搜索关键词"
            )
            
        if engine != "zhihu":
            return SearchResponse(
                status="error",
                message="目前只支持知乎搜索"
            )
            
        results = await search_zhihu(q)
        
        return SearchResponse(
            status="success",
            data=results,
            total=len(results),
            query=q,
            engine=engine
        )
        
    except Exception as e:
        logger.error(f"API错误: {e}")
        return SearchResponse(
            status="error",
            message=f"搜索失败: {str(e)}"
        )

@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭时清理资源"""
    global browser_instance
    if browser_instance:
        await browser_instance.close()
        browser_instance = None

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True) 