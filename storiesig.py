#!/usr/bin/python3
# -*- coding: utf-8 -*-
import requests, urllib3, json
import os, re, argparse
from tqdm import tqdm
from sys import exit
from html import unescape
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse
from urllib3.exceptions import InsecureRequestWarning

class downloader(object):
    def __init__(self, username, storiesFlag):
        self.username = username
        self.storiesFlag = storiesFlag
        self.api = 'https://storiesig.info/api/ig'
        self.user = self.api + '/userInfoByUsername/' + self.username
        self.root = requests.get(self.user, verify=False).text
        self.sdname = self.username + "_{}".format(datetime.now().strftime("%Y-%m-%d_%H%M%S"))
        profile = json.loads(self.root)
        self.storiesLink = self.api + '/stories/' + profile["result"]["user"]["pk"]

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
                    print("[*] User '{}' does not appear to have any highlights!".format(self.username))
            else:
                self.validate()
                self.getStories()

    def getStories(self):
        r = requests.get(self.storiesLink, verify=False).text
        if 'No stories to show' in r:
            print("[*] User '{}' did not post any recent story/stories!".format(self.username))
            os.rmdir(self.sdname)
            exit()

        links = []
        soup = BeautifulSoup(r, features="lxml")
        stories_dict = json.loads(r)
        if len(stories_dict["result"]) < 1:
            print("no story")
            exit()

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

        print('[*] Downloading last 24h stories...')
        try:
            for link in tqdm(links):
                r = requests.get(link["url"], verify=False)
                parser = urlparse(link["url"])
                filename = os.path.basename(os.path.basename(parser.path)
                                            + "."
                                            + link["expires"]
                                            + "."
                                            + link["format"])

                with open(self.sdname + '/' + filename, 'wb') as f:
                    f.write(r.content)
                    f.close()
        except KeyboardInterrupt:
            exit()

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
            print("[*] User '{}' does not exist!".format(self.username))
            return False
        elif "This Account is Private" in self.root:
            print("[*] Account '{}' is private!".format(self.username))
            return False
        else:
            return True

    def downloadHighlight(self, key, value):
        html = requests.get(key, verify=False).text
        od = self.username + '/' + value
        os.mkdir(od)
        soup = BeautifulSoup(html, features="lxml")

        links =  soup.findAll('a', attrs={'href': re.compile("^https://scontent")})
        
        print('[*] Downloading highlight {} of {}...'.format(self.c,self.t))
        try:
            for link in tqdm(links):
                url = link.get('href')
                r = requests.get(url, verify=False)
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
                print("[*] Highlights for user '{}' are already downloaded!".format(self.username))
                exit()
            else:
                os.mkdir(self.username)
        else:
            os.mkdir(self.sdname)

def main():
    urllib3.disable_warnings(InsecureRequestWarning)
    args = usage()

    downloader(args.user, args.stories)

def usage():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u','--user', nargs="?", help="Instagram username (required)", required=True)
    parser.add_argument('-s', '--stories', dest="stories", action="store_true", help="Only download last 24h stories")
    return parser.parse_args()

if __name__ == '__main__':
    main()
