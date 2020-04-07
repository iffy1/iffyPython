# coding:utf-8
import re
import requests
import time
from email.header import Header
from email.mime.text import MIMEText
import smtplib
import hashlib
import sched
import os
import configparser

from lxml import etree

from smzdm.sqllite_util import ConnectSqlite
from smzdmC.items import SmzdmItem


class SmzdmSpider():

    def __init__(self):
        # 用os模块来读取 realname(__file__))获取的__file__所在脚本的路径
        cur_path = os.path.dirname(os.path.realpath(__file__))
        conf_path = os.path.join(cur_path, "config.ini")  # 读取到本机的配置文件
        db_path = os.path.join(cur_path, "data.db")

        # 初始化数据库
        self.con = ConnectSqlite(db_path)
        # 创建数据表
        self.create_table()
        # 读取配置文件
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
    def get_smzdm_data(self, page, keyword):
        print('get_smzdm_data 从网络获取数据 page:' + str(page) + '|keyword:' + keyword)
        # Dictionary键值对
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Host': 'search.smzdm.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
        }
        url = 'https://search.smzdm.com/'
        # c 发现频道 s关键字 p分页 order=time 时间排序 order=score综合排序
        # 'v': "b",不知道作用
        # Dictionary键值对
        data = {
            'c': "faxian",
            'order': "time",
            'v': "b",
            's': keyword,
            'p': page
        }
        r = requests.get(url=url, headers=headers, params=data, verify=True)

        # 查看编码方式
        # enconding = requests.utils.get_encodings_from_content(r.text)
        # print(enconding)

        html_doc = r.content.decode("utf-8")
        # print(html_doc[:500])
        # 保存网页
        # with open('test.html', 'w', encoding='utf-8') as f:
        #    f.write(html_doc)

        # Parses an HTML document from a string constant.  Returns the root nood
        tree = etree.HTML(html_doc)

        # 获取商品节点
        selector_feed_main_list = tree.xpath('// *[ @ id = "feed-main-list"]')[0]

        # 返回的结果
        result_list = []

        # 遍历商品
        for selector_item in selector_feed_main_list:
            # 过滤文章 价钱里没有‘元’字 说明不是商品
            try:
                price = selector_item.xpath('./div/div[2]/h5/a[2]/div')[0].text
            except IndexError as e:
                print('获取价格发生异常 跳过')
                continue
            # print(price)
            # 标价没有元 跳过
            if price.find('元') == -1:
                print('跳过')
                continue

            item = SmzdmItem()
            item['title'] = selector_item.xpath('./div/div[2]/h5/a[1]')[0].text.replace("  ", "")
            item['price'] = selector_item.xpath('./div/div[2]/h5/a[2]/div')[0].text
            # 没有拦截到的文章会出现在这里 描述有可能在[0]或者[1]里
            item['desc'] = ''
            try:
                item['desc'] = selector_item.xpath('./div/div[2]/div[1]/text()')[1].replace("  ", "")
            except IndexError as e:
                # print('发生异常A')
                try:
                    item['desc'] = selector_item.xpath('./div/div[2]/div[1]/text()')[0].replace("  ", "")
                except IndexError as e:
                    print('获取产品描述失败')

            item['zhi_yes'] = int(
                selector_item.xpath('./div/div[2]/div[2]/div[1]/span[1]/span[1]/span[1]/span')[0].text)
            item['zhi_no'] = int(
                selector_item.xpath('./div/div[2]/div[2]/div[1]/span[1]/span[2]/span[1]/span')[0].text)
            item['start'] = int(selector_item.xpath('./div/div[2]/div[2]/div[1]/span[2]/span')[0].text)
            comments_string = selector_item.xpath('./div/div[2]/div[2]/div[1]/a/@title')[0]
            # 字符串为评论数x,这里只取数字
            item['comment'] = int(re.findall(r"\d+\.?\d*", comments_string)[0])
            item['time'] = selector_item.xpath('./div/div[2]/div[2]/div[2]/span/text()')[0].replace("  ", "")
            item['channel'] = selector_item.xpath('./div/div[1]/span')[0].text
            item['detail_url'] = selector_item.xpath('./div/div[2]/h5/a[1]/@href')[0]
            item['out_url'] = selector_item.xpath('./div/div[2]/div[2]/div[2]/div/div/a/@href')[0]
            item['img'] = selector_item.xpath('./div/div[1]/a/img/@src')[0]
            # print(item)

            # 创建结果字典
            result = {
                'title': item['title'],
                'price': item['price'],
                'comments_count': item['comment'],
                'time': item['time'],
                'page_url': item['detail_url'],
                'content': item['desc'],
                'link': item['out_url'],
                'pic_url': item['img']
            }
            result_list.append(result)
        return result_list

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
        # print(str)
        m = hashlib.md5()
        m.update(str.encode(encoding='utf-8'))
        return m.hexdigest()

    # 此数据是否已经在数据库中存在过
    def is_data_exist(self, result):
        # tempResult = sorted(result.items(), key=lambda result: result[0])
        # 根据page_url的md5,判断是否在数据库中
        sql = 'SELECT * FROM smzdm_record where md5 = "%s"' % self.md5(result['page_url'])
        # print(sql)
        cursor = self.con.execute_sql(sql)
        if len(cursor.fetchall()) > 0:
            return True
        else:
            return False

    # 插入数据到db
    def insert_data(self, result):
        # tempResult = sorted(result.items(), key=lambda result: result[0])
        sql = """INSERT INTO smzdm_record(title,comments_count,content,price,link,page_url,pic_url,md5) VALUES (?,?, ?, ?, ?, ?, ?, ?)"""
        value = [(result['title'], result['comments_count'], result['content'], result['price'], result['link'],
                  result['page_url'],
                  result['pic_url'], self.md5(result['page_url']))]
        print(self.md5(result['page_url']))
        self.con.insert_table_many(sql, value)

    # 插入数据到txt文件
    def insert_data_to_data_txt(self, result):
        # 输出到data.txt
        if int(self.is_output_log) == 1:
            with open('data.txt', 'a', encoding='utf-8') as f:
                f.write(str(result['title']) + '---' + str(result['price']) + '|' + str(
                    result['page_url']) + '\n')

    # 启动一次查询全过程
    def search(self):
        print('启动搜索')
        # 遍历关键字表
        for key in self.watch_keys:
            # 搜索页数范围
            for page in range(1, self.watch_page_range):
                result_list = self.get_smzdm_data(page, key)
                # 遍历商品
                for result in result_list:
                    # 评论数大于阈值
                    if int(result['comments_count']) >= self.comments_count:
                        # print('发现新商品-----', str(result)) 数据库查重
                        if not self.is_data_exist(result):
                            print('发现新商品数据库存在 插入----', str(result))
                            htmldata = "<div>{title}</div><div>{comments_count}</div><div style='margin-top:10px'>{content}</div><div style='margin-top:10px'>{price}</div><div style='margin-top:10px'><a href='{url}'>{url}</a></div><div style='margin-top:10px'><img src='{pic_url}'/></div>".format(
                                title=result['title'], comments_count=result['comments_count'],
                                content=result['content'], price=result['price'],
                                url=result['page_url'], pic_url=result['pic_url'])
                            try:
                                self.send_mail(htmldata, key, result['title'] + result['price'])
                            except Exception as e:
                                print('发送邮件异常')
                            # 写入data base
                            self.insert_data(result)
                            # 写入data.txt
                            self.insert_data_to_data_txt(result)


# 定时执行器
class ScheduleManager:
    def __init__(self, callback, interval_sec):
        self.schedule = sched.scheduler(time.time, time.sleep)
        # callback = spider.search任务
        self.callback = callback
        self.interval_sec = interval_sec

    def func(self):
        self.callback()
        self.schedule.enter(self.interval_sec, 0, self.func, ())

    def start(self):
        # 马上执行
        # 第一个参数是一个整数或浮点数，代表多少秒后执行这个action任务
        # 第二个参数priority是优先级，0代表优先级最高，1次之，2次次之，当两个任务是预定在同一个时刻执行时，根据优先级决定谁先执行。
        # 第三个参数就是你要执行的任务，可以简单理解成你要执行任务的函数的函数名
        # 第四个参数是你要传入这个定时执行函数名函数的参数，最好用括号包起来，如果只传入一个
        self.schedule.enter(0, 0, self.func, ())
        self.schedule.run()


if __name__ == '__main__':
    spider = SmzdmSpider()
    manager = ScheduleManager(spider.search, spider.interval_sec)
    # 开始任务
    manager.start()
