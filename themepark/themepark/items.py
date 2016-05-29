# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ThemeparkItem(scrapy.Item):
    # define the fields for your item here like:
    name = scrapy.Field()
    location = scrapy.Field()
    country = scrapy.Field()
    status = scrapy.Field()
    opened = scrapy.Field()
    closed = scrapy.Field()
    url = scrapy.Field()
    rcdburl = scrapy.Field()
