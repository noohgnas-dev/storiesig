#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import sys 
import random
import requests, urllib3, json
import os, re, argparse
from tqdm import tqdm
from sys import exit
from bs4 import BeautifulSoup
import datetime
from urllib.parse import urlparse
from urllib3.exceptions import InsecureRequestWarning
import time
import yaml
import logging
import asyncio
from telegram import Bot

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
USER_AGENT_HEADER = {'User-Agent': USER_AGENT}

BOT_INFO_FILE = ""  # XXX: make info file
BOT_TOKEN = ""
CHAT_ID = 0

if os.path.exists(BOT_INFO_FILE):
    with open(BOT_INFO_FILE) as f:
        j = json.loads(f.read())
    BOT_TOKEN = j['token']
    CHAT_ID = j['chat_id']
else:
    print(f"configuration file is not exist: {BOT_INFO_FILE}")
    exit(1)

REQ_TIMEOUT = 30
CHROME_DRIVER = None

logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %I:%M:%S ',
    handlers=[logging.FileHandler("logging_file.log"), logging.StreamHandler(sys.stdout)]
)
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("telegram").setLevel(logging.CRITICAL)


def get_chrome_driver():
    os.environ["DISPLAY"] = ":10.0"
    chrome_service = Service(executable_path='/usr/bin/chromedriver')
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    chrome_options.add_argument("window-size=400,400")
    chrome_options.add_experimental_option("excludeSwitches", ['enable-automation'])

    return webdriver.Chrome(service=chrome_service, options=chrome_options)


async def send_to_telegram_with_file(file_path, full_name):
    bot = Bot(BOT_TOKEN)
    caption_str = f"{full_name} {datetime.datetime.today().strftime('%Y/%m/%d %H:%M:%S')}"

    if ".jpg" in file_path or ".heic" in file_path:
        await bot.send_photo(
            CHAT_ID,
            photo=file_path,
            read_timeout=20,
            write_timeout=20,
            connect_timeout=20,
            pool_timeout=5,
            caption=caption_str
        )
    elif ".mp4" in file_path:
        await bot.send_video(
            CHAT_ID,
            video=file_path,
            read_timeout=20,
            write_timeout=20,
            connect_timeout=20,
            pool_timeout=5,
            caption=caption_str
        )
    logging.info(f"send to telegram channel: {file_path}")


async def send_to_telegram_with_msg(msg, count):
    bot = Bot(BOT_TOKEN)
    # msg_str = f"{full_name} has {count} files at {datetime.datetime.today().strftime('%Y/%m/%d %H:%M:%S')}"
    msg_str = msg

    await bot.send_message(chat_id=CHAT_ID, text=msg_str)
    logging.info(f"send to telegram channel: text = {msg_str}")


async def send_to_telegram_with_markdown_msg(msg):
    bot = Bot(BOT_TOKEN)

    await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='MarkdownV2')
    logging.info(f"send to telegram channel: text = {msg}")


