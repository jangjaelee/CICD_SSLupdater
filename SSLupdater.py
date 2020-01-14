#!/usr/bin/python3
# -*-Python-script-*-
#
#/**
# * Title    : CI/CD SSL updater with AWX
# * Auther   : by Alex, Lee
# * Created  : 11-11-2019
# * Modified : 12-20-2019
# * E-mail   : cine0831@gmail.com
#**/

import io
import json
import pycurl
import re
import jsbeautifier
import base64
import sys
from elasticsearch import Elasticsearch
from datetime import datetime

serverlist = []
jsonfile = []
#query = []
header_common = 'Content-type:application/json;charset=utf-8'
header_token_git = 'PRIVATE-TOKEN: xxxxxxxxxxxxxxxxxxxx'
# live.awx.kr
header_token_awx_LIVE = 'Authorization: Bearer xxxxxxxxxxxxxxxxxxxx'
# qa.awx.kr
header_token_awx_QA = 'Authorization: Bearer xxxxxxxxxxxxxxxxxxxx'


def git_get_targetlist():
    buffer_git = io.BytesIO()
    c_git_target = pycurl.Curl()
    url_targetlist = 'https://gitlab.awx.kr/api/v4/projects/43/repository/tree?ref=master&path=json'

    c_git_target.setopt(pycurl.URL, url_targetlist)
    c_git_target.setopt(pycurl.SSL_VERIFYPEER, True)
    c_git_target.setopt(pycurl.HTTPGET, 1)
    c_git_target.setopt(pycurl.HTTPHEADER, [ header_common, header_token_git ])
    c_git_target.setopt(pycurl.WRITEFUNCTION, buffer_git.write)
    c_git_target.perform()
    c_git_target.close()

    body = buffer_git.getvalue()
    temp_json = json.loads(body)
    for i in temp_json:
        if i['name'] != '.gitkeep':
            jsonfile.append(i['name'])

    for i in jsonfile:
        print('1) json filename : %s' % i)
        print('----------------------------------------------')


def git_get_jsonfile(jsonfilename):
    buffer_git = io.BytesIO()
    c_git_get = pycurl.Curl()
    url_getfile = 'https://gitlab.awx.com/api/v4/projects/43/repository/files/json%2F' + jsonfilename + '?ref=master'

    c_git_get.setopt(pycurl.URL, url_getfile)
    c_git_get.setopt(pycurl.SSL_VERIFYPEER, True)
    c_git_get.setopt(pycurl.HTTPGET, 1)
    c_git_get.setopt(pycurl.HTTPHEADER, [ header_common, header_token_git ])
    c_git_get.setopt(pycurl.WRITEFUNCTION, buffer_git.write)
    c_git_get.perform()
    c_git_get.close()

    body = buffer_git.getvalue()
    temp_json = json.loads(body)
    body = base64.b64decode(temp_json['content'])
    query = body.decode('UTF-8', 'strict')

    print('2) json content of %s' % jsonfilename)
    print('%s' % query) 
    print('----------------------------------------------')
    Elastic_get(query)


def git_push_updatelist(jsonfilename):
    buffer_git_push = io.BytesIO()
    c_git_push = pycurl.Curl()
    
    end_of_count = len(serverlist)
    inventory = ''
    cnt = 1

    print('3) serverlist of %s' % jsonfilename)
    for i in serverlist:
        if cnt != end_of_count:
            inventory = inventory + i + "\\n"
            cnt += 1
            print('%s' % i)
        else:
            inventory = inventory + i
            print('%s' % i)

    print('----------------------------------------------')

    data = '{"branch": "master", "author_email": "cine0831@gmail.com", "author_name": "Alex, Lee", "content": "' + inventory + '", "commit_message": "update list"}'
    url_serverlist = 'https://gitlab.awx.kr/api/v4/projects/93/repository/files/awx%2FSSL-update%2FSSL-update_list'

    '''
    print('----')
    print('%s' % data)
    print('----')
    print('%s' % url_serverlist)
    print('----')
    '''

    c_git_push.setopt(pycurl.URL, url_serverlist)
    c_git_push.setopt(pycurl.POSTFIELDS, data)
    c_git_push.setopt(pycurl.CUSTOMREQUEST, 'PUT')
    c_git_push.setopt(pycurl.SSL_VERIFYPEER, False)
    c_git_push.setopt(pycurl.HTTPHEADER, [ header_common, header_token_git ])
    c_git_push.setopt(pycurl.WRITEFUNCTION, buffer_git_push.write)
    c_git_push.perform()
    c_git_push.close()


def awx_launch():
    buffer_awx = io.BytesIO()
    c_awx = pycurl.Curl()
    data = '{"description":"Tower CLI", "application":null, "scope":"write"}'
    url_awx = 'https://live.awx.kr/api/v2/job_templates/1427/launch/'

    # AWX Rest-API call
    c_awx.setopt(c_awx.URL, url_awx)

    # Method Get / Post / Push
    c_awx.setopt(c_awx.POST, True)
    #c_awx.setopt(c_awx.POST, False)
    c_awx.setopt(c_awx.POSTFIELDS, data)
    c_awx.setopt(c_awx.SSL_VERIFYPEER, True)
    #c_awx.setopt(c_awx.SSL_VERIFYHOST, False)
    #c_awx.setopt(pycurl.HTTPGET, 1)
    c_awx.setopt(pycurl.HTTPHEADER, [ header_common, header_token_awx_LIVE ])
    c_awx.setopt(c_awx.WRITEFUNCTION, buffer_awx.write)
    #c_awx.setopt(c_awx.HEADERFUNCTION, header_function)
    c_awx.perform()
    
    http_code = c_awx.getinfo(pycurl.HTTP_CODE)
    #print(http_code)
    
    if http_code is 201:
        body = buffer_awx.getvalue().decode('UTF-8')
        beautify_json = jsbeautifier.beautify(body)
        print(beautify_json)
    
    c_awx.close()


def Elastic_get(query):
    host = "https://elasticsearch-log.awx.kr:9200"
    es = Elasticsearch(host, http_auth=('elastic', 'logtank'), scheme="https", port=9200)
    res = es.search(index="cert_test_log-2019-*", body=query)

    serverlist.append('[SSL_update]')
    for i in res['aggregations']['group_by_hostname']['buckets']:
        serverlist.append(i['key'])


if __name__ == '__main__':
    git_get_targetlist()

    for i in jsonfile:
        git_get_jsonfile(i)
        git_push_updatelist(i)

    awx_launch()
