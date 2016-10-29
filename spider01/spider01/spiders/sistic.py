# -*- coding: utf-8 -*-
from __future__ import division

import json
import re

import scrapy
from scrapy import Request
from scrapy.conf import settings
from scrapy.exceptions import CloseSpider

from ..items import SisticEventItem, SisticSeatsItem


class HtmlMarkup(Exception):
    def __init__(self):
        self.value = "Wrong HTML markup"

    def __str__(self):
        return repr(self.value)


class SisticSpider(scrapy.Spider):
    name = "sistic"
    allowed_domains = ["www.sistic.com.sg", "booking.sistic.com.sg", "booking.sistic.stixcloud.com"]
    start_urls = [
        'http://www.sistic.com.sg/events/search?c=Concert&l=50',
    ]

    # seats_URL = "https://smtickets.com//sections/generateSeat/"
    booking_URL_01 = 'http://booking.sistic.com.sg/SisticWebApp/Booking.do?contentCode='
    booking_URL_02 = 'http://booking.sistic.com.sg/SisticWebApp/retrieveOverviewSeatmap.do?jsondata=%7B+%27productCode%27%3A%27{PROD_CODE}%27%2C+%27specialCode%27%3A%27%27%7D&_='
    # To track those been processed
    EVENTS = []

    def parse(self, response):
        # Schedule page processing
        print("Processing URL: %s" % response.url)

        # Process links to other pages
        for link in response.xpath('//div[@class="pagination"]/a/@href').extract():
            link = response.urljoin(link)
            if link not in self.start_urls:
                self.start_urls.append(link)
                yield Request(link, callback=self.parse)

        # Process all events on page
        events = response.xpath('//table[@class="tbl_listing"]//div[@class="img"]/a/@href').extract()
        if not events and settings['BREAK_ON_HTML_MARKUP']:
            raise CloseSpider(reason='Unknown HTML markup')

        for link in events:
            link = response.urljoin(link)
            if link not in self.EVENTS:
                self.EVENTS.append(link)
                yield Request(link, callback=self.parse_event)

    def parse_event(self, response):
        # Parse event page
        url = response.url
        print("Processing event URL: %s" % url)

        # event id, url
        item = SisticEventItem()
        item['event_id'] = url.split('/')[-1]
        item['url'] = url
        # get event name
        block = response.xpath('//div[@class="event_details"]/div[@class="title"]//text()').extract()
        item['event_name'] = ' '.join([x.strip() for x in block if x.strip()])

        # Process entry block for date, time, venue
        for entry in response.xpath('//div[@class="details"]/div[@class="entry"]'):
            et = entry.xpath('div[@class="title"]/text()').extract()
            if et[0] == 'Event Date':
                # Process event date time
                block = entry.xpath('div[@class="desc"]//text()').extract()
                block = [x.strip() for x in ''.join(block).split('\n') if x.strip()]
                # print("TIME BLOCK: %s" % block)
                item['event_date'] = block[0]
                item['event_time'] = block[1:] if len(block) > 2 else block[1]
            elif et[0] == 'Venue':
                # Process venue
                # print(entry)
                block = [x.strip() for x in entry.xpath('div[@class="desc"]//text()').extract() if x.strip()]
                item['venue'] = block[0]
                item['venue_link'] = response.urljoin(entry.xpath('div[@class="desc"]//a/@href').extract()[0])

        # Get event image
        block = response.xpath('//div[@class="event_details"]//div[@class="display"]//img/@src').extract()
        item['image'] = response.urljoin(block[0])

        # Get selling dates
        for entry in response.xpath('//div[@id="tabsOuter"]/div[@id="tabsDetails"]/div[@class="entry"]'):
            et = entry.xpath('div[@class="title"]/text()').extract()
            if et[0] == 'Start Sales Date':
                # Get start Sales date
                block = ' '.join([x.strip() for x in entry.xpath('div[@class="desc"]//text()').extract() if x.strip()])
                item['start_sales_date'] = block.replace('\xa0', ' ')
            elif et[0] == 'Promoter Name':
                # Get promoter name
                block = ' '.join([x.strip() for x in entry.xpath('div[@class="desc"]//text()').extract() if x.strip()])
                item['promoter_name'] = block

        # Get seating plan ( CAN BE BLANK )
        block = response.xpath('//a[@class="seating_plan blue_btn"]/@href').extract()
        item['seating_img'] = block[0] if block else None

        # Get Synopsis links
        item['synopsis_links'] = response.xpath(
            '//div[@class="synopsis"]/div[@class="entry rich_content"]//a/@href').extract()

        # TODO: item consistency check
        yield item

        meta = {'event_id': item['event_id']}
        yield Request(self.booking_URL_01 + item['event_id'], callback=self.parse_booking, meta=meta)

    def parse_booking(self, response):
        # Parse booking page to get links to price tables
        url = response.url
        print("Processing booking URL: %s" % url)
        for s in response.xpath('//script/text()').extract():
            if "retrieveShowDateTime" in s:
                # Process ticket events
                m = re.match(r'.+(\[.+?\]).+', s, flags=re.DOTALL)
                for event in json.loads(m.group(1)):
                    # print('Product code: %s' % event['productCode'])
                    # print('showDateTime: %s' % event['showDateTime'])
                    meta = {'event_id': response.meta['event_id'], 'event_date': event['showDateTime']}
                    url = self.booking_URL_02.replace('{PROD_CODE}', event['productCode'])
                    yield Request(url,
                                  method='POST',
                                  headers={'X-Requested-With': 'XMLHttpRequest',
                                           'Content-Type': 'application/json'},
                                  callback=self.parse_booking_table, meta=meta)

    def parse_booking_table(self, response):
        # Parse booking page to get links to price tables
        url = response.url
        print("Processing booking table URL: %s" % url)
        event_dict = json.loads(response.body_as_unicode())
        for price_item in event_dict['priceTable']['priceTablePriceClassList']:
            item = SisticSeatsItem()
            item['event_id'] = response.meta['event_id']
            item['event_date'] = response.meta['event_date']
            item['category'] = price_item['priceClassAlias']
            prices = []
            for p_item in price_item['priceCatList']:
                sold = 1 if p_item['priceStatus'] == 16 else 0
                prices.append({'price': p_item['priceValue'], 'sold_out': sold})
            item['prices'] = prices

            # pprint(item)
            # TODO: item consistency check
            yield (item)
