import asyncio
import json
import random
import time
from pyppeteer import launch
from pyppeteer.errors import ElementHandleError, TimeoutError

async def main():
    browser = None
    try:
        # 启动浏览器，添加更多配置
        browser = await launch(
            executablePath="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
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
        
        page = await browser.newPage()
        
        # 设置更真实的浏览器特征
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        await page.setViewport({'width': 1920, 'height': 1080})
        
        # 注入用于绕过webdriver检测的JS
        await page.evaluateOnNewDocument('''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        ''')
        
        print("浏览器已启动")

        # 存储API响应数据
        api_data = None
        done = asyncio.Event()

        # 监听网络请求
        async def intercept_response(response):
            nonlocal api_data
            if 'api/v4/search_v3?' in response.url:
                try:
                    data = await response.json()
                    # print("\n成功获取到API数据")
                    # print("API数据内容：")
                    # print(json.dumps(data, ensure_ascii=False, indent=2))
                    # print(f"API URL: {response.url}")
                    if 'error' not in data:  # 只有在没有错误时才设置数据
                        api_data = data
                        done.set()  # 设置事件，表示已获取数据
                        return api_data
                except Exception as e:
                    print(f"解析API响应时出错: {e}")

        page.on('response', lambda res: asyncio.ensure_future(intercept_response(res)))

        # 读取cookies
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
                    print(f"解析cookie时出错: {cookie_part}, 错误: {e}")
        print(f"已读取 {len(cookies)} 个cookies")

        # 设置cookies并访问知乎
        await page.setCookie(*cookies)
        
        # 访问搜索页面
        print("正在访问搜索页面...")
        search_url = 'https://www.zhihu.com/search?type=content&q=java'
        await page.goto(search_url, {
            'waitUntil': 'networkidle0',
            'timeout': 30000
        })
        
        # 等待API数据或超时
        try:
            await asyncio.wait_for(done.wait(), timeout=10)  # 最多等待10秒
        except asyncio.TimeoutError:
            print("获取API数据超时")
        
        return api_data

    except Exception as e:
        print(f"发生错误: {e}")
        return None
        
    finally:
        if browser:
            try:
                await browser.close()
            except:
                pass

if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print("\n最终获取到的搜索结果：")
        print(json.dumps(result, ensure_ascii=False, indent=2))
