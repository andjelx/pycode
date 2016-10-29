# -*- coding: utf-8 -*-
from __future__ import division

import re
from collections import Counter

import scrapy
from scrapy import Request
from scrapy.conf import settings
from scrapy.exceptions import CloseSpider

from ..items import EventItem, SeatsItem


class HtmlMarkup(Exception):
    def __init__(self):
        self.value = "Wrong HTML markup"

    def __str__(self):
        return repr(self.value)


class SmticketsSpider(scrapy.Spider):
    name = "smtickets"
    allowed_domains = ["smtickets.com"]
    start_urls = (
        'https://smtickets.com/events/category/music+or+concert',
    )

    seats_URL = "https://smtickets.com//sections/generateSeat/"

    def parse(self, response):
        # Process each link in table
        rows = response.xpath('//table[@id="listing_table"]/*/tr')
        if not rows and settings['BREAK_ON_HTML_MARKUP']:
            raise CloseSpider(reason='Unknown HTML markup')

        for row in rows:
            edate = []
            # Date
            for i in range(1, 4):
                block = row.xpath('td[' + str(i) + ']//text()').extract()
                if block:
                    edate.extend(block)
            if len(edate) == 5:
                date = '{}, {} {}, {} {}'.format(edate[3], edate[1], edate[0], edate[2], edate[4])
            else:
                date = None

            # Get name
            block = row.xpath('td[4]//text()').extract()
            event_name = block[0] if block else None

            # Get venue
            block = row.xpath('td[5]//text()').extract()
            venue = block[0] if block else None

            # Get url
            block = row.xpath('td/a/@href').extract()
            url = block[0] if block else None

            if url and date and venue:
                meta = {'event_date': date, 'venue': venue, 'event_name': event_name}
                yield Request(url, callback=self.parse_event, meta=meta)
            elif settings['BREAK_ON_HTML_MARKUP']:
                raise CloseSpider(reason='Unknown HTML markup')

    def parse_event(self, response):
        # parse particular event page
        url = response.url
        # event id, venue, date, name
        item = EventItem()
        item['event_id'] = url.split('/')[-1]
        item['venue'] = response.meta['venue']
        item['event_name'] = response.meta['event_name']
        item['event_date'] = response.meta['event_date']
        # Get poster
        block = response.xpath('//img[@class="img-responsive event_img"]/@src').extract()
        item['event_poster'] = block[0] if block else None
        # Get seating chart
        block = response.xpath('//div[@class="col-sm-3"]//img/@src').extract()
        item['seating_chart'] = block[0] if block else None
        # Description
        block = response.xpath('//div[@id="event_description"]//text()').extract()
        item['description'] = [x.strip() for x in block if x.strip()] if block else None
        # Seats
        seats_table = response.xpath('//table[@id="seat_selection_table"]/tbody/tr')
        for row in seats_table:
            # Zone name
            block = row.xpath('td[@class="price_name_column"]//text()').extract()
            zone_name = block[0].strip() if block else None
            # Zone price
            block = row.xpath('td[@class="price_amount_column"]//text()').extract()
            # price =
            price = block[0].replace(',','') if block else None
            if price:
                pmatch = re.match(r'.*?([\d.]+)$', price)
                price = pmatch.group(1) if pmatch else None

            # Get each section name and id
            for zone in row.xpath('td/select/option[@class="section_dropdown"]'):
                block = zone.xpath('@sectionname').extract()
                sec_name = block[0].strip() if block else None
                block = zone.xpath('@sectiontype').extract()
                sec_type = block[0].strip() if block else None
                block = zone.xpath('@sectionid').extract()
                sec_id = block[0].strip() if block else None
                # if exists
                if sec_name and sec_id and sec_type:
                    meta = {
                        'event_id': item['event_id'],
                        'zone_name': zone_name,
                        'sec_name': sec_name,
                        'sec_type': sec_type,
                        'price': price
                    }
                    yield Request(self.seats_URL + sec_id, callback=self.parse_seats, meta=meta, method='POST')
                elif settings['BREAK_ON_HTML_MARKUP']:
                    raise CloseSpider(reason='Unknown HTML markup')

        yield item

    def parse_seats(self, response):
        # parse seats page
        item = SeatsItem()
        item['event_id'] = response.meta['event_id']
        item['name'] = response.meta['zone_name']
        item['section_name'] = response.meta['sec_name']
        item['type'] = response.meta['sec_type']
        item['price'] = response.meta['price']

        # Get seats counter
        block = response.xpath('//table[@id="seat_matrix"]/*/td/@class').extract()
        if block:
            counter = Counter(block)
            item['seats_used'] = int(counter['seat unavailable'])
            item['seats_available'] = int(counter['seat available'])
            item['seats_capacity'] = item['seats_used'] + item['seats_available']
            item['seats_percentage_left'] = (item['seats_capacity'] - item['seats_used']) / item['seats_capacity'] * 100
            yield item
