#coding=utf-8
#!/usr/bin/env python
'''
Created on 2017年2月14日

@author: sanhe
'''
from collections import deque
from deviceSet import deviceSet
import threading
from datetime import datetime
import time
import serial
from errcmd_deque import errcmd_deque
from util import crc16, Sum_Right, tryException
from serialsearch import Session_SerailMap

READ_INTERVAL = 0.001
INTERVAL = 0.5

class serial_session(object):
    def __init__(self, session_name, session_id, dev_dict, default=False, state =False, statetime=None, timeout = 0.2):
        self.session_name = session_name
        self.session_id = session_id
        self.dev_dict = deviceSet().initDevices(dev_dict, default)
        self.baudrate = 9600
        self.timeout = timeout
        self.state = state
        self.statetime = statetime
        self.finish_flag = False
        self.finish_time = None
        self.reconnect = False
        self.periods = None
        self.ctrlCmdLock = threading.Lock()
        self.ctrlCmdDeque = deque()
        self.ctrlCmdList = list()
        self.sleep_interval, self.cycleCmdDeque = self.dev_dict.getCmdSet()
        self.cycleCmdDeque.append({"id" : 0, "cmd" : "", "dev_id" : -1})
        self.errCmdDeque = errcmd_deque()
        self.rmid_list = []
        self.rmcmds_dict = {}
        self.errcmd = None
        self.ctrlCmd = None
        self.sendCmd = None
        self.errStartTime = time.time()
        self.sendtime = 0
        self.recvtime = 0
        self.recvfinish_time = 0
        self.data = ""
        self.com = None
    
    def updateDevID(self, dev_name, dev_id):
        old_id = self.dev_dict.updateDevID(dev_name, dev_id)
        if old_id:
            self.rmid_list.append(old_id)
            self.rmcmds_dict[old_id] = (dev_id, self.dev_dict.getDevCmdSet(dev_id))
            return old_id
        else:
            return 0
        
    def AddSendCmd(self, cmd):
        self.ctrlCmdLock.acquire()
        self.ctrlCmdDeque.append(cmd)
        self.ctrlCmdLock.release()
            
    def openSerial(self):
        if self.session_id in Session_SerailMap:
            self.port = "/dev/" + Session_SerailMap[self.session_id]
            print self.session_name, datetime.now(), 'openSerial:', self.port
            try:
                self.com = serial.Serial(self.port,self.baudrate)
                n = self.com.inWaiting()
                if n > 0:
                    self.com.read(n)
                else:
                    pass
                self.state = True
                self.statetime = datetime.now()
                self.__startTime = time.time()
                return True
            except Exception as e:
                print 'openSerial got Error:',self.session_name, e
        else:
            pass
#             print "Do not find data_session %s" % self.session_name
        return False
    
    def closeSerial(self):
        if self.com is not None:
            try:
                self.com.close()
            except Exception as e:
                print 'closeSerial:', e
        if self.state:
            self.state = False
            self.statetime = datetime.now()
            return True
        else:
            return False
    
    def genControlInstr(self, dev_name, conf_name, instr):
        return self.dev_dict.genControlInstr(dev_name, conf_name, instr)
    
    def setFinishFlag(self, flag):
        self.finish_flag = flag
        self.finish_time = datetime.now()
    
    def getFinishState(self):
        if self.finish_flag is True:
            return True
        else:
            if self.finish_time is not None and \
            (datetime.now() - self.finish_time).total_seconds() - self.timeout > 0.00001:
                return True
            else:
                return False
            
    def CmdThread(self, CMD, delay_second):
        time.sleep(delay_second)
        self.AddSendCmd(CMD)
    
    @tryException
    def sendData(self):
        if len(self.ctrlCmdDeque) > 0:
            self.sendCmd = self.ctrlCmdDeque.popleft()
            self.ctrlCmdList.append(self.sendCmd)
        else:
            self.sendCmd = self.cycleCmdDeque.popleft()
            if len(self.rmid_list)  > 0:
                dev_id = self.sendCmd['dev_id']
                if dev_id in self.rmid_list:
                    self.sendCmd['cmd'] = self.rmcmds_dict[dev_id][1].pop()
                    self.sendCmd['dev_id'] = self.rmcmds_dict[dev_id][0]
                    if len(self.rmcmds_dict[dev_id][1]) == 0:
                        del self.rmcmds_dict[dev_id]
                        self.rmid_list.remove(dev_id)
                else:
                    pass
            else:
                pass
        data = self.sendCmd['cmd']
        if data: 
#             if self.session_name == 'RS_WJ_4':
#                 print self.session_name, self.sendCmd
            try:
                self.data = ''
