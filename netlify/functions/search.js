const { spawn } = require('child_process');

exports.handler = async function (event, context) {
  // 设置CORS头
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Content-Type': 'application/json; charset=utf-8',
  }

  // 处理OPTIONS请求
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers,
      body: '',
    }
  }

  return new Promise((resolve, reject) => {
    // 启动Python进程
    const pythonProcess = spawn('python', ['search.py'], {
      cwd: __dirname,
    });

    let result = '';
    let error = '';

    // 发送搜索参数到Python进程
    pythonProcess.stdin.write(JSON.stringify({
      queryStringParameters: event.queryStringParameters
    }));
    pythonProcess.stdin.end();

    // 收集Python输出
    pythonProcess.stdout.on('data', (data) => {
      result += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      error += data.toString();
    });

    // 处理进程结束
    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        console.error('Python process error:', error);
        resolve({
          statusCode: 500,
          headers,
          body: JSON.stringify({
            status: 'error',
            message: '搜索服务出错'
          })
        });
        return;
      }

      try {
        // 解析Python返回的JSON结果
        const response = JSON.parse(result);
        resolve({
          statusCode: response.statusCode || 200,
          headers,
          body: response.body || JSON.stringify(response)
        });
      } catch (e) {
        console.error('JSON parse error:', e);
        resolve({
          statusCode: 500,
          headers,
          body: JSON.stringify({
            status: 'error',
            message: '解析结果出错'
          })
        });
      }
    });

    // 处理错误
    pythonProcess.on('error', (err) => {
      console.error('Process error:', err);
      resolve({
        statusCode: 500,
        headers,
        body: JSON.stringify({
          status: 'error',
          message: '启动搜索服务失败'
        })
      });
    });
  });
} 