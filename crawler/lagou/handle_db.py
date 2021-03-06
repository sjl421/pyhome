#!/usr/bin/env python
# -*- coding: utf-8 -*-

import _env
from pprint import pprint as pp
from tornado.util import ObjectDict
from lib._db import get_db, redis_client as r
from html_parser import Bs4HtmlParser
from lagou_parser import LagouHtmlParser
from spider import LagouCrawler
from web_util import logged


DEBUG = True
db = get_db('htmldb')
lagou_html_col = getattr(db, 'lagou_html')    # collection


def test_get_db():
    o = col.find_one({'_id': 1234})
    html = o['html']
    # print html
    pp(o)


def test_get_html():
    import chardet
    _id = 46167
    o = col.find_one({'_id': _id})
    p = Bs4HtmlParser('', o['html'])
    print(p.html)
    t = p.bs.find('p', class_='msg')
    text = t.get_text()
    print(text)


def count_how_many_block_html():
    col = lagou_html_col
    cnt = 0
    for html_doc in col.find(modifiers={"$snapshot": True}):
        url = html_doc['url']
        html = html_doc['html']
        if LagouCrawler.is_block_html(html, False):
            lagou_html_col.delete_one({'url': url})
            print(url)
            cnt += 1
    return cnt


def remove_deleted_html():
    cnt = 0
    for html_doc in lagou_html_col.find(modifiers={"$snapshot": True}):
        url = html_doc['url']
        html = html_doc['html']
        if LagouCrawler.is_deleted_html(html, False):
            lagou_html_col.delete_one({'url': url})
            print(url)
            cnt += 1
    return cnt


def count_how_many_check_html():
    col = lagou_html_col
    print(col.count())
    cnt = 0
    _id_list = []
    for html_doc in col.find(modifiers={"$snapshot": True}):
        html = html_doc['html']
        if LagouCrawler.is_check_html(html, verbose=False):
            cnt += 1
            _id_list.append(html_doc._id)
    print(cnt)
    return cnt
    print(col.count())
    # col.remove({'_id':{'$in':_id_list}})


@logged
class ParseJob(object):
    """用来处理抓下来的html页面，把需要的数据从html中提取出来单独存储"""

    db = get_db('htmldb')

    def __init__(self):
        self.from_col = getattr(self.db, 'lagou_html')
        self.to_col = getattr(self.db, 'lagou_job')
        self.key = self.__class__.__name__
        self.last_id = int(r.get(self.key) or 0)

    def set_id(self, last_id=0):
        r.set(self.key, last_id)

    def run_job(self):
        """lagou job页面的信息任务"""
        for doc_dict in self.from_col.find(
            {'_id': {'$gte': self.last_id}}
        ).sort('_id', 1):

            if 'job' in doc_dict['url']:    # job url
                doc = ObjectDict(doc_dict)
                assert doc.url and doc.html
                if LagouCrawler.is_deleted_html(doc.html, False):
                    self.from_col.delete_one({'url': doc.url})
                    continue
                job_parser = LagouHtmlParser(doc.url, doc.html)

                data_dict = job_parser.parse_job()
                if data_dict is None:
                    self.from_col.delete_one({'url': doc.url})
                    continue

                self.logger.info(
                    'handle url: %s %s:%s',
                    doc.url, data_dict['source'], data_dict['job']
                )
                if not DEBUG:
                    self.to_col.update(
                        {
                            '_id': doc._id,
                        },
                        {
                            '$set': data_dict
                        },
                        upsert=True
                    )
                self.set_id(doc._id)


if __name__ == '__main__':
    # test_get_html()
    # print(count_how_many_block_html())
    # print(count_how_many_check_html())
    # print(col.count())
    p = ParseJob()
    p.run_job()
    # remove_deleted_html()
    # print(count_how_many_block_html())
