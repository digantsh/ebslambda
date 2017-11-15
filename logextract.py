from __future__ import unicode_literals
import requests
import json
import datetime
import time
import yaml
from multiprocessing.dummy import Pool as ThreadPool
from Queue import Queue
from threading import Thread
import sys
# import grequests
global conturl
# files = []
with open("prod.yml", 'r') as ymlfile:
# with open("config.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)
target = open('config.txt', 'w')

q = Queue(maxsize=0)

def getToken(tokenUrl, payload):
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'cache-control': "no-cache",
        'postman-token': "2cc34a9e-753c-5f48-1f2b-9ef9378c9bac"
        }
    response = requests.request("POST", tokenUrl, data=payload, headers=headers)
    token = response.json().get('access_token')
    return token
def getContentHdr(sub_content_url, querystring, token):
    headers = {
    'authorization': "Bearer " + token,
    'cache-control': "no-cache",
    'postman-token': "ace7b595-d19b-2406-c904-61ab25f9d6fc"
    }
    response = requests.request("GET", sub_content_url, headers=headers, params=querystring)
    return response.headers.get('nextpageuri')

def getContentUrl(sub_content_url, querystring, token):
    # start_time = time.time()
    headers = {
    'authorization': "Bearer " + token,
    'cache-control': "no-cache",
    'postman-token': "ace7b595-d19b-2406-c904-61ab25f9d6fc"
    }
    response = requests.request("GET", sub_content_url, headers=headers, params=querystring)
    conturl = response.json()
    # d_time = time.time()
    # print "time to process all is : %.3f" % (d_time - start_time)
    return conturl

def getContentData(p, token):
    headers = {
    'authorization': "Bearer " + token,
    'cache-control': "no-cache",
    'postman-token': "ace7b595-d19b-2406-c904-61ab25f9d6fc"
    }
    # for content in p:
    cnt = 0
    while not q.empty():
        response = q.get(requests.request("GET", p, headers=headers))
        resp = requests.request("GET", response, headers=headers)
        # print resp.text.encode('utf-8').strip()
        # cat_json('audit.json', resp.text)
        # cnt = cnt + 1
        # tr = cnt
        # print tr
        # target = open((str(tr) + '.txt'), 'w')
        target.write(resp.text.encode('utf-8').strip())
        # target.close()
        q.task_done()

def cat_json(output_filename, input_filenames):
    with file(output_filename, "w") as outfile:
        first = True
        for infile_name in input_filenames:
            with file(infile_name) as infile:
                if first:
                    outfile.write('[')
                    first = False
                else:
                    outfile.write(',')
                outfile.write(mangle(infile.read()))
        outfile.write(']')

def mangle(s):
    return s.strip()[1:-1]

def main():
    start_time = time.time()
    tokenUrl = cfg['tokenUrl']
    payload = cfg['payload']

    sub_content_url = cfg['sub_content_url']
    querystring = {"contentType":"Audit.SharePoint"}

    urllist = []
    while sub_content_url:
        response = getContentUrl(sub_content_url, querystring, getToken(tokenUrl, payload))
        for content in response:
            cUrl = content.get('contentUri')
            # print cUrl
            urllist.append(cUrl)
        sub_content_url = getContentHdr(sub_content_url, querystring, getToken(tokenUrl, payload))
    for url in urllist:
        q.put(url)
    for i in range(10): #  number of threadtex
        t1 = Thread(target = getContentData, args=(url, getToken(tokenUrl, payload))) # target is the above function
        # t1.setDaemon(True)
        t1.start() # start the thread

    q.join()
    d_time = time.time()
    print "time to process all is : %.3f" % (d_time - start_time)
    target.close()
if __name__ == '__main__':
    main()

