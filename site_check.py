# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import sys
from datetime import datetime 

from tornado import gen, httpclient, ioloop
from tornado.ioloop import IOLoop
from tornado.queues import Queue

# Amount of parallel requests
concurrency = 10

PAGE = 'hc'
TOP_DOMAINS = ["support", "help", "faq", "soporte", "service", "supporto", "sales", "hilfe", "customer", "kc", "kb", "contact", "ask", "ajuda", "ajuto", "aide", "helpdesk"]

def generate_url_list(domain):
    """
    Generate urls list combination out of top domains + domain name + page
    """
    lst = []
    for td in TOP_DOMAINS:
        url = "http://" + td + "." + domain + "/" + PAGE
        lst.append(url.replace("..",".")) # Fixing possible double dots
    return lst

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
            try:
                response = yield httpclient.AsyncHTTPClient().fetch(item)
                code = True
                rcode = response.code
            except Exception as e:
                code = False
                rcode = str(e)
            print('%s,%s,%s,"%s"' % 
                            (datetime.now(), item, code, rcode))
        finally:
            q.task_done()

    @gen.coroutine
    def worker():
        while True:
            yield consumer()

    @gen.coroutine
    def producer():
        DOMAINS = []
        # Open and process file if supplied
        if len(sys.argv) >= 2:
            with open(sys.argv[1]) as f:
                for line in f:    
                    DOMAINS.append(line.strip())
        else:
            print("Domains list file wasn't provided")
            print("Usage: %s <domains.txt>" % sys.argv[0])
            sys.exit(2)
    
        # Generate processing list 
        for d in DOMAINS:
            for url in generate_url_list(d):
                q.put(url)

    yield producer()# Wait for producer to put all tasks.
    
    # Start workers, then wait for the work queue to be empty. 
    for _ in range(concurrency):
        worker()
    
    yield q.join() # Wait for consumer to finish all tasks.

# Main IO Loop
if __name__ == '__main__':
    io_loop = ioloop.IOLoop.current()
    io_loop.run_sync(main)
