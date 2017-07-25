#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年12月21日

@author: sanhe
'''
import json
import struct
from dsaur.util import tryException,decimal_default,getRefParamDict,getRefModeParamDict,getRefCondModeParamDict
from dsaur.protocol import protmap
from readconf import local_name
from datetime import datetime


__all__ = ['PackServerFinished','PackServiceState','PackServerState','PackSessionState','PackDataInfo', 
           'PackDevIDChanged', 'PackSessionIDChanged','PackRefParamINIT','PackIPCState','PackGetIPCStream',
           'PackGetIPCHistoryStream','PackVideoServerIPCS']

@tryException
def PackServerFinished(server_name, status):
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['ServerFinished']
    head[3] = 0
    body = {}
    body['server_name'] = server_name
    body['time'] = str(datetime.now())[:19]
    body['local_name'] = local_name
    body['status_code'] = status
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return (head[2],data)

@tryException
def PackServiceState(server_name, service_state, service_time):
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['ServiceState']
    head[3] = 0
    body = {}
    body['server_name'] = server_name
    body['service_state'] = service_state
    body['local_name'] = local_name
    body['status_code'] = 255
    encodedjson = json.dumps(body,ensure_ascii=False)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return (head[2],data)

@tryException
def PackServerState(local_server, server_name, server_state, server_time):
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['ServerState']
    head[3] = 0
    body = {}
    body['server_name'] = local_server
    mem = []
    item = {}
    item['server_name'] = server_name
    item['server_state'] = server_state
    item['time'] = str(server_time)[:19]
    mem.append(item)
    body['member'] = mem
    body['local_name'] = local_name
    body['status_code'] = 255
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return (head[2],data)

@tryException
def PackSessionState(server_name, session_name, state, time):
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['SessionState']
    head[3] = 0
    body = {}
    body['session_name'] = session_name
#     body['session_name'] = 'session_name'
    body['session_state'] = state
    body['server_name'] = server_name
    body['time'] = str(time)[:19]
    body['local_name'] = local_name
    body['status_code'] = 255
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return (head[2],data)

def PackDataInfo(dataitem, dataconf, status):
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['DataInfo']
    head[3] = 0
    body = {}
    body['data_ename'] = dataitem.name
#     if body['data_ename'] == 'KT_WJ_2_16_14':
#         m = 1
    body['data_cname'] = dataconf.get('data_cname')
#     body['data_cname'] = 'data_cname'
    body['value'] = dataitem.value
    body['error_flag'] = dataitem.error_flag
    body['time'] = str(dataitem.time)[:19] if dataitem.time is not None else None
    body['change_flag'] = dataitem.change_flag
    body['dis_flag'] = dataitem.dis_flag
    body['dis_time'] = str(dataitem.dis_time)[:19] if dataitem.dis_time is not None else None
    body['pri'] = dataconf.get('pri')
    body['reason'] = dataitem.encodeReason()
    body['local_name'] = local_name
    body['status_code'] = status
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return (head[2],data)

@tryException
def PackDevIDChanged(session_name, dev_name, dev_id):
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['DeviceIdChanged']
    head[3] = 0
    body = {}
    body['session_name'] = session_name
    body['dev_name'] = dev_name
    body['dev_id'] = dev_id
    body['local_name'] = local_name
    body['status_code'] = 255
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return (head[2],data)
    
@tryException
def PackSessionIDChanged(session_name, session_id):
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['SessionIdChanged']
    head[3] = 0
    body = {}
    body['session_name'] = session_name
    body['session_id'] = session_id
    body['local_name'] = local_name
    body['status_code'] = 255
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return (head[2],data)

def PackRefParamINIT():
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['RefParamINIT']
    head[3] = 0
    body = {}
    body['local_name'] = local_name
    body['status_code'] = 255
    ParamBody = {}
    member = []
    for k,v in getRefParamDict().iteritems():
        item = {}
        item['name'] = k
        item['value'] = v
        member.append(item)
    ParamBody['RefParam'] = member
    member = []
    for k,v in getRefModeParamDict().iteritems():
        item = {}
        item['name'] = k[0]
        item['mode'] = k[1]
        item['value'] = v
        member.append(item)
    ParamBody['RefModeParam'] = member
    member = []
    for k,v in getRefCondModeParamDict().iteritems():
        item = {}
        item['name'] = k[0]
        item['cond'] = k[1]
        item['mode'] = k[2]
        item['value'] = v
        member.append(item)
    ParamBody['RefCondModeParam'] = member
    body['ParamBody'] = ParamBody
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return data

@tryException
def PackIPCState(server_name, status, ipc_name, ipc_state, updatetime):
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['IPCState']
    head[3] = 0
    body = {}
    body['ipc_name'] = ipc_name
    body['ipc_state'] = ipc_state
    if type(updatetime) == type(datetime.now()):
        body['updatetime'] = updatetime.strftime('%Y-%m-%d %H:%M:%S')
    else:
        body['updatetime'] = updatetime
    body['server_name'] = server_name
    body['local_name'] = local_name
    body['status_code'] = status
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return (head[2],data)

@tryException
def PackGetIPCStream(server_name, ipc_name):
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['GetIPCStream']
    head[3] = 0
    body = {}
    body['ipc_name'] = ipc_name
    body['server_name'] = server_name
    body['local_name'] = local_name
    body['status_code'] = 2
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return data

@tryException
def PackGetIPCHistoryStream(server_name, ipc_name):
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['GetIPCHistoryStream']
    head[3] = 0
    body = {}
    body['ipc_name'] = ipc_name
    body['server_name'] = server_name
    body['local_name'] = local_name
    body['status_code'] = 1
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return data

def PackVideoServerIPCS(server_name):
    head = range(4)
    head[0] = 1
    head[1] = 0
    head[2] = protmap['VideoServerIPCS']
    head[3] = 0
    body = {}
    video_servers = []
    item = {}
    item['server_name'] = server_name
    video_servers.append(item)
    body['video_servers'] = video_servers
    body['local_name'] = local_name
    body['status_code'] = 1
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    return data