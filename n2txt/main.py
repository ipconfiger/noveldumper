# coding=utf8

import requests
import chardet
from lxml import html
import HTMLParser
import re
import click
import importlib
import sys
import os
import pickle
import time
from multiprocessing import Pool

htmlparser = HTMLParser.HTMLParser()
tag_reg = re.compile(r'<[^>]*>')
clean = lambda html_str: tag_reg.sub('',html_str).replace('\n','').replace(' ','').replace('<br>', '\n').replace('<br/>', '\n')


def tostr(s):
    if isinstance(s, unicode):
        return s.encode('utf8')
    return s


class TitleNotMatchedError(Exception):
    pass

class ContentNotMatchedError(Exception):
    pass

def final_text(ele):
    if ele.text:
        return ele.text
    else:
        return final_text(ele.getchildren()[0])


class ProcessState(object):
    chapter_list_url = ''
    book_name = ''
    chapters = []
    link_xpath = ''
    chaper_link_detected = False
    content_xpath = ''
    chapter_detected = False


def save_state(state):
    state_file = pickle.dumps(state)
    with open(os.path.join(os.getcwd(), ".n2t_state"), 'wb') as f:
        f.write(state_file)


def load_state():
    with open(os.path.join(os.getcwd(), '.n2t_state'), 'rb') as f:
        return pickle.loads(f.read())


def get_domain(url):
    return "%s://%s" % (url.split('/')[0], url.split('/')[2])


def get_content(url):
    origin = get_domain(url)
    session = requests.Session()
    session.headers.update(
        {
            'Referer': origin,
            'Origin': origin,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36',
            'Cookie': '_ga=GA1.2.915642510.1552870399; _gid=GA1.2.980717901.1552870399; _gat=1'
        }
    )
    return session.get(url).content


class NovelUrls(object):
    def __init__(self, base_url, xpath):
        self.urls = []
        domain = base_url.split('/') [2]

        html_content = get_content(base_url)
        if chardet.detect(html_content).get('encoding') == 'GB2312':
             html_content = html_content.decode('GBK').encode('utf8')
        root = html.document_fromstring(html_content)
        for element in root.xpath(xpath):
            path = element.attrib ['href']
            if path.startswith('/'):
                self.urls.append(("http://%s%s" % (domain, path), final_text(element)))
            if path.startswith('http'):
                self.urls.append(path)

    def __iter__(self):
        for url, title in self.urls:
            yield url, title

class NovelChapter(object):
    def __init__(self, url, content_xpath):
        content = get_content(url)
        if chardet.detect(content).get('encoding') == 'GB2312':
            content = content.decode('GBK').encode('utf8')
        self.html_content = content.replace('&nbsp;', ' ')
        root = html.document_fromstring(content, parser=html.HTMLParser(encoding='utf-8'))
        if content_xpath:
            matched_content = root.xpath(content_xpath)
            if not matched_content:
                raise ContentNotMatchedError()
            try:
                self.txt_content = clean(htmlparser.unescape(html.tostring(matched_content[0], pretty_print=True, encoding="utf8").decode('utf8')))
            except Exception as e:
                click.echo('<ERROR:> %s' % e)
                click.echo(type(html.tostring(matched_content[0], pretty_print=True, encoding="utf8")))


@click.group()
def cli():
    pass



@click.command()
@click.argument('url')
@click.argument('name')
def init(url, name):
    """
    初始化一个项目
    :param url:
    :type url:
    :return:
    :rtype:
    """
    processstate = ProcessState()
    processstate.book_name = name
    processstate.chapter_list_url = url
    save_state(processstate)
    click.echo('Book %s inited' % name)


@click.command()
@click.argument('xpath')
def analysis_url(xpath):
    """
    Show chapter URLs detected in Chapter list page
    :param url:  Chapter list page
    :type url: str
    :param xpath: xpath of href tag
    :type xpath: str
    :return:
    :rtype: 
    """
    try:
        processstate = load_state()
    except IOError as e:
        click.echo('Run init first')
        sys.exit(1)

    processstate.chapters = []

    processstate.link_xpath = xpath
    ct=0
    for url, title in NovelUrls(processstate.chapter_list_url, xpath):
        click.echo("detect %s of %s" % (url, title))
        processstate.chapters.append((url, title))
        ct+=1
    click.echo('----------------------------------')
    click.echo('%s URLs detected' % ct)
    processstate.chaper_link_detected = True
    processstate.chapter_detected = False
    save_state(processstate)
    click.echo('%s \'s Chapters detected!' % processstate.book_name)


