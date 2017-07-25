#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年2月24日

@author: sanhe
'''
from UserDict import UserDict
from collections import deque
from mydevice import devicecls_dict


class deviceSet(UserDict):
    def __init__(self):
        UserDict.__init__(self)
        self.name_idMap = {}
        self.id_nameMap = {}
        
    def addDevice(self, dev_name, dev_id, dev_type, data_dict=None, disCount=None, disMax=None):
#         print 'addDevice: ', dev_name,dev_id, dev_type, disCount, disMax
        self.name_idMap[dev_name] = dev_id
        self.id_nameMap[dev_id] = dev_name
        if dev_type not in devicecls_dict:
            print 'There is no {0} Type Device, name is {1}.'.format(dev_type, dev_name)
            return False 
        if disMax is not None:
            if disCount is None:
                disCount = 0
            self.update({dev_id : devicecls_dict[dev_type](disCount, disMax)})
        else:
            self.update({dev_id : devicecls_dict[dev_type]()})
        if data_dict is not None:
            for conf_name, v in data_dict.iteritems():
                self[dev_id].addDataName(conf_name,v[0],v[1],v[2])
        else:
            for conf_name in self[dev_id].data_dict.keys():
                self[dev_id].addDataName(conf_name,dev_name+'_'+conf_name)
        self[dev_id].setDataValue('DisCount',disCount)
        return True
            
    def initDevices(self, dev_dict,default=False):
        if default is False:
            for dev_name, v in dev_dict.iteritems():
                self.addDevice(dev_name, v[0], v[1], v[2], v[3], v[4])
        else:
            for dev_name, v in dev_dict.iteritems():
                self.addDevice(dev_name, v[0], v[1])
        return self
            
    def updateDevID(self, dev_name, dev_id):
        if dev_id in self.id_nameMap or dev_name not in self.name_idMap:
            return 0
        else:
            old_id = self.name_idMap[dev_name]
            dev = self.pop(old_id)
            self[dev_id] = dev
            self.name_idMap[dev_name] = dev_id
            del self.id_nameMap[old_id]
            self.id_nameMap[dev_id] = dev_name
            return old_id
        
    def genControlInstr(self, dev_name, conf_name, instr):
        dev = self.get(dev_name)
        if dev is not None:
            return dev.genControlInstr(self.name_idMap[dev_name], conf_name, instr)
        else:
            pass
        
    def get(self, key, failobj=None):
        if key in self:
            return self[key]
        elif key in self.name_idMap:
            return self[self.name_idMap[key]]
        else:
            return failobj
        
    def setDisConnect(self, dev_id, flag):
        if self.has_key(dev_id):
            return self[dev_id].setDisConnect(flag)
        else:
            pass
        
    def getDevStateByID(self, dev_id):
        dev = self.get(dev_id)
        if dev is not None:
            return dev.state
        else:
            pass
        
    def getDevCmdSet(self, dev_id):
        return self[dev_id].genPratrolInstr(dev_id)
        
    def getCmdSet(self):
        cycleCmds = {}
        interval = 0
        for dev_id, dev in self.iteritems():
            if dev.SLEEP_TIME > interval:
                interval = dev.SLEEP_TIME
            cmds = dev.genPratrolInstr(dev_id)
            cycleCmds[dev_id] = dev.genPratrolInstr(dev_id)
        cmdCount = 0
        line_cmdList = deque()
        for key,cmds in cycleCmds.iteritems():
            for cmd in cmds :
                cmdCount += 1
                line_cmdList.append({"id" : cmdCount, "cmd" : cmd, "dev_id" : key})
        return (interval,line_cmdList)
    
    def ParseData(self, dev_id, data):
        if self.get(dev_id):
            return self[dev_id].dataParse(data)
        else:
            return False
#             print "there is not device which it dev_id = " , dev_id