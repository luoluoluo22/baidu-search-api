from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import sys
import os
from urllib.parse import urlparse, parse_qs
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from netlify.functions.search import BaiduSearchClient
    logging.info("成功导入BaiduSearchClient")
except ImportError as e:
    logging.error(f"导入BaiduSearchClient失败: {e}")
    sys.exit(1)

PORT = 8000

class TestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        try:
            # 处理搜索API请求
            if self.path.startswith('/api/search'):
                self.handle_search_request()
                return
                
            # 处理静态文件请求
            if self.path == '/':
                self.path = '/public/index.html'
            return SimpleHTTPRequestHandler.do_GET(self)
            
        except Exception as e:
            logging.error(f"请求处理错误: {str(e)}")
            self.send_error_json(500, f"服务器错误: {str(e)}")

    def handle_search_request(self):
        """处理搜索请求"""
        try:
            # 解析查询参数
            query_components = urlparse(self.path).query
            params = parse_qs(query_components)
            
            # 获取搜索关键词和页码
            keyword = params.get('q', [''])[0]
            page = int(params.get('page', ['1'])[0])
            
            if not keyword:
                self.send_error_json(400, "缺少搜索关键词")
                return
                
            logging.info(f"开始搜索: 关键词='{keyword}', 页码={page}")
            
            # 创建搜索客户端并执行搜索
            client = BaiduSearchClient()
            result = client.search(keyword, page)
            
            # 发送搜索结果
            self.send_json_response(result)
            
        except ValueError as ve:
            self.send_error_json(400, f"参数错误: {str(ve)}")
        except Exception as e:
            logging.error(f"搜索处理错误: {str(e)}")
            self.send_error_json(500, f"搜索错误: {str(e)}")

    def send_json_response(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.wfile.write(response)

    def send_error_json(self, code, message):
        """发送错误响应"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        error_data = {
            'status': 'error',
            'message': message
        }
        self.wfile.write(json.dumps(error_data, ensure_ascii=False).encode('utf-8'))

def run_server():
    """运行测试服务器"""
    try:
        server = HTTPServer(('', PORT), TestHandler)
        print(f"启动测试服务器在 http://localhost:{PORT}")
        print(f"可以直接访问 http://localhost:{PORT} 开始测试搜索功能")
        print("按 Ctrl+C 停止服务器")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.server_close()
    except Exception as e:
        print(f"服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_server()