# -*- coding: utf-8 -*- 
import requests
from bs4 import BeautifulSoup
import unicodecsv as csv
import re

INITIAL_URL='http://www.creprice.cn/'
#http://www.creprice.cn/market/distrank/city/zy.html?flag=1
DATAURL='http://www.creprice.cn/market/distrank/city/'

areas = dict()

def getAreasList(url):
  results = dict()
  resp  = requests.get(url)
  soup = BeautifulSoup(resp.content, "lxml")
  
  for span in soup.find_all('span'):
      if span.get('code'):
         results[span.get('code')] = span.string

  return results

def is_month(href):
        return href and re.compile("month").search(href)

def getAreaDataRange(area):
  url = DATAURL + area + '.html?flag=1'
  resp  = requests.get(url)
  soup = BeautifulSoup(resp.content, "lxml")

  results = []
  for link in soup.find_all(href=is_month):
      results.append(link.get('href'))

  return results

def is_td(tag):
    return tag.parent.name == 'tbody' and tag.name == 'tr'

def getAreaData(area, url):
  resp  = requests.get(url)
  soup = BeautifulSoup(resp.content, "lxml")
  year, month = (url.split('month=',1)[1]).split('-',1)

  results = dict()
  data = []
  for td in soup.find_all(is_td):
      for l in td.children:
        l.string.strip() and data.append(l.string.strip())
      date = data[0]+'/'+month+'/'+year
      results[date] = (date, area, data[1],data[2],data[4])

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

