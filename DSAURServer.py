#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年12月26日

@author: sanhe
'''

import fcntl
import socket
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import struct
from readconf import getSqlUrl
from UserDict import UserDict
from datetime import datetime
import time
import sys
import signal
import os
from server import Server
from dsaur.models import *
from dsaur.util import *
from dsaur.logicset import logicObj, logicSet, chaObj
from dsaur.basedata import dataObj, dataCalObj
from dsaur.serialsearch import InitSerialNo
from sendgpio import SendGPIO

def handler(signal_num, frame):
    print "\nYou Pressed Ctrl-C"
    if Server().streamService is not None:
        for p in Server().streamService.livestream_dict.values():
            if p.poll() is None:
                p.terminate()
                p.wait()
                os.killpg(p.pid, signal.SIGTERM)
            else:
                pass
        for p in Server().streamService.localstream_dict.values():
            if p.poll() is None:
                p.terminate()
                p.wait()
                os.killpg(p.pid, signal.SIGTERM)
            else:
                pass
    os.kill(os.getpid(),signal.SIGTERM)
    sys.exit(signal_num)
    
signal.signal(signal.SIGINT, handler)

def get_ip_address(ifname):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print struct.pack('256s', ifname[:15])
    return socket.inet_ntoa(fcntl.ioctl(
                                        sock.fileno(),
                                        0x8915,  # SIOCGIFADDR
                                        struct.pack('256s', ifname[:15])
                                        )[20:24])
    
@tryException
def ServerState(server, server_name, state, statetime):
    engine = create_engine(getSqlUrl(),echo=False)
    DBSession = sessionmaker(bind=engine)
    dbsession = DBSession()
    str_statetime = statetime
    if statetime is not None:
        str_statetime = statetime.strftime('%Y-%m-%d %H:%M:%S')
    dbsession.query(ServerInfo).filter(ServerInfo.name==server_name).update({ServerInfo.state : state,
                                                                            ServerInfo.updatetime : str_statetime})
    dbsession.add(ServerInfoHistory(server_name,state,statetime))
    dbsession.commit()
    if state is False:
        if server_name == server.server_name:
            for datainfo in dbsession.query(DataInfo).filter(DataInfo.server_name==server_name,DataInfo.attribute<>2).all():
                if datainfo.name in server.data_dict:
                    if server.data_dict[datainfo.name].dis_flag is False:
                        server.data_dict[datainfo.name].change_flag = 7
                        server.data_dict[datainfo.name].dis_flag = True
                        server.data_dict[datainfo.name].dis_time = statetime
                        server.putPreCacheData(datainfo.name)
                    else:
                        pass
                else:
                    pass
        elif server_name in server.subnameip_dict:
            for datainfo in dbsession.query(DataInfo).filter_by(server_name=server_name).all():
                if datainfo.name in server.data_dict:
                    if server.data_dict[datainfo.name].dis_flag is False:
                        server.data_dict[datainfo.name].change_flag = 7
                        server.data_dict[datainfo.name].dis_flag = True
                        server.data_dict[datainfo.name].dis_time = statetime
                        server.putPreCacheData(datainfo.name)
                    else:
                        pass
                else:
                    pass
        elif server.superserver is not None and server.superserver.server_name == server_name:
            for transmitdata in dbsession.query(TransmitData).filter_by(server_name=server.server_name).all():
                if transmitdata.data_name in server.data_dict:
                    if server.data_dict[transmitdata.data_name].dis_flag is False:
                        server.data_dict[transmitdata.data_name].change_flag = 7
                        server.data_dict[transmitdata.data_name].dis_flag = True
                        server.data_dict[transmitdata.data_name].dis_time = statetime
                        server.putPreCacheData(transmitdata.data_name)
                    else:
                        pass
    else:
        pass
    dbsession.close()
            
@tryException
def WriteDB(server):
    engine = create_engine(getSqlUrl(),echo=False)
    DBSession = sessionmaker(bind=engine)
    dbsession = DBSession()
    while server.WriteDBflag:
#         import objgraph
#         objgraph.show_growth(limit=10)
# #             objgraph.show_most_common_types(limit=10)
#         print '_________________________________________'
        name = server.popWriteDBData()
        if name is not None:
#             print name,datetime.now()
            dataitem = server.data_dict.get(name)
            if dataitem is None:
                continue
            reason = dataitem.reason
            rs_type = 0
            rs_name = None
            rs_cname = None
            rs_value = None
            rs_change_flag = None
            rs_conf = None
            rs_user = None
            rs_time = None
            if reason is not None:
                rs_type = reason['rs_type']
                if rs_type == 1:
                    rs_name = reason['rs_name']
                    rs_cname = reason['rs_cname']
                    rs_value = reason['rs_value']
                    rs_change_flag = reason['rs_change_flag']
                    rs_time = reason['rs_time']
                elif rs_type == 2:
                    rs_conf = reason['rs_conf']
                else:
                    rs_user = reason['rs_user']
            if rs_time is not None:
                rs_time = rs_time.strftime('%Y-%m-%d %H:%M:%S')
            dbsession.query(ServerInfo).filter(ServerInfo.name==server.server_name).update({ServerInfo.runtime : datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            d_time =  dataitem.time
            if d_time is not None:
                d_time = d_time.strftime('%Y-%m-%d %H:%M:%S')
            dis_time = dataitem.dis_time
            if dis_time is not None:
                dis_time = dis_time.strftime('%Y-%m-%d %H:%M:%S')
            dbsession.query(DataInfo).filter(DataInfo.name==name).update({
                                                                  DataInfo.value : dataitem.value,
                                                                  DataInfo.error_flag : dataitem.error_flag,
                                                                  DataInfo.time : d_time,
                                                                  DataInfo.dis_flag : dataitem.dis_flag,
                                                                  DataInfo.dis_time : dis_time,
                                                                  DataInfo.change_flag : dataitem.change_flag,
                                                                  DataInfo.rs_type : rs_type})
            dbsession.commit()
            if rs_type != 0:
                dbsession.query(ReasonDataInfo).filter(ReasonDataInfo.name==name).update({
                                                                                   ReasonDataInfo.rs_name : rs_name,
                                                                                   ReasonDataInfo.rs_cname : rs_cname,
                                                                                   ReasonDataInfo.rs_value : rs_value,
                                                                                   ReasonDataInfo.rs_change_flag : rs_change_flag,
                                                                                   ReasonDataInfo.rs_conf : rs_conf,
                                                                                   ReasonDataInfo.rs_user : rs_user,
                                                                                   ReasonDataInfo.rs_time : rs_time})
                dbsession.add(DataHistory(dataitem.name,dataitem.change_flag,dataitem.value,dataitem.error_flag,d_time,
                            dataitem.dis_flag,dis_time,datetime.now().strftime('%Y-%m-%d %H:%M:%S'),rs_type,rs_name,rs_cname,rs_value,
                            rs_change_flag,rs_conf,rs_user,rs_time))
            else:
                dbsession.add(DataHistory(dataitem.name,dataitem.change_flag,dataitem.value,dataitem.error_flag,
                                   d_time,dataitem.dis_flag,dis_time))
            dbsession.commit()
        else:
            pass
            time.sleep(0.001)
    dbsession.close()
    
def serverStart():
    SendGPIO().sendSignal()
    time.sleep(10)
#     server_ip = get_ip_address('enp3s0')
#     server_ip = get_ip_address('wlp2s0')
#     INIT_LOGICS()
    server_ip = get_ip_address('eth0')
    engine = create_engine(getSqlUrl(),echo=False)
    DBSession = sessionmaker(bind=engine)
    dbsesson = DBSession()
    serverinfo = dbsesson.query(ServerInfo).filter_by(ip=server_ip).one_or_none()
    if serverinfo is None:
        raise Exception('%s is not in this System' % server_ip)
        return
    for data in dbsesson.query(RefParamInfo).all():
        def_refparam(data.name, data.value)
    for data in dbsesson.query(RefModeParamInfo).all():
        def_refmodeparam(data.name, data.mode, data.value)
    for data in dbsesson.query(RefCondModeParamInfo).all():
        def_refcondmodeparam(data.name, data.cond, data.mode, data.value)
    logicstate_dict = UserDict()
    datacha_dict = UserDict()
    datalogic_dict = UserDict()
    delaylogiclist = []
    for logicinfo in dbsesson.query(LogicInfo).all():
        logicstate_dict[logicinfo.name] = logicinfo.status
    for datalogicinfo in dbsesson.query(DataLogicInfo).filter_by(server_name=serverinfo.name).all():
        if datalogicinfo.logic_name is not None:
            logic = logicObj(datalogicinfo.logic_name, datalogicinfo.logic_cha, datalogicinfo.logic_onoff)
            if datalogicinfo.data_name is not None:
                if datalogicinfo.data_name not in datalogic_dict:
                    datalogic_dict[datalogicinfo.data_name] = []
                datalogic_dict[datalogicinfo.data_name].append(logic)
                if datalogicinfo.data_cha is not None:
                    cha = chaObj(datalogicinfo.data_name, datalogicinfo.dl_alg)
                    if datalogicinfo.data_cha not in datacha_dict:
                        datacha_dict[datalogicinfo.data_cha] = []
                    datacha_dict[datalogicinfo.data_cha].append(cha)
            else:
                delaylogiclist.append((None, logic, datetime.now()))
        else:
            if datalogicinfo.data_cha is not None:
                cha = chaObj(datalogicinfo.data_name, datalogicinfo.dl_alg)
                if datalogicinfo.data_cha not in datacha_dict:
                    datacha_dict[datalogicinfo.data_cha] = []
                datacha_dict[datalogicinfo.data_cha].append(cha)
            else:
                pass
    logicSet(logicstate_dict,datacha_dict,datalogic_dict,delaylogiclist)
    logicstate_dict.clear()
    datacha_dict.clear()
    datalogic_dict.clear()
    del delaylogiclist
    runtime = serverinfo.runtime
    session_dict = UserDict()
    for sessioninfo in serverinfo.sessions:
        dev_dict = UserDict()
        for deviceinfo in sessioninfo.devices:
            disMax = None
            disCount = None
            data_dict = UserDict()
            for datatype in deviceinfo.datatypes.all():
                conf_name = datatype.conf_name
                if conf_name == 'DisCount':
                    disCount = int(datatype.data.value) if datatype.data.value is not None else None
                    disMax = int(datatype.data.max_val)
                dataname = datatype.name
                link_conf = None
                algorithm = datatype.algorithm
                linkflag = datatype.link_flag
                if linkflag:
                    devdatalink = dbsesson.query(DevDataLink).filter_by(dev_name=datatype.dev_name,
                                                                        conf_name=conf_name).one_or_none()
                    link_conf = devdatalink.link_key
                data_dict[conf_name] = (dataname,link_conf,algorithm)
            dev_dict[deviceinfo.name] = (deviceinfo.id, deviceinfo.type, data_dict, disCount, disMax)
        statetime = runtime if sessioninfo.state else sessioninfo.updatetime
        session_dict[sessioninfo.name] = (sessioninfo.id, dev_dict, False, statetime, sessioninfo.timeout)
    Server(serverinfo.name,server_ip,session_dict)
    data_dict = UserDict()
    transmitdatasvs_dict = UserDict()
    dataconf_dict = UserDict()
    subsv_dict= UserDict()
    videosv_dict = UserDict()
    superdata=None
    ipc_dict = None
    servername_list = [serverinfo.name,]
    if serverinfo.type == 'region':
        for svinfo in dbsesson.query(ServerInfo).filter(ServerInfo.name!=serverinfo.name).all():
            servername_list.append(svinfo.name)
            statetime = runtime if svinfo.state else svinfo.updatetime
            if svinfo.type == 'video':
                ipcs = []
                for ipc in dbsesson.query(IPCVideoServerMap).filter_by(server_name=svinfo.name).all():
                    ipcs.append(ipc.ipc_name)
                videosv_dict[svinfo.ip] = (svinfo.name, False, statetime, ipcs)
            elif svinfo.type == 'unit':
                subsv_dict[svinfo.ip] = (svinfo.name, svinfo.timeout, False, statetime)
                for tranmitdatainfo in dbsesson.query(TransmitData).filter_by(server_name=svinfo.name).all():
                    if tranmitdatainfo.data_name not in transmitdatasvs_dict:
                        transmitdatasvs_dict[tranmitdatainfo.data_name] = []
                    transmitdatasvs_dict[tranmitdatainfo.data_name].append(tranmitdatainfo.server_name)
            else:
                for tranmitdatainfo in dbsesson.query(TransmitData).filter_by(server_name=svinfo.name).all():
                    node_unit1 = dbsesson.query(NodeUnitMap).filter_by(node_name=
                                                                       tranmitdatainfo.data.server_name).one_or_none()
                    node_unit2 = dbsesson.query(NodeUnitMap).filter_by(node_name=
                                                                       tranmitdatainfo.server_name).one_or_none()
                    if node_unit1.unit_name != node_unit2.unit_name:
                        if tranmitdatainfo.data_name not in transmitdatasvs_dict:
                            transmitdatasvs_dict[tranmitdatainfo.data_name] = []
                        transmitdatasvs_dict[tranmitdatainfo.data_name].append(tranmitdatainfo.server_name)
                    else:
                        pass
    elif serverinfo.type == 'unit':
        regioninfo = dbsesson.query(ServerInfo).filter_by(type='region').one_or_none()
        superdata = UserDict()
        superdata['server_name'] = regioninfo.name
        superdata['ip'] = regioninfo.ip
        superdata['state'] = regioninfo.state
        superdata['statetime'] = regioninfo.updatetime
        if serverinfo.unit_nodes is not None:
            for unit_node in serverinfo.unit_nodes:
                servername_list.append(unit_node.node_name)
                statetime = runtime if unit_node.node.state else unit_node.node.updatetime
                subsv_dict[unit_node.node.ip] = (unit_node.node.name, unit_node.node.timeout, False, statetime)
                for tranmitdatainfo in dbsesson.query(TransmitData).filter_by(server_name=unit_node.node_name).all():
                    if tranmitdatainfo.data_name not in transmitdatasvs_dict:
                        transmitdatasvs_dict[tranmitdatainfo.data_name] = []
                    transmitdatasvs_dict[tranmitdatainfo.data_name].append(tranmitdatainfo.server_name)
        else:
            pass
    elif serverinfo.type == 'node':
        superdata = UserDict()
        superdata['server_name'] =  serverinfo.node_unit
        superdata['ip'] = serverinfo.node_unit.node.ip
        superdata['state'] = serverinfo.node_unit.state
        superdata['statetime'] = serverinfo.node_unit.updatetime
    elif serverinfo.type == 'video':
        regioninfo = dbsesson.query(ServerInfo).filter_by(type='region').one_or_none()
        superdata = UserDict()
        superdata['server_name'] = regioninfo.name
        superdata['ip'] = regioninfo.ip
        superdata['state'] = regioninfo.state
        superdata['statetime'] = regioninfo.updatetime
        ipc_dict = UserDict()
        for ipc_server in dbsesson.query(IPCVideoServerMap).filter_by(server_name=serverinfo.name).all():
            ipc = ipc_server.ipc
            ipc_dict[ipc_server.ipc_name] = (ipc.cname,ipc.ip,ipc.rtsp_type,ipc.fps,ipc.resolution,
                                      ipc.streamsize,ipc.state,ipc.streamsize)
    else:
        pass
    for name in servername_list:
        for datainfo in dbsesson.query(DataInfo).filter_by(server_name=name).all():
            reason = None
            if datainfo.rs_type == 1:
                reason = {'rs_type' : 1,
                          'rs_name' : datainfo.reason.rs_name,
                          'rs_cname' : datainfo.reason.rs_cname,
                          'rs_value' : datainfo.reason.rs_value,
                          'rs_time' : datainfo.reason.rs_time,
                          'rs_change_flag' : datainfo.reason.rs_change_flag}
            elif datainfo.rs_type == 2:
                reason = {'rs_type' : 2,
                          'rs_conf' : datainfo.reason.rs_conf}
            elif datainfo.rs_type == 3:
                reason = {'rs_type' : 3,
                          'rs_user' : datainfo.reason.rs_user}
            value = float(datainfo.value) if datainfo.value is not None else None
            data = dataObj(datainfo.name,value,datainfo.error_flag,datainfo.time,datainfo.dis_flag,
                           datainfo.dis_time,datainfo.change_flag,reason,datainfo.attribute)
            if datainfo.server_name == serverinfo.name:
                dataconstraint = UserDict()
                dataconstraint['min_variation'] = datainfo.min_variation
                dataconstraint['min_val'] = datainfo.min_val
                dataconstraint['max_val'] = datainfo.max_val
                if datainfo.attribute == 1 and datainfo.datatype.link_flag:
                    devdatalink = dbsesson.query(DevDataLink).filter_by(
                                dev_name=datainfo.datatype.dev_name,
                                conf_name=datainfo.datatype.conf_name).one_or_none()
                    data = dataCalObj(data,dataconstraint,devdatalink.link_para1)
                else:
                    data = dataCalObj(data,dataconstraint)
            else:
                pass
            data_dict[datainfo.name] = data
            dataconf = UserDict()
            dataconf['data_cname'] = datainfo.cname
            dataconf['server_name'] = datainfo.server_name
            dataconf['dis_interval'] = datainfo.dis_interval
            dataconf['start_sec'] = datainfo.start_sec
            dataconf['end_sec'] = datainfo.end_sec
            dataconf['pri'] = datainfo.pri
            ipcs = []
            for ipc in dbsesson.query(DataIPCInfo).filter_by(data_name=datainfo.name).all():
                ipcs.append(ipc.ipc_name)
            dataconf['ipcs'] = ipcs
            if datainfo.attribute == 1:
                dataconf['dev_name'] = datainfo.datatype.dev_name
                dataconf['conf_name'] = datainfo.datatype.conf_name
                dataconf['session_name'] = datainfo.datatype.dev.session_name
            elif datainfo.attribute == 2:
                dataconf['type'] = datainfo.udatatype.type
            elif datainfo.attribute == 3:
                dataconf['mep'] = datainfo.mdatatype.mep_name
            elif datainfo.attribute == 4:
                dataconf['session_name'] = datainfo.pdatatype.session_name
            dataconf_dict[datainfo.name] = dataconf
    for tranmitdatainfo in dbsesson.query(TransmitData).filter_by(server_name=serverinfo.name).all():
        datainfo = tranmitdatainfo.data
        reason = None
        if datainfo.rs_type == 1:
            reason = {'rs_type' : 1,
                      'rs_name' : datainfo.reason.rs_name,
                      'rs_cname' : datainfo.reason.rs_cname,
                      'rs_value' : datainfo.reason.rs_value,
                      'rs_time' : datainfo.reason.rs_time,
                      'rs_change_flag' : datainfo.reason.rs_change_flag}
        elif datainfo.rs_type == 2:
            reason = {'rs_type' : 2,
                      'rs_conf' : datainfo.reason.rs_conf}
        elif datainfo.rs_type == 3:
            reason = {'rs_type' : 3,
                      'rs_user' : datainfo.reason.rs_user}
        data = dataObj(datainfo.name,value,datainfo.error_flag,datainfo.time,datainfo.dis_flag,
                       datainfo.dis_time,datainfo.change_flag,reason)
        data_dict[datainfo.name] = data
        dataconf = UserDict()
        dataconf['data_cname'] = datainfo.cname
        dataconf['server_name'] = datainfo.server_name
        dataconf['dis_interval'] = datainfo.dis_interval
        dataconf['pri'] = datainfo.pri
        ipcs = []
        for ipc in dbsesson.query(DataIPCInfo).filter_by(data_name=datainfo.name).all():
            ipcs.append(ipc.ipc_name)
        dataconf['ipcs'] = ipcs
        dataconf['server_name'] = datainfo.server_name
        if datainfo.attribute == 1:
            dataconf['dev_name'] = datainfo.datatype.dev_name
            dataconf['conf_name'] = datainfo.datatype.conf_name
            dataconf['session_name'] = datainfo.datatype.dev.session_name
        elif datainfo.attribute == 2:
            dataconf['type'] = datainfo.udatatype.type
        elif datainfo.attribute == 3:
            dataconf['mep'] = datainfo.mdatatype.mep_name
        elif datainfo.attribute == 4:
            dataconf['session_name'] = datainfo.pdatatype.session_name
        dataconf_dict[datainfo.name] = dataconf
    InitSerialNo(dbsesson)
    Server().initServer(data_dict, dataconf_dict, transmitdatasvs_dict, subsv_dict, videosv_dict, superdata, ipc_dict)
    ServerState(Server(), serverinfo.name, False, runtime)
    dbsesson.close()
    for v in subsv_dict.values():
        if v[2] is False:
            ServerState(Server(), v[0], False, v[3])
        else:
            ServerState(Server(), v[0], False, runtime)
    if superdata is not None:
        if superdata['state'] is False:
            ServerState(Server(), superdata['server_name'], False, superdata['statetime'])
        else:
            ServerState(Server(), superdata['server_name'], False, runtime)
    Server().start(serverinfo.timeout,WriteDB,ServerState)

if __name__ == '__main__':
    print datetime.now(),'serverStart!!!'
    try:
        serverStart()
    except Exception as e:
        print 'DSAURServer serverStart : ', e
    finally:
        pass
    
    