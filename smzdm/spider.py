# coding:utf-8
import requests
import time
import json
from email.header import Header
from email.mime.text import MIMEText
import smtplib
import hashlib
import sched
import os
import configparser

from smzdm.sqllite_util import ConnectSqlite


class SmzdmSpider():

    def __init__(self):
        # 用os模块来读取
        cur_path = os.path.dirname(os.path.realpath(__file__))
        conf_path = os.path.join(cur_path, "config.ini")  # 读取到本机的配置文件
        db_path = os.path.join(cur_path, "data.db")

        self.con = ConnectSqlite(db_path)
        self.create_table()

        self.readConfig(conf_path)

    def create_table(self):
        sql = '''CREATE TABLE IF NOT EXISTS `smzdm_record`(
                  `title` varchar(1000) DEFAULT NULL,
                  `comments_count` varchar(1000) DEFAULT NULL,
                  `content` varchar(1000) DEFAULT NULL,
                  `price` varchar(1000) DEFAULT NULL,
                  `link` varchar(1000) DEFAULT NULL,
                  `page_url` varchar(1000) DEFAULT NULL,
                  `pic_url` varchar(1000) DEFAULT NULL,
                  `md5` varchar(255) NOT NULL,
                  PRIMARY KEY (`md5`)
                )'''
        result = self.con.create_tabel(sql)
        print('建表成功', str(result))

    # 读取配置文件
    def readConfig(self, path):

        # 调用读取配置模块中的类
        conf = configparser.ConfigParser()
        conf.read(path, encoding="utf-8-sig")

        # smtp_server
        self.smtp_server_host = conf.get("smtp_server", "smtp_server_host")
        self.smtp_server_port = int(conf.get("smtp_server", "smtp_server_port"))
        self.mail_username = conf.get("smtp_server", "smtp_server_username")
        self.mail_password = conf.get("smtp_server", "smtp_server_password")
        self.smtp_server_ssl = int(conf.get("smtp_server", "smtp_server_ssl"))

        # email_receiver
        self.target_mail_address = conf.get("email_receiver", "email_receiver")

        # watch_keys 商品关键词
        self.watch_keys = conf.get("watch_keys", "watch_keys").split(sep=',')

        # product_comments_count 商品评论数
        self.comments_count = int(conf.get("product_comments_count", "product_comments_count"))

        # watch_page_range 搜索范围
        self.watch_page_range = int(conf.get("watch_page_range", "watch_page_range"))

        # is_output_log
        self.is_output_log = int(conf.get("is_output_log", "is_output_log"))

        # interval_sec
        self.interval_sec = int(conf.get("interval", "interval_sec"))

    # 从网络获取数据
    def get_smzdm_data(self, page):
        print('get_smzdm_data 从网络获取数据')
        c_time = int(time.time())
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Host': 'www.smzdm.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
        }
        # 获取第一页
        url = 'https://www.smzdm.com/homepage/json_more?timesort=' + str(c_time) + '&p=' + str(page)
        # 精选
        #url = 'https://www.smzdm.com/jingxuan/json_more?timesort=' + str(c_time) + '&p=' + str(page)

        r = requests.get(url=url, headers=headers)

        # data = r.text.encode('utf-8').decode('unicode_escape')
        data = r.text
        # 获取json信息
        json_data = json.loads(data)
        # 获取商品信息 core_data
        # 01 = {dict: 56} {'article_type': '好价', 'article_id': '20103848', 'article_title': '有品米粉节：VIOMI 云米 1A 互联网燃气热水器 13L', 'article_price': '698元包邮', 'yh_type': 'youhui', 'buy_button_name': '去购买', 'article_content_all': '<strong>多重安全模式，APP链接手机，±1摄氏度控温。</strong><p>云米互联网热水器具有13L流量，可实现±1摄氏度的控温，可在进水温度、水流量、压力几个方面监控用水情况。通过搭载的数码恒温技术，让温度维持在更舒适的水平。内置记忆合金调水阀，在冬季水口收缩，加快加热速度。夏天加大开口，提高水流量。另一方面，燃气阀门也可根据水量自动调节进气量，让燃气和水达到最佳比例。</p><p>机身搭载旁通管解决了在使用热水时，关闭<a href="http://www.smzdm.com/fenlei/longtou/" target="_blank">水龙头</a>再开会出现突然烫手的情况，能够将水温控制在±3.5摄氏度以内。采用分段式燃烧，根据水温需求自动切换燃烧档位，让燃气使用效率更高，更节能。内置双速风机，根据进气量调节风扇转速，让燃气充分燃烧，发挥更多热能。采用无氧铜水箱，导热速度更快，也不易被氧化。<br/></p><p>可通过APP链接手机，在手机端掌握运行状态，实时水温。并且能切换“宝宝洗”“老人洗”“舒适洗”等多重供水模式。在冬天低于5摄氏度时，会启动防冻模式，开启电热系统，防止热水器被冻坏。支持过热保护、断流保护、熄火保护、开机自检等多重安全模式。在开机
        # 02 = {dict: 56} {'article_type': '好价', 'article_id': '20102319', 'article_title': 'PHILIPS 飞利浦 ACA308 AirMax净速型 车载空气净化器', 'article_price': '579元包邮', 'yh_type': 'youhui', 'buy_button_name': '去购买', 'article_content_all': '<strong>有效过滤甲醛甲苯</strong><p>飞利浦ACA308车载净化器能够有效去除车内PM2.5等有害颗粒污染物，尤其是刚购置的新车，还能去除甲苯甲醛等气态污染物，包括空气中的粉尘，花粉以及车内异味，可谓是车内空气净化小能手。吸烟人士也不例外，30分钟内去除75%尼古丁，这也是降低了他人吸入二手烟。全新超宽绑带和新一代吸盘，多种安装方法，非常方便。</p><a id="link_1585793978726" href="https://go.smzdm.com/b7ee6a5b30fe4886/ca_aa_yh_147_20102319_11256_273_149_0" target="_blank" syncyh="false" syncact="false" rel="nofollow"  onclick="gtmAddToCart({\'name\':\'PHILIPS 飞利浦 ACA308 AirMax净速型 车载空气净化器\',\'id\':\'20102319\' , \'price\':\'579\',\'brand\':\'PHILIPS/飞利浦\' ,\'mall\':\'京东\', \'category\':\'汽车消费/车载电器/车载空气净化器/无\',\'metric1\':\'579\',\'dimension10\':\'jd.com\',\'dimension9\':\'youhui\',\'dimension11\':\'6阶价格\',\'dimension12\':\'京东
        core_data = json_data['data']
        # core_data = json_data['article_list']

        resultList = []

        for item in core_data:
            if item.__contains__('type'):
                if item['type'] == 'ad':
                    continue
            comments_count = item['article_comment']
            title = item['article_title']
            content = ''
            if 'article_content_all' in item.keys():
                content = item['article_content_all']
            price = ''
            if 'article_price' in item.keys():
                price = item['article_price']
            link = ''
            if 'article_link' in item.keys():
                link = item['article_link']
            page_url = item['article_url']
            pic_url = ''
            if 'article_pic' in item.keys():
                pic_url = item['article_pic']
            result = {
                'title': title,
                'comments_count': comments_count,
                'content': content,
                'price': price,
                'link': link,
                'page_url': page_url,
                'pic_url': pic_url
            }
            resultList.append(result)
        return resultList

    # 发送邮件
    def send_mail(self, data, key, title):
        username = self.mail_username
        password = self.mail_password
        to_addr = self.target_mail_address.split(',')
        msg = MIMEText(data, "html", 'utf-8')
        msg['From'] = 'SMZDM最新优惠'
        msg['To'] = 'Target'
        msg['Subject'] = Header(title, 'utf-8').encode()
        server = None;
        # 判断是否ssl
        if self.smtp_server_ssl == 1:
            server = smtplib.SMTP_SSL(self.smtp_server_host, self.smtp_server_port)
        else:
            server = smtplib.SMTP(self.smtp_server_host, self.smtp_server_port)
            server.set_debuglevel(1)
            # server.starttls()
        server.login(username, password)
        server.sendmail(username, to_addr, msg.as_string())
        server.quit()

    # md5
    @staticmethod
    def md5(str):
        print(str)
        m = hashlib.md5()
        m.update(str.encode(encoding='utf-8'))
        return m.hexdigest()

    # 此数据是否已经在数据库中存在过
    def is_data_exist(self, result):
        # tempResult = sorted(result.items(), key=lambda result: result[0])
        # 根据page_url的md5,判断是否在数据库中
        sql = 'SELECT * FROM smzdm_record where md5 = "%s"' % self.md5(result['page_url'])
        print(sql)
        cursor = self.con.execute_sql(sql)
        if len(cursor.fetchall()) > 0:
            print('商品已经存在')
            return True
        else:
            print('商品不存在')
            return False

    # 插入数据
    def insert_data(self, result):
        # tempResult = sorted(result.items(), key=lambda result: result[0])
        sql = """INSERT INTO smzdm_record(title,comments_count,content,price,link,page_url,pic_url,md5) VALUES (?,?, ?, ?, ?, ?, ?, ?)"""
        value = [(result['title'],result['comments_count'], result['content'], result['price'], result['link'], result['page_url'],
                  result['pic_url'], self.md5(result['page_url']))]
        print(self.md5(result['page_url']))
        self.con.insert_table_many(sql, value)

    # 启动一次查询全过程
    def search(self):
        print('启动搜索')
        for page in range(1, self.watch_page_range, 10):
            # 每页查询间隔
            time.sleep(60)
            resultList = self.get_smzdm_data(page)
            for result in resultList:
                # 输出到data.txt
                if int(self.is_output_log) == 1:
                    with open('data.txt', 'a', encoding='utf-8') as f:
                        f.write('page' + str(page) + str(result['title']) + '\n')
                for key in self.watch_keys:
                    # 关键字匹配
                    if result['title'].find(key) != -1:
                        # 评论数大于阈值
                        if int(result['comments_count']) >= self.comments_count:
                            print('发现新商品-----', str(result))
                            if not self.is_data_exist(result):
                                print('发现新商品数据库存在 插入----', str(result))
                                htmldata = "<div>{title}</div><div>{comments_count}</div><div style='margin-top:10px'>{content}</div><div style='margin-top:10px'>{price}</div><div style='margin-top:10px'><a href='{url}'>{url}</a></div><div style='margin-top:10px'><img src='{pic_url}'/></div>".format(
                                    title=result['title'], comments_count=result['comments_count'], content=result['content'], price=result['price'],
                                    url=result['page_url'], pic_url=result['pic_url'])
                                # self.send_mail(htmldata, key, result['title'])
                                self.insert_data(result)


# 定时执行器
class ScheduleManager:
    def __init__(self, callback, interval_sec):
        self.schedule = sched.scheduler(time.time, time.sleep)
        self.callback = callback
        self.interval_sec = interval_sec

    def func(self):
        self.callback()
        self.schedule.enter(self.interval_sec, 0, self.func, ())

    def start(self):
        self.schedule.enter(0, 0, self.func, ())
        self.schedule.run()


if __name__ == '__main__':
    spider = SmzdmSpider()
    manager = ScheduleManager(spider.search, spider.interval_sec)
    manager.start()
