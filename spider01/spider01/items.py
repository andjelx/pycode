# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

class EventItem(scrapy.Item):
    #
    event_id = scrapy.Field()
    event_name = scrapy.Field()
    venue = scrapy.Field()
    event_poster = scrapy.Field()
    event_date = scrapy.Field()
    description = scrapy.Field()
    seating_chart = scrapy.Field()
    pass

class SeatsItem(scrapy.Item):
    #
    event_id = scrapy.Field()
    name = scrapy.Field()
    section_name = scrapy.Field()
    type = scrapy.Field()
    price = scrapy.Field()
    seats_capacity = scrapy.Field()
    seats_used = scrapy.Field()
    seats_available = scrapy.Field()
    seats_percentage_left = scrapy.Field()
    pass

class SisticEventItem(scrapy.Item):
    event_id = scrapy.Field()
    event_name = scrapy.Field()
    url = scrapy.Field()
    event_date = scrapy.Field()
    event_time = scrapy.Field()
    image = scrapy.Field()
    venue = scrapy.Field()
    venue_link = scrapy.Field()
    synopsis_links = scrapy.Field()
    start_sales_date = scrapy.Field()
    promoter_name = scrapy.Field()
    seating_img = scrapy.Field()
    pass


class SisticSeatsItem(scrapy.Item):
    event_id = scrapy.Field()
    event_date = scrapy.Field()
    category = scrapy.Field()
    prices = scrapy.Field()
    pass
