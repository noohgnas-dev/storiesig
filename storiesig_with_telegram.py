#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys 
import random
import requests, urllib3, json
import os, re, argparse
from tqdm import tqdm
from sys import exit
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse
from urllib3.exceptions import InsecureRequestWarning
import time
import yaml
import logging
import asyncio
from telegram import Bot


CHAT_ID = 0  # TODO: input your chatting room id
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
USER_AGENT_HEADER = {'User-Agent': USER_AGENT}
BOT_TOKEN = ""
BOT_TOKEN_PATH = "./token.txt"
if os.path.exists(BOT_TOKEN_PATH):
    with open(BOT_TOKEN_PATH) as f:
        lines = f.readlines()
        BOT_TOKEN = lines[0].strip()


logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %I:%M:%S ',
    handlers=[logging.FileHandler("logging_file.log"), logging.StreamHandler(sys.stdout)]
)
logging.getLogger("requests").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("telegram").setLevel(logging.CRITICAL)


async def send_to_telegram_with_file(file_path, full_name):
    bot = Bot(BOT_TOKEN)
    caption_str = f"{full_name} {datetime.today().strftime('%Y/%m/%d %H:%M:%S')}"

    if ".jpg" in file_path or ".heic" in file_path:
        await bot.send_photo(
            CHAT_ID,
            photo=file_path,
            caption=caption_str
        )
    elif ".mp4" in file_path:
        await bot.send_video(
            CHAT_ID,
            video=file_path,
            caption=caption_str
        )
    logging.info(f"send to telegram channel: {file_path}")


async def send_to_telegram_with_msg(full_name, count):
    bot = Bot(BOT_TOKEN)
    msg_str = f"{full_name} has {count} files at {datetime.today().strftime('%Y/%m/%d %H:%M:%S')}"

    await bot.send_message(chat_id=CHAT_ID, text=msg_str)
    logging.info(f"send to telegram channel: text = {msg_str}")


class downloader(object):
    profile = {}
    def __init__(self, username, storiesFlag):
        global USER_AGENT_HEADER
        self.username = username
        self.storiesFlag = storiesFlag
        self.api = 'https://storiesig.info/api/ig'
        self.user = self.api + '/userInfoByUsername/' + self.username
        try:
            self.root = requests.get(self.user, headers=USER_AGENT_HEADER, verify=False, timeout=20).text
        except requests.exceptions.Timeout:
            logging.info(f"Timed out: {self.user}")
        # self.sdname = self.username + "_{}".format(datetime.now().strftime("%Y-%m-%d_%H%M%S"))
        self.sdname = "story/" + self.username
        logging.info(f"{self.username}")
        try:
            self.profile = json.loads(self.root)
        except:
            print(self.user)
            print(self.root)
            logging.info("json load error")
            return
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
        global USER_AGENT_HEADE
        try:
            r = requests.get(self.storiesLink, headers=USER_AGENT_HEADER, verify=False, timeout=20).text
        except requests.exceptions.Timeout:
            logging.info(f"Timed out: {self.storiesLink}")
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
        except:
            logging.info("json load error")
            return

        with open("storiex.json", "w") as f:
            f.write(r)

        date_str = lambda s: datetime.fromtimestamp(s).strftime('%Y-%m-%d_%H%M%S')
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
        try:
            file_count = 0
            for link in tqdm(links):
                parser = urlparse(link["url"])
                file_path = self.sdname + '/' + os.path.basename(parser.path)
                if not os.path.isfile(file_path):
                    # print(f"try to download: {file_path}")
                    r = requests.get(link["url"], headers=USER_AGENT_HEADER, verify=False, timeout=20)
                    with open(file_path, 'wb') as f:
                        f.write(r.content)
                        f.close()
                    asyncio.run(send_to_telegram_with_file(file_path, target_full_name))
                    file_count = file_count + 1
                else:
                    logging.info(f"already exist: {file_path}")
            asyncio.run(send_to_telegram_with_msg(target_full_name, file_count))

        except KeyboardInterrupt:
            exit()
        except requests.exceptions.Timeout:
            logging.info(f"Timed out download file")

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

    if args.list:
        with open(args.list, 'r') as f:
            users = yaml.load(f, Loader=yaml.FullLoader)

        for u in users["users"]:
            downloader(u, args.stories)
            wait_time = random.randrange(181, 241)
            logging.info(f"wait {wait_time/60:.1} min. to avoid ban")
            time.sleep(wait_time)
    else:
        downloader(args.user, args.stories)

def usage():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', nargs="?", help="Instagram username (required)", required=True)
    parser.add_argument('-s', '--stories', dest="stories", action="store_true", help="Only download last 24h stories")
    parser.add_argument('-l', '--list', nargs="?", help="Only download last 24h stories with list of file")
    return parser.parse_args()

if __name__ == '__main__':
    main()
