# coding=utf8

import requests
import re
import time

def fetch(chapter_url, html):
    """
    ["'book','ajax','pinyin','taiyangdejuli','id','1','sky','ce3ec3c575c8b4699a6171afdcdc595c','t','1552898764'"]
    :param chapter_url:
    :type chapter_url:
    :param html:
    :type html:
    :return:
    :rtype:
    """
    matched = re.findall('setTimeout\(\"ajax_post\((.*?)\)', html)
    if not matched:
        return
    params = matched[0].replace('\'', '').split(',')
    time.sleep(1.1)
    session = requests.Session()
    session.headers.update(
        {
            'Referer': chapter_url,
            'Origin': 'http://www.quanben.io',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36',
            'Cookie':'_ga=GA1.2.915642510.1552870399; _gid=GA1.2.980717901.1552870399; _gat=1'
        }
    )
    while True:
        data = dict(
                  pinyin=params[3],
                  id=int(params[5]),
                  sky=params[7],
                  t=int(params[9]),
                  _type=params[1],
                  rndval=int(time.time())
              )
        content = session.post('http://www.quanben.io/index.php?c=book&a=ajax',
                          data=data
        ).content
        if "[温馨提示]请到 quanben.io 阅读完整章节内容。" not in content:
            time.sleep(1.1)
            return content.replace('<p>', '').replace('</p>', '\n')
        else:
            time.sleep(1.1)

