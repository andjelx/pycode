# -*- coding: utf-8 -*-
import scrapy
from themepark.items import ThemeparkItem
import re
from HTMLParser import HTMLParser 

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

class RcdbSpider(scrapy.Spider):
    name = "rcdb"
    allowed_domains = ["rcdb.com"]
    start_urls = ['http://rcdb.com/r.htm?ot=3&nm=na&ar=3168000&page=%d' % i for i in range(1, 154)]
#    start_urls = ('http://rcdb.com/r.htm?na=&nm=na&ol=&al=&ar=3168000&ot=3&page=5', )

    def parse(self, response):
        urlpath = '//*[@id="report"]/tbody/tr/td[2]/a/@href'
        for href in response.xpath(urlpath):
            url = response.urljoin(href.extract())
            yield scrapy.Request( url, callback=self.parse_park)

    def parse_park(self, response):
        item = ThemeparkItem()
        
        name = response.xpath('//*[@id="feature"]/div/h1/text()').extract()
        item['name'] = [ s.encode('utf-8') for s in name ] 
        
        # Search for URL 
        url = response.xpath('//*[@id="feature"]/a[2]/@href').extract()
        if url:
            urls = [ s.encode('utf-8') for s in url ]
            item['url'] = urls if 'http:' in str(urls) else "nodata"
        else:
            item['url'] = 'nodata'
        
        item['rcdburl'] = response.url
        
        # Operating status
        # //*[@id="feature"]/a[1]
        st = response.xpath('//*[@id="feature"]/a[1]/text()').extract()
        status = ''.join(st)
        item['status'] = status if st else 'Operated'
                

        # Parse main block
        feature = str(response.xpath('//*[@id="feature"]').extract())        
        re.M
        
        item['closed'] = 'nodata'    
        # Search for open date
        if 'opening' in feature:
            s = re.search('opening\s([^<]+)',feature)
            item['opened'] = s.group(1) if s else "nodata"
        # Search for open date
        if 'since' in feature:
            s = re.search('since\s([^<]+)',feature)
            item['opened'] = s.group(1) if s else "nodata"

        # Search for open and closed date
        s = re.search(r'from\s(.+)(\sto\s)(.+?)(\\n)?<',feature)
        if s:
            item['opened'] = s.group(1) if s else "nodata"
            item['closed'] = s.group(3) if s else "nodata"

        loc = response.xpath('//*[@id="feature"]/div[1]').extract()
        # Search for location
        location = ''
        for s in response.xpath('//*[@id="feature"]/div[1]').extract():
            location = location + s.encode('utf-8')
        
        location = location.replace('<br><a','<br> <a')
        s = re.search('</h1>(.*)',str(location))
        item['location'] = strip_tags(s.group(1)) if s else "nodata"
        # Search for country
        s = re.search(',\s([\w|\s]+)$',item['location'])
        item['country'] = s.group(1) if s else "nodata"

        yield item 
