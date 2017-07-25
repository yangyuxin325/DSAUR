#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年12月22日

@author: sanhe
'''
import json
import struct
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from readconf import getSqlUrl,local_name,video_port
import copy
from dsaur.models import *
from dsaur.util import tryException,decimal_default,def_refparam,def_refmodeparam,def_refcondmodeparam
from dsaur.protocol import protmap,protdrivemap
from packProtocol import PackSessionState, PackDataInfo, PackIPCState
import threading

doMesssages = {}

def def_protmsg(prot, handle):
    if prot in protmap:
        doMesssages[protmap[prot]] = handle
    else:
        pass
    
def doServerParam(server, sockSession, head, body):
#     print 'doServerParam, ' ,body
    head = list(head)
    member = body['member']
    status_code = body['status_code']
    body['local_name'] = local_name
    if len(member) == 0 and status_code == 1:
        if sockSession.addr[1] <> int(video_port):
            sockSession.uploadFlag = False
            server.preuser_dict.pop(id(sockSession))
            server.user_dict[sockSession.addr[0]] = sockSession
            member = []
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            for sv in dbsesson.query(ServerInfo).all():
                item = {}
                item['server_name'] = sv.name
                item['server_cname'] = sv.cname
                item['server_type'] = sv.type
                item['server_ip'] = sv.ip
                item['ipc_name'] = sv.ipc_name
                item['pri'] = sv.pri
                member.append(item)
            dbsesson.close()
            body['member'] = member
            body['status_code'] = 2
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
            sockSession.echoProtSet.update(protdrivemap.get(head[2],set()))
        else:
            member = []
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            sv = dbsesson.query(ServerInfo).filter_by(ip=server.host).one_or_none()
            if sv is not None:
                item = {}
                item['server_name'] = sv.name
                item['server_cname'] = sv.cname
                item['server_type'] = sv.type
                item['server_ip'] = sv.ip
                item['ipc_name'] = sv.ipc_name
                item['pri'] = sv.pri
                member.append(item)
            dbsesson.close()
            body['member'] = member
            body['status_code'] = 2
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
#         print sockSession.addr[0], body
    elif status_code == 1:
        if len(member) == 1:
            server_type = member[0]['server_type']
            server_ip = member[0]['server_ip']
            if server_type == 'video':
                if server_ip in server.videosv_dict:
                    engine = create_engine(getSqlUrl(),echo=False)
                    DBSession = sessionmaker(bind=engine)
                    dbsesson = DBSession()
                    sv = dbsesson.query(ServerInfo).filter_by(ip=server_ip).one_or_none()
                    if sv is not None:
                        item = {}
                        member[0]['server_name'] = sv.name
                        member[0]['server_cname'] = sv.cname
                        member[0]['server_type'] = sv.type
                        member[0]['ipc_name'] = sv.ipc_name
                        member[0]['pri'] = sv.pri
                    dbsesson.close()
                    body['member'] = member
                    body['status_code'] = 2
                    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                    head[3] = len(encodedjson.encode('utf-8'))
                    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                    sockSession.sendData(data)
            else:
                pass
        else:
            pass
    else:
        pass
    
def doServicesState(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    server_name = body['server_name']
    if server_name == server.server_name:
        body['service_state'] = server.init_flag
#         body['service_state'] = True
        body['status_code'] = 2
    else:
        body['service_state'] = False
        body['status_code'] = 3
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    sockSession.sendData(data)
    
def doServerState(server, sockSession, head, body):
    body['local_name'] = local_name
#     print id(sockSession), 'doServerState: ', body, sockSession.addr
    head = list(head)
    member = body['member']
    server_name = body['server_name']
    if body['status_code'] == 1:
        if server_name == server.server_name:
            item = {}
            item['server_name'] = server.server_name
            item['server_state'] = server.init_flag
            item['time'] = str(server.init_time)[:19] if server.init_time is not None else None
            item['flag'] = 0
            member.append(item)
            for sv in server.subsv_dict.values():
                item = {}
                item['server_name'] = sv.server_name
                item['server_state'] = sv.state
                item['time'] = str(sv.statetime)[:19] if sv.statetime is not None else None
                item['flag'] = 0
                member.append(item)
            for sv in server.videosv_dict.values():
                item = {}
                item['server_name'] = sv.server_name
                item['server_state'] = sv.state
                item['time'] = str(sv.statetime)[:19] if sv.statetime is not None else None
                item['flag'] = 2
                member.append(item)
            if server.superserver is not None:
                item = {}
                item['server_name'] = server.superserver.server_name
                item['server_state'] = server.superserver.state
                item['time'] = str(server.superserver.statetime)[:19] if server.superserver.statetime is not None else None
                item['flag'] = 1
                member.append(item)
        body['member'] = member
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
    elif body['status_code'] == 255:
        if server_name not in server.subnameip_dict:
            item = member[0]
            server_name = item['server_name']
            state = item['server_state']
            statetime = datetime.strptime(item['time'],'%Y-%m-%d %H:%M:%S')
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            dbsesson.query(ServerInfo).filter(ServerInfo.name==server_name).update({ServerInfo.state : state,
                                                                                    ServerInfo.updatetime : statetime})
            dbsesson.close()
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            server.sendClients((head[2], data))
            server.reportData((head[2],data))
    else:
        pass
    
def doVideoServerIPCS(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
#     print id(sockSession), 'doVideoServerIPCS: ', body
    if body['status_code'] == 1:
        video_servers = body['video_servers']
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        for video_server in video_servers:
            server_name = video_server['server_name']
            member = []
            if server_name in server.videonameip_dict:
                for ipc_name, sv_name in server.ipcvideo_dict.iteritems():
                    if sv_name == server_name:
                        ipcinfo = dbsesson.query(IPCInfo).filter_by(name=ipc_name).one_or_none()
                        if ipcinfo is not None:
                            item = {}
                            item['name'] = ipcinfo.name
                            item['cname'] = ipcinfo.cname
                            item['ip'] = ipcinfo.ip
                            item['rtsp_type'] = ipcinfo.rtsp_type
                            item['fps'] = ipcinfo.fps
                            item['resolution'] = ipcinfo.resolution
                            item['streamsize'] = ipcinfo.streamsize
                            item['state'] = ipcinfo.state
                            item['time'] = str(ipcinfo.updatetime)[:19] if ipcinfo.updatetime is not None else None
                            member.append(item)
                video_server['member']=member
                serverinfo = dbsesson.query(ServerInfo).filter_by(name=server_name).one_or_none()
                video_server['savedays'] = serverinfo.savedays
            elif server_name == server.server_name:
                if server.streamService is not None:
                    for ipc_name in server.streamService.ipc_dict.keys():
                        ipcinfo = dbsesson.query(IPCInfo).filter_by(name=ipc_name).one_or_none()
                        if ipcinfo is not None:
                            item = {}
                            item['name'] = ipcinfo.name
                            item['cname'] = ipcinfo.cname
                            item['ip'] = ipcinfo.ip
                            item['rtsp_type'] = ipcinfo.rtsp_type
                            item['fps'] = ipcinfo.fps
                            item['resolution'] = ipcinfo.resolution
                            item['streamsize'] = ipcinfo.streamsize
                            item['state'] = ipcinfo.state
                            item['time'] = str(ipcinfo.updatetime)[:19] if ipcinfo.updatetime is not None else None
                            member.append(item)
                    video_server['member']=member
                serverinfo = dbsesson.query(ServerInfo).filter_by(name=server_name).one_or_none()
                video_server['savedays'] = serverinfo.savedays
        dbsesson.close()
        body['video_servers'] = video_servers
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
        if sockSession.addr[0] in server.user_dict:
            sockSession.echoProtSet.update(protdrivemap.get(head[2],set()))
        else:
            pass
    elif body['status_code'] == 2:
        video_servers = body['video_servers']
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        for sv in video_servers:
            server_name = sv['server_name']
            for item in sv['member']:
                ipc_name = item['name']
                ipc_state = item['state']
                updatetime = item['time']
                dbsesson.query(IPCInfo).filter(IPCInfo.name==ipc_name).update({IPCInfo.state : ipc_state,
                                                                       IPCInfo.updatetime : updatetime})
                dbsesson.commit()
                server.sendClients(PackIPCState(server_name,255,ipc_name,ipc_state,updatetime))
        dbsesson.close()
    
def doNodeUnitMap(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 1:
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        member = []
        for node_unit in dbsesson.query(NodeUnitMap).all():
            item = {}
            item['node_name'] = node_unit.node_name
            item['unit_name'] = node_unit.unit_name
            member.append(item)
        body['member'] = member
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
        dbsesson.close()
    else:
        pass
    
def doDeviceTypes(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 1:
        member = []
        from dsaur.mydevice import device_Dict
        for dev_type,description in device_Dict.iteritems():
            item = {}
            item['dev_type'] = dev_type
            item['description'] = description
            member.append(item)
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
    else:
        pass
    
def doSessionTypes(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 1:
        member = []
        from dsaur.mydevice import sesstype_Dict
        for session_type,description in sesstype_Dict.iteritems():
            item = {}
            item['session_type'] = session_type
            item['description'] = description
            member.append(item)
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
    else:
        pass
    
def doSessions(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 1:
        server_sessions = body['server_sessions']
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        for server_session in server_sessions:
            server_name = server_session['server_name']
            if server_name in server.subnameip_dict or server_name == server.server_name:
                member = []
                for sessioninfo in dbsesson.query(SessionInfo).filter_by(server_name=server_name).all():
                    item = {}
                    item['session_name'] = sessioninfo.name
                    item['session_cname'] = sessioninfo.cname
                    item['session_id'] = sessioninfo.id
                    item['session_type'] = sessioninfo.type
                    item['ipc_name'] = sessioninfo.ipc_name
                    item['pri'] = sessioninfo.pri
                    item['session_state'] = sessioninfo.state
                    item['time'] = str(sessioninfo.updatetime)[:19] if sessioninfo.updatetime is not None else None
                    member.append(item)
                server_session['member'] = member
            else:
                pass
        dbsesson.close()
        body['server_sessions'] = server_sessions
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
        sockSession.echoProtSet.update(protdrivemap.get(head[2],set()))
    else:
        pass
    
def doDevices(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 1:
        session_name = body['session_name']
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        member = []
        sessinfo = dbsesson.query(SessionInfo).filter_by(name=session_name).one_or_none()
        if sessinfo is not None:
            for deviceinfo in sessinfo.devices:
                item = {}
                item['dev_name'] = deviceinfo.name
                item['dev_cname'] = deviceinfo.cname
                item['dev_type'] = deviceinfo.type
                item['dev_id'] = deviceinfo.id
                if deviceinfo.area is not None:
                    item['area_flag'] = True
                    item['area_id'] = deviceinfo.area.id
                    item['area_name'] = deviceinfo.area.name
                else:
                    item['area_flag'] = False
                member.append(item)
        else:
            pass
        dbsesson.close()
        body['member'] = member
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
        sockSession.echoProtSet.update(protdrivemap.get(head[2],set()))
    else:
        pass
    
def doDeviceDataItems(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 1:
        dev_name = body['dev_name']
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        member = []
        for devdatatype in dbsesson.query(DevDataType).filter_by(dev_name=dev_name).all():
            name = devdatatype.name
            dataitem = server.data_dict.get(name)
            if dataitem is None:
                continue
            dataconf = server.dataconf_dict.get(name)
            item = {}
            item['data_ename'] = dataitem.name
            item['data_cname'] = devdatatype.data.cname
            item['conf_name'] = dataconf.get('conf_name')
            item['algorithm'] = devdatatype.algorithm
            item['min_variation'] = devdatatype.data.min_variation
            item['min_val'] = devdatatype.data.min_val
            item['max_val'] = devdatatype.data.max_val
            item['dis_interval'] = dataconf.get('dis_interval')
            item['value'] = dataitem.value
            item['error_flag'] = dataitem.error_flag
            item['time'] = str(dataitem.time)[:19] if dataitem.time is not None else None
            item['change_flag'] = dataitem.change_flag
            item['dis_flag'] = dataitem.dis_flag
            item['dis_time'] = str(dataitem.dis_time)[:19] if dataitem.dis_time is not None else None
            item['ipc_array'] = dataconf.get('ipcs') 
            item['pri'] = dataconf.get('pri')
            item['start_sec'] = dataconf.get('start_sec')
            item['end_sec'] = dataconf.get('end_sec')
            item['reason'] = dataitem.encodeReason()
            member.append(item)
        body['member'] = member
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
        dbsesson.close()
    else:
        pass
    
def doServerDataTypes(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 1:
        server_name = body['server_name']
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        data_types = []
        for item in dbsesson.query(UDevDataType.type).filter_by(server_name=server_name).group_by(UDevDataType.type).all():
            data_types.append(item[0])
        dbsesson.close()
        body['data_types'] = data_types
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
    else:
        pass
    
def doUDevDataItems(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 1:
        server_name = body['server_name']
        data_type = body['data_type']
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        member = []
        for udevdatatype in dbsesson.query(UDevDataType).filter_by(server_name=server_name,type=data_type).all():
            name = udevdatatype.name
            dataitem = server.data_dict.get(name)
            if dataitem is None:
                continue
            dataconf = server.dataconf_dict.get(name)
            item = {}
            item['data_ename'] = dataitem.name
            item['data_cname'] = udevdatatype.data.cname
            item['min_variation'] = udevdatatype.data.min_variation
            item['min_val'] = udevdatatype.data.min_val
            item['max_val'] = udevdatatype.data.max_val
            item['dis_interval'] = dataconf.get('dis_interval')
            item['value'] = dataitem.value
            item['error_flag'] = dataitem.error_flag
            item['time'] = str(dataitem.time)[:19] if dataitem.time is not None else None
            item['change_flag'] = dataitem.change_flag
            item['dis_flag'] = dataitem.dis_flag
            item['dis_time'] = str(dataitem.dis_time)[:19] if dataitem.dis_time is not None else None
            item['ipc_array'] = dataconf.get('ipcs') 
            item['pri'] = dataconf.get('pri')
            item['start_sec'] = dataconf.get('start_sec')
            item['end_sec'] = dataconf.get('end_sec')
            item['reason'] = dataitem.encodeReason()
            member.append(item)
        dbsesson.close()
        body['member'] = member
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
    else:
        pass
    
def doPeriodDataItems(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 1:
        period_sessions = body['period_sessions']
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        for period_session in period_sessions:
            session_name = period_session['session_name']
            perioddatatype = dbsesson.query(PeriodDataType).filter_by(session_name=session_name).one_or_none()
            if perioddatatype is not None:
                name = perioddatatype.name
                dataitem = server.data_dict.get(name)
                if dataitem is None:
                    continue
                dataconf = server.dataconf_dict.get(name)
                item = {}
                item['data_ename'] = dataitem.name
                item['data_cname'] = perioddatatype.data.cname
                item['min_variation'] = perioddatatype.data.min_variation
                item['min_val'] = perioddatatype.data.min_val
                item['max_val'] = perioddatatype.data.max_val
                item['dis_interval'] = dataconf.get('dis_interval')
                item['value'] = dataitem.value
                item['error_flag'] = dataitem.error_flag
                item['time'] = str(dataitem.time)[:19] if dataitem.time is not None else None
                item['change_flag'] = dataitem.change_flag
                item['dis_flag'] = dataitem.dis_flag
                item['dis_time'] = str(dataitem.dis_time)[:19] if dataitem.dis_time is not None else None
                item['ipc_array'] = dataconf.get('ipcs') 
                item['pri'] = dataconf.get('pri')
                item['start_sec'] = dataconf.get('start_sec')
                item['end_sec'] = dataconf.get('end_sec')
                item['reason'] = dataitem.encodeReason()
                period_session['dataitem'] = item
            else:
                pass
        dbsesson.close()
        body['period_sessions'] = period_sessions
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
        sockSession.echoProtSet.update(protdrivemap.get(head[2],set()))
    else:
        pass
    
def doMachineDataItems(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 1:
        server_name = body['server_name']
        member = []
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        for mepdatatype in dbsesson.query(MepDataType).filter_by(server_name=server_name).all():
            name = mepdatatype.name
            dataitem = server.data_dict.get(name)
            if dataitem is None:
                continue
            dataconf = server.dataconf_dict.get(name)
            item = {}
            item['data_ename'] = dataitem.name
            item['data_cname'] = mepdatatype.data.cname
            item['mep'] = mepdatatype.mep_name
            item['min_variation'] = mepdatatype.data.min_variation
            item['min_val'] = mepdatatype.data.min_val
            item['max_val'] = mepdatatype.data.max_val
            item['dis_interval'] = dataconf.get('dis_interval')
            item['value'] = dataitem.value
            item['error_flag'] = dataitem.error_flag
            item['time'] = str(dataitem.time)[:19] if dataitem.time is not None else None
            item['change_flag'] = dataitem.change_flag
            item['dis_flag'] = dataitem.dis_flag
            item['dis_time'] = str(dataitem.dis_time)[:19] if dataitem.dis_time is not None else None
            item['ipc_array'] = dataconf.get('ipcs') 
            item['pri'] = dataconf.get('pri')
            item['start_sec'] = dataconf.get('start_sec')
            item['end_sec'] = dataconf.get('end_sec')
            item['reason'] = dataitem.encodeReason()
            member.append(item)
        dbsesson.close()
        body['member'] = member
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
    else:
        pass
    
def doTransmitDataItems(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 1:
        server_name = body['server_name']
        if server.superserver is not None and server_name == server.server_name:
            member = []
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            for transmitdata in dbsesson.query(TransmitData).filter_by(server_name=server_name).all():
                name = transmitdata.data_name
                datainfo = transmitdata.data
                dataitem = server.data_dict.get(name)
                if dataitem is None:
                    continue
                dataconf = server.dataconf_dict.get(name)
                item = {}
                item['data_ename'] = dataitem.name
                item['data_cname'] = datainfo.cname
                item['min_variation'] = datainfo.min_variation
                item['min_val'] = datainfo.min_val
                item['max_val'] = datainfo.max_val
                item['dis_interval'] = dataconf.get('dis_interval')
                item['value'] = dataitem.value
                item['error_flag'] = dataitem.error_flag
                item['time'] = str(dataitem.time)[:19] if dataitem.time is not None else None
                item['change_flag'] = dataitem.change_flag
                item['dis_flag'] = dataitem.dis_flag
                item['dis_time'] = str(dataitem.dis_time)[:19] if dataitem.dis_time is not None else None
                item['ipc_array'] = dataconf.get('ipcs') 
                item['pri'] = dataconf.get('pri')
                item['start_sec'] = dataconf.get('start_sec')
                item['end_sec'] = dataconf.get('end_sec')
                item['reason'] = dataitem.encodeReason()
                item['attribute'] = datainfo.attribute
                item['server_name'] = dataconf.get('server_name')
                if datainfo.attribute == 1:
                    item['dev_name'] = dataconf.get('dev_name')
                    item['conf_name'] = dataconf.get('conf_name')
                    item['session_name'] = dataconf.get('session_name')
                elif datainfo.attribute == 2:
                    item['data_type'] = dataconf.get('type')
                elif datainfo.attribute == 3:
                    item['mep'] = dataconf.get('mep')
                elif datainfo.attribute == 4:
                    item['session_name'] = dataconf.get('session_name')
                member.append(item)
            dbsesson.close()
            body['member'] = member
        else:
            pass
        body['status_code'] = 2
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
        sockSession.echoProtSet.update(protdrivemap.get(head[2],set()))
    else:
        pass
    
def doRefParamInfo(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        server_name = body['server_name']
        if server.server_name == server_name:
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            member = []
            for refparam in dbsesson.query(RefParamInfo).all():
                item = {}
                item['name'] = refparam.name
                item['cname'] = refparam.cname
                item['value'] = refparam.value
                item['updatetime'] = str(refparam.updatetime)[:19] if refparam.updatetime is not None else None
                member.append(item)
            dbsesson.close()
            body['member'] = member
            body['status_code'] = 2
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
        else:
            if server_name in server.subnameip_dict:
                ip = server.subnameip_dict[server_name]
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                if server.subsv_dict[ip].sendData((head[2],data)):
                    body['status_code'] = 4
                else:
                    body['status_code'] = 5
            else:
                body['status_code'] = 5
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)

def doRefModeParamInfo(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        server_name = body['server_name']
        if server.server_name == server_name:
            member = []
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            for refparam in dbsesson.query(RefModeParamInfo).all():
                item = {}
                item['name'] = refparam.name
                item['cname'] = refparam.cname
                item['mode'] = refparam.mode
                item['value'] = refparam.value
                item['updatetime'] = str(refparam.updatetime)[:19] if refparam.updatetime is not None else None
                member.append(item)
            dbsesson.close()
            body['member'] = member
            body['status_code'] = 2
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
        else:
            if server_name in server.subnameip_dict:
                ip = server.subnameip_dict[server_name]
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                if server.subsv_dict[ip].sendData((head[2],data)):
                    body['status_code'] = 4
                else:
                    body['status_code'] = 5
            else:
                body['status_code'] = 5
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
                        
def doRefCondModeParamInfo(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        server_name = body['server_name']
        if server.server_name == server_name:
            member = []
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            for refparam in dbsesson.query(RefCondModeParamInfo).all():
                item = {}
                item['name'] = refparam.name
                item['cname'] = refparam.cname
                item['cond'] = refparam.cond
                item['mode'] = refparam.mode
                item['value'] = refparam.value
                item['updatetime'] = str(refparam.updatetime)[:19] if refparam.updatetime is not None else None
                member.append(item)
            dbsesson.close()
            body['member'] = member
            body['status_code'] = 2
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
        else:
            if server_name in server.subnameip_dict:
                ip = server.subnameip_dict[server_name]
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                if server.subsv_dict[ip].sendData((head[2],data)):
                    body['status_code'] = 4
                else:
                    body['status_code'] = 5
            else:
                body['status_code'] = 5
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
        
def sendInitData(server, sockSession):
    if sockSession.connected:
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        for sessioninfo in dbsesson.query(SessionInfo).filter_by(server_name=server.server_name).all():
            packdata = PackSessionState(server.server_name,sessioninfo.name,sessioninfo.state, sessioninfo.updatetime)
            sockSession.sendData(packdata[1])
        for sv in server.subsv_dict.values():
            for sessioninfo in dbsesson.query(SessionInfo).filter_by(server_name=sv.server_name).all():
                packdata = PackSessionState(server.server_name,sessioninfo.name,sessioninfo.state, sessioninfo.updatetime)
                sockSession.sendData(packdata[1])
        sockSession.dataSet = set(server.data_dict.keys())
        while sockSession.connected and len(sockSession.dataSet) > 0:
            name = sockSession.dataSet.pop()
            dataconf = server.dataconf_dict[name]
            dataitem = server.data_dict[name]
            packdata = PackDataInfo(dataitem,dataconf,999)
#             time.sleep(0.001)
            sockSession.sendData(packdata[1])
            
#         while sockSession.connected:
#             for name, dataitem in server.data_dict.items():
#                 dataconf = server.dataconf_dict[name]
#                 dataitem = server.data_dict[name]
#                 packdata = PackDataInfo(dataitem,dataconf,999)
#                 time.sleep(0.001)
#                 sockSession.sendData(packdata[1])
#                 sockSession.sendData(struct.pack('!4i', 1, 0, 0, 0))
                
#             time.sleep(0.1)
#         time.sleep(3)
    print 'sendInitData Over!'

        
def doInitFinished(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 255:
        sockSession.uploadFlag = True
    elif body['status_code'] == 1:
        sockSession.uploadFlag = True
        threading.Thread(target=sendInitData,args=(server, sockSession)).start()
    else:
        pass
    
# 多条协议确认
def doItemsFinished(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    if body['status_code'] == 255:
        sockSession.echoProtSet.update(protdrivemap.get(head[2],set()))
    else:
        pass
    
def doSessionState(server, sockSession, head, body):
    body['local_name'] = local_name
#     print 'doSessionState: ', body
    head = list(head)
    if body['status_code'] == 255:
        session_name = body['session_name']
        state = body['session_state']
        statetime  = datetime.strptime(body['time'],'%Y-%m-%d %H:%M:%S')
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        dbsesson.query(SessionInfo).filter(SessionInfo.name==session_name).update({SessionInfo.state : state,
                                                                                   SessionInfo.updatetime : statetime})
        dbsesson.commit()
        dbsesson.close()
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        server.reportData((head[1],data))
        server.sendClients((head[1],data))
    else:
        pass
    
@tryException
def doDataInfo(server, sockSession, head, body):
    body['local_name'] = local_name
#     print 'doDataInfo: ', body, sockSession.addr
    head = list(head)
#     status_code = body['status_code']
    name = body['data_ename']
    value = body['value']
    error_flag = body['error_flag']
    time = datetime.strptime(body['time'],'%Y-%m-%d %H:%M:%S') if body['time'] is not None else None
    dis_flag = body['dis_flag']
    dis_time = datetime.strptime(body['dis_time'],'%Y-%m-%d %H:%M:%S') if body['dis_time'] is not None else None
    change_flag = body['change_flag']
    reason = copy.deepcopy(body['reason'])
    if reason is not None and reason['rs_type'] == 1:
        if reason['rs_time'] is not None:
            reason['rs_time'] = datetime.strptime(reason['rs_time'],'%Y-%m-%d %H:%M:%S')
    body['status_code'] = 255
    if name in server.data_dict:
        from dsaur.basedata import dataObj
        obj = dataObj(name,value,error_flag,time,dis_flag,dis_time,change_flag,reason)
#         print server.data_dict[name]
        server.data_dict[name].setData(obj)
        server.putCacheData(name)
    else:
        pass
    
def doYHDataUpdate(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    print 'doYHDataUpdate: ', body
    status_code = body['status_code']
    if status_code == 1:
        name = body['data_ename']
        value = body['value']
        mac = body['mac']
        if name in server.dataconf_dict:
            #有效数据
            server_name = server.dataconf_dict[name].get('server_name')
            if server.server_name == server_name:
                
                if server.setDataValue(name,float(value)):
                    data_reason = {'rs_type' : 3,
                                   'rs_user' : mac}
                    server.setDataReason(name,data_reason)
                    server.putCacheData(name)
                    body['status_code'] = 2
                else:
                    body['status_code'] = 3
                print server_name, name, value, body['status_code'], datetime.now()
                    #修改值与原值相同
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                sockSession.sendData(data)
            else:
                pass
                #发送给其他服务器
                if server_name in server.subnameip_dict:
                    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                    head[3] = len(encodedjson.encode('utf-8'))
                    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                    ip = server.subnameip_dict[server_name]
                    if server.subsv_dict[ip].passonData((head[2],data)):
                        body['status_code'] = 4
                    else:
                        body['status_code'] = 5
                else:
                    body['status_code'] = 5
                print server_name, name, value, body['status_code']
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                sockSession.sendData(data)
        else:
            body['status_code'] = 6
            print server_name, name, value, body['status_code']
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
            #无效数据
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        server.sendClients((head[2], data))
        
def doSessionIdChanged(server, sockSession, head, body):
    body['local_name'] = local_name
    print 'doSessionIdChanged: ', body
    head = list(head)
    status_code = body['status_code']
    session_name = body['session_name']
    session_id = body['session_id']
    engine = create_engine(getSqlUrl(),echo=False)
    DBSession = sessionmaker(bind=engine)
    dbsesson = DBSession()
    sessioninfo = dbsesson.query(SessionInfo).filter_by(name=session_name).one_or_none()
    if status_code == 1:
        if server.server_name == sessioninfo.server_name:
            if server.collector.updateSessionID(session_name, session_id):
                body['status_code'] = 2
            else:
                body['status_code'] = 3
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
        else:
            if sessioninfo.server_name in server.subnameip_dict:
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                ip = server.subnameip_dict[sessioninfo.server_name]
                if server.subsv_dict[ip].passonData((head[2],data)):
                    body['status_code'] = 4
                else:
                    body['status_code'] = 5
            else:
                body['status_code'] = 5
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sessioninfo.id = session_id
        dbsesson.commit()
        server.sendClients((head[2],data))
    dbsesson.close()
            
def doSessionConfChanged(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    session_name = body['session_name']
    ipc_name = body['ipc_name']
    pri = body['pri']
    if status_code == 1:
        server_name = body['server_name']
        if server.server_name == server_name:
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            sessioninfo = dbsesson.query(SessionInfo).filter_by(name=session_name).one_or_none()
            if sessioninfo is not None and (sessioninfo.ipc_name <> ipc_name or sessioninfo.pri <> pri):
                sessioninfo.ipc_name = ipc_name
                sessioninfo.pri = pri
                dbsesson.commit()
                body['status_code'] = 2
            else:
                body['status_code'] = 3
            dbsesson.close()
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            server.reportData((head[2],data))
            if body['status_code'] == 2:
                server.reportData((head[2],data))
                server.sendClients((head[2],data))
            else:
                sockSession.sendData(data)
        else:
            if server_name in server.subnameip_dict:
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                ip = server.subnameip_dict[server_name]
                if server.subsv_dict[ip].passonData((head[2],data)):
                    body['status_code'] = 4
                else:
                    body['status_code'] = 5
            else:
                body['status_code'] = 5
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        if status_code == 2:
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            dbsesson.execute("update sessioninfo set ipc_name = %s, pri = %d where name = '%s'" % (ipc_name, pri, session_name))
            dbsesson.close()
        server.sendClients((head[2],data))
            
def doDeviceIdChanged(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    dev_name = body['dev_name']
    engine = create_engine(getSqlUrl(),echo=False)
    DBSession = sessionmaker(bind=engine)
    dbsesson = DBSession()
    devinfo = dbsesson.query(DeviceInfo).filter_by(name=dev_name).one_or_none()
    if status_code == 1:
        server_name = devinfo.session.server_name
        if server.server_name == server_name:
            session_name = devinfo.session_name
            dev_id = body['dev_id']
            if server.collector.updateDevID(session_name,dev_name,dev_id):
                body['status_code'] = 2
            else:
                body['status_code'] = 3
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
        else:
            if server_name in server.subnameip_dict:
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                ip = server.subnameip_dict[server_name]
                if server.subsv_dict[ip].passonData((head[2],data)):
                    body['status_code'] = 4
                else:
                    body['status_code'] = 5
            else:
                body['status_code'] = 5
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        devinfo.id = body['dev_id']
        dbsesson.commit()
        server.sendClients((head[2],data))
    dbsesson.close()
            
def doDataConfInfo(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        name = body['data_ename']
        if name in server.dataconf_dict:
            server_name = server.dataconf_dict[name].get('server_name')
            if server.server_name == server_name:
                data_name = body['data_ename']
                from UserDict import UserDict
                dataconstraint = UserDict()
                dataconstraint['min_variation'] = body['min_variation']
                dataconstraint['min_val'] = body['min_val']
                dataconstraint['max_val'] = body['max_val']
                if server.updateDataConf(data_name,dataconstraint):
                    body['status_code'] = 2
                    engine = create_engine(getSqlUrl(),echo=False)
                    DBSession = sessionmaker(bind=engine)
                    dbsesson = DBSession()
                    datainfo = dbsesson.query(DataInfo).filter_by(name=data_name).one_or_none()
                    if datainfo is not None:
                        datainfo.min_variation = body['min_variation']
                        datainfo.min_val = body['min_val']
                        datainfo.max_val = body['max_val']
                    dbsesson.commit()
                    dbsesson.close()
                else:
                    body['status_code'] = 3
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                if body['status_code'] == 2:
                    server.reportData((head[2],data))
                    server.sendClients((head[2],data))
                else:
                    sockSession.sendData(data)
            else:
                if server_name in server.subnameip_dict:
                    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                    head[3] = len(encodedjson.encode('utf-8'))
                    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                    ip = server.subnameip_dict[server_name]
                    if server.subsv_dict[ip].passonData((head[2],data)):
                        body['status_code'] = 4
                    else:
                        body['status_code'] = 5
                else:
                    body['status_code'] = 5
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                sockSession.sendData(data)
        else:
            body['status_code'] = 6
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
            #无效数据
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        if body['status_code'] == 2:
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            datainfo = dbsesson.query(DataInfo).filter_by(name=body['data_ename']).one_or_none()
            if datainfo is not None:
                datainfo.min_variation = body['min_variation']
                datainfo.min_val = body['min_val']
                datainfo.max_val = body['max_val']
                dbsesson.commit()
            dbsesson.close()
        server.sendClients((head[2],data))
            
def doDataPriChange(server, sockSession, head, body):
    body['local_name'] = local_name            
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        name = body['data_ename']
        pri = body['pri']
        if name in server.dataconf_dict:
            #有效数据
            server_name = server.dataconf_dict[name].get('server_name')
            if server.server_name == server_name:
                if server.dataconf_dict[name]['pri'] <> pri:
                    server.dataconf_dict[name]['pri'] = pri
                    body['status_code'] = 2
                    engine = create_engine(getSqlUrl(),echo=False)
                    DBSession = sessionmaker(bind=engine)
                    dbsesson = DBSession()
                    dbsesson.execute("update datainfo set pri = %d where name = '%s'" % (body['pri'],body['data_ename']))
                    dbsesson.commit()
                    dbsesson.close()
                else:
                    body['status_code'] = 3
                    #修改值与原值相同
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                if body['status_code'] == 2:
                    server.reportData((head[2],data))
                    server.sendClients((head[2],data))
                else:
                    sockSession.sendData(data)
            else:
                pass
                #发送给其他服务器
                if server_name in server.subnameip_dict:
                    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                    head[3] = len(encodedjson.encode('utf-8'))
                    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                    ip = server.subnameip_dict[server_name]
                    if server.subsv_dict[ip].passonData((head[2],data)):
                        body['status_code'] = 4
                    else:
                        body['status_code'] = 5
                else:
                    body['status_code'] = 5
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                sockSession.sendData(data)
        else:
            body['status_code'] = 6
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
            #无效数据
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        if body['status_code'] == 2:
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            dbsesson.execute("update datainfo set pri = %d where name = '%s'" % (body['pri'],body['data_ename']))
            dbsesson.commit()
            dbsesson.close()
        server.sendClients((head[2],data))
            
def doDataIPCSChange(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        name = body['data_ename']
        ipc_array = body['ipc_array']
        ipc_array.sort()
        if name in server.dataconf_dict:
            #有效数据
            server_name = server.dataconf_dict[name].get('server_name')
            if server.server_name == server_name:
                ipcs = server.dataconf_dict[name]['ipcs'].sort()
                if ipcs <> ipc_array:
                    server.dataconf_dict[name]['ipcs'] = ipc_array
                    body['status_code'] = 2
                    engine = create_engine(getSqlUrl(),echo=False)
                    DBSession = sessionmaker(bind=engine)
                    dbsesson = DBSession()
                    dbsesson.query(DataIPCInfo).filter_by(name=body['data_ename']).delete()
                    for ipc_name in ipc_array:
                        dbsesson.add(DataIPCInfo(body['data_ename'],ipc_name,datetime.now()))
                    dbsesson.commit()
                    dbsesson.close()
                else:
                    body['status_code'] = 3
                    #修改值与原值相同
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                if body['status_code'] == 2:
                    server.reportData((head[2],data))
                    server.sendClients((head[2],data))
                else:
                    sockSession.sendData(data)
            else:
                #发送给其他服务器
                if server_name in server.subnameip_dict:
                    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                    head[3] = len(encodedjson.encode('utf-8'))
                    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                    ip = server.subnameip_dict[server_name]
                    if server.subsv_dict[ip].passonData((head[2],data)):
                        body['status_code'] = 4
                    else:
                        body['status_code'] = 5
                else:
                    body['status_code'] = 5
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                sockSession.sendData(data)
        else:
            body['status_code'] = 6
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
            #无效数据
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        if body['status_code'] == 2:
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            dbsesson.query(DataIPCInfo).filter_by(name=body['data_ename']).delete()
            for ipc_name in ipc_array:
                dbsesson.add(DataIPCInfo(body['data_ename'],ipc_name,datetime.now()))
            dbsesson.commit()
            dbsesson.close()
        server.sendClients((head[2],data))
            
def doServerConfChange(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        server_name = body['server_name']
        if server.server_name == server_name:
            ipc_name = body['ipc_name']
            pri = body['pri']
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            serverinfo = dbsesson.query(SessionInfo).filter_by(name=server_name).one_or_none()
            if serverinfo is not None and (serverinfo.ipc_name <> ipc_name or serverinfo.pri <> pri):
                serverinfo.ipc_name = ipc_name
                serverinfo.pri = pri
                dbsesson.commit()
                body['status_code'] = 2
            else:
                body['status_code'] = 3
            dbsesson.close()
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            if body['status_code'] == 2:
                server.reportData((head[2],data))
                server.sendClients((head[2],data))
            else:
                sockSession.sendData(data)
        else:
            if server_name in server.subnameip_dict:
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                ip = server.subnameip_dict[server_name]
                if server.subsv_dict[ip].passonData((head[2],data)):
                    body['status_code'] = 4
                else:
                    body['status_code'] = 5
            else:
                body['status_code'] = 5
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        if body['status_code'] == 2:
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            dbsesson.execute("update serverinfo set ipc_name = %s, pri = %d where name = '%s'" % (ipc_name, pri, server_name))
            dbsesson.commit()
            dbsesson.close()
        server.sendClients((head[2],data))
            
def doLogicInfo(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        server_name = body['server_name']
        if server.server_name == server_name:
            member = []
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            for logicinfo in dbsesson.query(LogicInfo).all():
                item = {}
                item['name'] = logicinfo.name
                item['status'] = logicinfo.status
                item['addtime'] = str(logicinfo.addtime)[:19]
                member.append(item)
            dbsesson.close()
            body['member'] = member
            body['status_code'] = 2
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
        else:
            if server_name in server.subnameip_dict:
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                ip = server.subnameip_dict[server_name]
                if server.subsv_dict[ip].passonData((head[2],data)):
                    body['status_code'] = 4
                else:
                    body['status_code'] = 5
            else:
                body['status_code'] = 5
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        server.reportData((head[2],data))
        server.sendClients((head[2],data))
        
def doDataLogicInfo(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        server_name = body['server_name']
        if server.server_name == server_name:
            member = []
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            for datalogicinfo in dbsesson.query(DataLogicInfo).filter_by(server_name=server_name).all():
                item = {}
                item['data_name'] = datalogicinfo.data_name
                item['logic_name'] = datalogicinfo.logic_name
                item['data_cha'] = datalogicinfo.data_cha
                item['data_onoff'] = datalogicinfo.data_onoff
                item['logic_cha'] = datalogicinfo.logic_cha
                item['logic_onoff'] = datalogicinfo.logic_onoff
                item['dl_alg'] = datalogicinfo.dl_alg
                item['addtime'] = str(datalogicinfo.addtime)[:19]
                member.append(item)
            dbsesson.close()
            body['member'] = member
            body['status_code'] = 2
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
        else:
            if server_name in server.subnameip_dict:
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                ip = server.subnameip_dict[server_name]
                if server.subsv_dict[ip].passonData((head[2],data)):
                    body['status_code'] = 4
                else:
                    body['status_code'] = 5
            else:
                body['status_code'] = 5
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        server.reportData((head[2],data))
        server.sendClients((head[2],data))
        
def doLogicStatusChange(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        server_name = body['server_name']
        if server.server_name == server_name:
            name = body['name']
            status = body['status']
            from dsaur.logicset import logicSet
            if logicSet().setLogicState(name,status):
                body['status_code'] = 2
                engine = create_engine(getSqlUrl(),echo=False)
                DBSession = sessionmaker(bind=engine)
                dbsesson = DBSession()
                logicinfo = dbsesson.query(LogicInfo).filter_by(name=name).one_or_none()
                if logicinfo is not None:
                    logicinfo.status = status
                    dbsesson.commit()
                dbsesson.close()
            else:
                body['status_code'] = 3
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            if body['status_code'] == 2:
                server.sendClients((head[2],data))
            else:
                sockSession.sendData(data)
        else:
            if server_name in server.subnameip_dict:
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                ip = server.subnameip_dict[server_name]
                if server.subsv_dict[ip].passonData((head[2],data)):
                    body['status_code'] = 4
                else:
                    body['status_code'] = 5
            else:
                body['status_code'] = 5
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        server.reportData((head[2],data))
        server.sendClients((head[2],data))
        
def doDataLogicStatusChange(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        server_name = body['server_name']
        if server.server_name == server_name:
            data_name = body['data_name']
            logic_name = body['logic_name']
            logic_cha = body['logic_cha']
            logic_onoff = body['logic_onoff']
            from dsaur.logicset import logicSet
            if logicSet().setDataLogicOnoff(data_name,logic_name,logic_cha,logic_onoff):
                body['status_code'] = 2
                engine = create_engine(getSqlUrl(),echo=False)
                DBSession = sessionmaker(bind=engine)
                dbsesson = DBSession()
                datalogicinfo = dbsesson.query(DataLogicInfo).filter_by(data_name=data_name,logic_name=logic_name,
                                                                        logic_cha=logic_cha).one_or_none()
                if datalogicinfo is not None:
                    datalogicinfo.logic_onoff = logic_onoff
                    dbsesson.commit()
                dbsesson.close()
            else:
                body['status_code'] = 3
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            if body['status_code'] == 2:
                server.sendClients((head[2],data))
            else:
                sockSession.sendData(data)
        else:
            if server_name in server.subnameip_dict:
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                ip = server.subnameip_dict[server_name]
                if server.subsv_dict[ip].passonData((head[2],data)):
                    body['status_code'] = 4
                else:
                    body['status_code'] = 5
            else:
                body['status_code'] = 5
            encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
            head[3] = len(encodedjson.encode('utf-8'))
            data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
            sockSession.sendData(data)
    else:
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        if body['status_code'] == 2:
            engine = create_engine(getSqlUrl(),echo=False)
            DBSession = sessionmaker(bind=engine)
            dbsesson = DBSession()
            datalogicinfo = dbsesson.query(DataLogicInfo).filter_by(data_name=body['data_name'],
                                                                    logic_name=body['logic_name'],
                                                                    logic_cha=body['logic_cha']).one_or_none()
            if datalogicinfo is not None:
                datalogicinfo.logic_onoff = logic_onoff
                dbsesson.commit()
            dbsesson.close()
        server.reportData((head[2],data))
        server.sendClients((head[2],data))

def doRefParamChange(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        name = body['name']
        value = body['value']
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        paraminfo = dbsesson.query(RefParamInfo).filter_by(name=name).one_or_none()
        if paraminfo is not None:
            paraminfo.value = value
            body['updatetime'] = str(datetime.now())[:19]
            paraminfo.updatetime = datetime.now()
            def_refparam(name,value)
            print 'doRefParamChange:', paraminfo
            dbsesson.commit()
            for sv in server.subsv_dict.values():
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                sv.sendData(data)
            body['status_code'] = 2
        else:
            body['status_code'] = 3
        dbsesson.close()
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        server.sendClients((head[2],data))
            
def doRefModeParamChange(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        name = body['name']
        mode = body['mode']
        value = body['value']
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        paraminfo = dbsesson.query(RefModeParamInfo).filter_by(name=name,mode=mode).one_or_none()
        if paraminfo is not None:
            paraminfo.value = value
            body['updatetime'] = str(datetime.now())[:19]
            paraminfo.updatetime = datetime.now()
            def_refmodeparam(name, mode, value)
            print 'doRefModeParamChange:', paraminfo
            dbsesson.commit()
            for sv in server.subsv_dict.values():
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                sv.sendData(data)
            body['status_code'] = 2
        else:
            body['status_code'] = 3
        dbsesson.close()
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        server.sendClients((head[2],data))
            
def doRefCondModeParamChange(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    status_code = body['status_code']
    if status_code == 1:
        name = body['name']
        cond = body['cond']
        mode = body['mode']
        value = body['value']
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        paraminfo = dbsesson.query(RefCondModeParamInfo).filter_by(name=name,cond=cond,mode=mode).one_or_none()
        if paraminfo is not None:
            paraminfo.value = value
            body['updatetime'] = str(datetime.now())[:19]
            paraminfo.updatetime = datetime.now()
            def_refcondmodeparam(name, cond, mode, value)
            print 'doRefCondModeParamChange:', paraminfo
            dbsesson.commit()
            for sv in server.subsv_dict.values():
                encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
                head[3] = len(encodedjson.encode('utf-8'))
                data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
                sv.sendData(data)
            body['status_code'] = 2
        else:
            body['status_code'] = 3
        dbsesson.close()
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        server.sendClients((head[2],data)) 
    
# 下级上报计算完成
def doServerFinished(server, sockSession, head, body):
    
    body['local_name'] = local_name
    head = list(head)
    server_name = body['server_name']
    status_code = body['status_code']
#     print 'doServerFinished:', status_code,server_name
    if server_name in server.subnameip_dict:
        sv = server.subsv_dict[server.subnameip_dict[server_name]]
        if status_code == 1:
            sv.wait_flag = True
            if server.getFinishState():
                sv.setFinishFlag(False)
        elif status_code == 255:
            sv.setFinishFlag(True)
            sv.wait_flag = False
            server.startDataProcess()

def doRefParamINIT(server, sockSession, head, body):
    head = list(head)
    ParamBody = body['ParamBody']
    RefParam = ParamBody['RefParam']
    engine = create_engine(getSqlUrl(),echo=False)
    DBSession = sessionmaker(bind=engine)
    dbsesson = DBSession()
    for item in RefParam:
        name = item['name']
        value = item['value']
        paraminfo = dbsesson.query(RefParamInfo).filter_by(name=name).one_or_none()
        if paraminfo is not None:
            paraminfo.value = value
            paraminfo.updatetime = datetime.now()
            def_refparam(name,value)
            dbsesson.commit()
    RefModeParam = ParamBody['RefModeParam']
    for item in RefModeParam:
        name = item['name']
        mode = item['mode']
        value = item['value']
        paraminfo = dbsesson.query(RefModeParamInfo).filter_by(name=name,mode=mode).one_or_none()
        if paraminfo is not None:
            paraminfo.value = value
            paraminfo.updatetime = datetime.now()
            def_refmodeparam(name, mode, value)
            dbsesson.commit()
    RefCondModeParam = ParamBody['RefCondModeParam']
    for item in RefCondModeParam:
        name = item['name']
        cond = item['cond']
        mode = item['mode']
        value = item['value']
        paraminfo = dbsesson.query(RefCondModeParamInfo).filter_by(name=name,cond=cond,mode=mode).one_or_none()
        if paraminfo is not None:
            paraminfo.value = value
            paraminfo.updatetime = datetime.now()
            def_refcondmodeparam(name, cond, mode, value)
            dbsesson.commit()
    server.PARAM_Flag = True
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    for sv in server.subsv_dict.values():
        sv.socksession.sendData(data)
    print 'doRefParamINIT Finished!!!!!!'
    
def doGetIPCStream(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    ipc_name = body['ipc_name']
    status_code =  body['status_code']
    if status_code == 1:
        if server.streamService.getIPC_Stream(ipc_name).flag:
            if server.streamService.startLiveStream(ipc_name,local_name):
                body['status_code'] = 2
            else:
                if ipc_name in server.streamService.livestream_dict:
                    if server.streamService.livestream_dict[ipc_name].poll() is None:
                        body['status_code'] = 2
                    else:
                        body['status_code'] = 3
                        del server.streamService.livestream_dict[ipc_name]
                        print 'doGetIPCStream:', 'del streamService livestream'
                else:
                    body['status_code'] = 3
                    print 'doGetIPCStream:', '----------------------------'
#             from server import subsocksession
#             subsocksession(ipc_name,sockSession.addr[0],int(video_port),None)
        else:
            body['status_code'] = 3
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
    elif status_code == 10:
        if ipc_name in server.streamService.livestream_dict:
            if server.streamService.stopLiveStream(ipc_name):
                body['status_code'] = 11
            else:
                body['status_code'] = 12
        else:
            body['status_code'] = 12
        encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
        head[3] = len(encodedjson.encode('utf-8'))
        data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
        sockSession.sendData(data)
    else:
        pass
        
        
def doGetIPCHistoryStream(server, sockSession, head, body):
    body['local_name'] = local_name
    head = list(head)
    ipc_name = body['ipc_name']
    event_time = body['event_time'].decode('ascii').encode('gbk')
    start_time = datetime.strptime(body['start_time'],'%Y-%m-%d %H:%M:%S')
    end_time = datetime.strptime(body['end_time'],'%Y-%m-%d %H:%M:%S')
    if ipc_name not in server.streamService.ipc_histream_dict:
        from server import subsocksessionHis
        con = subsocksessionHis(ipc_name,sockSession.addr[0],int(video_port),None)
        con.putMsg(ipc_name, start_time, end_time, event_time)
    else:
        con = server.streamService.ipc_histream_dict.get(ipc_name)
        con.putMsg(ipc_name, start_time, end_time, event_time)
        
@tryException
def doIPCState(server, sockSession, head, body):
    print 'doIPCState:', body
    body['local_name'] = local_name
    head = list(head)
    ipc_name = body['ipc_name']
    ipc_state = body['ipc_state']
    updatetime = body['updatetime']
    engine = create_engine(getSqlUrl(),echo=False)
    DBSession = sessionmaker(bind=engine)
    dbsession = DBSession()
    dbsession.query(IPCInfo).filter(IPCInfo.name==ipc_name).update({IPCInfo.state : ipc_state,
                                                                       IPCInfo.updatetime : updatetime})
    dbsession.commit()
    dbsession.close()
    encodedjson = json.dumps(body,ensure_ascii=False,default=decimal_default)
    head[3] = len(encodedjson.encode('utf-8'))
    data = struct.pack('!4i{}s'.format(head[3]), head[0], head[1], head[2], head[3], encodedjson.encode('utf-8'))
    server.sendClients((head[2],data))
    
    
def_protmsg('ServerParam',doServerParam)
def_protmsg('ServiceState',doServicesState)
def_protmsg('ServerState',doServerState)
def_protmsg('VideoServerIPCS',doVideoServerIPCS)
def_protmsg('NodeUnitMap',doNodeUnitMap)
def_protmsg('DeviceTypes',doDeviceTypes)
def_protmsg('SessionTypes',doSessionTypes)
def_protmsg('Sessinons',doSessions)
def_protmsg('Devices',doDevices)
def_protmsg('DeviceFinished',doItemsFinished)
def_protmsg('DevDataItems', doDeviceDataItems)
def_protmsg('DevDataItemsFinished', doItemsFinished)
def_protmsg('ServerDataTypes', doServerDataTypes)
def_protmsg('UDevDataItems', doUDevDataItems)
def_protmsg('UDevDataItemsFinished', doItemsFinished)
def_protmsg('PeriodDataItems', doPeriodDataItems)
def_protmsg('MachineDataItems', doMachineDataItems)
def_protmsg('MachineDataItemsFinished', doItemsFinished)
def_protmsg('TransmitDataItems', doTransmitDataItems)
def_protmsg('RefParamInfo', doRefParamInfo)
def_protmsg('RefModeParamInfo', doRefModeParamInfo)
def_protmsg('RefCondModeParamInfo', doRefCondModeParamInfo)
def_protmsg('InitFinished', doInitFinished)
def_protmsg('SessionState', doSessionState)
def_protmsg('DataInfo', doDataInfo)
def_protmsg('YHDataUpdate', doYHDataUpdate)
def_protmsg('SessionIdChanged', doSessionIdChanged)
def_protmsg('SessionConfChanged', doSessionConfChanged)
def_protmsg('DeviceIdChanged', doDeviceIdChanged)
def_protmsg('DataConfInfo', doDataConfInfo)
def_protmsg('DataPriChange', doDataPriChange)
def_protmsg('DataIPCSChange',doDataIPCSChange)
def_protmsg('ServerConfChange', doServerConfChange)
def_protmsg('LogicInfo', doLogicInfo)
def_protmsg('DataLogicInfo', doDataLogicInfo)
def_protmsg('LogicStatusChange', doLogicStatusChange)
def_protmsg('DataLogicStatusChange', doDataLogicStatusChange)
def_protmsg('RefParamChange', doRefParamChange)
def_protmsg('RefModeParamChange', doRefModeParamChange)
def_protmsg('RefCondModeParamChange', doRefCondModeParamChange)
def_protmsg('ServerFinished',doServerFinished)
def_protmsg('RefParamINIT',doRefParamINIT)
def_protmsg('GetIPCStream', doGetIPCStream)
def_protmsg('GetIPCHistoryStream', doGetIPCHistoryStream)
def_protmsg('IPCState', doIPCState)