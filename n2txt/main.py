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

htmlparser = HTMLParser.HTMLParser()
tag_reg = re.compile(r'<[^>]*>')
clean = lambda html_str: tag_reg.sub('',html_str).replace('\n','').replace(' ','').replace('<br>', '\n').replace('<br/>', '\n')



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



class NovelUrls(object):
    def __init__(self, base_url, xpath):
        self.urls = []
        domain = base_url.split('/')[2]
        html_content = requests.get(base_url).content
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
        content = requests.get(url).content
        if chardet.detect(content).get('encoding') == 'GB2312':
            content = content.decode('GBK').encode('utf8')
        self.html_content = content.replace('&nbsp;', ' ')
        root = html.document_fromstring(content, parser=html.HTMLParser(encoding='utf-8'))
        if content_xpath:
            matched_content = root.xpath(content_xpath)
            if not matched_content:
                raise ContentNotMatchedError()
            self.txt_content = clean(htmlparser.unescape(html.tostring(matched_content[0], pretty_print=True, encoding="utf8")))


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


@click.command()
def dump_flat():
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

    for url_, title in processstate.chapters:
        try:
            content = NovelChapter(url_, processstate.content_xpath).txt_content
            lines.append("\n%s\n\n" % title.encode('utf8'))
            lines.append(content)
            click.echo("%s processed" % title.encode('utf8'))
            time.sleep(1)
        except ContentNotMatchedError:
            continue

    with open(os.path.join(os.getcwd(), "%s.txt" % processstate.book_name.encode('utf8')), 'w') as f:
        f.writelines(lines)
    click.echo('Ajax Dump Complete!')
        

@click.command()
@click.argument('name')
def dump_ajax(name):
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
    sys.path.append(os.getcwd())
    md = importlib.import_module(name)
    lines = []
    lines.append(processstate.book_name.encode('utf8'))

    for url_, title in processstate.chapters:
        content = md.fetch(url_, NovelChapter(url_, None).html_content)
        lines.append("\n%s\n\n" % title.encode('utf8'))
        lines.append(content)
        click.echo("%s processed" % title.encode('utf8'))

    with open(os.path.join(os.getcwd(), "%s.txt" % processstate.book_name.encode('utf8')), 'w') as f:
        f.writelines(lines)
    click.echo('Ajax Dump Complete!')


def main():
    cli.add_command(init)
    cli.add_command(analysis_url)
    cli.add_command(flat_chapter)
    cli.add_command(ajax_chapter)
    cli.add_command(dump_flat)
    cli.add_command(dump_ajax)
    cli()


if __name__ == "__main__":
    main()
