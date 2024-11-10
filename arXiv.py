import os
import sys
import logging
import csv
import time
import random
import requests
import re
import html
from datetime import datetime
from urllib import parse
from bs4 import BeautifulSoup

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,  # 设置记录的最低级别
    format='%(asctime)s - %(levelname)s - %(message)s',  # 设置日志格式
    handlers=[
        logging.FileHandler("arXiv.log", mode='a', encoding='utf-8'),  # 记录到文件
        logging.StreamHandler(sys.stdout)  # 同时输出到控制台
    ]
)

# 定义 Google 翻译 URL 和头信息
GOOGLE_TRANSLATE_URL = 'http://translate.google.com/m?q=%s&tl=%s&sl=%s'

# 定义用户代理列表
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; AS; rv:11.0) like Gecko",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.101 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.57",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 OPR/73.0.3856.284"
]

# 随机选择一个用户代理
headers = {
    "User-Agent": random.choice(user_agents)
}

# 设置要爬取的 arXiv 分类
categories = ["cs.AI", "cs.CV", "cs.DS", "cs.LG", "cs.OS", "cs.SE"]

# 获取当前日期
current_date = datetime.now()
# 获取日期并去掉前导零
day = current_date.day  # day 方法会返回不带前导零的日期
formatted_date = current_date.strftime(f"%a, {day} %b %Y")
# 格式化为 2024-11-07 的格式
today_date = current_date.strftime('%Y-%m-%d')


# 翻译函数
# def translate(text, to_language, text_language):
#     text = parse.quote(text)
#     url = GOOGLE_TRANSLATE_URL % (text, to_language, text_language)
#     response = requests.get(url)
#     data = response.text
#     expr = r'(?s)class="(?:t0|result-container)">(.*?)<'
#     result = re.findall(expr, data)
#     return html.unescape(result[0]) if result else ""

def translate(text, to_language, text_language):
    text = parse.quote(text)
    url = GOOGLE_TRANSLATE_URL % (text, to_language, text_language)
    retries = 5  # 尝试 3 次
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                data = response.text
                expr = r'(?s)class="(?:t0|result-container)">(.*?)<'
                result = re.findall(expr, data)
                return html.unescape(result[0])
            else:
                logging.info(f"请求失败，状态码: {response.status_code}")
        except requests.Timeout:
            logging.info("请求超时，重试中...")
        except requests.ConnectionError as e:
            logging.info(f"连接错误: {e}")
            logging.info("重试中...")
        if i < retries - 1:
            time.sleep(random.uniform(1, 3))  # 随机延迟
        elif i == retries - 1:
            time.sleep(10)  # 延迟10s
    return ""


# 获取网页内容
def fetch_content(category, max_entries=500):
    url = f"https://arxiv.org/list/{category}/recent?skip=0&show={max_entries}"
    response = requests.get(url, headers=headers)
    return BeautifulSoup(response.text, 'html.parser')


# 解析 HTML 内容，提取文章链接、PDF链接和标题
def parse_articles(soup):
    articles_dl = soup.find('dl', id='articles')
    entries = []

    if articles_dl:
        h3_tags = articles_dl.find_all('h3')  # 找到该 <dl> 内部所有的 <h3> 标签
        for i, h3 in enumerate(h3_tags, start=1):
            # 使用正则表达式提取日期部分
            match = re.match(r"(\w{3}, \d{1,2} \w{3} \d{4})", h3.get_text(strip=True))
            page_date = match.group(1)
            if match:
                logging.info(f"文章日期: {page_date}")
            logging.info(f"当前日期: {formatted_date}")
            if page_date != formatted_date:
                logging.info("当前日期与文章日期不匹配,退出程序。")
                break
            else:
                logging.info("当前日期与文章日期匹配，继续执行程序。")
                dt_tags = articles_dl.find_all('dt')
                dd_tags = articles_dl.find_all('dd')

                # 如果有<dt>和<dd>标签，则提取链接和标题
                if len(dt_tags) != 0:
                    for dt, dd in zip(dt_tags, dd_tags):
                        entry = {}
                        arxiv_link_tag = dt.find('a', href=True, title="Abstract")
                        pdf_link_tag = dt.find('a', href=True, title="Download PDF")
                        title_div = dd.find('div', class_='list-title')

                        # 提取链接和标题
                        entry['arxiv_link'] = 'https://arxiv.org' + arxiv_link_tag['href'] if arxiv_link_tag else ""
                        entry['pdf_link'] = 'https://arxiv.org' + pdf_link_tag['href'] if pdf_link_tag else ""
                        if title_div:
                            title_text = title_div.get_text(strip=True).replace("Title:", "").strip()
                            entry['title'] = title_text
                            entry['translated_title'] = translate(title_text, "zh-CN", "en")
                            time.sleep(random.uniform(1, 2))
                        entries.append(entry)
                else:
                    logging.info("当前日期没有找到任何文章。")
    return entries


# 将结果保存到 CSV 文件
def save_to_csv(entries, filename):
    with open(filename, mode="w", encoding="utf-8", newline="") as csv_file:
        fieldnames = ['arxiv_link', 'pdf_link', 'title', 'translated_title']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(entries)
    logging.info(f"数据已成功存储到 {filename} 文件中。")


# 主函数，遍历所有类别并存储结果
def main():
    # 检查本地是否有当前日期的文件
    for category in categories:
        if os.path.exists(f"{category}_articles_{today_date}.csv"):
            logging.info(f"文件 {category}_articles_{today_date}.csv 已经存在，继续下一个分类。")
            pass
        else:
            logging.info(f"文件 {category}_articles_{today_date}.csv 不存在，继续执行程序。")
            logging.info(f"正在处理分类: {category}")
            soup = fetch_content(category)
            entries = parse_articles(soup)
            # 判断是否有数据
            if entries and len(entries) > 0:
                save_to_csv(entries, f"{category}_articles_{today_date}.csv")
                # 休眠 20 秒
                time.sleep(random.uniform(20, 30))
            else:
                logging.info(f"分类 {category} 没有找到任何文章。")


# 执行爬虫主程序
if __name__ == "__main__":
    main()
