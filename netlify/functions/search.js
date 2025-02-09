import fetch from 'node-fetch';
import cheerio from 'cheerio';

// 随机User-Agent
const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
];

// 获取随机User-Agent
const getRandomUserAgent = () => {
  return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
};

// 搜索引擎配置
const SEARCH_ENGINES = {
  bing: {
    url: (query) => `https://www.bing.com/search?q=${encodeURIComponent(query)}&setlang=zh-CN`,
    resultSelector: '#b_results .b_algo',
    transform: ($, element) => {
      const $element = $(element);
      const $title = $element.find('h2 a');
      const $desc = $element.find('.b_caption p');
      
      return {
        title: $title.text().trim(),
        link: $title.attr('href'),
        description: $desc.text().trim(),
        source: 'bing'
      };
    },
    headers: {
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache',
      'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
      'Sec-Ch-Ua-Mobile': '?0',
      'Sec-Ch-Ua-Platform': '"Windows"',
      'Sec-Fetch-Dest': 'document',
      'Sec-Fetch-Mode': 'navigate',
      'Sec-Fetch-Site': 'none',
      'Sec-Fetch-User': '?1',
      'Upgrade-Insecure-Requests': '1'
    }
  },
  yahoo: {
    url: (query) => `https://search.yahoo.com/search?p=${encodeURIComponent(query)}&ei=UTF-8&fr=yfp-t&fp=1`,
    resultSelector: '#main .algo',
    transform: ($, element) => {
      const $element = $(element);
      const $title = $element.find('h3.title a');
      const $desc = $element.find('.compText p');
      
      return {
        title: $title.text().trim(),
        link: $title.attr('href'),
        description: $desc.text().trim(),
        source: 'yahoo'
      };
    },
    headers: {
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.5',
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache'
    }
  }
};

// 搜索单个引擎
async function searchEngine(engine, query) {
  try {
    const headers = {
      'User-Agent': getRandomUserAgent(),
      ...engine.headers
    };

    const response = await fetch(engine.url(query), { headers });

    if (!response.ok) {
      console.error(`Search engine error (${engine}): HTTP ${response.status}`);
      return [];
    }

    const html = await response.text();
    
    // 检查是否被重定向到验证页面
    if (html.includes('detected unusual traffic') || html.includes('verify you are a human')) {
      console.error(`Search engine (${engine}) requested verification`);
      return [];
    }

    const $ = cheerio.load(html);
    const results = [];

    $(engine.resultSelector).each((i, element) => {
      if (i < 20) { // 限制结果数量
        const result = engine.transform($, element);
        if (result.title && result.link) {
          results.push(result);
        }
      }
    });

    // 如果没有找到结果，记录HTML以便调试
    if (results.length === 0) {
      console.error(`No results found for ${engine}. HTML length: ${html.length}`);
    }

    return results;
  } catch (error) {
    console.error(`Search engine error (${engine}):`, error);
    return [];
  }
}

export const handler = async function (event, context) {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Content-Type': 'application/json; charset=utf-8'
  };

  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers,
      body: ''
    };
  }

  try {
    const query = event.queryStringParameters?.q;
    const selectedEngines = (event.queryStringParameters?.engines || 'bing,yahoo')
      .toLowerCase()
      .split(',')
      .filter(e => SEARCH_ENGINES[e]);

    if (!query) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({
          status: 'error',
          message: '请提供搜索关键词 (使用q参数)'
        })
      };
    }

    if (selectedEngines.length === 0) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({
          status: 'error',
          message: '请选择有效的搜索引擎 (bing 或 yahoo)'
        })
      };
    }

    // 并行执行所有搜索
    const searchPromises = selectedEngines.map(engineName => 
      searchEngine(SEARCH_ENGINES[engineName], query)
    );

    const results = await Promise.all(searchPromises);
    const allResults = results.flat();

    // 如果所有引擎都没有结果，返回错误
    if (allResults.length === 0) {
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          status: 'error',
          message: '未找到搜索结果，可能是搜索引擎限制访问，请稍后再试'
        })
      };
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
          total_found: allResults.length
        }
      })
    };

  } catch (error) {
    console.error('Search error:', error);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        status: 'error',
        message: '搜索服务出错'
      })
    };
  }
}; 