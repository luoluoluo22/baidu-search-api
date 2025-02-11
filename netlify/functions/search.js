import fetch from 'node-fetch'
import cheerio from 'cheerio'

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
    url: (query) => `https://www.zhihu.com/api/v4/search_v3?gk_version=gz-gaokao&t=general&q=${encodeURIComponent(query)}&correction=1&offset=0&limit=20&filter_fields=&lc_idx=0&show_all_topics=0&search_source=Normal`,
    isApi: true,
    resultSelector: 'data',
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
          if (obj.type === 'answer' || obj.type === 'article') {
            title = cleanHtml(obj.question?.name || obj.title || '');
            link = obj.url?.replace('api.zhihu.com/articles', 'zhuanlan.zhihu.com/p')
                          .replace('api.zhihu.com/answers', 'www.zhihu.com/answer');
            description = cleanHtml(obj.excerpt || obj.content || '');
            meta = {
              type: obj.type,
              voteup_count: obj.voteup_count,
              comment_count: obj.comment_count,
              author: obj.author?.name
            };
          } else if (obj.type === 'question') {
            title = cleanHtml(obj.title);
            link = `https://www.zhihu.com/question/${obj.id}`;
            description = cleanHtml(obj.excerpt || '');
            meta = {
              type: 'question',
              answer_count: obj.answer_count,
              follower_count: obj.follower_count
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
    },
    headers: {
      "accept": "application/json, text/plain, */*",
      "accept-encoding": "gzip, deflate, br",
      "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
      "content-type": "application/json",
      "cookie": process.env.ZHIHU_COOKIE||'',
      "origin": "https://www.zhihu.com",
      "referer": (query) => `https://www.zhihu.com/search?type=content&q=${encodeURIComponent(query)}`,
      "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Microsoft Edge";v="132"',
      "sec-ch-ua-mobile": "?0",
      "sec-ch-ua-platform": '"Windows"',
      "sec-fetch-dest": "document",
      "sec-fetch-mode": "navigate",
      "sec-fetch-site": "same-origin",
      "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
      "x-zse-93":"101_3_3.0",
      "x-zse-96":"2.0_OcF2c4f+cD+zA9HWxvf=pDSb5AqR4KMeoLnxTYclT/0cI9TpZx/wi/g3KoidyTkk",
      "x-zst-81":"3_2.0VhnTj77m-qofgh3TxTnq2_Qq2LYuDhV80wSL7iUZQ6nxET20m4fBJCHMiqHPD4S1hCS974e1DrNPAQLYlUefii7q26fp2L2ZKgSfnveCgrNOQwXTt_Fq6DQye8t9DGwT9RFZQAuTLbHP2GomybO1VhRTQ6kp-XxmxgNK-GNTjTkxkhkKh0PhHix_F0PM69H82UFqhDwCe7xMCwo82wgMgbOftBFKST3_WgNBc9OffheBeAOLlGcBFH_z6RC_JUpGsDXqnvu1ABHKfCtLXDCmciC06MSX6QxmcB3LXG7B89FB_qVfgBVLVc3mjDSBQcPK7rxy6hXmPUFX2cfZqgcMoHXOxvwfHCF9Uw2YCUSLurOs"
    }
  },
}

// 搜索单个引擎
async function searchEngine(engine, query) {
  try {
    const headers = {
      ...engine.headers,
      'User-Agent': getRandomUserAgent(),
    }

    // 处理动态referer
    if (typeof headers.referer === 'function') {
      headers.referer = headers.referer(query)
    }

    console.log('Request URL:', engine.url(query));
    console.log('Request Headers:', headers);

    const response = await fetch(engine.url(query), { headers })

    if (!response.ok) {
      console.error(`Search engine error: HTTP ${response.status}`)
      console.error('Response Headers:', response.headers);
      const text = await response.text();
      console.error('Response Body:', text);
      return []
    }

    // 处理API响应
    if (engine.isApi) {
      const json = await response.json()
      return engine.transform(json[engine.resultSelector] || [])
    }

    // 处理HTML响应
    const html = await response.text()

    // 检查是否被重定向到验证页面
    if (
      html.includes('detected unusual traffic') ||
      html.includes('verify you are a human')
    ) {
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

    if (results.length === 0) {
      console.error(`No results found. HTML length: ${html.length}`)
    }

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