class downloader(object):
    profile = {}
    file_count = 0

    def __init__(self, username, storiesFlag):
        global USER_AGENT_HEADER, CHROME_DRIVER

        if not CHROME_DRIVER:
            CHROME_DRIVER = get_chrome_driver()

        self.username = username
        self.storiesFlag = storiesFlag
        self.api = 'https://storiesig.info/api/ig'
        self.user = self.api + '/userInfoByUsername/' + self.username
        try:
            CHROME_DRIVER.implicitly_wait(5)
            CHROME_DRIVER.get(self.user)
            self.root = CHROME_DRIVER.switch_to.active_element.text
        except requests.exceptions.Timeout:
            logging.info(f"Timed out: {self.user}")
        # self.sdname = self.username + "_{}".format(datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S"))
        self.sdname = "story/" + self.username
        try:
            self.profile = json.loads(self.root)
        except Exception as e:
            print(e)
            print(self.user)
            print(self.root)
            logging.info(f"json load error: {self.user}")
            tmp_msg = self.username + " may change to other id. Please look for in Instagram."
            asyncio.run(send_to_telegram_with_msg(tmp_msg, 0))
            self.profile = None
            return
        full_name = self.profile['result']['user']['full_name'] if len(self.profile['result']['user']['full_name']) > 0 else f"{self.username}(empty)"
        # logging.info(f"id: {self.username} - {self.profile['result']['user']['full_name']}")
        logging.info(f"id: {self.username} - {full_name}")
        self.storiesLink = self.api + '/stories/' + self.profile["result"]["user"]["pk"]

        if self.exists():
            if not self.storiesFlag:
                hld = self.getHighlights()
                if hld:
                    self.validate()
                    self.t = len(hld)
                    self.c = 1
                    for key, value in hld.items():
                        self.downloadHighlight(key, value)
                        self.c += 1
                else:
                    logging.info("[*] User '{}' does not appear to have any highlights!".format(self.username))
            else:
                self.validate()
                self.getStories()

    def getStories(self):
        global USER_AGENT_HEADER, REQ_TIMEOUT, CHROME_DRIVER
        try:
            CHROME_DRIVER.implicitly_wait(5)
            CHROME_DRIVER.get(self.storiesLink)
            r = CHROME_DRIVER.switch_to.active_element.text
        except requests.exceptions.Timeout:
            logging.info(f"Timed out: {self.storiesLink}")
        except Exception as e:
            print(e)
            return

        if 'No stories to show' in r:
            logging.info("[*] User '{}' did not post any recent story/stories!".format(self.username))
            os.rmdir(self.sdname)
            return

        links = []
        try:
            soup = BeautifulSoup(r, features="lxml")
            stories_dict = json.loads(r)
            if len(stories_dict["result"]) < 1:
                logging.info("getStories is null")
                return
        except Exception as e:
            print(e)
            return

        with open("storiex.json", "w") as f:
            f.write(r)

        date_str = lambda s: datetime.datetime.fromtimestamp(s).strftime('%Y-%m-%d_%H%M%S')
        if len(stories_dict["result"][0]):
            for k in stories_dict["result"]:
                # print(k)
                if "video_versions" in k:
                    links.append({"url": k["video_versions"][0]["url"],
                                  "format": "mp4",
                                  "expires": date_str(k["video_versions"][0]["url_signature"]["expires"])})
                if "image_versions2" in k:
                    links.append(
                        {"url": k["image_versions2"]["candidates"][0]["url"],
                         "format": "jpg",
                         "expires": date_str(k["image_versions2"]["candidates"][0]["url_signature"]["expires"])})

        target_full_name = self.profile["result"]["user"]["full_name"]
        logging.info(f'[*] Downloading last 24h stories of {target_full_name}')
        self.file_count = 0
        try:
            for link in tqdm(links):
                parser = urlparse(link["url"])
                file_path = self.sdname + '/' + os.path.basename(parser.path)
                if not os.path.isfile(file_path):
                    # print(f"try to download: {file_path}")
                    r = requests.get(link["url"], headers=USER_AGENT_HEADER, verify=False, timeout=REQ_TIMEOUT)
                    with open(file_path, 'wb') as f:
                        f.write(r.content)
                        f.close()
                    asyncio.run(send_to_telegram_with_file(file_path, target_full_name))
                    self.file_count = self.file_count + 1
                else:
                    logging.info(f"already exist: {file_path}")

        except KeyboardInterrupt:
            CHROME_DRIVER.close()
            exit()
        except requests.exceptions.Timeout:
            logging.info(f"Timed out download file")
        except Exception as e:
            print(e)
            return

    def getHighlights(self):
            hlarray = []
            hlnarray = []
            hnarray = []
            hdirname = []
            soup = BeautifulSoup(self.root, features="lxml")

            hlinks =  soup.findAll('a', attrs={'href': re.compile("^/highlights/")})
            for highlight in hlinks:
                url = highlight.get('href')
                parser = urlparse(url)
                hname = os.path.basename(parser.path)
                hlnarray.append(hname)
                hlarray.append(self.api + url)

            hnames = soup.findAll("img", {"class": "jsx-2521016335"})
            for i in hnames:
                dname = i['alt']
                hnarray.append(dname)

            for i, j in zip(hnarray, hlnarray):
                hdirname.append(i + '_' + j)

            dictionary = dict(zip(hlarray, hdirname))
            return dictionary

    def exists(self):
        if "Sorry, this username isn't available." in self.root:
            logging.info("[*] User '{}' does not exist!".format(self.username))
            return False
        elif "This Account is Private" in self.root:
            logging.info("[*] Account '{}' is private!".format(self.username))
            return False
        else:
            return True

    def downloadHighlight(self, key, value):
        global USER_AGENT_HEADER
        html = requests.get(key, verify=False).text
        od = self.username + '/' + value
        os.mkdir(od)
        soup = BeautifulSoup(html, features="lxml")

        links =  soup.findAll('a', attrs={'href': re.compile("^https://scontent")})
        
        logging.info('[*] Downloading highlight {} of {}...'.format(self.c,self.t))
        try:
            for link in tqdm(links):
                url = link.get('href')
                r = requests.get(url, headers=USER_AGENT_HEADER, verify=False)
                parser = urlparse(url)
                filename = os.path.basename(parser.path)

                with open(od + '/' + filename, 'wb') as f:
                    f.write(r.content)
                    f.close()
        except KeyboardInterrupt:
            CHROME_DRIVER.close()
            exit()

    def validate(self):
        if not self.storiesFlag:
            if os.path.isdir(self.username):
                logging.info("[*] Highlights for user '{}' are already downloaded!".format(self.username))
                return
            else:
                os.mkdir(self.username)
        else:
            if not os.path.isdir(self.sdname):
                os.makedirs(self.sdname, exist_ok=True)

