import sys
import json
import requests
from bs4 import BeautifulSoup

def clean_text(text):
    """清理文本内容"""
    if not text:
        return ""
    return ' '.join(text.split())

def search_baidu(keyword, page=1):
    """执行百度搜索"""
    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        session.headers.update(headers)
        
        # 访问首页获取cookie
        session.get('https://www.baidu.com')
        
        # 执行搜索
        params = {
            'wd': keyword,
            'pn': str((page - 1) * 10),
            'rn': '10',
            'ie': 'utf-8'
        }
        
        response = session.get('https://www.baidu.com/s', params=params)
        response.raise_for_status()
        
        # 解析结果
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # 查找搜索结果
        for container in soup.select('.result, .result-op, .c-container'):
            try:
                # 提取标题和链接
                h3 = container.select_one('h3')
                if not h3:
                    continue
                    
                a_tag = h3.select_one('a')
                if not a_tag:
                    continue
                
                title = clean_text(a_tag.get_text())
                link = a_tag.get('href', '')
                
                # 提取描述
                abstract = container.select_one('.content-right, .c-abstract')
                description = clean_text(abstract.get_text()) if abstract else ""
                
                # 提取来源
                source = container.select_one('.c-showurl, .source')
                source_text = clean_text(source.get_text()) if source else ""
                
                # 提取时间
                time_elem = container.select_one('.c-color-gray2')
                publish_time = clean_text(time_elem.get_text()) if time_elem else ""
                
                results.append({
                    'title': title,
                    'link': link,
                    'description': description,
                    'source': source_text,
                    'publish_time': publish_time
                })
                
            except Exception as e:
                continue
        
        return {
            'status': 'success',
            'data': {
                'keyword': keyword,
                'page': page,
                'total_found': len(results),
                'results': results
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

if __name__ == "__main__":
    # 从命令行参数获取搜索关键词和页码
    if len(sys.argv) < 2:
        result = {
            'status': 'error',
            'message': '请提供搜索关键词'
        }
    else:
        keyword = sys.argv[1]
        page = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        result = search_baidu(keyword, page)
    
    # 输出JSON结果
    print(json.dumps(result, ensure_ascii=False))