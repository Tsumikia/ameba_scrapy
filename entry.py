from datetime import datetime
from email.header import Header
import json
import requests
import urllib.request
from lxml import etree
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email import encoders
import re

url_head = 'https://ameblo.jp'
pattern = re.compile(r'https://ameblo\.jp/(\w+)-blog/entrylist\.html')
latest_url = None

class UserData:
    def __init__(self, email, data):
        self.email = email
        self.data = data

class DataItem:
    def __init__(self, url, cache):
        self.url = url
        self.cache = cache

def data_initialization():
    # 读取 JSON 数据文件
    file_path = "data.json"
    with open(file_path, "r") as file:
        json_data = json.load(file)

    # 创建对象数组
    user_data_objects = []
    for item in json_data:
        email = item["email"]
        data_list = [DataItem(data["url"], data["cache"]) for data in item["data"]]
        user_data_objects.append(UserData(email, data_list))

    return user_data_objects

def save_to_file(file_path, user_data_objects):
    # 将数据保存到文件
    with open(file_path, "w") as file:
        # 转换为字典列表再保存
        data_to_save = [{"email": user.email, "data": [{"url": item.url, "cache": item.cache} for item in user.data]}
                        for user in user_data_objects]
        json.dump(data_to_save, file, indent=4)

def get_response(url):
    return requests.get(url=url)

def get_last_title(url):
    response = get_response(url)
    tree = etree.HTML(response.content)

    title_list = tree.xpath("//ul[@class='skin-archiveList']/li//h2/a/text()")
    href_list = tree.xpath("//ul[@class='skin-archiveList']/li//h2/a/@href")

    return title_list[0]

def get_last_url(url):
    response = get_response(url)
    tree = etree.HTML(response.content)

    href_list = tree.xpath("//ul[@class='skin-archiveList']/li//h2/a/@href")

    return href_list[0]

def send_email(to_addr, blog_body, img_url, subject, blog_url):
    from_addr = 'your email address'
    password = 'your password'
    smtp_server = 'smtp.qq.com'

    server = smtplib.SMTP_SSL(smtp_server)
    server.connect(smtp_server, 465)

    server.login(from_addr, password)

    msg = MIMEMultipart()

    msg.attach(MIMEText(blog_body))
    msg.attach(MIMEText('\n今日博客url: ' + blog_url + '\n'))

    msg['From'] = Header('Natane <2229703286@qq.com>')
    msg['To'] = Header('Natane')
    msg['Subject'] = Header(subject)

    if img_url is not None:
        for img in img_url:
            flag = True
            # 获取图片数据
            try:
                image_data = requests.get(img, timeout=10).content
            except requests.exceptions.RequestException as e:
                print(f"Error fetching image: {e}")
                flag = False

            if flag:
                # 将图片附加到邮件
                image_part = MIMEImage(image_data, name='image.jpg')
                image_part.add_header('Content-ID', '<image1>')
                msg.attach(image_part)

    server.sendmail(from_addr=from_addr, to_addrs=to_addr, msg=msg.as_string())

    server.quit()

if __name__ == '__main__':
    print('start')

    user_data_list = data_initialization()

    for user in user_data_list:
        for data in user.data:
            url = data.url
            cache = data.cache
            blog_user_name = pattern.search(url).group(1)
            subject = blog_user_name + ' 发博客啦~'

            if cache is None:
                latest_url = url_head + get_last_url(url)
                tree = etree.HTML(get_response(latest_url).content)
                body_list = tree.xpath("//div[@id='entryBody']/text()")

                img_src_list_0 = tree.xpath("//img[@class='PhotoSwipeImage']/@src")

                img_src_list = [item for index, item in enumerate(img_src_list_0) if
                                item not in img_src_list_0[:index]]  # 去重

                if len(img_src_list) > 0:
                    body_list.append("\n本次博客图片url地址:")
                    for img_src in img_src_list:
                        body_list.append(img_src + '\n')
                else:
                    body_list.append("\n今天的博客没有图片~")

                body_list.append("\n注: 本脚本爬取时间与博客实际发布时间可能有差异哦~")

                print('start sending ' + blog_user_name + '\'s email to ' + user.email)
                send_email(user.email, '\n'.join(body_list), img_src_list[0] if len(img_src_list) > 0 else None, subject, latest_url)
                data.cache = latest_url

            else:
                latest_url = get_last_title(url)

                if latest_url != cache:  
                    latest_url = url_head + get_last_url(url)

                    tree = etree.HTML(get_response(latest_url).content)
                    body_list = tree.xpath("//div[@id='entryBody']/text()")

                    img_src_list_0 = tree.xpath("//img[@class='PhotoSwipeImage']/@src")

                    img_src_list = [item for index, item in enumerate(img_src_list_0) if item not in img_src_list_0[:index]]  # 去重

                    if len(img_src_list) > 0:
                        body_list.append("\n本次博客图片url地址:")
                        for img_src in img_src_list:
                            body_list.append(img_src + '\n')
                    else:
                        body_list.append("\n今天的博客没有图片~")

                    body_list.append("\n注: 本脚本爬取时间与博客实际发布时间可能有差异哦~")

                    data.cache = latest_url
                    print('start sending ' + blog_user_name + '\'s email to ' + user.email)
                    send_email(user.email, '\n'.join(body_list), img_src_list if len(img_src_list) > 0 else None, subject, latest_url)

                else:
                    print("pass")

    print('save to file...')
    save_to_file('./data.json', user_data_list)
    print('success.')
