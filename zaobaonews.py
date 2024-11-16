import base64
import os
import random
import shutil
import textwrap
import time

import requests
from bs4 import BeautifulSoup
from datetime import datetime


def fetch_latest_news(url, target_date):
    # 发送请求并获取网页内容
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'html.parser')

    # 查找所有符合条件的文章
    articles = soup.find_all('a', class_='col-lg-4 col-12 list-block no-gutters row')
    news_list = []

    for article in articles:
        # 提取标题、链接和日期
        link = 'https://www.zaobao.com' + article.get('href')
        title = article.find('div', class_='f18 m-eps').get_text(strip=True)
        date = article.find('div', class_='text-tip-color pdt10').get_text(strip=True)

        # 检查日期是否符合条件
        if date != target_date:
            continue

        # 获取并解码文章内容
        content = fetch_and_decode_article_content(link)
        if content:
            news_list.append({
                '标题': title,
                '链接': link,
                '日期': date,
                '内容': content
            })
        time.sleep(random.uniform(1, 3))
    return news_list


def fetch_and_decode_article_content(link):
    response = requests.get(link)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'html.parser')

    article = soup.find('article', id='article-body')
    if not article:
        return None

    # 解码并排序文章段落
    paragraphs = article.find_all('p')
    decoded_paragraphs = []

    for paragraph in paragraphs:
        data_s_value = paragraph.get('data-s')
        text_content = paragraph.get_text(strip=True)
        if data_s_value and text_content:
            try:
                decoded_value = int(base64.b32decode(data_s_value[3:]).decode('utf-8'))
                decoded_paragraphs.append((decoded_value, text_content))
            except Exception as e:
                print(f"解码失败: {e}")

    # 排序并返回文章内容
    sorted_content = "\n".join(text for _, text in sorted(decoded_paragraphs))
    return sorted_content


def wrap_text_to_terminal_width(text):
    # 获取当前终端宽度
    terminal_width = shutil.get_terminal_size().columns
    # 初始化 TextWrapper
    wrapper = textwrap.TextWrapper(width=terminal_width, break_long_words=True, break_on_hyphens=False)
    return wrapper.fill(text)


# 获取当前日期并调用主函数
today = datetime.now().strftime('%m-%d')
url = 'https://www.zaobao.com/news/china'
news_list = fetch_latest_news(url, today)

# 输出结果
for news in news_list:
    print(f"标题: {news['标题']}")
    print(f"链接: {news['链接']}")
    print(f"日期: {news['日期']}")
    print("内容:")

    # 使用 TextWrapper 控制每行宽度并避免提前换行
    wrapper = textwrap.TextWrapper(width=80)
    wrapped_content = wrapper.fill(news['内容'])
    print(wrapped_content)

    print("\n" + "=" * 150 + "\n")

os.system('pause')
