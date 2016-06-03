# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import sys
import os
import re
from datetime import datetime 
from itertools import product

from tornado import gen, httpclient, ioloop
from tornado.ioloop import IOLoop
from tornado.queues import Queue

# Amount of parallel requests
concurrency = 10

PAGE = 'hc'
ZENDESK_PAGE = '.zendesk.com/hc'
TOP_DOMAINS = ["support", "help", "faq", "soporte", "service", "supporto", "sales", "hilfe", "customer", "kc", "kb", "contact", "ask", "ajuda", "ajuto", "aide", "helpdesk"]
TLD = [".com", ".co.uk", ".de", ".it"]

RESULT = {}
DOMAINS = {}

DEBUG = False 
DEBUG_DIR = 'debug/'


def generate_url_list(domain):
    """
    Generate urls list combination out of top domains + domain name + page
    """
    lst = [ "http://" + s + "." + domain for s in TOP_DOMAINS ]
    lst_out = [ a + b + "/" + PAGE for a, b in product(lst, TLD)]
    zen_page = "http://" + domain + ZENDESK_PAGE
    lst_out.append(zen_page)
    for url in lst_out:
        RESULT[url] = domain
        RESULT[zen_page] = domain
    return lst_out

@gen.coroutine
def main():
    # Start consumer without waiting
    # Tornado framework used for async IO
    # http://www.tornadoweb.org/en/stable/index.html
    q = Queue()

    @gen.coroutine
    def consumer():
        item = yield q.get()
        try:
            code = False
            try:
                response = yield httpclient.AsyncHTTPClient().fetch(item)
                codes = ['200', '301', '302']
                code = any(s in response.headers['Status'] for s in codes)
                rcode = response.code
                if DEBUG:
                    fname = re.match(r'http://([\w+|.]+)/',item).group(1)
                    fname = os.path.join(DEBUG_DIR,fname.replace(".","_"))
                    with open(fname, 'w') as f:
                        for k,v in response.headers.get_all():
                            f.write(k+' '+v+'\n')
                        f.write('\n')
                        f.write(response.body)
                    f.close()
            except Exception as e:
                code = False
                rcode = str(e)
            
            print('%s,%s,%s,"%s"' % 
                            (datetime.now(), item, code, rcode))
            # Append to DOMAINS found URL 
            if code:
                DOMAINS[RESULT[item]].append(item)            
        
        finally:
            q.task_done()

    @gen.coroutine
    def worker():
        while True:
            yield consumer()

    @gen.coroutine
    def producer():
        if DEBUG and not os.path.exists(DEBUG_DIR):
            print('Creating debug out dir: %s' % DEBUG_DIR)
            os.makedirs(DEBUG_DIR)
  
        # Open and process file if supplied
        if len(sys.argv) >= 2:
            with open(sys.argv[1]) as f:
                for line in f:    
                    DOMAINS[line.strip()]= []
        else:
            print("Domains list file wasn't provided")
            print("Usage: %s <domains.txt> [ report.txt ]" % sys.argv[0])
            sys.exit(2)
        # Generate processing list 
        for d in DOMAINS.keys():
            for url in generate_url_list(d):
                q.put(url)

    yield producer()# Wait for producer to put all tasks.
    # Start workers, then wait for the work queue to be empty. 
    for _ in range(concurrency):
        worker()
    
    yield q.join() # Wait for consumer to finish all tasks.
    
    # Out results
    if len(sys.argv) >= 3:
        f = open(sys.argv[2],'w')
    else:
        f = sys.stdout

    for key, val in DOMAINS.items():
        if DOMAINS[key]:
            DOMAINS[key] = '"'+" ".join(val)+'"'
        else:
            DOMAINS[key] = 'No'
    out = "\n".join([",".join([key, str(val)]) for key, val in DOMAINS.items()]) + '\n'
    
    f.write(out)
    

# Main IO Loop
if __name__ == '__main__':
    io_loop = ioloop.IOLoop.current()
    io_loop.run_sync(main)
