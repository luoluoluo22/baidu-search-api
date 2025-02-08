const fetch = require('node-fetch')

exports.handler = async function (event, context) {
  // 设置CORS头
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Content-Type': 'application/json',
  }

  // 处理OPTIONS请求
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers,
      body: '',
    }
  }

  // 获取查询参数
  const params = event.queryStringParameters
  const keyword = params.q
  const page = params.page || '1'

  if (!keyword) {
    return {
      statusCode: 400,
      headers,
      body: JSON.stringify({
        status: 'error',
        message: '请提供搜索关键词(q参数)',
      }),
    }
  }

  try {
    // 创建session
    const userAgent =
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    const requestHeaders = {
      'User-Agent': userAgent,
      Accept:
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
      'Accept-Encoding': 'gzip, deflate, br',
      Connection: 'keep-alive',
    }

    // 首先获取百度首页的cookies
    await fetch('https://www.baidu.com', {
      headers: requestHeaders,
    })

    // 执行搜索
    const searchParams = new URLSearchParams({
      wd: keyword,
      pn: ((parseInt(page) - 1) * 10).toString(),
      rn: '10',
      ie: 'utf-8',
    })

    const response = await fetch(
      `https://www.baidu.com/s?${searchParams.toString()}`,
      {
        headers: requestHeaders,
      }
    )

    const html = await response.text()

    // 使用正则表达式提取搜索结果
    const results = []
    const resultRegex =
      /<div[^>]*class="[^"]*result[^"]*"[^>]*>[\s\S]*?<h3[^>]*>[\s\S]*?<a[^>]*href="([^"]*)"[^>]*>([\s\S]*?)<\/a>[\s\S]*?(?:<div[^>]*class="[^"]*content-right[^"]*"[^>]*>([\s\S]*?)<\/div>|<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>([\s\S]*?)<\/div>)/g

    let match
    while ((match = resultRegex.exec(html)) !== null) {
      const link = match[1]
      const title = match[2].replace(/<[^>]+>/g, '').trim()
      const description = (match[3] || match[4] || '')
        .replace(/<[^>]+>/g, '')
        .trim()

      results.push({
        title,
        link,
        description,
      })
    }

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        status: 'success',
        data: {
          keyword,
          page: parseInt(page),
          total_found: results.length,
          results,
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
        message: `搜索失败: ${error.message}`,
      }),
    }
  }
}
