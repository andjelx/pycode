# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
from scrapy import signals
from scrapy.exporters import JsonLinesItemExporter


class Spider01Pipeline(object):
    def process_item(self, item, spider):
        return item


class MyJsonLinesItemExporter(object):

    # Items and writers
    JSONWriters = {
        'EventItem': 'sm_events',
        'SeatsItem': 'sm_seats',
        'SisticEventItem': 'sistic_events',
        'SisticSeatsItem': 'sistic_seats',
    }

    def __init__(self):
        self.files = {}
        self.exporters = {}

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signals.spider_closed)
        return pipeline

    def spider_opened(self, spider):
        for i in self.JSONWriters.values():
            file = open('%s_out.json' % i, 'w+b')
            self.files[spider] = file
            exporter = JsonLinesItemExporter(file)
            self.exporters[i] = exporter
            exporter.start_exporting()
        print(self.exporters)

    def spider_closed(self, spider):
        for e in self.exporters.values():
            e.finish_exporting()
        file = self.files.pop(spider)
        file.close()

    def process_item(self, item, spider):
        # Process depends on item type
        out = self.JSONWriters[item.__class__.__name__]
        self.exporters[out].export_item(item)
        return item
