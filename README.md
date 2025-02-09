# 多引擎搜索 API

一个基于 Netlify Functions 的多搜索引擎聚合 API，支持 Bing 和 Yahoo 搜索。

## API 使用方法

### 接口地址
```
https://incredible-bonbon-8786a7.netlify.app/.netlify/functions/search
```

### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| q | string | 是 | 搜索关键词 | javascript教程 |
| engines | string | 否 | 搜索引擎，多个用逗号分隔，默认为 bing,yahoo | bing 或 yahoo 或 bing,yahoo |

### 示例请求

```bash
# 使用所有搜索引擎
curl "https://incredible-bonbon-8786a7.netlify.app/.netlify/functions/search?q=javascript教程"

# 仅使用 Bing
curl "https://incredible-bonbon-8786a7.netlify.app/.netlify/functions/search?q=javascript教程&engines=bing"
```

### 返回数据格式

```json
{
  "status": "success",
  "data": {
    "keyword": "javascript教程",
    "engines": ["bing", "yahoo"],
    "results": [
      {
        "title": "搜索结果标题",
        "link": "https://example.com",
        "description": "搜索结果描述",
        "source": "bing"
      }
    ],
    "total_found": 10
  }
}
```

### 错误响应

```json
{
  "status": "error",
  "message": "错误信息"
}
```

## 本地开发

1. 克隆仓库
```bash
git clone https://github.com/luoluoluo22/baidu-search-api.git
cd baidu-search-api
```

2. 安装依赖
```bash
yarn install
```

3. 启动开发服务器
```bash
yarn dev
```

## 部署

项目已配置好 Netlify 部署。只需将代码推送到 GitHub，Netlify 就会自动构建和部署。

## 技术栈

- Netlify Functions
- Node.js
- Cheerio (网页解析)
- Node-fetch (网络请求)

## 许可证

MIT