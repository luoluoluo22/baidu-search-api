const { spawn } = require('child_process')
const path = require('path')

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
    // 运行Python脚本
    const pythonProcess = spawn('python', [
      path.join(__dirname, 'search.py'),
      keyword,
      page,
    ])

    return new Promise((resolve, reject) => {
      let result = ''
      let error = ''

      pythonProcess.stdout.on('data', (data) => {
        result += data.toString()
      })

      pythonProcess.stderr.on('data', (data) => {
        error += data.toString()
      })

      pythonProcess.on('close', (code) => {
        if (code !== 0) {
          resolve({
            statusCode: 500,
            headers,
            body: JSON.stringify({
              status: 'error',
              message: `Python脚本执行失败: ${error}`,
            }),
          })
        } else {
          resolve({
            statusCode: 200,
            headers,
            body: result,
          })
        }
      })

      pythonProcess.on('error', (err) => {
        resolve({
          statusCode: 500,
          headers,
          body: JSON.stringify({
            status: 'error',
            message: `启动Python脚本失败: ${err.message}`,
          }),
        })
      })
    })
  } catch (error) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        status: 'error',
        message: error.message,
      }),
    }
  }
}
