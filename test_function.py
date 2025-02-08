import json
from netlify.functions.search import handler

def test_search():
    # 模拟Netlify函数的事件对象
    event = {
        'queryStringParameters': {
            'q': 'Python教程',
            'page': '1'
        }
    }
    
    # 模拟上下文对象
    context = {}
    
    print("正在测试搜索功能...")
    print(f"搜索关键词: {event['queryStringParameters']['q']}")
    
    # 调用处理函数
    response = handler(event, context)
    
    # 检查状态码
    print(f"\n状态码: {response['statusCode']}")
    
    # 解析响应体
    body = json.loads(response['body'])
    
    # 打印结果
    if body['status'] == 'success':
        print(f"\n找到 {body['data']['total_found']} 条结果")
        print("\n搜索结果:")
        for i, result in enumerate(body['data']['results'], 1):
            print(f"\n结果 {i}:")
            print(f"标题: {result['title']}")
            print(f"链接: {result['link']}")
            if result['description']:
                print(f"描述: {result['description'][:200]}...")
            if result['publish_time']:
                print(f"发布时间: {result['publish_time']}")
            print("-" * 50)
    else:
        print(f"\n搜索失败: {body['message']}")
    
    return response

if __name__ == "__main__":
    test_search()