@click.command()
def reverse():
    try:
        processstate = load_state()
    except IOError as e:
        click.echo('Run init first')
        sys.exit(1)
    if not processstate.chaper_link_detected:
        click.echo('Run analysis-url to check chapter\'s url')
        sys.exit(1)
    processstate.chapters.reverse()
    save_state(processstate)
    click.echo("Reversed!")


@click.command()
@click.argument('xpath')
def flat_chapter(xpath):
    try:
        processstate = load_state()
    except IOError as e:
        click.echo('Run init first')
        sys.exit(1)
    if not processstate.chaper_link_detected:
        click.echo('Run analysis-url to check chapter\'s url')
        sys.exit(1)

    for url_, title in processstate.chapters:
        content = NovelChapter(url_, xpath).txt_content
        if content:
            click.echo(content)
            processstate.chapter_detected = True
            processstate.content_xpath = xpath
            save_state(processstate)
            
        else:
            click.echo("No content detected!")
        break


@click.command()
@click.argument('name')
def ajax_chapter(name):
    try:
        processstate = load_state()
    except IOError as e:
        click.echo('Run init first')
        sys.exit(1)
    if not processstate.chaper_link_detected:
        click.echo('Run analysis-url to check chapter\'s url')
        sys.exit(1)

    for url_, title in processstate.chapters:
        sys.path.append(os.getcwd())
        md = importlib.import_module(name)
        content = md.fetch(url_, NovelChapter(url_, None).html_content)
        if content:
            click.echo(content)
            processstate.chapter_detected = True
            save_state(processstate)

        else:
            click.echo("No content detected!")
        break


def asyncGetChapter(idx, url, title, processstate, ajax_md):
    if ajax_md:
        content = ajax_md.fetch(url, NovelChapter(url, None).html_content)
    else:
        content = NovelChapter(url, processstate.content_xpath).txt_content
    click.echo("%s processed" % title.encode('utf8'))
    return {'idx': idx, 'title':title, 'content': content}
    

@click.command()
@click.option('-f', '--min', default=0)
@click.option('-t', '--max', default=9999)
@click.option('-p', '--process', default=5)
def dump_flat(min, max, process):
    execute_dump(max, min, process)
    click.echo('Dump Complete!')


def execute_dump (max, min, process_num, ajax_md=None):
    try:
        processstate = load_state()
    except IOError as e:
        click.echo('Run init first')
        sys.exit(1)
    if not processstate.chaper_link_detected:
        click.echo('Run analysis-url to check chapter\'s url')
        sys.exit(1)
    if not processstate.chapter_detected:
        click.echo('Run flat_chapter to check chapter')
        sys.exit(1)
    lines = []
    lines.append(processstate.book_name.encode('utf8'))
    _idx = 0
    pool = Pool(processes=int(process_num))
    results = []
    for url_, title in processstate.chapters [min: max]:
        results.append(pool.apply_async(asyncGetChapter, args=(_idx, url_, title, processstate, ajax_md)))
        _idx += 1
    pool.close()
    pool.join()
    async_results = []
    for res in results:
        async_results.append(res.get())
    sorted_results = sorted(async_results, key=lambda item: item.get('idx'))
    for item in sorted_results:
        title = item.get('title')
        content = item.get('content')
        lines.append("\n%s\n\n" % title.encode('utf8'))
        lines.append(tostr(content))
    click.echo("done")
    with open(os.path.join(os.getcwd(), "%s.txt" % processstate.book_name.encode('utf8')), 'w') as f:
        f.writelines(lines)


@click.command()
@click.argument('name')
@click.option('-f', '--min', default=0)
@click.option('-t', '--max', default=9999)
@click.option('-p', '--process', default=5)
def dump_ajax(name, min, max, process):
    sys.path.append(os.getcwd())
    md = importlib.import_module(name)
    execute_dump(max, min, process, ajax_md=md)
    click.echo('Ajax Dump Complete!')


def main():
    cli.add_command(init)
    cli.add_command(analysis_url)
    cli.add_command(flat_chapter)
    cli.add_command(ajax_chapter)
    cli.add_command(dump_flat)
    cli.add_command(dump_ajax)
    cli.add_command(reverse)
    cli()


if __name__ == "__main__":
    main()
