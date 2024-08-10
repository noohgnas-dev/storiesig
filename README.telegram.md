# storiesig
Instagram story downloader using storiesig.com as a pseudo-API.

```
usage: storiesig_with_telegram.py [-h] -u [USER] [-s]

optional arguments:
  -h, --help            show this help message and exit
  -u [USER], --user [USER]
                        Instagram username (required but useless)
  -s, --stories         Only download last 24h stories
  -l, --list            Only download last 24h stories with list of file
```

## Installation
```
$ git clone https://github.com/noohgnas-dev/storiesig.git
$ cd storiesig
$ sudo pip3 install -r requirements.txt
$ chmod +x storiesig_with_telegram.py
```

## Usage

There are two ways you can use this script:

1. If you want to download stored highlights for a user:  
`$ ./storiesig_with_telegram.py -u <username>`  
This will create a new directory based on username with its relevant subdirectories based on highlight names.

2. If you want to only download last 24h stories:  
`$ ./storiesig_with_telegram.py -u <username> --stories`  
This will create a new directory based on username and date/time when the script is executed.

3. Download last 24h stories with list of users in file:  
`$ ./storiesig_with_telegram.py -u <username> -s -l users.yaml`  

4. Use crontab in your system:
`11 9,13,15,17,19,21,23 * * * /home/nooh/stories/venv/bin/python /home/nooh/stories/storiesig_with_telegram.py -u tmp -s -l /home/nooh/stories/users.yaml >> /home/nooh/stories/log.log 2>&1`
