#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年3月16日

@author: sanhe
'''
from UserDict import UserDict

__all__ = ['protdrivemap','protmap']

protmap = {}

def def_prot(name, typeno):
    protmap[name] = typeno
    
def_prot('ServerParam',1)
def_prot('ServiceState',2)
def_prot('ServerState',3)
def_prot('VideoServerChange',4)
def_prot('ServerConfChange',5)
def_prot('VideoServerIPCS',6)
def_prot('VideoServerIPCChange',7)
def_prot('IPCState',8)
def_prot('VideoServerRecords',9)
def_prot('NodeUnitMap',10)
def_prot('DeviceTypes',11)
def_prot('SessionTypes',12)
def_prot('Sessinons',13)
def_prot('SessionIdChanged',14)
def_prot('SessionConfChanged',15)
def_prot('SessionState',16)
def_prot('Devices',17)
def_prot('DeviceFinished',18)
def_prot('DeviceIdChanged',19)
def_prot('DeviceAreaChanged',20)
def_prot('DevDataItems',21)
def_prot('DevDataItemsFinished',22)
def_prot('DataInfo',23)
def_prot('DevDataConfItems',24)
def_prot('DevDataConfItemsFinished',25)
def_prot('DataConfInfo',26)
def_prot('ServerDataTypes',27)
def_prot('UDevDataItems',28)
def_prot('UDevDataItemsFinished',29)
def_prot('UDevDataInfo',30)
def_prot('PeriodDataItems',31)
def_prot('UDevDataConfItems',32)
def_prot('UDevDataConfItemsFinished',33)
def_prot('UDevDataConfInfo',34)
def_prot('MachineDataItems',35)
def_prot('MachineDataItemsFinished',36)
def_prot('MachineDataInfo',37)
def_prot('MachineDataConfItems',38)
def_prot('MachineDataConfInfo',39)
def_prot('TransmitDataItems',40)
def_prot('PeriodDataInfo',41)
def_prot('TransmitDataInfo',42)
# def_prot('TransmitDataReasonItem',43)
def_prot('StartorStopService',44)
def_prot('InitFinished',45)
def_prot('ServerFinished',46)
def_prot('SessionUploadFinished',47)
def_prot('SessionPeriod',48)
def_prot('YHDataUpdate',49)
def_prot('AllSessionIdChanged',50)
def_prot('DataPriChange', 51)
def_prot('DataIPCSChange', 52)
def_prot('LogicInfo', 53)
def_prot('DataLogicInfo', 54)
def_prot('LogicStatusChange', 55)
def_prot('DataLogicStatusChange', 56)
def_prot('RefParamInfo', 57)
def_prot('RefModeParamInfo', 58)
def_prot('RefCondModeParamInfo', 59)
def_prot('RefParamChange', 60)
def_prot('RefModeParamChange', 61)
def_prot('RefCondModeParamChange', 62)
def_prot('RefParamINIT', 63)
def_prot('GetIPCStream', 64)
def_prot('GetIPCHistoryStream', 65)
def_prot('SendControlInstr',101)


protdrivemap = UserDict()

def add_prodrive(prot, driveprot):
    if prot in protmap:
        if protmap[prot] in protdrivemap:
            protdrivemap[protmap[prot]].add(protmap[driveprot])
        else:
            protdrivemap[protmap[prot]] = set({protmap[driveprot]})
    else:
        pass
    
add_prodrive('ServerParam','ServerParam')
add_prodrive('ServerParam','ServiceState')
add_prodrive('ServerParam','ServerState')
add_prodrive('ServerParam','VideoServerChange')
add_prodrive('ServerParam','ServerConfChange')
add_prodrive('VideoServerIPCS','VideoServerIPCChange')
add_prodrive('VideoServerIPCS','IPCState')
add_prodrive('VideoServerIPCS','VideoServerRecords')
add_prodrive('Sessinons','SessionIdChanged')
add_prodrive('Sessinons','SessionConfChanged')
add_prodrive('Sessinons','SessionState')
add_prodrive('Sessinons','SessionPeriod')
add_prodrive('DeviceFinished','DeviceIdChanged')
add_prodrive('DeviceFinished','DeviceAreaChanged')
add_prodrive('RefParamInfo', 'RefParamChange')
add_prodrive('RefModeParamInfo', 'RefModeParamInfo')
add_prodrive('RefCondModeParamInfo', 'RefCondModeParamChange')