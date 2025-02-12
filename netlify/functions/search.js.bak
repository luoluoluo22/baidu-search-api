import fetch from 'node-fetch'
import cheerio from 'cheerio'
import puppeteer from 'puppeteer-core'

// 随机User-Agent
const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
]

// 获取随机User-Agent
const getRandomUserAgent = () => {
  return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)]
}

// 清理HTML标签的辅助函数
function cleanHtml(text) {
  if (!text) return '';
  // 移除所有HTML标签
  let clean = text.replace(/<[^>]+>/g, '');
  // 移除多余的空白字符
  clean = clean.replace(/\s+/g, ' ');
  // 移除特殊字符
  clean = clean.replace(/&nbsp;/g, ' ')
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
  return clean.trim();
}

// 搜索引擎配置
const SEARCH_ENGINES = {
  bing: {
    url: (query) =>
      `https://www.bing.com/search?q=${encodeURIComponent(
        query
      )}&setlang=zh-CN`,
    resultSelector: '#b_results .b_algo',
    transform: ($, element) => {
      const $element = $(element)
      const $title = $element.find('h2 a')
      const $desc = $element.find('.b_caption p')

      return {
        title: $title.text().trim(),
        link: $title.attr('href'),
        description: $desc.text().trim(),
        source: 'bing',
      }
    },
    headers: {
      Accept:
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
      'Cache-Control': 'no-cache',
      Pragma: 'no-cache',
      'Sec-Ch-Ua':
        '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
      'Sec-Ch-Ua-Mobile': '?0',
      'Sec-Ch-Ua-Platform': '"Windows"',
      'Sec-Fetch-Dest': 'document',
      'Sec-Fetch-Mode': 'navigate',
      'Sec-Fetch-Site': 'none',
      'Sec-Fetch-User': '?1',
      'Upgrade-Insecure-Requests': '1',
    },
  },
  yahoo: {
    url: (query) => `https://search.yahoo.com/search?p=${encodeURIComponent(query)}&ei=UTF-8&fr=yfp-t&fp=1`,
    resultSelector: '#main .algo',
    transform: ($, element) => {
      const $element = $(element)
      const $title = $element.find('h3.title a')
      const $desc = $element.find('.compText p')

      return {
        title: $title.text().trim(),
        link: $title.attr('href'),
        description: $desc.text().trim(),
        source: 'yahoo'
      }
    },
    headers: {
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.5',
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache'
    }
  },
  zhihu: {
    url: (query) => `https://www.zhihu.com/search?type=content&q=${encodeURIComponent(query)}`,
    isApi: true,
    resultSelector: 'data',
    usePuppeteer: true,
    transform: (data) => {
      // 直接返回原始数据，保持与Python版本一致
      return data;
    }
  },
}

