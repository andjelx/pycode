# -*- coding: utf-8 -*- 
import requests
from lxml import html
import unicodecsv as csv

INITIAL_URL='http://www.creprice.cn/'
#http://www.creprice.cn/market/distrank/city/zy.html?flag=1
DATAURL='http://www.creprice.cn/market/distrank/city/'

areas = dict()

def getAreasList(url):
  resp  = requests.get(url)
  tree = html.fromstring(resp.content)
  results = dict()

  for i, tag in enumerate(tree.xpath('//*[self::span]')):
    code_id = tag.xpath('.//@code')
    area = tag.xpath('.//text()')
    if code_id and code_id[0] not in results:
      results[code_id[0]] = area[0]

  return results

def getAreaDataRange(area):
  url = DATAURL + area + '.html?flag=1'
  resp  = requests.get(url)
  tree = html.fromstring(resp.content)

  results = []
  for i, tag in enumerate(tree.xpath('//li/a')):
    link = tag.xpath('.//@href')
    if link and "month" in link[0]:
      results.append(link[0])

  return results

def getAreaData(area, url):
  resp  = requests.get(url)
  year, month = (url.split('month=',1)[1]).split('-',1)
  tree = html.fromstring(resp.content)

  results = dict()
  for i, tag in enumerate(tree.xpath('//tbody/tr')):
     l = tag.xpath('.//text()')
     for j, val  in enumerate(l):
        l[j] = val.strip()
     date = l[1]+'/'+month+'/'+year
     results[i] = (date,area,l[3],l[5],l[9])

  return results

areas = getAreasList(INITIAL_URL)
f = open('report.csv', 'wb')
writer = csv.writer(f)

for key, value in areas.iteritems():
    print('Processing ' + key + ' ' + value)
    for url in getAreaDataRange(key):
        print('Processing url: ' + url) 
        for line in getAreaData(value,url).itervalues():
            writer.writerow(line)

