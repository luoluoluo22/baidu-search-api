import { handler } from './netlify/functions/search.js';

// 设置环境变量
process.env.ZHIHU_COOKIE = "_xsrf=uZ15KPSZPWWTdCnEuXixHaYmkvgARlFg; _zap=a20b0eb5-b916-447f-8a81-044ef4adaf9e; d_c0=AADSRU-DiRmPTgWG6PwxO0X1zWFcfNoDZfU=|1731505066; q_c1=dd628d1c9d934bc9b62fed808d493f1c|1739172066000|1739172066000; tst=r; z_c0=2|1:0|10:1739172070|4:z_c0|80:MS4xV1VwdEJnQUFBQUFtQUFBQVlBSlZUZWIybG1qd29zdWNSUHQ1OS13X2EtR2pUUDM0RE05WFFnPT0=|c7b896db62ac5763e9ebaeba3c1d621943b46e2053d4493937070d3950ed99a9; __zse_ck=004_mZKPo6v3w6cnbeDWA/qHlGxklB0EOXyywhZCl21m17LmCvik6lK4Fz/uaZBP4rfszdgraR6RQ8L0ME/X4LeX6OpimCiEdh2N5Yd=2fVCHbxUOg6KRrZrxB/XS8p68szA-HaO9T/zgd4lHLdSRDqgbCvpKb83d60ipbzeb/HYuKbxdXafVDK0sAlzR7lSny8DojdeezwPi+SXi+T7kTcp4uTVUSJH7BhJAOm47/ODHy/Rxw4eqsi8RKeqG2SrpdA9ZTjUZvg1K/dcsFKy3z36wVPo1eS0rQPvdWoYDaGWyQMk=; BEC=e9bdbc10d489caddf435785a710b7029; Hm_lvt_98beee57fd2ef70ccdd5ca52b9740c49=1738918722,1739033289,1739172069,1739264362; Hm_lpvt_98beee57fd2ef70ccdd5ca52b9740c49=1739264362; HMACCOUNT=F9E1C1F954F61F3F";

async function testZhihuSearch() {
  console.log('开始测试知乎搜索...\n');

  // 测试用例
  const testCases = [
    {
      name: '知乎搜索测试',
      event: {
        httpMethod: 'GET',
        queryStringParameters: {
          q: 'python',
          engines: 'zhihu'
        }
      }
    }
  ];

  for (const test of testCases) {
    console.log(`==================================================`);
    console.log(`测试用例: ${test.name}`);
    console.log(`查询参数:`, test.event.queryStringParameters);
    console.log();

    try {
      const response = await handler(test.event);
      const data = JSON.parse(response.body);

      if (data.status === 'success') {
        console.log('✅ 搜索成功');
        console.log(`找到结果数: ${data.data.total_found}`);
        console.log(`使用的搜索引擎: ${data.data.engines.join(', ')}`);
        console.log('\n前3个结果:\n');

        data.data.results.slice(0, 3).forEach((result, index) => {
          console.log(`${index + 1}. ${result.title}`);
          console.log(`   链接: ${result.link}`);
          console.log(`   描述: ${result.description}`);
          if (result.meta) {
            console.log(`   元信息: ${result.meta}`);
          }
          console.log(`   来源: ${result.source}\n`);
        });
      } else {
        console.log('❌ 搜索失败');
        console.log(`错误信息: ${data.message}`);
      }

      console.log('\n调试信息:');
      console.log('状态码:', response.statusCode);
      console.log('Headers:', response.headers);
    } catch (error) {
      console.error('❌ 测试出错:', error);
    }
  }
}

testZhihuSearch(); 