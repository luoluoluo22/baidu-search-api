import requests
import logging
import json
from urllib.parse import urlencode
import time
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('baidu_search.log'),
        logging.StreamHandler()
    ]
)

class BaiduSearchClient:
    """
    百度搜索客户端
    模拟浏览器行为发送搜索请求并记录网络交互日志
    
    关键特征：
    1. 使用session维护cookies状态
    2. 模拟真实浏览器请求头
    3. 支持URL参数自动编码
    4. 详细的请求响应日志记录
    """
    
    def __init__(self):
        self.session = requests.Session()
        # 百度搜索的基础URL
        self.base_url = 'https://www.baidu.com/s'
        
        # 模拟Chrome浏览器的请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',  # 支持压缩
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        }
        self.session.headers.update(self.headers)

    def _log_request(self, response, keyword):
        """
        记录请求和响应的详细信息
        
        记录内容包括：
        - 完整的请求URL和方法
        - 请求头信息（包括User-Agent和Cookie）
        - 响应状态码和头信息
        - 响应cookies
        """
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'request': {
                'url': response.request.url,
                'method': response.request.method,
                'headers': dict(response.request.headers),
                'keyword': keyword
            },
            'response': {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'encoding': response.encoding,
                'cookies': dict(response.cookies)
            }
        }
        logging.info(f"Search Request Details: {json.dumps(log_data, indent=2, ensure_ascii=False)}")

    def search(self, keyword, page=1):
        """
        执行百度搜索并记录日志
        
        参数说明：
        - wd: 搜索关键词
        - pn: 页码偏移量，每页偏移10个结果
        - rn: 每页返回的结果数量
        - ie: 输入编码方式
        """
        # 计算分页偏移量
        offset = (page - 1) * 10
        
        params = {
            'wd': keyword,     # 搜索关键词
            'pn': str(offset), # 分页偏移量
            'rn': '10',        # 每页结果数
            'ie': 'utf-8'      # 输入编码
        }

        logging.info(f"开始搜索关键词: {keyword}")
        
        try:
            # 首先访问百度首页获取初始化cookie
            # 这一步很重要，因为百度会设置一些必要的cookies
            self.session.get('https://www.baidu.com')
            
            # 执行搜索请求
            response = self.session.get(
                self.base_url,
                params=params,
                allow_redirects=True  # 允许重定向
            )
            
            # 记录请求日志
            self._log_request(response, keyword)
            
            if response.status_code == 200:
                logging.info(f"搜索成功, 响应长度: {len(response.text)} bytes")
                return response
            else:
                logging.error(f"搜索失败, 状态码: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"请求发生错误: {str(e)}")
            return None

def main():
    """
    主函数：测试不同关键词的搜索效果并记录结果
    """
    # 创建搜索客户端实例
    client = BaiduSearchClient()
    
    # 测试搜索并展示结果
    keywords = ['Python编程', '网络爬虫', 'API测试']
    
    for keyword in keywords:
        logging.info(f"\n{'='*50}\n开始测试关键词: {keyword}\n{'='*50}")
        
        # 执行搜索
        response = client.search(keyword)
        
        if response:
            # 保存响应内容到文件（用于分析）
            filename = f"search_result_{int(time.time())}_{keyword}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            logging.info(f"搜索结果已保存到文件: {filename}")
            
            # 分析响应内容
            content_length = len(response.text)
            encoding = response.encoding
            content_type = response.headers.get('Content-Type', '')
            
            logging.info(f"""
响应分析:
- 内容长度: {content_length} bytes
- 编码方式: {encoding}
- 内容类型: {content_type}
""")
        
        # 请求间隔2秒，避免触发反爬机制
        time.sleep(2)

if __name__ == "__main__":
    main()