#                 self.com.flushInput()
                self.com.write(data)
                self.com.flushOutput()
                self.recvtime = self.sendtime = time.time()
                return 1
            except Exception as e:
                self.sendtime = time.time()
                self.cycleCmdDeque.append(self.sendCmd)
                self.closeSerial()
                print 'sendData got Error: ',self.session_name, e
                return 3
        else:
            self.__PeriodProcess()
            return 2
    
    def recvData(self):
        totalsumT = time.time() - self.sendtime
        sumT = time.time() - self.recvtime
        if totalsumT < INTERVAL:
            if sumT < READ_INTERVAL:
                return 0
            else:
                try:
                    n = self.com.inWaiting()
                    self.recvtime = time.time()
                    if n > 0:
                        subdata = self.com.read(n)
                        self.data = self.data + subdata
                        r_data = self.__dataFirstCheck(self.data)
                        if r_data:
                            self.__dataProcess(r_data[0],r_data[1])
                            self.recvfinish_time = time.time()
                            return 1
                        else:
                            return 2
                    else:
                        return 2
                except Exception as e:
                    self.recvfinish_time = time.time()
                    self.cycleCmdDeque.append(self.sendCmd)
                    print 'sendData got Error: ',self.session_name, e
                    self.closeSerial()
                    return 3
        else:
            self.__DisConnect()
            return 1
        
    @tryException
    def __dataFirstCheck(self, data):
        strdata = data.encode("hex")
        listdata = []
        for j in range(0,len(strdata),2):
            listdata.append(int(strdata[j:j+2],16))
        if (listdata[0] == 0x99 and Sum_Right(listdata)) or crc16().calcrc(listdata):
            dev_id = listdata[0]
            if (listdata[0] == 0x99) :
                dev_id = listdata[1]
                if len(listdata) < 17:
                    return False
            else:
                if len(listdata) - 5 < listdata[2]:
                    return False
            return (dev_id, listdata)
        else:
            return False
        
    @tryException
    def __PeriodProcess(self):
        self.periods = round(time.time() - self.__startTime,2)
        self.__startTime = time.time()
#         print self.session_name, time.time() - self.errStartTime
        if len(self.cycleCmdDeque) == 0  or  time.time() - self.errStartTime > 60:
            self.errcmd = self.errCmdDeque.popcmd()
            if self.errcmd is not None:
                self.cycleCmdDeque.append(self.errcmd)
                self.errStartTime = time.time()
            else:
                pass
        else:
            pass
        self.cycleCmdDeque.append(self.sendCmd)
#         print self.session_name, self.periods, self.sendCmd
        
    @tryException
    def __DisConnect(self):
        if self.sendCmd['id'] <> 0:
            dev_id = self.sendCmd["dev_id"]
            if self.dev_dict.getDevStateByID(dev_id) is False:
                self.errCmdDeque.push(self.sendCmd)
            else:
                flag = self.dev_dict.setDisConnect(dev_id,True)
                if not flag:
                    self.errCmdDeque.push(self.sendCmd)
                    cmdlen = len(self.ctrlCmdList)
                    index = 0
                    while index < cmdlen:
                        cmd = self.ctrlCmdList[index]
                        if cmd['dev_id'] == self.sendCmd['dev_id']:
                            self.ctrlCmdList.pop(index)
                            cmdlen = cmdlen - 1
                        else:
                            index = index + 1
                else:
                    self.cycleCmdDeque.append(self.sendCmd)
        else:
            cmdlen = len(self.ctrlCmdList)
            index = 0
            templist = []
            while index < cmdlen:
                cmd = self.ctrlCmdList[index]
                if cmd['dev_id'] == self.sendCmd['dev_id']:
                    self.ctrlCmdList.pop(index)
                    templist.append(cmd)
                    cmdlen = cmdlen - 1
                else:
                    index = index + 1
            self.ctrlCmdList.extend(templist)
            self.ctrlCmdList.append(self.sendCmd)
          
    @tryException      
    def __dataProcess(self, dev_id, listdata):
        if self.sendCmd['dev_id'] == dev_id:
            if self.sendCmd['id'] <> 0:
                self.cycleCmdDeque.append(self.sendCmd)
                if self.dev_dict.ParseData(dev_id,listdata):
                    self.dev_dict.setDisConnect(dev_id,False)
                    if len(self.ctrlCmdList) > 0:
                        cmd = self.ctrlCmdList[0]
                        if cmd['dev_id'] == dev_id:
                            self.ctrlCmdDeque.append(cmd)
                            self.ctrlCmdList.pop(0)
                        else:
                            pass
                    else:
                        pass
                    if self.sendCmd == self.errcmd:
                        cmdSet =  self.errCmdDeque.popcmdset(dev_id)
                        if cmdSet is not None:
                            self.cycleCmdDeque.extend(cmdSet)
                        else:
                            pass
                        self.errcmd = self.errCmdDeque.popcmd()
                        if self.errcmd is not None:
                            self.cycleCmdDeque.append(self.errcmd)
                        else:
                            pass 
                    else:
                        pass
                else:
                    pass
            else:
                for index,cmd in enumerate(self.ctrlCmdList):
                    if cmd['cmd'] == self.sendCmd['cmd']:
                        self.ctrlCmdList.pop(index)
                        break
                    else:
                        pass
        else:
            self.__DisConnect()
            print datetime.now(), self.session_name, '返回错误数据:', listdata