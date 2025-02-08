# 百度搜索 API

基于Selenium的百度搜索API实现，支持Netlify Serverless部署。

## 功能特点

- 使用Selenium实现可靠的搜索结果抓取
- 完整的搜索结果解析（标题、链接、描述、来源、发布时间）
- 提供结构化的JSON数据
- 现代化的前端界面，支持搜索结果和JSON数据双视图
- 完整的错误处理机制

## API使用说明

### 搜索接口

```
GET /api/search?q={keyword}&page={page}

参数：
- q: 搜索关键词（必需）
- page: 页码（可选，默认1）

返回格式：
{
  "status": "success",
  "data": {
    "keyword": "搜索关键词",
    "page": 1,
    "total_found": 10,
    "results": [
      {
        "title": "结果标题",
        "link": "目标链接",
        "description": "结果描述",
        "source": "来源网站",
        "publish_time": "发布时间"
      }
      // ... 更多结果
    ]
  }
}
```

## 本地开发

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 启动开发服务器：
```bash
python test_server.py
```

3. 访问测试页面：
```
http://localhost:8000
```

## Netlify部署

1. Fork本仓库
2. 在Netlify中创建新项目
3. 连接GitHub仓库
4. 部署完成后即可通过 `https://你的域名/api/search` 访问API

## 技术栈

- Backend:
  - Python
  - Selenium
  - BeautifulSoup4
  - Netlify Functions

- Frontend:
  - HTML5
  - CSS3
  - JavaScript

## 注意事项

- 需要在Netlify环境中安装Edge WebDriver
- API有请求频率限制，建议添加适当的延迟
- 建议在生产环境中添加缓存机制

## License

MIT