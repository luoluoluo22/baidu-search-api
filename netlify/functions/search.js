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
      if (!data || !Array.isArray(data)) {
        console.error('Invalid Zhihu API response:', data);
        return [];
      }

      return data
        .filter(item => item.type === 'search_result' && item.object)
        .map(item => {
          const obj = item.object;
          let title = '';
          let link = '';
          let description = '';
          let meta = {};

          // 处理不同类型的内容
          if (obj.type === 'answer') {
            title = cleanHtml(obj.question?.name || '');
            link = `https://www.zhihu.com/answer/${obj.id}`;
            description = cleanHtml(obj.excerpt || obj.content || '');
            meta = {
              type: 'answer',
              voteup_count: obj.voteup_count,
              comment_count: obj.comment_count,
              author: obj.author?.name,
              created_time: obj.created_time,
              updated_time: obj.updated_time
            };
          } else if (obj.type === 'article') {
            title = cleanHtml(obj.title || '');
            link = `https://zhuanlan.zhihu.com/p/${obj.id}`;
            description = cleanHtml(obj.excerpt || obj.content || '');
            meta = {
              type: 'article',
              voteup_count: obj.voteup_count,
              comment_count: obj.comment_count,
              author: obj.author?.name,
              created_time: obj.created_time,
              updated_time: obj.updated_time
            };
          } else if (obj.type === 'question') {
            title = cleanHtml(obj.title);
            link = `https://www.zhihu.com/question/${obj.id}`;
            description = cleanHtml(obj.excerpt || '');
            meta = {
              type: 'question',
              answer_count: obj.answer_count,
              follower_count: obj.follower_count,
              created_time: obj.created_time,
              updated_time: obj.updated_time
            };
          }

          return {
            title: title || '无标题',
            link: link || '#',
            description: description.substring(0, 200) + (description.length > 200 ? '...' : ''),
            source: 'zhihu',
            meta
          };
        })
        .filter(item => item.title && item.link !== '#');
    }
  },
}

// 搜索单个引擎
async function searchEngine(engine, query) {
  try {
    // 使用Puppeteer的情况
    if (engine.usePuppeteer) {
      let browser = null;
      try {
        console.log('启动Chrome浏览器...');
        console.log('Chrome路径:', process.env.CHROME_PATH);
        
        // 启动浏览器
        browser = await puppeteer.launch({
          executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome',
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
          userDataDir: '/tmp/puppeteer_user_data'
        });

        console.log('浏览器启动成功');
        const page = await browser.newPage();
        console.log('新页面创建成功');

        // 设置浏览器特征
        await page.setUserAgent(getRandomUserAgent());
        await page.setViewport({ width: 1920, height: 1080 });

        // 注入反检测代码
        await page.evaluateOnNewDocument(`
          Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
          });
          Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
          });
        `);

        // 设置cookies
        if (process.env.ZHIHU_COOKIE) {
          console.log('开始设置知乎Cookie...');
          const cookies = process.env.ZHIHU_COOKIE.split('; ').map(cookie => {
            const [name, value] = cookie.split('=');
            return {
              name,
              value,
              domain: '.zhihu.com',
              path: '/'
            };
          });
          await page.setCookie(...cookies);
          console.log('Cookie设置完成');
        } else {
          console.log('警告: 未找到知乎Cookie配置');
        }

        // 存储API响应数据
        let apiData = null;
        const responsePromise = new Promise((resolve, reject) => {
          page.on('response', async response => {
            const url = response.url();
            if (url.includes('api/v4/search_v3?') && url.includes('search_source=Normal')) {
              try {
                const responseText = await response.text();
                console.log('API原始响应:', responseText);
                
                try {
                  const data = JSON.parse(responseText);
                  console.log('API响应数据:', JSON.stringify(data, null, 2));
                  if (data && data.data) {
                    apiData = data;
                    resolve(data);
                  } else {
                    console.log('API响应数据格式不正确');
                  }
                } catch (parseError) {
                  console.error('JSON解析错误:', parseError);
                }
              } catch (e) {
                console.error('获取响应内容出错:', e);
              }
            }
          });

          // 设置超时
          setTimeout(() => reject(new Error('API响应超时')), 30000);
        });

        // 访问搜索页面
        console.log('正在访问页面:', engine.url(query));
        await page.goto(engine.url(query), {
          waitUntil: 'networkidle0',
          timeout: 30000
        });

        // 等待页面加载完成后执行搜索操作
        await page.waitForSelector('.Search-container', { timeout: 10000 });
        console.log('页面加载完成');

        // 模拟搜索行为
        console.log('模拟搜索行为...');
        const searchInput = await page.$('.SearchBar-input input');
        await searchInput.click();
        await searchInput.type(query);
        await page.keyboard.press('Enter');
        console.log('搜索触发完成');

        // 等待搜索结果加载
        await page.waitForSelector('.SearchResult-Card', { timeout: 10000 });
        console.log('搜索结果已加载');

        // 等待API响应
        try {
          console.log('等待API响应...');
          const data = await responsePromise;
          console.log('成功获取API响应');
          return engine.transform(data.data || []);
        } catch (e) {
          console.error('获取搜索结果失败:', e);
          return [];
        }

      } catch (error) {
        console.error('Puppeteer错误:', error);
        return [];
      } finally {
        if (browser) {
          console.log('关闭浏览器');
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
