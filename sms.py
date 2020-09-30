import settings
import struct
import socket
import random
import time
import datetime
import pymysql
from random import choice
import aiohttp
import asyncio



class Sms:
    def __init__(self):
        self.tasks = []
        self.session = None
        self.proxyList = []

    def set_ProxyList(self, proxyList):
        self.proxyList = proxyList

    async def connect_session(self):
        self.session = aiohttp.ClientSession()

    async def close_session(self):
        await self.session.close()

    async def send(self, api):
        # 随机生成请求头
        headers = settings.get_random_headers()
        proxy = ''
        # 使用代理ip
        if self.proxyList:
            # 随机获取一个代理ip
            proxy = choice(self.proxyList)
            proxy = proxy[3] + '://' + proxy[1] + ':' + proxy[2]
        else:
            # 随机生成ip 伪造ip发送请求
            ip = socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))
            headers['CLIENT-IP'] = ip
            headers['X-FORWARDED-FOR'] = ip
        res = None
        try:
            if api.get('referer') != "":
                await self.session.get(api.get('referer'), timeout=20, headers=headers, proxy=proxy, ssl=False)
                headers['Referer'] = api.get('referer')
            if api.get('method') == "GET":
                res = await self.session.get(api.get('SMSApi'), params=api.get('params'), timeout=20, headers=headers,
                                             proxy=proxy, ssl=False)
            else:
                res = await self.session.post(api.get('SMSApi'), data=api.get('params'), timeout=20, headers=headers,
                                              proxy=proxy, ssl=False)
        except Exception as e:
            pass
        api['requestTime'] = time.time()
        if res:
            print("发送成功: %s ,返回码: %s" % (
                api.get('remark'), res.status) if res.status == 200 else "发送失败 %s ,返回码: %s:" % (
                api.get('remark'), res.status))
        else:
            print("发送失败: %s" % api.get('remark'))


if __name__ == '__main__':
    sms = Sms()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(sms.connect_session())
    # 使用代理ip
    if settings.proxy:
        conn = pymysql.connect(host='localhost', user='root', password='root', database='ip_pool', port=3306)
        cursor = conn.cursor()
        sql = "SELECT * FROM ip_pool LIMIT 200"
        cursor.execute(sql)
        sms.set_ProxyList(cursor.fetchall())
        conn.close()
    while True:
        tasks = []
        for item in settings.SMSApiList:
            if "requestTime" not in item:
                tasks.append(asyncio.ensure_future(sms.send(item)))
            else:
                if (datetime.datetime.fromtimestamp(time.time()) - datetime.datetime.fromtimestamp(
                        item.get('requestTime'))).seconds > item.get('interval'):
                    tasks.append(asyncio.ensure_future(sms.send(item)))
        if tasks:
            loop.run_until_complete(asyncio.wait(tasks))
