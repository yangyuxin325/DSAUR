#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年12月19日

@author: sanhe
'''
import asyncore
import threading
from datetime import datetime, timedelta
from UserDict import UserDict
import struct
import json
import copy
from handler import doMesssages
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from readconf import getSqlUrl, remote_ip, timeout_refparam,video_ip,video_port,local_name,remote_port
from dsaur.logicset import logicSet
from dsaur.models import *
from dsaur.util import tryException,singleton
from dsaur.vlcIPCStream import StreamRecordService
from dsaur.sock_session import *
from dsaur.metaserver import *
from dsaur.datacollector import dataCollector
from dsaur.serialsearch import *
from packProtocol import *
from dsaur.raspberrypi_info import raspberrypi_info
import time
import socket
import os
from sqlalchemy import and_
from collections import deque

# def MatchIP(ip):
#     import re
#     ipm = re.match(r'^([1-9]?\d|1\d\d|2[0-4]\d|25[0-5])\.([1-9]?\d|1\d\d|2[0-4]\d|25[0-5])\.([1-9]?\d|1\d\d|2[0-4]\d|25[0-5])\.([1-9]?\d|1\d\d|2[0-4]\d|25[0-5])$',ip)
#     if ipm is None:
#         return False
#     else:
#         return True

def ServerState(server, server_name, state, statetime):
    pass

def WriteDB(server):
    pass        

class recordService(StreamRecordService):
    ipc_stream_dict = UserDict()
    ipc_histream_dict = UserDict()
    def recordFileName(self, stream):
        StreamRecordService.recordFileName(self, stream)
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsession = DBSession()
        dbsession.add(RecordHistroy(stream.name,stream.start.strftime('%Y-%m-%d %H:%M:%S'),stream.end.strftime('%Y-%m-%d %H:%M:%S')))
        dbsession.commit()
        dbsession.close()
        if stream.name in self.ipc_stream_dict and self.ipc_stream_dict[stream.name].send_flag:
            threading.Thread(target=self.sendThread,args=(stream.name,stream.recordname)).start()
        
    def sendThread(self,ipc_name, recordname):
        f = open(recordname,'rb')
        f.seek(0,2)
        bufsize = f.tell()
        f.seek(0,0)
        if bufsize == 0:
            return
        buf = f.read(bufsize)
        head = range(4)
        head[0] = 2
        head[1] = 0
        head[2] = 1
        head[3] = len(buf)+4
        snd = struct.pack('!5i{}s'.format(len(buf)),head[0], head[1],head[2], head[3],len(buf),buf)
        print len(snd),recordname
        self.ipc_stream_dict[ipc_name].sendData(snd)
        time.sleep(0.01)
        
    def checkFlag(self):
        print datetime.now(), '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
        Server().startDataProcess()
        from timercheck import TimerCheck
        TimerCheck().excuteCheck()
        
    def streamState(self, stream):
        StreamRecordService.streamState(self, stream)
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsession = DBSession()
        dbsession.query(IPCInfo).filter(IPCInfo.name==stream.name).update({IPCInfo.state : stream.flag,
                                                                           IPCInfo.updatetime : stream.updatetime})
        dbsession.commit()
        dbsession.close()
        packdata = PackIPCState(Server().server_name, 255, stream.name, stream.flag, stream.updatetime)
        if Server().superserver is not None:
            Server().superserver.reportData(packdata)
        if Server().video_local_main is not None:
            Server().video_local_main.sendData(packdata[1])
        if Server().video_remote_main is not None:
            Server().video_remote_main.sendData(packdata[1])
            
class subsocksession(AsyncSession):
    def __init__(self, ipc_name, host, port, handleData=None, doConnect = None, doClose = None):
        AsyncSession.__init__(self, host, port, handleData, doConnect, doClose)
        self.ipc_name = ipc_name
        self.send_flag = True
        
    @tryException
    def handle_read(self):
        asyncore.dispatcher_with_send.handle_read(self)
        self.count = 0
#         self.timer.count = 0
        if self.connected:
            buf = self.recv(8192)
            if len(buf) > 0:
                self.readbuf = self.readbuf + buf
            else:
                return
            try:
                while len(self.readbuf) >= self.bufsize:
                    buftemp  = self.readbuf[self.bufsize:]
                    if self.bufsize == 16:
                        head = struct.unpack('!4i', self.readbuf[:16])
                        if head[3] > 0:
                            self.bufsize = head[3]
                            self.head = head
                        else:
                            self.bufsize = 16
                            self.head = None
                    else:
                        tempbuf = self.readbuf[:self.bufsize]
                        body = json.loads(tempbuf)
                        if self.head[2] in doMesssages:
                            try:
                                doMesssages[self.head[2]](self, self, self.head, body)
                            except Exception as e:
                                print 'handleReceive Error: ', self.addr[0], self.head[2],body,e
                        self.bufsize = 16
                        self.head = None
                    self.readbuf = buftemp
            except Exception  as e:
                print 'handleData:', e, self.readbuf, len(self.readbuf), self.bufsize
                self.close()
        else:
            pass
        
    @tryException
    def handle_connect(self):
        AsyncSession.handle_connect(self)
        Server().asyncserver.addSocket(self)
        if self.connected:
            recordService.ipc_stream_dict[self.ipc_name] = self
            self.sendData(PackGetIPCStream(Server().server_name,self.ipc_name))
        else:
            pass
        
    @tryException
    def handle_close(self):
        AsyncSession.handle_close(self)
        if self.ipc_name in recordService.ipc_stream_dict:
            del recordService.ipc_stream_dict[self.ipc_name]

            
class subsocksessionHis(AsyncSession):
    def __init__(self, ipc_name, host, port, handleData=None, doConnect = None, doClose = None):
        AsyncSession.__init__(self, host, port, handleData, doConnect, doClose)
        self.ipc_name = ipc_name
        self.msg_deque = deque()
        
    def putMsg(self,ipc_name, start_time, end_time, event_time):
        self.msg_deque.append((ipc_name,start_time,end_time, event_time))
        
    @tryException
    def handle_read(self):
        asyncore.dispatcher_with_send.handle_read(self)
        self.count = 0
#         self.timer.count = 0
        if self.connected:
            buf = self.recv(8192)
            if len(buf) > 0:
                self.readbuf = self.readbuf + buf
            else:
                return
            try:
                while len(self.readbuf) >= self.bufsize:
                    buftemp  = self.readbuf[self.bufsize:]
                    if self.bufsize == 16:
                        head = struct.unpack('!4i', self.readbuf[:16])
                        if head[3] > 0:
                            self.bufsize = head[3]
                            self.head = head
                        else:
                            self.bufsize = 16
                            self.head = None
                    else:
                        tempbuf = self.readbuf[:self.bufsize]
                        body = json.loads(tempbuf)
                        if self.head[2] in doMesssages:
                            try:
                                doMesssages[self.head[2]](self, self, self.head, body)
                            except Exception as e:
                                print 'handleReceive Error: ', self.addr[0], self.head[2],body,e
                        self.bufsize = 16
                        self.head = None
                    self.readbuf = buftemp
            except Exception  as e:
                print 'handleData:', e, self.readbuf, len(self.readbuf), self.bufsize
                self.close()
        else:
            pass
        
    @tryException
    def sendThread(self):
        engine = create_engine(getSqlUrl(),echo=True)
        DBSession = sessionmaker(bind=engine)
        dbsession = DBSession()
        while len(self.msg_deque) > 0:
            ipc_name, start_time, end_time, event_time = self.msg_deque.popleft()
#             print ipc_name, start_time, end_time
            rhs = dbsession.query(RecordHistroy).filter(and_(RecordHistroy.name==ipc_name,
                                                             RecordHistroy.end>start_time,
                                                             RecordHistroy.start<end_time)
                                                        ).order_by(RecordHistroy.id).all()
            file_count = len(rhs)
            head = range(4)
            head[0] = 2
            head[1] = 0
            head[2] = 2
            head[3] = 61
            snd = ''
            str_start = start_time.strftime('%Y-%m-%d %H:%M:%S')
            str_end = end_time.strftime('%Y-%m-%d %H:%M:%S')
            if file_count > 0:
                for rh in rhs:
                    str_file_start = rh.start.strftime('%Y-%m-%d %H:%M:%S')
                    str_file_end = rh.end.strftime('%Y-%m-%d %H:%M:%S')
                    subdir = rh.start.year*1000000 + rh.start.month*10000 + rh.start.day*100 + rh.start.hour
                    filename = '{0}/{1}/{2}-{3}.mp4'.format(rh.name,subdir,str_file_start,str_file_end)
#                     filename = rh.name + '/' + str(subdir) + '/' + str_file_start + '-' + str_file_end + '.mp4'
                    print 'sendThread recordHistory:', filename 
                    if os.path.exists(filename):
                        f = open(filename,'rb')
                        f.seek(0,2)
                        bufsize = f.tell()
                        print filename, bufsize
                        f.seek(0,0)
                        if bufsize == 0:
                            file_count = file_count - 1
                        else:
                            head[3] = head[3] + bufsize + 42
                            snd = snd + str_file_start + str_file_end + struct.pack('!i',bufsize) + f.read(bufsize)
                snd = struct.pack('!5i19s19s19s',head[0], head[1],head[2],head[3],file_count,event_time,str_start,str_end) + snd
            else:
                snd = struct.pack('!5i19s19s19s',head[0], head[1],head[2],head[3],file_count,event_time,str_start,str_end)
            print id(self.socket), head[3],len(snd)
            self.sendData(snd)
            time.sleep(0.01)
            while self.snd_len != 0 or not self.sendQueue.empty():
#                 print self.snd_len,'&&&&&&&&&&&&&&',self.sendQueue.qsize()
                time.sleep(0.01)
            time.sleep(0.1)
            print 'subsocksessionHis, sendThread, Finished!!!!!!!!!!!!!!!!!!!!!!'
        dbsession.close()
        self.handle_close()


    @tryException
    def handle_connect(self):
        asyncore.dispatcher_with_send.handle_connect(self)
        Server().asyncserver.addSocket(self)
        if self.connected:
            print 'PackGetIPCHistoryStream111111111:', self.ipc_name, self.addr
#             threading.Thread(target=self.sndThread).start()
#             self.timer.start()
            recordService.ipc_histream_dict[self.ipc_name] = self
            self.sendData(PackGetIPCHistoryStream(Server().server_name,self.ipc_name))
            print 'PackGetIPCHistoryStream2222222222:', self.ipc_name, self.addr
            threading.Thread(target=self.sendThread).start()
        else:
            pass
        
    @tryException
    def handle_close(self):
        AsyncSession.handle_close(self)
        if self.ipc_name in recordService.ipc_histream_dict:
            del recordService.ipc_histream_dict[self.ipc_name]

def setSessionDataState(dev_dict, state, statetime):
    for devdata in dev_dict.values():
        for conf_item in devdata.values():
            name = conf_item[0]
            dataitem = Server().data_dict[name]
            if dataitem.dis_flag == state:
                if dataitem.dis_flag:
                    if dataitem.change_flag == 5:
                        dataitem.change_flag = 4
                        dataitem.dis_flag = False
                        dataitem.dis_time = statetime
                        Server().putCacheData(name)
                    else:
                        pass
                else:
                    dataitem.change_flag = 5
                    dataitem.dis_flag = True
                    dataitem.dis_time = statetime
                    Server().putPreCacheData(name)
            else:
                pass

def processSessState(data, dev_dict):
    session_name = data['session_name']
    state = data['state']
    statetime = data['statetime']
    engine = create_engine(getSqlUrl(),echo=False)
    DBSession = sessionmaker(bind=engine)
    dbsesson = DBSession()
    dbsesson.query(SessionInfo).filter(SessionInfo.name==session_name).update({SessionInfo.state : state,
                                                                               SessionInfo.updatetime : statetime})
    dbsesson.commit()
    dbsesson.close()
    packdata = PackSessionState(Server().server_name, session_name, state, statetime)
    Server().reportData(packdata)
    Server().sendClients(packdata)
    if state is False:
        setSessionDataState(dev_dict, state, statetime)
#         server().collector.stopSession(session_name)
#         server().collector.startSession(session_name)
    else:
        pass
    
def processSessData(data):
#     print 'processSessData:', data
    sess_name = data['sess_name']
    sess_data = data['sess_data']
    for name,value in sess_data.iteritems():
        if name in Server().data_dict:
            change_flag = 0
            if name in Server().cache_data:
                if value <> Server().data_dict[name].value:
                    change_flag = Server().setDataValue(name, value)
                else:
                    pass
            else:
                change_flag = Server().setDataValue(name, value)
                if change_flag > 0:
                    if name not in Server().cache_data:
                        Server().putCacheData(name)
                    else:
                        pass
                else:
                    pass
            if name in Server().collector.disdev_dict:
                if value == 11:
                    dev_id = Server().collector.disdev_dict[name]
                    devdata = Server().collector.session_dict[sess_name].dev_dict.get(dev_id)
                    if devdata is not None:
                        for conf_name,item in devdata.iteritems():
                            if conf_name != 'DisCount':
                                if item[0] in Server().data_dict:
                                    if Server().data_dict[item[0]].dis_flag is False:
                                        Server().data_dict[item[0]].dis_flag = True
                                        Server().data_dict[item[0]].dis_time = Server().data_dict[name].time
                                        Server().data_dict[item[0]].change_flag = 3
                                        Server().putPreCacheData(item[0])
                                    else:
                                        pass
                                else:
                                    pass
                    else:
                        print Server().collector.session_dict[sess_name].dev_dict.keys()
                        print 'processSessData &&&&&&&&&', sess_name, name, dev_id
                elif value == 0:
                    dev_id = Server().collector.disdev_dict[name]
                    devdata = Server().collector.session_dict[sess_name].dev_dict.get(dev_id)
                    if devdata is not None:
                        for conf_name,item in devdata.iteritems():
                            if conf_name != 'DisCount':
                                if item[0] in Server().data_dict:
                                    if Server().data_dict[item[0]].dis_flag is True:
                                        Server().data_dict[item[0]].dis_flag = False
                                        Server().data_dict[item[0]].dis_time = Server().data_dict[name].time
                                        Server().data_dict[item[0]].change_flag = 2
                                        Server().putCacheData(item[0])
                                    else:
                                        pass
                                else:
                                    pass
                    else:
                        print Server().collector.session_dict[sess_name].dev_dict.keys()
                        print 'processSessData &&&&&&&&&', sess_name, name, dev_id
        else:
            if name == 'period':
                period_name = sess_name + '_period'
                if period_name in Server().data_dict:
                    change_flag = Server().setDataValue(period_name, value)
                    if change_flag > 0:
                        Server().putCacheData(name)
                    else:
                        pass
            else:
                print 'processSessData: there is no this data, name is ', name, 'value is', value
    if Server().collector.getReconnect(sess_name):
        Server().collector.setReconnect(sess_name,False)
    Server().startDataProcess()
                

def processDevData(data):
#     dev_name = data['dev_name']s
    devdata = data['devdata']
#     for conf_name, conf_item in devdata.items():
#         pass
#         print conf_name, conf_item
#         if conf_name == 'AI2':
#         if conf_item[0] == '1KT_WJ_1_2_YX':
#         print conf_name, conf_item
    disitem = devdata.get('DisCount')
    if disitem is None:
        return
#     print disitem
    name = disitem[0]
    value  = disitem[1]
    if name in Server().data_dict:
        dis_change_flag = 0
        discount_time = Server().data_dict[name].time
        if name in Server().cache_data:
            if value <> Server().data_dict[name].value:
                dis_change_flag = Server().setDataValue(name, value)
            else:
                pass
        else:
            dis_change_flag = Server().setDataValue(name, value)
            if dis_change_flag > 0:
                Server().putCacheData(name)
            else:
                pass
#         print '------', server().data_dict[name]
#             server().setDataValue(name, None)
#             server().setDataValue(name, value)
        if value == 0:
            for conf_name, conf_item in devdata.iteritems():
                if conf_name == 'DisCount':
                    continue
                name = conf_item[0]
                value  = conf_item[1]
                if name in Server().data_dict:
                    change_flag = 0
                    if name in Server().cache_data:
                        if value <> Server().data_dict[name].value:
                            change_flag = Server().setDataValue(name, value)
                        else:
                            pass
                    else:
                        change_flag = Server().setDataValue(name, value)
                        if change_flag > 0:
                            Server().putCacheData(name)
                        else:
                            pass
                else:
                    print 'processDevData: there is no this data, name is ', name, 'value is', value
        else:
            if dis_change_flag == 11:
                for conf_name, conf_item in devdata.iteritems():
                    if conf_name == 'DisCount':
                        continue
                    name = conf_item[0]
                    value  = conf_item[1]
                    if name in Server().data_dict:
                        if Server().data_dict[name].dis_flag is False:
                            Server().data_dict[name].dis_flag = True
                            Server().data_dict[name].dis_time = discount_time
                            Server().data_dict[name].change_flag = 3
#                             print '------', server().data_dict[name]
                            Server().putPreCacheData(name)
                        else:
                            pass
                    else:
                        print 'processDevData: there is no this data, name is ', name, 'value is', value
            else:
                pass
    else:
        print 'processDevData: there is no this data, name is ', name, 'value is', value
    
@tryException
def processPeriodData(data):
#     print 'processPeriodData:', data
    session_name = data['session_name']
    period = data['period']
    name = session_name + '_period'
    if name in Server().data_dict:
        change_flag = Server().setDataValue(name, period)
        if change_flag > 0:
            Server().putCacheData(name)
        else:
            pass
    else:
        print 'processPeriodData: there is no this data, name is ', name, 'value is', period
    if Server().collector.getReconnect(session_name):
        Server().collector.setReconnect(session_name,False)
    Server().startDataProcess()

@tryException
def processDevID(data):
    session_name = data['session_name']
    dev_name = data['dev_name']
    dev_id = data['dev_id']
    engine = create_engine(getSqlUrl(),echo=False)
    DBSession = sessionmaker(bind=engine)
    dbsesson = DBSession()
    devinfo = dbsesson.query(DeviceInfo).filter_by(name=dev_name).one_or_none()
    devinfo.id = dev_id
    dbsesson.commit()
    dbsesson.close()
    packdata = PackDevIDChanged(session_name, dev_name, dev_id)
    Server().reportData(packdata)
    Server().sendClients(packdata)
    print 'processDevID:', data

@tryException
def processSessionID(data):
    session_name = data['session_name']
    session_id = data['session_id']
    engine = create_engine(getSqlUrl(),echo=False)
    DBSession = sessionmaker(bind=engine)
    dbsesson = DBSession()
    sessioninfo = dbsesson.query(SessionInfo).filter_by(name=session_name).one_or_none()
    sessioninfo.id = session_id
    dbsesson.commit()
    dbsesson.close()
    packdata = PackSessionIDChanged(session_name, session_id)
    Server().reportData(packdata)
    Server().sendClients(packdata)
        
class MyDataCollector(dataCollector):
    def doSessionState(self, data):
        dataCollector.doSessionState(self, data)
#         if data['state']:
#             Server().GPIOCheck_Flag = True
        processSessState(data,self.session_dict[data['session_name']].dev_dict)
        
    def doDevData(self, data):
#         Server().GPIOCheck_Flag = True
        dataCollector.doDevData(self, data)
        processDevData(data)
        
    def doSessData(self, data):
        dataCollector.doSessData(self, data)
        from timercheck import TimerCheck
        TimerCheck().excuteCheck()
        processSessData(data)
        
    def doPeriodFinished(self, data):
        from timercheck import TimerCheck
        TimerCheck().excuteCheck()
        dataCollector.doPeriodFinished(self, data)
        processPeriodData(data)
        
    def doUpdateDevID(self, data):
        dataCollector.doUpdateDevID(self, data)
        processDevID(data)
        
    def doUpdateSessionID(self, data):
        dataCollector.doUpdateSessionID(self, data)
        processSessionID(data)
     
@singleton   
class Server(object):
    def __init__(self, server_name = 'server', host= 'localhost', session_dict=UserDict(), port=8899):
        self.server_name = server_name
        self.host = host
        self.port = port
        self.asyncserver = AsyncServer(host,port,self.handleConnect)
        self.collector = MyDataCollector().initSessions(session_dict)
        self.subsv_dict = UserDict()
        self.subnameip_dict = UserDict()
        self.videosv_dict = UserDict()
        self.videonameip_dict = UserDict()
        self.ipcvideo_dict = UserDict()
        self.superserver = None
        self.prevideosv_dict = UserDict()
        self.init_flag = False
        self.init_time = datetime.now()
        self.user_dict = UserDict()
        self.transmitdatasvs_dict = UserDict()
        self.data_dict = UserDict()
        self.dataconf_dict = UserDict()
        self.cache_data = set()
        self.precache_data = set()
        self.cache_mutex = threading.Lock()
        self.precache_mutex = threading.Lock()
        self.machineInfo = raspberrypi_info()
        self.WriteDBflag = True
        self.WriteDBCache = list()
        self.dbcache_mutex = threading.Lock()
        self.WriteDB = None
        self.ServerState = None
        self.preuser_dict = UserDict()
        self.cmpFlag = False
        self.calate_mutex = threading.Lock()
        self.PARAM_Flag = False
        self.PARAM_TimerFlag = False
        self.streamService = None
        self.remote_session = None
        self.video_local_main = None
        self.video_remote_main = None
        self.delFlag = False
        self.remote_ip = socket.gethostbyname('thic.cn')
        self.collectTimer = threading.Timer(60,self.collectCheck)
        
    def delHistoryData(self):
        if self.delFlag:
            return
        self.delFlag = True
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        subdir = 0
        for rh in dbsesson.query(RecordHistroy).order_by(RecordHistroy.id).limit(24*60*30):
            subdir = rh.start.year*1000000 + rh.start.month*10000 + rh.start.day*100 + rh.start.hour
#             subname = rh.name + '/' + str(subdir)
            delname = '{0}/{1}/{2}-{3}.mp4'.format(rh.name,subdir,rh.start.strftime('%Y-%m-%d %H:%M:%S'),
                                                   rh.end.strftime('%Y-%m-%d %H:%M:%S'))
#             delname = subname + '/' + rh.start.strftime('%Y-%m-%d %H:%M:%S') + '-' + rh.end.strftime('%Y-%m-%d %H:%M:%S') + '.mp4'
            print delname
            if os.path.exists(delname):
                os.remove(delname)
                print '---------------', delname
            dbsesson.delete(rh)
        dh1 = dbsesson.query(DataHistory).order_by(DataHistory.id).first()
        if dh1 is not None:
            end = dh1.addtime
            start = dh1.addtime - timedelta(days=1)
            dbsesson.query(DataHistory).filter(and_(DataHistory.addtime >= start,DataHistory.addtime <= end)).delete()
        else:
            pass
        dbsesson.commit()
        dbsesson.close()
        if self.streamService is not None:
            for name in self.streamService.ipc_dict.keys():
                if os.path.exists(name):
                    for subname in os.listdir(name):
                        if subdir > int(subname):
                            for ssubname in os.listdir(name + '/' + subname):
                                os.remove(name + '/' + subname + '/' + ssubname)
                            os.removedirs(name + '/' + subname)
#                             os.removedirs(name + '/' + subname)
#                         if not os.listdir(name + '/' + subname):
#                             os.removedirs(name + '/' + subname)
#                         else:
#                             pass
                            
                else:
                    pass
        else:
            pass
        self.delFlag = False
      
    @tryException  
    def setMachineData(self):
        info = self.machineInfo.startCmp()
        for k, v in info.iteritems():
            data_name = self.server_name + '_' + k
            if v is not None:
                if self.data_dict[data_name].setValue(v) > 0:
                    self.putCacheData(data_name)
                else:
                    pass
            else:
                pass
    
    @tryException
    def dataSetPasson(self, dataset):
#         print 'dataSetPasson:--------------------', len(dataset)
        for name in dataset:
            dataitem = self.data_dict.get(name)
            if dataitem is None:
                continue
            dataconf = self.dataconf_dict[name]
            packdata = PackDataInfo(dataitem, dataconf, 255)
#             time.sleep(0.001)
            if dataitem.attribute <> 0:
                self.reportData(packdata)
            self.newSendClients(packdata,name)
#             ipcs = dataconf.get('ipcs')
#             for ipc in ipcs:
#                 if ipc in self.ipcvideo_dict:
#                     v_name = self.ipcvideo_dict[ipc]
#                     ip = self.videonameip_dict[v_name]
#                     self.videosv_dict[ip].passonData(packdata)
#                     time.sleep(0.001)
        if self.superserver is not None and self.superserver.reconnect:
            diff_dataset = set(self.data_dict.keys()) - dataset
            #上报未变数据
            for name in diff_dataset:
                dataitem = self.data_dict.get(name)
                if dataitem is None:
                    continue
                dataconf = self.dataconf_dict[name]
                if dataitem.attribute <> 0:
                    packdata = PackDataInfo(dataitem, dataconf, 1)
#                     time.sleep(0.001)
                    self.reportData(packdata)
            for name, session in self.collector.session_dict.iteritems():
                packdata = PackSessionState(self.server_name, name, session.state, session.statetime)
#                 time.sleep(0.001)
                self.reportData(packdata)
            self.superserver.reconnect = False
        else:
            pass
        for sv in self.subsv_dict.values():
            if sv.reconnect:
#                 print '000000000000000000000000000000000000000000000000000'
                for data_name,svnames in self.transmitdatasvs_dict.iteritems():
#                     print data_name, svnames
                    for svname in svnames:
                        if svname == sv.server_name:
                            dataitem = self.data_dict.get(data_name)
                            if dataitem is None:
                                continue
#                             print '1111111', dataitem,'11111'
                            dataconf = self.dataconf_dict[data_name]
                            packdata = PackDataInfo(dataitem, dataconf, 0)
#                             time.sleep(0.001)
                            sv.passonData(packdata)
#                             print sv.passonData(packdata), '000000000',dataitem
                            
                sv.reconnect = False
        #下发变化的转发数据
        trans_names =  dataset & set(self.transmitdatasvs_dict.keys())
        for data_name in trans_names:
#             if data_name == 'KT_XHB_YQ_WJ':
#                 print '&&&&&&', self.transmitdatasvs_dict[data_name]
            dataitem = self.data_dict.get(data_name)
            if dataitem is None:
                continue
            dataconf = self.dataconf_dict[data_name]
            packdata = PackDataInfo(dataitem, dataconf, 0)
            sv_names = self.transmitdatasvs_dict[data_name]
            for svname in sv_names:
                ip = self.subnameip_dict[svname]
                sv = self.subsv_dict[ip]
                if sv is not None and sv.reconnect is False:
#                     time.sleep(0.001)
                    sv.passonData(packdata)
                else:
                    pass
        
    @tryException
    def executeLogic(self, name, logic, midSet, logic_type='JS'):
        t, handle = logic.getLogicCP()
        if t == logic_type and handle is not None:
            handle(name,logic,midSet,self)
            return True
        else:
            return False
        
    @tryException
    def startCMP(self):
#         return self.getAllCacheData()
        midSet = set()
        for i in xrange(logicSet().getDelayLogiclength()):
            name, logic, ltime = logicSet().popDelayLogic()
            if datetime.now() >= ltime:
                if self.executeLogic(name, logic, midSet) is False:
                    logicSet().addDelayLogic(name, logic, ltime)
                else:
                    pass
            else:
                logicSet().addDelayLogic(name, logic, ltime)
        newSet = midSet | self.getAllCacheData()
        cmpCount = 0
        dataSet = set()
        while True:
            cmpCount = cmpCount + 1
            midSet.clear()
            for name in newSet:
                logics = logicSet().getDataLogicList(name)
                if logics is not None:
                    for logic in logics:
                        self.executeLogic(name, logic, midSet)
                else:
                    pass
            dataSet = dataSet | newSet
            if len(midSet) > 0:
                newSet = copy.deepcopy(midSet)
#                 if cmpCount > 1:
#                     print 'startCMP:', newSet
#                 elif cmpCount > 50:
#                     print 'cmpCount>50','JS_Logic Finished!!!!!!!!!!!!!!!!!!!!!!!!!!!' 
#                     break
            else:
                break
#         print cmpCount,'JS_Logic Finished!!!!!!!!!!!!!!!!!!!!!!!!!!!'
        for i in xrange(logicSet().getDelayLogiclength()):
            name, logic, ltime = logicSet().popDelayLogic()
            if datetime.now() >= ltime:
                if self.executeLogic(name, logic, midSet, 'KZ') is False:
                    logicSet().addDelayLogic(name, logic, ltime)
                else:
                    pass
            else:
                logicSet().addDelayLogic(name, logic, ltime)
        dataSet = dataSet | midSet
        midSet.clear()
        for name in dataSet:
            logics =logicSet().getDataLogicList(name)
            if logics is not None:
                for logic in logics:
                    self.executeLogic(name, logic, midSet, 'KZ')
        for name in midSet:
            self.putCacheData(name)
#         print 'startCMPFINISHED:', dataSet
        return dataSet
        
    @tryException
    def sendCtrlCMD(self, data_name, instr, delay_second):
        dataconf = self.dataconf_dict.get(data_name)
        if dataconf.get('server_name') == self.server_name:
            session_name = dataconf.get('session_name')
            dev_name = dataconf.get('dev_name')
            conf_name = dataconf.get('conf_name')
            return self.collector.putSessionCMD(session_name, dev_name, conf_name, instr, delay_second)
        else:
            return False
        
    def updateDataConf(self, data_name, dataconstraint):
        if data_name in self.data_dict:
            self.data_dict[data_name].constraint = dataconstraint
            return True
        else:
            return False
        
    def setDataValue(self, data_name, value):
        if data_name in self.data_dict:
            return self.data_dict[data_name].setValue(value)
        else:
            return False
        
    def setDataReason(self, data_name, reason):
        if data_name in self.data_dict:
            self.data_dict[data_name].reason = reason
        else:
            pass
        
    def getDataValue(self, data_name):
        dataitem = self.data_dict.get(data_name)
        value = None
        if dataitem is not None:
            value = dataitem.getValue()
            if dataitem.dis_flag:
                dataconf = self.dataconf_dict.get(data_name)
                dis_interval = dataconf.get('dis_interval')
                if (dataitem.dis_time is None) or \
                (datetime.now() - dataitem.dis_time).total_seconds() >= dis_interval * 60:
                    value = None
            else:
                pass
        else:
            pass
        return value
        
    @tryException
    def updateWriteDBCache(self, dataset):
        self.dbcache_mutex.acquire()
        tempset = dataset - set(self.WriteDBCache)
        self.WriteDBCache.extend(list(tempset))
        self.dbcache_mutex.release()
      
    @tryException
    def popWriteDBData(self):
        data = None
        self.dbcache_mutex.acquire()
        if len(self.WriteDBCache) > 0:
            data = self.WriteDBCache.pop(0)
        else:
            pass
        self.dbcache_mutex.release()
        return data
    
    def newSendClients(self, packdata, name):
        for user in self.user_dict.values():
            if user.uploadFlag or packdata[0] in user.echoProtSet and name not in user.dataSet:
                user.sendData(packdata[1])
    
    def sendClients(self, packdata):
        for user in self.user_dict.values():
            if user.uploadFlag or packdata[0] in user.echoProtSet:
                user.sendData(packdata[1])
            else:
                pass
    
    def reportData(self, packdata):
        if self.superserver is not None:
            return self.superserver.reportData(packdata)
        else:
            return False
        
    def passonData(self, server_name, packdata):
        if server_name in self.subnameip_dict:
            return self.subsv_dict[self.subnameip_dict[server_name]].passonData(packdata)
        elif server_name in self.videonameip_dict:
            return self.videosv_dict[self.videonameip_dict[server_name]].passonData(packdata)
        else:
            return False
        
    @tryException
    def startDataProcess(self):
        self.calate_mutex.acquire()
        if self.init_flag is False:
            self.initFinished()
        if self.init_flag and self.cmpFlag is False:
            threading.Thread(target=self.startCaculate).start()
        self.calate_mutex.release()
        
    def initFinished(self):
#         print 'initFinished:', self.getFinishState(), self.PARAM_Flag,'!!!!!!!!!!!!!!!!!!!!!!!!!'
        if self.getFinishState() and self.PARAM_Flag:
            self.init_flag = True
            self.init_time = datetime.now()
            self.ServerState(self, self.server_name, self.init_flag, self.init_time)
#                 self.doServerState(self.server_name, self.init_flag, self.init_time)
            packdata = PackServiceState(self.server_name, True, datetime.now())
            self.sendClients(packdata)
            for i in range(2):
                th = threading.Thread(target= self.WriteDB, args= (self,))
                th.start()
        else:
            pass
        
    @tryException
    def startCaculate(self):
#         print datetime.now(), 'startCaculate cmpFlag: ', self.cmpFlag,'----------'
        
#         print '磁盘占用率：', self.getDataValue(data_name)
#                 删除视频文件或数据库中的历史数据
        self.setMachineData()
        if self.cmpFlag:
            return
        data_name = self.server_name + '_DISK_perc'
        if self.getDataValue(data_name) > 90:
            threading.Thread(target=self.delHistoryData).start()
#         print 'startCaculate PARAM_Flag: ', self.PARAM_Flag, '---------------', self.init_flag, self.PARAM_Flag
        self.cmpFlag = True
        if self.getFinishState():
            #所有服务器完成标记改成False
            self.setFinishState()
            #上报服务器开始上报标记
            packdata = PackServerFinished(self.server_name, 1)
            self.reportData(packdata)
            #计算逻辑开始
            
            dataSet = self.startCMP()
            self.dataSetPasson(dataSet)
            self.updateWriteDBCache(dataSet)
            del dataSet
            #上报服务器上报完成标记
            packdata = PackServerFinished(self.server_name, 255)
            self.reportData(packdata)
            del packdata
        else:
            pass
        self.cmpFlag = False
        
        
    @tryException
    def getAllCacheData(self):
        self.cache_mutex.acquire()
        dataSet = self.cache_data | self.getPreDataSet()
        self.cache_data.clear()
        self.cache_mutex.release()
        return dataSet
    
    @tryException
    def putCacheData(self, name):
        self.cache_mutex.acquire()
        if name in self.precache_data:
            self.precache_mutex.acquire()
            self.precache_data.remove(name)
            self.precache_mutex.release()
        self.cache_data.add(name)
        self.cache_mutex.release()
        
    @tryException
    def getAllPreCacheData(self):
        self.precache_mutex.acquire()
        dataSet = copy.deepcopy(self.precache_data)
        self.precache_data.clear()
        self.precache_mutex.release()
        return dataSet
        
    @tryException
    def putPreCacheData(self, name):
        self.precache_mutex.acquire()
        self.precache_data.add(name)
        self.precache_mutex.release()
        
    def getPreDataSet(self):
        dataset = set()
        preDataSet = self.getAllPreCacheData()
        for name in preDataSet:
            dataconf = self.dataconf_dict.get(name)
            dis_time = self.data_dict.get(name).dis_time
            if dis_time is None:
                if (datetime.now() - self.init_time).total_seconds() >= dataconf.get('dis_interval') * 60:
                    dataset.add(name)
                else:
                    if name not in self.cache_data:
                        self.putPreCacheData(name)
                    else:
                        pass
            else:
                if (datetime.now() - dis_time).total_seconds() >= dataconf.get('dis_interval') * 60:
                    dataset.add(name)
                else:
                    if name not in self.cache_data:
                        self.putPreCacheData(name)
                    else:
                        pass
        return dataset
        
    def doServerState(self, server_name, state, statetime):
#         print 'doServerState: ', server_name, state, statetime
        packdata = PackServerState(self.server_name, server_name, state, statetime)
        self.sendClients(packdata)
        self.reportData(packdata)
        self.ServerState(self, server_name, state, statetime)
        
    @tryException
    def collectCheck(self):
        engine = create_engine(getSqlUrl(),echo=False)
        DBSession = sessionmaker(bind=engine)
        dbsesson = DBSession()
        InitSerialNo(dbsesson)
        dbsesson.close()
        if len(Session_SerailMap) > 0:
            self.collector.StartCollect()
        else:
            self.collectTimer.cancel()
            del self.collectTimer
            self.collectTimer = threading.Timer(60,self.collectCheck)
            self.collectTimer.start()
            
    def start(self, timeout, WriteDB= WriteDB, ServerState=ServerState):
        self.WriteDB = WriteDB
        self.ServerState = ServerState
        threading.Timer(timeout,self.handleTimer).start()
        if self.streamService is not None:
            self.streamService.startService(local_name,self.host)
        else:
            if len(Session_SerailMap) > 0:
                self.collector.StartCollect()
            else:
                self.collectTimer.cancel()
                del self.collectTimer
                self.collectTimer = threading.Timer(60,self.collectCheck)
                self.collectTimer.start()
#         while True:
#             time.sleep(0.1)
        self.asyncserver.run()
        from timercheck import TimerCheck
        TimerCheck()
        threading.Thread(target=self.asyncserver.sndThread).start()
#         threading.Thread(target=asyncore.loop()).start()
#         threading.Timer(10,self.setSessionID,args=['DN_SANSU',10]).start()
        try:
            asyncore.loop(timeout=2)
        except Exception as e:
            print 'sever start:', e
        
    def getFinishState(self):
#         print 'getFinishState:',self.collector.getAllSessionFinishState(),
        if self.collector.getAllSessionFinishState() is False:
            return False
        for sv in self.subsv_dict.values():
#             print 'getFinishState: sv', sv.getFinishState()
            if sv.getFinishState() is False:
                return False
        return True
    
    def setFinishState(self):
        self.collector.setAllSessionFinish()
        for sv in self.subsv_dict.values():
            sv.setFinishFlag(False)
        
    def handleTimer(self):
        if self.init_flag is False:
            for sv in self.subsv_dict.values():
                if sv.wait_flag is False:
                    sv.setFinishFlag(True)
                else:
                    pass
            self.startDataProcess()
        else:
            pass
        
    @tryException
    def initServer(self, data_dict, dataconf_dict, transmitdatasvs_dict, subsv_dict, videosv_dict, 
                   superdata=None, ipc_dict=None, default=False):
        self.data_dict = data_dict
        self.dataconf_dict = dataconf_dict
        self.transmitdatasvs_dict = transmitdatasvs_dict
        if default is False:
            if superdata is not None:
                self.superserver = superior(superdata['server_name'],superdata['ip'],
                                            AsyncSession(superdata['ip'],self.port,self.handleData,self.doConnect,self.doClose),
                                            superdata['state'],
                                            superdata['statetime'])
            for ip, subsvdata in subsv_dict.iteritems():
                self.subsv_dict[ip] = subordinate(subsvdata[0],subsvdata[1],subsvdata[2],subsvdata[3])
                self.subnameip_dict[subsvdata[0]] = ip
            for ip, vdsvdata in videosv_dict.iteritems():
                self.videosv_dict[ip] = videoserver(vdsvdata[0],vdsvdata[1],vdsvdata[2])
                self.videonameip_dict[vdsvdata[0]] = ip
                for ipc in vdsvdata[3]:
                    self.ipcvideo_dict[ipc] = vdsvdata[0]
        else:
            if superdata is not None:
                superior(superdata['server_name'],superdata['ip'],
                         AsyncSession(superdata['ip'],self.port,self.handleData,self.doConnect,self.doClose))
            for ip, subsvdata in subsv_dict.iteritems():
                self.subsv_dict[ip] = subordinate(subsvdata[0],subsvdata[1])
                self.subnameip_dict[subsvdata[0]] = ip
            for ip, vdsvdata in videosv_dict.iteritems():
                self.videosv_dict[ip] = videoserver(vdsvdata[0])
                self.videonameip_dict[vdsvdata[0]] = ip
        if ipc_dict is not None:
#             def recordFunc(name,start,end):
#                 engine = create_engine(getSqlUrl(),echo=False)
#                 DBSession = sessionmaker(bind=engine)
#                 dbsession = DBSession()
#                 dbsession.add(RecordHistroy(name,start,end))
#                 dbsession.commit()
#                 dbsession.close()
            self.streamService = recordService(ipc_dict)
            self.video_local_main = AsyncSession(video_ip,int(video_port),self.handleData,self.doConnect,self.doClose)
            self.video_remote_main = AsyncSession(self.remote_ip,int(video_port),self.handleData,self.doConnect,self.doClose)
        if superdata is None:
            self.PARAM_Flag = True
#             self.remote_ip = '172.16.1.2'
            user = AsyncSession(self.remote_ip,int(remote_port),self.handleData,self.doConnect,self.doClose)
            self.remote_session = user
            user.uploadFlag = False
            user.echoProtSet = set()
            self.preuser_dict[id(user)] = user
        else:
            pass
                
    @tryException
    def handleData(self, sockSession):
        buf = sockSession.recv(8192)
#         print '---------------------------', len(buf)
        if len(buf) > 0:
            sockSession.readbuf = sockSession.readbuf + buf
        else:
            return
        try:
            while len(sockSession.readbuf) >= sockSession.bufsize:
                buftemp  = sockSession.readbuf[sockSession.bufsize:]
                if sockSession.bufsize == 16:
                    head = struct.unpack('!4i', sockSession.readbuf[:16])
                    if head[3] > 0:
                        sockSession.bufsize = head[3]
                        sockSession.head = head
                    else:
                        sockSession.bufsize = 16
                        sockSession.head = None
    #                     print sockSession.addr[0], '心跳！！！！！！！！！！'
                else:
    #                 print sockSession.addr[0], sockSession.head, sockSession.readbuf[:sockSession.bufsize]
    #                 body = json.loads(sockSession.readbuf[:sockSession.bufsize].decode(encoding='UTF-8'))
    #                 print sockSession.addr[0], 'json body: ', body
                    tempbuf = sockSession.readbuf[:sockSession.bufsize]
                    body = json.loads(tempbuf)
                    if sockSession.head[2] in doMesssages:
                        try:
                            doMesssages[sockSession.head[2]](self, sockSession, sockSession.head, body)
                        except Exception as e:
                            print 'handleReceive Error: ', sockSession.addr[0], sockSession.head[2],body,e
                    sockSession.bufsize = 16
                    sockSession.head = None
                sockSession.readbuf = buftemp
        except Exception  as e:
            print 'handleData:', e, sockSession.readbuf, len(sockSession.readbuf), sockSession.bufsize
            sockSession.close()
#         print len(sockSession.readbuf), sockSession.bufsize
    
    def doConnect(self, sockSession):
        print 'doConnect:', sockSession.addr[0]
        self.asyncserver.addSocket(sockSession)
        if sockSession.addr[0] <> self.remote_ip and sockSession.addr[0] <> video_ip:
            self.superserver.setState(True, datetime.now())
            self.superserver.reconnect = True
            self.doServerState(self.superserver.server_name, self.superserver.state, self.superserver.statetime)
        else:
            self.GPIOClient_Flag = True
#             print 'remote Connect :',sockSession.addr[0]
            
    def setRefParamFlag(self):
        print datetime.now(), 'self.setRefParamFlag SET!!!'
        if self.superserver.state is False:
            self.PARAM_Flag = True
        else:
            self.PARAM_TimerFlag = False
            
    def videoRemoteReconnect(self):
#         print datetime.now(), 'self.videoRemote Reconnect!'
        self.remote_ip = socket.gethostbyname('thic.cn')
        self.video_remote_main = AsyncSession(self.remote_ip,int(video_port),self.handleData,self.doConnect,self.doClose)
        
    def videoLocalReconnect(self):
        print datetime.now(), 'self.videoLocal Reconnect!'
        self.video_local_main = AsyncSession(video_ip,int(video_port),self.handleData,self.doConnect,self.doClose)
        
    def superReconnect(self):
#         print datetime.now(), 'self.superserver Reconnect!'
        try:
            self.superserver.socksession = AsyncSession(self.superserver.ip, self.port, self.handleData, self.doConnect, self.doClose)
        except Exception as e:
            print 'superReconnect got error:',e
             
        
    @tryException
    def remoteReconnect(self):
        try:
            self.remote_ip = socket.gethostbyname('thic.cn')
#             self.remote_ip = '172.16.1.2'
            print datetime.now(), 'remote Reconnect!', self.remote_ip
        
            user = AsyncSession(self.remote_ip,int(remote_port),self.handleData,self.doConnect,self.doClose)
            self.remote_session = user
            user.uploadFlag = False
            user.echoProtSet = set()
            self.preuser_dict[id(user)] = user
        except Exception as e:
            print 'remoteReconnect got error:',e
    
    @tryException
    def doClose(self, sockSession):
        ip = sockSession.addr[0]
        port = sockSession.addr[1]
        print datetime.now(),'doClose:', sockSession.addr
        if ip in self.subsv_dict:
            if self.subsv_dict[ip].state:
                self.subsv_dict[ip].setFinishFlag(True)
                self.subsv_dict[ip].wait_flag = False
                self.subsv_dict[ip].reconnect = False
                self.subsv_dict[ip].setState(False,datetime.now())
                self.doServerState(self.subsv_dict[ip].server_name, self.subsv_dict[ip].state, 
                                   self.subsv_dict[ip].statetime)
            else:
                pass
        elif ip in self.videosv_dict:
            if self.videosv_dict[ip].state:
                self.videosv_dict[ip].setState(False,datetime.now())
                self.doServerState(self.videosv_dict[ip].server_name, self.videosv_dict[ip].state, 
                                   self.videosv_dict[ip].statetime)
            else:
                pass
        elif ip in self.user_dict:
            if ip in self.user_dict:
                self.user_dict.pop(ip)
        else:
            if self.superserver is not None and ip == self.superserver.socksession.addr[0]:
#                 print self.superserver.socksession.addr[0],ip
#                 print 'self.PARAM_TimerFlag', self.PARAM_TimerFlag
#                 print 'self.PARAM_Flag', self.PARAM_Flag
                if self.superserver.state:
                    self.superserver.setState(False,datetime.now())
                    self.doServerState(self.superserver.server_name, self.superserver.state, 
                                       self.superserver.statetime)
                else:
                    pass
                if self.PARAM_TimerFlag is False:
                    self.PARAM_TimerFlag = True
                    threading.Timer(float(timeout_refparam),self.setRefParamFlag).start()
            else:
                if id(sockSession) in self.preuser_dict:
                    self.preuser_dict.pop(id(sockSession))
                
    def handleConnect(self, pair):
        print 'handleConnect:', pair
        ip = pair[1][0]
        if ip in self.subsv_dict:
            if self.subsv_dict[ip].state != True:
                self.subsv_dict[ip].socksession = AsyncClient(pair[0], self.handleData, self.doClose)
                self.asyncserver.addSocket(self.subsv_dict[ip].socksession)
                self.subsv_dict[ip].wait_flag = True
                self.subsv_dict[ip].reconnect = True
                self.subsv_dict[ip].setState(True,datetime.now())
                self.doServerState(self.subsv_dict[ip].server_name, self.subsv_dict[ip].state, 
                                   self.subsv_dict[ip].statetime)
                if self.PARAM_Flag:
                    self.subsv_dict[ip].socksession.sendData(PackRefParamINIT())
            else:
                pair[0].close()
#                 print datetime.now(), 'handleConnect:',pair[0], 'close()'
        elif ip in self.videosv_dict:
            if self.videosv_dict[ip].state != True:
                self.videosv_dict[ip].socksession = AsyncClient(pair[0], self.handleData, self.doClose)
                self.asyncserver.addSocket(self.videosv_dict[ip].socksession)
                self.videosv_dict[ip].setState(True,datetime.now())
                self.doServerState(self.videosv_dict[ip].server_name, self.videosv_dict[ip].state, 
                                   self.videosv_dict[ip].statetime)
                if self.PARAM_Flag:
                    self.videosv_dict[ip].socksession.sendData(PackVideoServerIPCS(self.videosv_dict[ip].server_name))
                    self.videosv_dict[ip].socksession.sendData(PackRefParamINIT())
            else:
                pair[0].close()
#                 print datetime.now(), 'handleConnect:', pair, self.subsv_dict
        else:
            user = AsyncClient(pair[0], self.handleData, self.doClose)
            self.asyncserver.addSocket(user)
#             user.debug = True
            user.uploadFlag = False
            user.echoProtSet = set()
            self.preuser_dict[id(user)] = user
