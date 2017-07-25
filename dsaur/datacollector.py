#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年12月19日

@author: sanhe
'''

from UserDict import UserDict
from serial_session import serial_session, READ_INTERVAL
import greenlet
import threading
import multiprocessing
from util import tryException
import time
from datetime import datetime

def startSession_task(collector, data):
    print 'startSession_task:', data
    if not collector.session_dict[data['session_name']].state:
        collector.removePreSendSession(data['session_name'])
        collector.removeDisSession(data['session_name'])
        if collector.session_dict[data['session_name']].openSerial():
            collector.appendSendSession(data['session_name'])
            collector.putHandleData('sessionstate', {'session_name' : data['session_name'],
                                                     'state' : collector.session_dict[data['session_name']].state,
                                                     'statetime' : collector.session_dict[data['session_name']].statetime})
        else:
            collector.appendDisSession(data['session_name'])
    else:
        pass
            
def stopSession_task(collector, data):
    print 'stopSession_task:', data
    if collector.removeRecvSession(data['session_name']):
        collector.session_dict[data['session_name']].cycleCmdDeque.\
        append(collector.session_dict[data['session_name']].sendCmd)
    else:
        collector.removeSendSession(data['session_name'])
    if collector.session_dict[data['session_name']].closeSerial():
        collector.putHandleData('sessionstate', {'session_name' : data['session_name'],
                                                 'state' : collector.session_dict[data['session_name']].state,
                                                 'statetime' : collector.session_dict[data['session_name']].statetime})
    else:
        collector.removePreSendSession(data['session_name'])
        collector.removeDisSession(data['session_name'])
    collector.appendDisSession(data['session_name'])

def putSessionCMD_task(collector, data):
#     print 'putSessionCMD_task:', data, data['delay_second']
    CMD = collector.session_dict[data['session_name']].genControlInstr(data['dev_name'],
                                                                       data['conf_name'],
                                                                       data['instr'])
    if CMD is not None:
        if data['delay_second'] > 0:
            th = threading.Thread(target= collector.session_dict[data['session_name']].CmdThread, 
                                  args= (CMD, data['delay_second']))
            th.start()
        else:
            collector.session_dict[data['session_name']].AddSendCmd(CMD)
    else:
        pass

def updateDevID_task(collector, data):
    print 'updateDevID_task:', data
    old_id = collector.session_dict[data['session_name']].updateDevID(data['dev_name'],data['dev_id'])
    if old_id:
        print 'updateDevID_task:', old_id
        collector.putHandleData('updatedevid', {'session_name' : data['session_name'],
                                                'dev_name' : data['dev_name'],
                                                'dev_id' : data['dev_id'],
                                                'old_id' : old_id})
    else:
        pass
    
def updateSessionID_task(collector, data):
    print 'updateSessionID_task:', data
    collector.session_dict[data['session_name']].session_id = data['session_id']
    collector.putHandleData('updatesessid', {'session_name' : data['session_name'],'session_id' : data['session_id']})

class MyTaskThread(threading.Thread):
    def __init__(self, collector):
        threading.Thread.__init__(self)
        self.collector = collector
        self.stop_thread = False
        self.queue = multiprocessing.Queue()
        self.tlock = multiprocessing.Lock()
        
    def putHandleData(self, handle, data=None):
        self.queue.put({'handle' : handle, 'data' : data})
#         self.tlock.acquire()
#         self.queue.put_nowait({'handle' : handle, 'data' : data})
#         self.tlock.release()
        
    @tryException
    def dohandle(self, data):
        if data['handle']:
#             print 'taskThread dohandle:', data
            data['handle'](self.collector, data['data'])
        else:
            pass
        
    def run(self):
        while not self.stop_thread :
            data = None
            data = self.queue.get()
#             self.tlock.acquire()
#             if not self.queue.empty():
#                 data = self.queue.get_nowait()
#             else:
#                 pass
#             self.tlock.release()
            if data is not None:
                self.dohandle(data)
#                 time.sleep(0.001)
            else:
                time.sleep(0.001)
                
        def stop(self):
            self.stop_thread = True
            self.queue.close()

class dataCollector(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.__stop_thread = False
        self.__queue = multiprocessing.Queue()
        self.__queue_data = multiprocessing.Queue()
        self.__lock = multiprocessing.Lock()
        self.__handle_map = {'period' : self.doPeriodFinished,
                             'devdata' : self.doDevData,
                             'sessionstate' : self.doSessionState,
                             'updatedevid' : self.doUpdateDevID,
                             'updatesessid' : self.doUpdateSessionID,
                             'sessdata' : self.doSessData}
        self.session_dict = UserDict()
        self.__sendlist = list()
        self.__sendLock = threading.Lock()
        self.__recvlist = list()
        self.__recvLock = threading.Lock()
        self.presendlist = list()
        self.presendLock = threading.Lock()
        self.dis_sessions= list()
        self.dis_sessLock = threading.Lock()
        self.__alive = True
        self.__collect_process = None
        self.session_data = UserDict()
        self.disdev_dict = UserDict()
        self.puttime = datetime.now()
        
    @tryException
    def StartCollect(self):
#         p = multiprocessing.Process(target=self.doRevData)
#         p.start()
        self.start()
        self.__taskthread = MyTaskThread(self)
#         self.__startDataPatrol()
        self.__collect_process = multiprocessing.Process(name='DataPatrol',target=self.__startDataPatrol)
        self.__collect_process.start()
#         print 'StartCollect:', datetime.now(), 'Over!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
        
    def stopCollect(self):
        self.__collect_process.terminate()
        self.__stop()
        
    def __startDataPatrol(self):
        self.__taskthread.start()
        for name,sess in self.session_dict.items():
            if sess.openSerial():
                self.appendSendSession(name)
                self.putHandleData('sessionstate',{'session_name' : name,
                                                   'state' : self.session_dict[name].state,
                                                   'statetime' : self.session_dict[name].statetime})
            else:
                self.putHandleData('period',{'session_name' : name,'period' : None})
                self.appendDisSession(name)
        self.sendGR = greenlet.greenlet(self.__sendData)
        self.recvGR = greenlet.greenlet(self.__receiveData)
        self.sendGR.switch()
        print '__startDataPatrol exit :', self.__alive, datetime.now()
        
    def putTaskHandleData(self, handle, data):
        self.__taskthread.putHandleData(handle, data)
        
    def startSession(self, session_name):
        data = {}
        data['session_name'] = session_name
        if session_name in self.session_dict and not self.session_dict[session_name].state:
            self.putTaskHandleData(startSession_task, data)
            return True
        else:
            return False
        
    def stopSession(self, session_name):
        data = {}
        data['session_name'] = session_name
        if session_name in self.session_dict and self.session_dict[session_name].state:
            self.putTaskHandleData(stopSession_task, data)
            return True
        else:
            return False
            
    def updateSessionID(self, session_name, session_id):
        data = {}
        data['session_name'] = session_name
        data['session_id'] = session_id
        if session_name in self.session_dict:
            for sess in self.session_dict.values():
                if sess.session_id == session_id:
                    return False
            if self.session_dict[session_name].state:
                if self.stopSession(session_name):
                    self.putTaskHandleData(updateSessionID_task, data)
                    self.startSession(session_name)
                    return True
                else:
                    return False
            else:
                self.putTaskHandleData(updateSessionID_task, data)
                self.startSession(session_name)
                return True
        else:
            return False
        
    def updateDevID(self, session_name, dev_name, dev_id):
        data = {}
        data['session_name'] = session_name
        data['dev_name'] = dev_name
        data['dev_id'] = dev_id
        session = self.session_dict.get(session_name)
        if session is not None and dev_name in session.dev_dict.name_idMap:
            self.putTaskHandleData(updateDevID_task, data)
            return True
        else:
            return False
        
    def putSessionCMD(self, session_name, dev_name, conf_name, instr, delay_second):
        data = {}
        data['session_name'] = session_name
        data['dev_name'] = dev_name
        data['conf_name'] = conf_name
        data['instr'] = instr
        data['delay_second'] = delay_second
        if session_name in self.session_dict and self.session_dict[session_name].state:
            self.putTaskHandleData(putSessionCMD_task, data)
            return True
        else:
            return False
        
    def doPeriodFinished(self, data):
        session_name = data['session_name']
        self.session_dict[session_name].setFinishFlag(True)
#         print data

    def doSessData(self, data):
        session_name = data['sess_name']
        self.session_dict[session_name].setFinishFlag(True)
#         print 'doSessData:', data
    
    def doDevData(self, data):
        pass
#         print datetime.now(), 'doDevData:'
#         print data

    def getReconnect(self, session_name):
        return self.session_dict[session_name].reconnect
    
    def setReconnect(self, session_name, flag):
        self.session_dict[session_name].reconnect = flag
        
    def doSessionState(self, data):
        session_name = data['session_name']
        state = data['state']
        statetime = data['statetime']
        self.session_dict[session_name].state = state
        self.session_dict[session_name].statetime = statetime
        if state is False:
            self.setReconnect(session_name, False)
            self.session_dict[session_name].setFinishFlag(True)
        else:
            self.setReconnect(session_name, True)
#         print data
        
    def doUpdateDevID(self, data):
        session_name = data['session_name']
        dev_name = data['dev_name']
        dev_id = data['dev_id']
        old_id = data['old_id']
        self.session_dict[session_name].dev_dict.name_idMap[dev_name] = dev_id
        del self.session_dict[session_name].dev_dict.id_nameMap[old_id]
        self.session_dict[session_name].dev_dict.id_nameMap[dev_id] = dev_name
        print 'doUpdateDevID:', data
        
    def doUpdateSessionID(self, data):
        session_name = data['session_name']
        session_id = data['session_id']
        self.session_dict[session_name].session_id = session_id
#         print data
                
    @tryException
    def __dohandle(self, data):
        handletype = data['handle']
        if handletype in self.__handle_map:
            self.__handle_map[handletype](data['data'])
        else:
            pass
        
    def putHandleData(self, handle, data):
        self.__queue.put({'handle' : handle, 'data' : data})
#         self.__lock.acquire()
#         self.__queue.put_nowait({'handle' : handle, 'data' : data})
#         self.__lock.release()

    def doRevData(self):
        while not self.__stop_thread:
            data = None
#             print datetime.now(),'dataCollector queue size:', self.__queue.qsize()
#             print 'dataCollector run +++++++++++++++++++++++++++++++++++++++++++'
            data = self.__queue.get()
            if data['handle'] == 'devdata':
                sess_name = data['data']['sess']
                for item in data['data']['devdata'].values():
                    if self.session_data[sess_name][item[0]][0] != item[1]:
                        self.session_data[sess_name][item[0]][0] = item[1]
                        self.session_data[sess_name][item[0]][1] = 1
                    else:
                        if self.session_data[sess_name][item[0]][1] == 1:
                            self.session_data[sess_name][item[0]][1] = 2
                        elif self.session_data[sess_name][item[0]][1] == 2:
                            self.session_data[sess_name][item[0]][1] = 0
            elif data['handle'] == 'period':
                sess_name = data['data']['session_name']
                value = data['data']['period']
                if self.session_data[sess_name]['period'][0] != value:
                    self.session_data[sess_name]['period'][0] = value
                    self.session_data[sess_name]['period'][1] = 1
                else:
                    if self.session_data[sess_name]['period'][1] == 1:
                        self.session_data[sess_name]['period'][1] = 2
                    elif self.session_data[sess_name]['period'][1] == 2:
                        self.session_data[sess_name]['period'][1] = 0
                sess_data = UserDict()
                for name,item in self.session_data[sess_name].iteritems():
                    if item[1] > 0:
                        sess_data[name] = item[0]
                if len(sess_data) > 1 or (len(sess_data) == 1 and 'period' not in sess_data):
                    data = {'sess_name' : sess_name, 'sess_data' : sess_data}
                    self.__queue_data.put({'handle' : 'sessdata', 'data' : data})
                    self.puttime = datetime.now()
                else:
                    if (datetime.now() - self.puttime).total_seconds() > 30:
                        sess_data['period'] = self.session_data[sess_name]['period'][0]
                        data = {'sess_name' : sess_name, 'sess_data' : sess_data}
                        self.__queue_data.put({'handle' : 'sessdata', 'data' : data})
                        self.puttime = datetime.now()
                        print '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~', self.puttime
            else:
                self.__queue_data.put(data)
            time.sleep(0.0001)
     
    @tryException   
    def run(self):
        while not self.__stop_thread :
            data = None
#             print datetime.now(),'dataCollector queue_data size:', self.__queue.qsize()
#             print 'dataCollector run +++++++++++++++++++++++++++++++++++++++++++'
            data = self.__queue.get()
#             print 'dataCollector queue_data data:', data
            if data is not None:
                self.__dohandle(data)
#                 time.sleep(0.001)
            else:
                time.sleep(0.0001)
            
    def __stop(self):
        self.__stop_thread = True
        self.__queue.close()
        
    def initSessions(self, session_dict, default=False):
        if default is False:
            for sess_name, v in session_dict.items():
                data_dict = UserDict()
                self.session_dict[sess_name] = serial_session(sess_name, v[0], v[1], default, v[2], v[3], v[4])
                for dev_id, devdata in self.session_dict[sess_name].dev_dict.iteritems():
                    for dataitem in devdata.values():
                        data_dict[dataitem[0]] = [None,0]
                    self.disdev_dict[devdata['DisCount'][0]] = dev_id
                data_dict['period'] = [None,0]
                self.session_data[sess_name] = data_dict
        else:
            for sess_name, v in session_dict.items():
                data_dict = UserDict()
                self.session_dict[sess_name] = serial_session(sess_name, v[0], v[1], default)
                for dev_id, devdata in self.session_dict[sess_name].dev_dict.iteritems():
                    for dataitem in devdata.values():
                        data_dict[dataitem[0]] = [None,0]
                    self.disdev_dict[devdata['DisCount'][0]] = dev_id
                data_dict['period'] = [None,0]
                self.session_data[sess_name] = data_dict
        return self
        
    def setAllSessionFinish(self):
        for sess in self.session_dict.values():
            if sess.finish_flag:
                sess.setFinishFlag(False)
            else:
                pass
            
    def getInitFinishState(self):
        for sess in self.session_dict.values():
            if sess.finish_flag is False:
                return False
        return True
            
    def getAllSessionFinishState(self):
        for sess in self.session_dict.values():
            if sess.getFinishState() is False:
                return False
        return True
        
    @tryException
    def __reconnt_sessions(self):
        dis_sess = list()
        if len(self.dis_sessions) > 1:
            from serialsearch import ReInitSerial
            ReInitSerial()
        while len(self.dis_sessions) > 0:
            name = self.__popDisSession()
            if self.session_dict[name].openSerial():
                self.appendSendSession(name)
                self.putHandleData('sessionstate', {'session_name' : name,
                                                    'state' : self.session_dict[name].state,
                                                    'statetime' : self.session_dict[name].statetime})
            else:
                dis_sess.append(name)
        self.__updateDisSessions(dis_sess)
    
    @tryException
    def __sendData(self):
        while self.__alive:
#             time.sleep(0.000001)
            if len(self.__sendlist) +  len(self.__recvlist) < len(self.session_dict):
                pass
                print datetime.now()
                print 'sendlist:', self.__sendlist
                print 'recvlist:', self.__recvlist
                print 'presendlist:', self.presendlist
#             print datetime.now(), '__sendData start-------------------------'
            if len(self.__sendlist) > 0:
                name = self.__popSendSession()
                sumt = time.time() -self.session_dict[name].recvfinish_time
                if sumt > self.session_dict[name].sleep_interval:
                    ret = self.session_dict[name].sendData()
                    if ret == 1:
                        self.__appendRecvSession(name)
                        self.recvGR.switch()
                    elif ret == 2:
                        for devdata in self.session_dict[name].dev_dict.values():
                            for item in devdata.values():
                                if self.session_data[name][item[0]][0] != item[1]:
                                    self.session_data[name][item[0]][0] = item[1]
                                    self.session_data[name][item[0]][1] = 1
                                else:
                                    if self.session_data[name][item[0]][1] == 1:
                                        self.session_data[name][item[0]][1] = 2
                                    elif self.session_data[name][item[0]][1] == 2:
                                        self.session_data[name][item[0]][1] = 0
                        if self.session_data[name]['period'][0] != self.session_dict[name].periods:
                            self.session_data[name]['period'][0] = self.session_dict[name].periods
                            self.session_data[name]['period'][1] = 1
                        else:
                            if self.session_data[name]['period'][1] == 1:
                                self.session_data[name]['period'][1] = 2
                            elif self.session_data[name]['period'][1] == 2:
                                self.session_data[name]['period'][1] = 0
                        sess_data = UserDict()
                        for data_name,item in self.session_data[name].iteritems():
                            if item[1] > 0:
                                sess_data[data_name] = item[0]
                        if len(sess_data) > 1 or (len(sess_data) == 1 and 'period' not in sess_data):
                            data = {'sess_name' : name, 'sess_data' : sess_data}
                            self.putHandleData('sessdata', data)
                            self.puttime = datetime.now()
                        else:
                            if (datetime.now() - self.puttime).total_seconds() > 30:
                                sess_data['period'] = self.session_data[name]['period'][0]
                                data = {'sess_name' : name, 'sess_data' : sess_data}
                                self.putHandleData('sessdata', data)
                                self.puttime = datetime.now()
                                print '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~', self.puttime
#                         for dev_id, devdata in self.session_dict[name].dev_dict.items():
#                             self.putHandleData('devdata', {'sess' : name,'dev_id' : dev_id, 'devdata' : devdata.data})
#                         self.putHandleData('period', {'session_name' : name,
#                                                       'period' : self.session_dict[name].periods})
                        self.appendSendSession(name)
                        self.__reconnt_sessions()
#                         dev_num = len(self.session_dict[name].dev_dict)
#                         st = dev_num*0.03
#                         time.sleep(st)
                        self.recvGR.switch()
                    else:
                        self.appendDisSession(name)
                        self.putHandleData('sessionstate', {'session_name' : name,
                                                            'state' : self.session_dict[name].state,
                                                            'statetime' : self.session_dict[name].statetime})
                else:
                    mint = sumt
                    if mint < 0:
                        mint = 0
                    min_sess = name
                    flag = True
                    while len(self.__sendlist) > 0:
                        name = self.__sendlist[0]
                        sumt = time.time() -self.session_dict[name].recvfinish_time
                        if sumt < 0:
                            sumt = 0
                        if sumt > self.session_dict[name].sleep_interval:
                            self.__appendPreSendSession(min_sess)
                            flag = False
                            break
                        else:
                            self.__popSendSession()
                            if sumt < mint:
                                self.__appendPreSendSession(min_sess)
                                mint = sumt
                                min_sess = name
                            else:
                                self.__appendPreSendSession(name)
                    if flag:
                        if mint > READ_INTERVAL:
                            time.sleep(READ_INTERVAL)
                        else:
                            time.sleep(mint)
                        self.__insert0SendSession(min_sess)
                    else:
                        pass
                    if len(self.presendlist) > 0:
                        self.__extendSendList(self.presendlist)
                        self.__clearPreSendList()
                    else:
                        pass
                    self.recvGR.switch()
            else:
                if len(self.__recvlist) > 0:
                    name = self.__recvlist[0]
                    sumt = READ_INTERVAL- (time.time() - self.session_dict[name].recvtime)
                    if sumt > 0:
                        time.sleep(sumt)
                    else:
                        pass
                    self.recvGR.switch()
                else:
                    self.__reconnt_sessions()
                    if len(self.__sendlist) == 0:
                        print '__reconnt_sessions',datetime.now(),'__reconnt_sessions'
                        time.sleep(1)
#             print datetime.now(), '__sendData end++++++++++++++++++++++++++++'
         
    @tryException               
    def __receiveData(self):
        while self.__alive:
            if len(self.__recvlist) > 0:
                name = self.__recvlist[0]
                ret = self.session_dict[name].recvData()
#                 if name == 'KT_WJ_PDJ_HW' and ret == 1:
#                     print '----------recvLIST:',ret, self.__recvlist,time.time() - self.session_dict[name].sendtime,'---------------'
#                     print 'sendlist:', self.__sendlist
                if ret == 0:
                    self.sendGR.switch()
                else:
                    self.__popRecvSession()
                    if ret == 1:
                        self.appendSendSession(name)
                    elif ret == 2:
                        self.__appendRecvSession(name)
                        self.sendGR.switch()
                    else:
                        self.appendDisSession(name)
                        self.putHandleData('sessionstate', {'session_name' : name,
                                                            'state' : self.session_dict[name].state,
                                                            'statetime' : self.session_dict[name].statetime})
            else:
                self.sendGR.switch()
    
    @tryException
    def __popSendSession(self):
#         self.__sendLock.acquire()
        value = self.__sendlist.pop(0)
#         self.__sendLock.release()
        return value
    
    @tryException
    def removeSendSession(self, name):
        if name in self.__sendlist:
#             self.__sendLock.acquire()
            self.__sendlist.remove(name)
#             self.__sendLock.release()
            return True
        else:
            return False
    
    @tryException
    def appendSendSession(self, name):
#         self.__sendLock.acquire()
        self.__sendlist.append(name)
#         self.__sendLock.release()
        
    @tryException
    def __insert0SendSession(self, name):
#         self.__sendLock.acquire()
        self.__sendlist.insert(0, name)
#         self.__sendLock.release()
     
    @tryException   
    def __extendSendList(self, pre_list):
#         self.__sendLock.acquire()
        self.__sendlist.extend(pre_list)
#         self.__sendLock.release()
      
    @tryException  
    def __popRecvSession(self):
#         self.__recvLock.acquire()
        value = self.__recvlist.pop(0)
#         self.__recvLock.release()
        return value
    
    @tryException
    def removeRecvSession(self, name):
        if name in self.__recvlist:
#             self.__recvLock.acquire()
            self.__recvlist.remove(name)
#             self.__recvLock.release()
            return True
        else:
            return False
    
    @tryException
    def __appendRecvSession(self, name):
#         self.__recvLock.acquire()
        self.__recvlist.append(name)
#         self.__recvLock.release()
        
    @tryException
    def __clearPreSendList(self):
#         self.presendLock.acquire()
        self.presendlist = list()
#         self.presendLock.release()
        
    @tryException
    def __appendPreSendSession(self, name):
#         self.presendLock.acquire()
        self.presendlist.append(name)
#         self.presendLock.release()
        
    @tryException
    def removePreSendSession(self, name):
        if name in self.presendlist:
#             self.presendLock.acquire()
            self.presendlist.remove(name)
#             self.presendLock.release()
            return True
        else:
            return False
        
    @tryException
    def __popDisSession(self):
#         self.dis_sessLock.acquire()
        value = self.dis_sessions.pop(0)
#         self.dis_sessLock.release()
        return value
    
    @tryException
    def removeDisSession(self, name):
        if name in self.dis_sessions:
#             self.dis_sessLock.acquire()
            self.dis_sessions.remove(name)
#             self.dis_sessLock.release()
            return True
        else:
            return False
    
    @tryException
    def appendDisSession(self, name):
#         self.dis_sessLock.acquire()
        self.dis_sessions.append(name)
#         self.dis_sessLock.release()
        
    @tryException
    def __updateDisSessions(self, dis_list):
#         self.dis_sessLock.acquire()
        self.dis_sessions = dis_list
#         self.dis_sessLock.release()