def main():
    urllib3.disable_warnings(InsecureRequestWarning)
    args = usage()
    download_task = None
    targets = []
    send_msg = ""
    total_wait_time = 0
    total_file_count = 0

    if args.list:
        with open(args.list, 'r') as f:
            users = yaml.load(f, Loader=yaml.FullLoader)

        for u in users["users"]:
            download_task = downloader(u, args.stories)
            wait_time = random.randrange(5, 21)
            total_wait_time = total_wait_time + wait_time
            logging.info(f"wait {wait_time/60:0.1f} min. to avoid ban")
            time.sleep(wait_time)
            if download_task.profile:
                targets.append({"id": u, "fullname": download_task.profile['result']['user']['full_name'], "file_count": download_task.file_count})

        for target in targets:
            total_file_count = total_file_count + target["file_count"]
            text_template = f"""
||{target["fullname"]}||: {target["file_count"]}"""
            send_msg = send_msg + text_template
        now = datetime.datetime.now()
        time_difference = datetime.timedelta(seconds=total_wait_time)
        new_time = now - time_difference
        send_msg = f"Collected at {new_time.strftime('%Y/%m/%d %H:%M:%S')}" + send_msg
        if total_file_count == 0:
            send_msg = f"Nothing at {new_time.strftime('%Y/%m/%d %H:%M:%S')}"
        logging.info(send_msg)
        asyncio.run(send_to_telegram_with_markdown_msg((send_msg)))
    else:
        downloader(args.user, args.stories)

    if CHROME_DRIVER:
        print("close chrome")
        CHROME_DRIVER.close()

def usage():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', nargs="?", help="Instagram username (required)", required=True)
    parser.add_argument('-s', '--stories', dest="stories", action="store_true", help="Only download last 24h stories")
    parser.add_argument('-l', '--list', nargs="?", help="Only download last 24h stories with list of file")
    return parser.parse_args()

if __name__ == '__main__':
    main()
