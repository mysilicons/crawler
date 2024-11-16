import os
import datetime
import requests
from bs4 import BeautifulSoup
import PyPDF2
import time
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


# 创建一个带重试机制的请求
def get_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("http://", HTTPAdapter(max_retries=retries))
    return session


# 生成日期范围列表
def generate_date_range(start_date, end_date):
    try:
        start = datetime.datetime.strptime(start_date, "%Y%m%d")
        end = datetime.datetime.strptime(end_date, "%Y%m%d")
        return [start + datetime.timedelta(days=i) for i in range((end - start).days + 1)]
    except ValueError:
        logging.error("日期格式错误，请使用YYYYMMDD格式")
        exit()


# 获取网页HTML
def get_html(date):
    session = get_session()
    url = f"http://paper.people.com.cn/rmrb/html/{date[:4]}-{date[4:6]}/{date[6:]}/nbs.D110000renmrb_01.htm"
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return response.text, url
    except requests.RequestException as e:
        logging.error(f"获取HTML网页异常: {e}")
        exit()


# 解析页面获取PDF链接
def parse_page(html, flag):
    try:
        soup = BeautifulSoup(html, "html.parser")
        if flag == 0:
            right_pdf = soup.find_all(class_="right_title-pdf")
            suburl = right_pdf[0].a.attrs['href'][9:]
        elif flag == 1:
            right_pdf = soup.find_all(class_="right btn")
            suburl = right_pdf[0].a.attrs['href'][9:]

        pdf_url = f"http://paper.people.com.cn/rmrb/{suburl}"
        pdf_num = len(soup.find_all(class_="swiper-slide")) if flag == 1 else len(right_pdf)
        return pdf_url, pdf_num
    except Exception as e:
        logging.error(f"解析页面异常: {e}")
        exit()


# 保存PDF到本地
def save_pdf(pdf_url, pdf_num, date):
    folder = os.path.join("PDF_Download", date)
    os.makedirs(folder, exist_ok=True)

    session = get_session()
    for i in range(1, pdf_num + 1):
        pdf_url_page = f"{pdf_url[:-21]}{i:02d}{pdf_url[-19:-6]}{i:02d}{pdf_url[-4:]}"
        logging.info(f"下载 PDF: {pdf_url_page}")

        try:
            response = session.get(pdf_url_page)
            response.raise_for_status()
            with open(os.path.join(folder, f"{date}_{i:02d}.pdf"), 'wb') as f:
                f.write(response.content)
            logging.info(f"PDF {i} 下载成功")
        except requests.RequestException as e:
            logging.error(f"下载 PDF {i} 失败: {e}")
            continue


# 合并下载的PDF文件
def merge_pdfs(date):
    folder = os.path.join("PDF_Download", date)
    file_list = sorted(os.listdir(folder))  # 按文件名排序，确保按顺序合并

    pdf_merger = PyPDF2.PdfMerger(strict=False)
    for file in file_list:
        file_path = os.path.join(folder, file)
        pdf_merger.append(file_path)

    output_pdf = f"人民日报{date}.pdf"
    with open(output_pdf, 'wb') as output_file:
        pdf_merger.write(output_file)
    logging.info(f"合并 PDF 成功，保存为 {output_pdf}")


# 删除下载的PDF文件
def delete_pdfs(date):
    folder = os.path.join("PDF_Download", date)
    for file in os.listdir(folder):
        file_path = os.path.join(folder, file)
        os.remove(file_path)
    os.rmdir(folder)


# 主程序
def main():
    print("{:^40}".format("人民日报PDF下载工具"))
    print("{:=^40}".format(""))
    print("{:<40}".format("支持2020年7月1日起新版，并兼容旧版"))
    print("{:<40}".format("开发日期：2021.06.14"))
    print("{:<40}".format("版本：v2.0"))
    print("{:=^40}".format(""))

    choice = input("[1] 批量下载\n[2] 当日下载\n请输入选项: ")

    if choice == '1':
        try:
            start_date = input("请输入开始时间，如“20210101”：")
            end_date = input("请输入结束时间，如“20210701”：")
            time_list = generate_date_range(start_date, end_date)
        except Exception as e:
            logging.error(f"日期输入异常: {e}")
            return

        for date in time_list:
            date_str = date.strftime("%Y%m%d")
            logging.info(f"开始下载日期: {date_str}")
            html, url = get_html(date_str)
            flag = 0 if date < datetime.datetime(2020, 7, 1) else 1
            pdf_url, pdf_num = parse_page(html, flag)
            save_pdf(pdf_url, pdf_num, date_str)
            merge_pdfs(date_str)
            delete_pdfs(date_str)

    elif choice == '2':
        date_str = time.strftime('%Y%m%d', time.localtime())
        logging.info(f"开始下载今日 PDF: {date_str}")
        html, url = get_html(date_str)
        flag = 1
        pdf_url, pdf_num = parse_page(html, flag)
        save_pdf(pdf_url, pdf_num, date_str)
        merge_pdfs(date_str)

    else:
        logging.error("无效选项，请选择[1] 或 [2]")


if __name__ == "__main__":
    main()
