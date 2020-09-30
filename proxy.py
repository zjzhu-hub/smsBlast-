import settings
import time
from parsel import Selector
import pymysql
import json
import asyncio
import aiohttp


class Proxy:
    def __init__(self):
        self.clientIp = ''
        self.ipList = []
        self.tasks = []
        self.session = None

    def get_tasks(self):
        return self.tasks

    async def close_session(self):
        await self.session.close()

    async def get_client_ip(self):
        self.session = aiohttp.ClientSession()
        res = await self.session.get('http://httpbin.org/get')
        self.clientIp = json.loads(await res.text()).get('origin')

    async def get_ip(self):
        for item in settings.proxyApiList:
            for url in item.get('urls'):
                headers = settings.get_random_headers()
                res = await self.session.get(url, headers=headers, ssl=False)
                if res.status == 200:
                    dom = Selector(await res.text()).xpath(item.get('resolveRule'))
                    for key in dom:
                        self.tasks.append(asyncio.ensure_future(
                            self.check_ip(key.xpath(item.get('resolveDom').get('ip')).extract_first(),
                                          key.xpath(item.get('resolveDom').get('port')).extract_first(),
                                          key.xpath(item.get('resolveDom').get('protocol')).extract_first())))
                time.sleep(1)

    async def check_ip(self, ip, port, protocol):
        try:
            protocol = protocol.lower()
            if protocol.count('s') != 0:
                proxy = "https://" + ip + ":" + port + ""
            else:
                proxy = "http://" + ip + ":" + port + ""
            headers = settings.get_random_headers()
            res = await self.session.get('http://httpbin.org/get', headers=headers, proxy=proxy, timeout=5,
                                         ssl=False)  # 如需筛选更快的ip 可修改timeout参数 越小越快
            proxyIp = json.loads(await res.text()).get('origin')
            if res.status == 200 and proxyIp != self.clientIp:
                print('成功:' + proxy)
                self.ipList.append({"ip": ip, "port": port, "protocol": protocol})
        except Exception as e:
            pass

    def add(self):
        print('有效IP数量' + str(len(self.ipList)))
        conn = pymysql.connect(host='localhost', user='root', password='root', database='ip_pool', port=3306)
        cursor = conn.cursor()
        for item in self.ipList:
            cursor.execute("SELECT COUNT(0) FROM ip_pool WHERE ip=%s ", (item.get('ip')))
            if cursor.fetchone()[0] <= 0:
                sql = "INSERT INTO ip_pool(ip, port, protocol) values('" + item.get('ip') + "', '" + item.get(
                    'port') + "', '" + item.get('protocol') + "')"
            cursor.execute(sql)
        conn.commit()
        conn.close()


if __name__ == '__main__':
    proxy = Proxy()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(proxy.get_client_ip())
    loop.run_until_complete(proxy.get_ip())
    loop.run_until_complete(asyncio.wait(proxy.get_tasks()))
    loop.run_until_complete(proxy.close_session())
    proxy.add()