// 搜索单个引擎
async function searchEngine(engine, query) {
  try {
    if (engine.usePuppeteer) {
      let browser = null;
      try {
        browser = await puppeteer.launch({
          executablePath: process.env.CHROME_PATH,
          headless: true,
          args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--window-size=1920,1080',
            '--start-maximized',
            '--disable-gpu',
            '--disable-dev-shm-usage'
          ],
          ignoreHTTPSErrors: true,
          userDataDir: './user_data'
        });

        const page = await browser.newPage();
        
        // 设置浏览器特征
        await page.setUserAgent(getRandomUserAgent());
        await page.setViewport({ width: 1920, height: 1080 });

        // 设置必要的请求头
        await page.setExtraHTTPHeaders({
          'x-api-version': '3.0.91',
          'x-app-version': '8.6.0',
          'x-zse-93': '101_3_3.0',
          'x-zse-96': '2.0_',
          'x-requested-with': 'fetch'
        });

        // 注入反检测代码
        await page.evaluateOnNewDocument(`
          Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
          });
          Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
          });
          // 注入用户状态
          window.g_user = {
            is_login: true
          };
        `);

        // 设置cookies
        if (process.env.ZHIHU_COOKIE) {
          // 检查是否包含关键cookie
          if (!process.env.ZHIHU_COOKIE.includes('z_c0=')) {
            throw new Error('缺少知乎认证cookie');
          }
          
          // 修改cookie解析逻辑
          const cookiePairs = process.env.ZHIHU_COOKIE.split(/;\s*(?=[^;]*=)/);
          const cookies = cookiePairs.map(pair => {
            const firstEqualIndex = pair.indexOf('=');
            const name = pair.slice(0, firstEqualIndex);
            const value = pair.slice(firstEqualIndex + 1);
            
            // 跳过无效的cookie
            if (!name || !value) {
              return null;
            }

            return {
              name,
              value,
              domain: '.zhihu.com',
              path: '/',
              secure: true,
              httpOnly: name === '_zap' || name === 'd_c0' || name === 'z_c0',
              expires: Date.now() + 86400000 * 30
            };
          }).filter(cookie => cookie !== null);
          
          // 先清除所有已存在的cookies
          const client = await page.target().createCDPSession();
          await client.send('Network.clearBrowserCookies');
          
          // 设置新的cookies
          await page.setCookie(...cookies);
          
          // 验证关键cookie是否存在
          const currentCookies = await page.cookies('https://www.zhihu.com');
          const hasZC0 = currentCookies.some(cookie => cookie.name === 'z_c0');
          if (!hasZC0) {
            throw new Error('知乎认证cookie设置失败');
          }
        } else {
          throw new Error('未找到知乎Cookie配置');
        }

        // 存储API响应数据
        let apiData = null;
        let apiResponseReceived = false;
        
        // 监听API响应
        page.on('response', async response => {
          const url = response.url();
          if (url.includes('api/v4/search_v3?')) {
            console.log('捕获到知乎API响应:', url);
            try {
              const data = await response.json();
              console.log('API响应数据:', JSON.stringify(data, null, 2));
              if (data && !data.error) {
                apiData = data;
                apiResponseReceived = true;
              } else {
                console.error('API返回错误:', data.error);
                // 尝试直接从页面提取数据
                const pageData = await page.evaluate(() => {
                  const items = Array.from(document.querySelectorAll('.SearchResult-Card'));
                  return items.map(item => {
                    return {
                      title: item.querySelector('.ContentItem-title')?.textContent?.trim() || '',
                      content: item.querySelector('.RichContent-inner')?.textContent?.trim() || '',
                      author: item.querySelector('.AuthorInfo-name')?.textContent?.trim() || '',
                      link: item.querySelector('a[data-za-detail-view-element_name="Title"]')?.href || ''
                    };
                  });
                });
                if (pageData && pageData.length > 0) {
                  apiData = { data: pageData };
                  apiResponseReceived = true;
                }
              }
            } catch (e) {
              console.error('获取响应内容出错:', e);
            }
          }
        });

        // 访问搜索页面
        console.log('开始访问知乎搜索页面...');
        try {
          // 直接访问搜索页面
          await page.goto(engine.url(query), {
            waitUntil: 'networkidle0',
            timeout: 30000
          });
          console.log('页面加载完成');
        } catch (navigationError) {
          console.error('页面导航错误:', navigationError);
          throw navigationError;
        }

        // 等待API响应或超时
        console.log('等待API响应...');
        let retryCount = 0;
        const maxRetries = 3;
        while (!apiResponseReceived && retryCount < maxRetries) {
          console.log(`第${retryCount + 1}次等待...`);
          await new Promise(resolve => setTimeout(resolve, 3000));
          retryCount++;
        }

        if (apiResponseReceived && apiData) {
          console.log('成功获取API数据');
          return engine.transform(apiData.data || []);
        }

        console.log('未能获取到任何搜索结果');
        return [];

      } catch (error) {
        console.error('Puppeteer错误:', error);
        return [];
      } finally {
        if (browser) {
          await browser.close();
        }
      }
    }

    // 原有的非Puppeteer处理逻辑
    const headers = {
      ...engine.headers,
      'User-Agent': getRandomUserAgent(),
    }

    if (typeof headers.referer === 'function') {
      headers.referer = headers.referer(query)
    }

    const response = await fetch(engine.url(query), { headers })

    if (!response.ok) {
      console.error(`Search engine error: HTTP ${response.status}`)
      return []
    }

    if (engine.isApi) {
      const json = await response.json()
      return engine.transform(json[engine.resultSelector] || [])
    }

    const html = await response.text()

    if (html.includes('detected unusual traffic') || html.includes('verify you are a human')) {
      console.error(`Search engine requested verification`)
      return []
    }

    const $ = cheerio.load(html)
    const results = []

    $(engine.resultSelector).each((i, element) => {
      if (i < 20) {
        const result = engine.transform($, element)
        if (result.title && result.link) {
          results.push(result)
        }
      }
    })

    return results
  } catch (error) {
    console.error(`Search engine error:`, error)
    return []
  }
}

export const handler = async function (event, context) {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Content-Type': 'application/json; charset=utf-8',
  }

  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers,
      body: '',
    }
  }

  try {
    const query = event.queryStringParameters?.q
    const selectedEngines = (
      event.queryStringParameters?.engines || 'bing,yahoo,zhihu'
    )
      .toLowerCase()
      .split(',')
      .filter((e) => SEARCH_ENGINES[e])

    if (!query) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({
          status: 'error',
          message: '请提供搜索关键词 (使用q参数)',
        }),
      }
    }

    if (selectedEngines.length === 0) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({
          status: 'error',
          message: '请选择有效的搜索引擎 (bing 、 yahoo 、 zhihu)',
        }),
      }
    }

    // 并行执行所有搜索
    const searchPromises = selectedEngines.map((engineName) =>
      searchEngine(SEARCH_ENGINES[engineName], query)
    )

    const results = await Promise.all(searchPromises)
    const allResults = results.flat()

    // 如果所有引擎都没有结果，返回错误
    if (allResults.length === 0) {
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          status: 'error',
          message: '未找到搜索结果，可能是搜索引擎限制访问，请稍后再试'+process.env.ZHIHU_COOKIE,
        }),
      }
    }

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        status: 'success',
        data: {
          keyword: query,
          engines: selectedEngines,
          results: allResults,
          total_found: allResults.length,
        },
      }),
    }
  } catch (error) {
    console.error('Search error:', error)
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        status: 'error',
        message: '搜索服务出错',
      }),
    }
  }
}
