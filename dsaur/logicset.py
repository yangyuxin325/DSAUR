#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年8月19日

@author: sanhe
'''

from UserDict import UserDict
from datetime import datetime,timedelta,date
from dsaur.util import singleton, get_refparam, get_refmodeparam, get_refcondmodeparam,tryException,INSTRUCTIONS
import copy
from reasonDesc import REASON_DICT
import random

__all__ = ['logicSet', 'chaObj', 'logicObj','INIT_LOGICS']

JS_logicMap = UserDict()
KZ_logicMap = UserDict()

def SearchGeneralDataValue(name, server, status=0):
    value = server.getDataValue(name)
    if value is not None:
        return value
    else:
        ls = name.split('_')
        while len(ls) > 1:
            del ls[-2]
            value = server.getDataValue('_'.join(ls))
            if value is not None:
                break
    if status == 1:
        return ('_'.join(ls), value)
    return value

def GetStaticParam(name, server):
    value = get_refparam('SD_'+name)
    if value is not None:
        return value
    else:
        ls = name.split('_')
        while len(ls) > 2:
            del ls[-2]
            value = get_refparam('_'.join(ls))
            if value is not None:
                break
    return value

def GetGeneralParam(name, server, status=0):
    MS = server.getDataValue(server.server_name + '_MS')
    if MS is None:
        MS = server.getDataValue(name.split('_')[0] + '_MS')
    GK = server.getDataValue(server.server_name + '_GK')
    if GK is None:
        GK = server.getDataValue(name.split('_')[0] + '_GK')
#     print 'GetGeneralParam:','MS: ', MS, 'GK: ', GK
    SD = None
    JD = None
    funclist = []
    funclist.append(get_refparam)
    def getParam1(name):
        return get_refmodeparam(name, MS)
    funclist.append(getParam1)
    def getParam2(name):
        return get_refcondmodeparam(name, GK, MS)
    funclist.append(getParam2)
    ls = []
    ls.append('SD')
    ls.extend(name.split('_'))
    n = len(ls)
    data_name = '_'.join(ls)
    for i in xrange(n):
        SD = None
        flag = False
        for func in funclist:
            SD = func(data_name)
            if SD is not None:
                if status == 1:
                    return SD
                ls[0] = 'JD'
                JD = func('_'.join(ls))
                if JD is not None:
                    flag = True
                    break
                else:
                    if len(ls) > 2:
                        del ls[-2]
                        m = len(ls)
                        for j in xrange(m):
                            JD = func('_'.join(ls))
                            if JD is not None:
                                flag = True
                                break
                            else:
                                if len(ls) > 2:
                                    del ls[-2]
                                else:
                                    flag = True
                                    break
                        if flag:
                            break
                    else:
                        flag = True
                        break
            else:
                pass
        if flag:
            break
        else:
            if len(ls) > 2:
                del ls[-2]
                data_name = '_'.join(ls)
            else:
                break
    return (SD,JD)
  
@tryException          
def SetOutputData(name, value, out_name, out_value, midSet, server):
    if server.getDataValue(out_name) <> out_value:
        changeflag = 0
        if out_value is None:
            changeflag = server.setDataValue(out_name,out_value)
        else:
            changeflag = server.setDataValue(out_name,round(out_value,2))
        if changeflag:
            dataitem = server.data_dict.get(name)
            dataconf = server.dataconf_dict.get(name)
            pri = dataconf.get('pri')
            if pri < 3 and dataitem.reason is not None:
                server.setDataReason(out_name,dataitem.reason)
            else:
                rs_time = dataitem.time
                if dataitem.dis_time is not None:
                    rs_time = (dataitem.time if dataitem.time > dataitem.dis_time else dataitem.dis_time) \
                    if dataitem.time is not None else dataitem.dis_time
                data_reason = {'rs_type' : 1,
                               'rs_name' : dataitem.name,
                               'rs_cname': dataconf.get('data_cname'),
                               'rs_value' : value if value is not None else value,
                               'rs_change_flag' : dataitem.change_flag,
                               'rs_time' : rs_time
                               }
                server.setDataReason(out_name,data_reason)
            midSet.add(out_name)
        else:
            pass
    else:
        pass

def def_jslogic(name, logic):
    JS_logicMap[name] = logic
    
def def_kzlogic(name, logic):
    KZ_logicMap[name] = logic
    
def getLogic(name):
    if name in JS_logicMap:
        return ('JS', JS_logicMap[name])
    elif name in KZ_logicMap:
        return ('KZ', KZ_logicMap[name])
    else:
        return (None,None)

class chaObj(object):
    def __init__(self, data_name, dl_alg):
        self.data_name = data_name
        self.dl_alg = dl_alg
        
class logicObj(object):
    def __init__(self, logic_name, logic_cha, onoff=True):
        self.logic_name = logic_name
        self.logic_cha = logic_cha
        self.logicCP = getLogic(self.logic_name)
        self.onoff = onoff
        
    def getLogicCP(self):
        if self.logic_name in logicSet().logicstate_dict:
            if logicSet().logicstate_dict[self.logic_name]:
                if self.onoff:
                    return self.logicCP
        return(None,None)
    
    def getDataSet(self):
        m = logicSet().getDataList(self.logic_cha)
        if m is not None:
            return set(m)
        else:
            return set()
    
    def __cmp__(self, other):
        if self.logic_name == other.logic_name and self.logic_cha == other.logic_cha:
            return 0
        else:
            return -1
        
        
# def INIT_LOGICS():
#     from PumpAutoCtrl import AutoCtrlTest
#     from PumpZMA194EAutoStateCmp import AutoStateCmp
#     from CondInit import CondInit
#     from ModeInit import ModeInit
#     from NewDataUpdate import NewDataUpdate, NotNoneNewDataUpdate
#     from PumpSZDCmp import PumpSZDCmp
#     from CollectGetMin import CollectGetMin
#     from RoundCompareDeviation import RoundCompareDeviation
#     from OPJudgementOfEE import OPJudgementOfEE
#     from ERTProcessing import ERTProcessing
#     from RequireOutputDO import RequireOutputDO
#     from ESSAccumulatedTime import ESSAccumulatedTime
#     from CollectGetMax import CollectGetMax
#     from SXDB_ESS import SXDB_ESS
#     from CollectPosSum import CollectPosSum
#     from CollectOrCmp import CollectOrCmp
#     from TemperatureCmpCond import TemperatureCmpCond
#     from CollectAndCmp import CollectAndCmp
#     from DelayedReset import DelayedReset
#     from ChangedAs1 import ChangedAs1
#     from Greater0AssignByDl_alg import Greater0AssignByDl_alg
#     from CollectGetAverage import CollectGetAverage
#     from New01ReverseAssign import New01ReverseAssign
#     from MOV_OnOffState import MOV_OnOffState
# #     from JSDS_KTRequireProcess import JSDS_KTRequireProcess
#     from One2Many01SYN import One2Many01SYN
#     from LENRE50P_KTStateOutPut import LENRE50P_KTStateOutPut
#     from New01Assign import New01Assign
#     from CollectOrCmp_ACPermission import CollectOrCmp_ACPermission
#     from MOVOnOff_DelayCheck import MOVOnOff_DelayCheck
#     from MOV_StateMatchCheck import MOV_StateMatchCheck
#     from CollectGetMax_Toplimit import CollectGetMax_Toplimit
#     from ErrorAssign import ErrorAssign
#     from ErrorReverseAssign import ErrorReverseAssign
#     from SumNotNone import SumNotNone
#     from Division import Division
#     from PositiveDelayAssign import PositiveDelayAssign
#     from MOV_OnOffInstr import MOV_ONInstr, MOV_OnOffInstr
#     from Reverse01Assign import Reverse01Assign
#     from NewDataUpdate import PreNotNoneNewDataUpdate
# #     from MOVOff_AbortCheck import MOVOff_AbortCheck
#     from CollectSum_Toplimit import CollectSum_Toplimit
#     from BidirectionalJudge01 import BidirectionalJudge01
#     
#     def_jslogic(u'新数值则赋值',NewDataUpdate)
#     def_jslogic(u'非空新数则赋值',NotNoneNewDataUpdate)
#     def_jslogic(u'汇总_正数累加运算', CollectPosSum)
#     def_jslogic(u'大于零新值赋算法特征值', Greater0AssignByDl_alg)
#     def_jslogic(u'汇总_取最高_有上限', CollectGetMax_Toplimit)
#     def_jslogic(u'汇总_累加_有上限', CollectSum_Toplimit)
#     def_jslogic(u'汇总_或运算', CollectOrCmp)
#     def_jslogic(u'汇总_与运算', CollectAndCmp)
#     def_jslogic(u'汇总_平均值', CollectGetAverage)
#     def_jslogic(u'备用非空新数赋值', PreNotNoneNewDataUpdate)
#     def_jslogic(u'新数值0/1赋值', New01Assign)
#     def_jslogic(u'新数值0/1反向赋值', New01ReverseAssign)
#     def_jslogic(u'双阈值双向判断0/1', BidirectionalJudge01)
#     def_jslogic(u'异常数据反向赋值', ErrorReverseAssign)
#     def_jslogic(u'异常数据同步赋值', ErrorAssign)
#     def_jslogic(u'非空加减运算', SumNotNone)
#     def_jslogic(u'两数相除', Division)
#     def_jslogic(u'正数延时赋值', PositiveDelayAssign)
#     def_jslogic(u'有偏差比较并取整',RoundCompareDeviation)
#     def_jslogic(u'电动阀开关状态', MOV_OnOffState)
#     def_jslogic(u'电动阀开关后延时复查', MOVOnOff_DelayCheck)
#     def_jslogic(u'电动阀状态匹配检查', MOV_StateMatchCheck)
#     def_jslogic(u'电器设备运行判断',OPJudgementOfEE)
#     def_jslogic(u'设备运行时间处理',ERTProcessing)
#     def_jslogic(u'按累计时间启停设备',ESSAccumulatedTime)
#     def_kzlogic(u'电动阀开指令', MOV_ONInstr)
#     def_kzlogic(u'电动阀开关指令', MOV_OnOffInstr)
#     def_kzlogic(u'PHINX50P空调机组启停指令', LENRE50P_KTStateOutPut)
#     def_kzlogic(u'三相表设备启停',SXDB_ESS)
#     
#     
#     def_jslogic(u'反向0/1赋值', Reverse01Assign)
#     def_jslogic(u'汇总_或运算_有自控许可',CollectOrCmp_ACPermission)
#     def_jslogic(u'泵三相表手自动位置计算',AutoStateCmp)
#     def_kzlogic(u'泵自动启停测试',AutoCtrlTest)
#     def_jslogic(u'工况上电初始化',CondInit)
#     def_jslogic(u'模式上电初始化',ModeInit)
#     def_jslogic(u'泵手自动位置计算',PumpSZDCmp)
#     def_jslogic(u'汇总_取最低',CollectGetMin)
#     def_kzlogic(u'根据要求输出DO',RequireOutputDO)
#     def_jslogic(u'汇总_取最高',CollectGetMax)
#     def_jslogic(u'温度算工况', TemperatureCmpCond)
#     def_jslogic(u'延时自复位', DelayedReset)
#     def_jslogic(u'变化则为1', ChangedAs1)
#     def_jslogic(u'一对多非空0/1同步', One2Many01SYN)
#     def_jslogic(u'京师大厦空调运行要求处理', JSDS_KTRequireProcess)
#     def_jslogic(u'电动阀异常关闭检查', MOVOff_AbortCheck)

@singleton
class logicSet(object):
    def __init__(self, logicstate_dict=UserDict(), datacha_dict=UserDict(), datalogic_dict=UserDict(), delaylogiclist=[]):
        self.logicstate_dict = copy.deepcopy(logicstate_dict)
        self.datacha_dict = copy.deepcopy(datacha_dict)
        self.datalogic_dict = copy.deepcopy(datalogic_dict)
        self.delaylogiclist = copy.deepcopy(delaylogiclist)

    def getDelayLogiclength(self):
        return len(self.delaylogiclist)
    
    def popDelayLogic(self):
        if self.getDelayLogiclength() > 0:
            return self.delaylogiclist.pop(0)
        else:
            pass
        
    def existDelayLogic(self, name, logic):
        for item in self.delaylogiclist:
            if item[0] == name and item[1] == logic:
                return True
        return False
        
    def addDelayLogic(self, name, logic, addtime):
        self.delDelayLogic(name, logic)
        self.delaylogiclist.append((name, logic, addtime))
        
    def delDelayLogic(self, name, logic):
        for item in self.delaylogiclist:
            if item[0] == name and item[1] == logic:
                del self.delaylogiclist[self.delaylogiclist.index(item)]
        
    def addCycleLogic(self, logic, addtime=datetime.now()):
        self.delaylogiclist.append((None, logic, addtime))
    
    def getDataLogicList(self, data_name):
        return self.datalogic_dict.get(data_name)
    
    def getDataList(self, data_cha):
        return self.datacha_dict.get(data_cha)
    
    def setLogicState(self, logic_name, state):
        if logic_name in self.logicstate_dict:
            if self.logicstate_dict[logic_name] != state:
                self.logicstate_dict[logic_name] = state
                return True
        return False
    
    def setDataLogicOnoff(self, data_name, logic_name, logic_cha, onoff):
        if data_name in self.datalogic_dict:
            for logic in self.datalogic_dict[data_name]:
                if logic.logic_name == logic_name and logic.logic_cha == logic_cha:
                    if logic.onoff != onoff:
                        logic.onoff = onoff
                        return True
        return False
    
    def setCycleLogicOnOff(self, logic_name, onoff):
        for logic in self.delaylogiclist:
            if logic.logic_name == logic_name:
                if logic.onoff != onoff:
                    logic.onoff = onoff
                    return True
        return False
    
@tryException
def NewDataUpdate(name, logicObj, midSet, server):
#     print 'NewDataUpdate Start: ', name
    in_value = server.getDataValue(name)
    item = server.data_dict.get(name)
    if item is not None and item.time is not None:
        dataitem = server.data_dict.get(logicObj.logic_cha)
        if dataitem is not None and (dataitem.time is None or (dataitem.time is not None and item.time > dataitem.time)):
            SetOutputData(name, in_value, logicObj.logic_cha, in_value, midSet, server)
    #         print 'NewDataUpdate input_name : {0}, input_value : {1}, out_name: \
    #             {2}, out_value: {3}'.format(name, value, outname, value)
        else:
            pass
    else:
        pass
    
def NotNoneNewDataUpdate(name, logicObj, midSet, server):
#     print 'NotNoneNewDataUpdate Start: ', name
    value = server.getDataValue(name)
    if value is not None:
        NewDataUpdate(name, logicObj, midSet, server)
    else:
        pass
    
@tryException
def CollectPosSum(name, logicObj, midSet, server):
#     if 'KT_WJ_1_1_YSJ_1_YX':
#         print 'CollectPosSum Start: ', name
    in_value = server.getDataValue(name)
    out_value = None
    for datacha in logicObj.getDataSet():
        other_value = server.getDataValue(datacha.data_name)
#         print datacha.data_name, other_value
        if other_value is not None:
            out_value = (out_value if out_value is not None else 0) + \
                        (other_value if other_value > 0 else 0)
        else:
            pass
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'CollectPosSum input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def Greater0AssignByDl_alg(name, logicObj, midSet, server):
#     print 'Greater0AssignByDl_alg Start: ', name
    in_value = server.getDataValue(name)
    if in_value > 0:
        out_value = None
        datachas = logicSet().getDataList(name + '_>0')
        if len(datachas) > 0:
            for datacha in datachas:
                dl_alg = datacha.dl_alg
                if out_value is not None:
                    out_value = -255
                    break
                out_value = dl_alg if dl_alg is not None else -255
            outitem = server.data_dict.get(logicObj.logic_cha)
            if outitem is not None:
                dataitem = server.data_dict.get(name)
                if outitem.time is None or dataitem.time > outitem.time:
                    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#                     print 'Greater0AssignByDl_alg input_name : {0}, input_value : {1}, out_name: \
#                     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)
                else:
                    pass
            else:
                pass
        else:
            pass
    else:
        pass
    
@tryException
def CollectGetMax_Toplimit(name, logicObj, midSet, server):
#     print 'CollectGetMax_Toplimit Start: ', name
    out_value = None
    for datacha in logicObj.getDataSet():
        other_value = server.getDataValue(datacha.data_name)
        if other_value > out_value:
            out_value = other_value
    value = GetStaticParam(logicObj.logic_cha + '_SX', server)
    if out_value > value:
        out_value = value
    in_value = server.getDataValue(name)
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'CollectGetMax_Toplimit input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def CollectSum_Toplimit(name, logicObj, midSet, server):
#     print 'CollectSum_Toplimit Start: ', name
    in_value = server.getDataValue(name)
    out_value = None
    for datacha in logicObj.getDataSet():
        other_value = server.getDataValue(datacha.data_name)
#         print datacha.data_name, other_value
        if other_value is not None:
            out_value = (out_value if out_value is not None else 0) + \
                        (other_value if other_value > 0 else 0)
        else:
            pass
    value = GetStaticParam(logicObj.logic_cha+'_SX')
    if out_value > value:
        out_value = value
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'CollectSum_Toplimit input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def CollectOrCmp(name, logicObj, midSet, server):
#     print 'CollectOrCmp Start: ', name
    in_value = server.getDataValue(name)
    out_value = None
    if in_value >= 1:
        out_value = 1
    else:
        out_value = 0
        for datacha in logicObj.getDataSet():
            other_value = server.getDataValue(datacha.data_name)
            if other_value >= 1:
                out_value = 1
                break
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'CollectOrCmp input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def CollectAndCmp(name, logicObj, midSet, server):
#     print 'CollectAndCmp Start: ', name
    in_value = server.getDataValue(name)
    out_value = None
    if in_value == 0:
        out_value = 0
    else:
        for datacha in logicObj.getDataSet():
            other_value = server.getDataValue(datacha.data_name)
            if other_value == 0:
                out_value = 0
                break
            elif other_value >= 1:
                out_value = 1
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'CollectAndCmp input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def CollectGetAverage(name, logicObj, midSet, server):
#     print 'CollectGetAverage Start: ', name
    total = 0
    count = 0
    out_value = None
    in_value = server.getDataValue(name)
    for datacha in logicObj.getDataSet():
        other_value = server.getDataValue(datacha.data_name)
        if other_value is not None:
            total = total + other_value
            count = count + 1
    if count > 0:
        out_value = total / float(count)
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'CollectGetAverage input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def PreNotNoneNewDataUpdate(name, logicObj, midSet, server):
#     print 'PreNotNoneNewDataUpdate Start: ', name
    in_value = server.getDataValue(name)
    datachas = logicSet().getDataList(logicObj.logic_cha)
    for datacha in datachas:
        value = server.getDataValue(datacha.data_name)
        if value is None:
            SetOutputData(name, in_value, datacha.data_name, in_value, midSet, server)
#             print 'PreNotNoneNewDataUpdate input_name : {0}, input_value : {1}, out_name: \
#             {2}, out_value: {3}'.format(name, value, datacha.data_name, value)

@tryException
def New01Assign(name, logicObj, midSet, server):
#     print 'New01Assign Start: ', name
    out_value = None
    dataitem = server.data_dict.get(name)
    outdataitem = server.data_dict.get(logicObj.logic_cha)
    if dataitem.time is not None and (outdataitem.time is None or dataitem.time > outdataitem.time):
        in_value = server.getDataValue(name)
        if in_value > 0:
            out_value = 1
        elif in_value is not None:
            out_value = 0
        SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
    #     print 'New01Assign input_name : {0}, input_value : {1}, out_name: \
    #     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)
    else:
        pass
    
@tryException
def New01ReverseAssign(name, logicObj, midSet, server):
#     print 'New01ReverseAssign Start: ', name
    dataitem = server.data_dict.get(name)
    outdataitem = server.data_dict.get(logicObj.logic_cha)
    if dataitem.time is not None and (outdataitem.time is None or dataitem.time > outdataitem.time):
        in_value = server.getDataValue(name)
        out_value = None
        if in_value >= 1:
            out_value = 0
        elif in_value is not None:
            out_value = 1
        SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
    #     print 'New01ReverseAssign input_name : {0}, input_value : {1}, out_name: \
    #     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)
    else:
        pass
    
@tryException
def BidirectionalJudge01(name, logicObj, midSet, server):
#     print 'BidirectionalJudge01 Start: ', name
    out_value = None
    SD = None
    JD = None
    in_value = server.getDataValue(name)
    if in_value is not None:
        SD, JD = GetGeneralParam(name,server)
        if SD is None:
            return
        if JD is None:
            JD = 1
        datachas = logicSet().getDataList(name)
        if len(datachas) == 1:
            for datacha in datachas:
                if datacha.dl_alg == -1:
                    if in_value <= SD:
                        out_value = 1
                    elif in_value > SD * JD:
                        out_value = 0
                    else:
                        return
                else:
                    if in_value >= SD:
                        out_value = 1
                    elif in_value < SD * JD:
                        out_value = 0
                    else:
                        return
            SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#             print 'BidirectionalJudge01 input_name : {0}, input_value : {1}, out_name: \
#             {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def ErrorReverseAssign(name, logicObj, midSet, server):
#     print 'ErrorReverseAssign Start: ', name
    dataitem = server.data_dict.get(name)
    out_value = 0
    if not dataitem.error_flag:
        out_value = 1
    else:
        pass
    in_value = server.getDataValue(name)
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'ErrorReverseAssign input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def ErrorAssign(name, logicObj, midSet, server):
#     print 'ErrorAssign Start: ', name
    dataitem = server.data_dict.get(name)
    out_value = 0
    if dataitem.error_flag:
        out_value = 1
    else:
        pass
    in_value = server.getDataValue(name)
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'ErrorAssign input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def SumNotNone(name, logicObj, midSet, server):
#     print 'SumNotNone Start: ', name
    out_value = None
    for datacha in logicObj.getDataSet():
        other_value = server.getDataValue(datacha.data_name)
        if other_value is not None:
            factor = datacha.dl_alg
            if datacha.dl_alg is None:
                factor = 1
            if factor == 1 or factor == -1:
                out_value = (out_value if out_value is not None else 0) + float(other_value) * float(factor)
            else:
                out_value = -255
                break
        else:
            pass
    in_value = server.getDataValue(name)
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'SumNotNone input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def Division(name, logicObj, midSet, server):
#     print 'Division Start: ', name
    out_value = None
    vflag = False
    dl_alg1 = None
    exvalue = None
    for datacha in logicObj.getDataSet():
        other_value = server.getDataValue(datacha.data_name)
        if other_value is None:
            break
        if not vflag:
            vflag = True
            dl_alg1 = datacha.dl_alg
            exvalue = other_value
        else:
            if dl_alg1 <> datacha.dl_alg:
                if dl_alg1 == 0:
                    if other_value <> 0:
                        out_value = float(exvalue)/float(other_value)
                    else:
                        out_value = 0
                elif datacha.dl_alg == 0:
                    if exvalue <> 0:
                        out_value = float(other_value)/float(exvalue)
                    else:
                        out_value = 0
                else:
                    out_value = -255
            else:
                out_value = -255
    in_value = server.getDataValue(name)
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'Division input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)
    
@tryException
def PositiveDelayAssign(name, logicObj, midSet, server):
#     print 'PositiveDelayAssign Start: ', name
    in_value = server.getDataValue(name)
    if in_value <= 0:
        SetOutputData(name, in_value, logicObj.logic_cha, in_value, midSet, server)
#         print 'PositiveDelayAssign input_name : {0}, input_value : {1}, out_name: \
#         {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, in_value)
        logicSet().delDelayLogic(name, logicObj)
    else:
        interval = 5
        param = GetGeneralParam(name, server, 1)
        if param is not None:
            interval = param
        dataitem = server.data_dict.get(name)
        if (datetime.now() - dataitem.time).total_seconds() >= interval:
            SetOutputData(name, in_value, logicObj.logic_cha, in_value, midSet, server)
#                 print 'PositiveDelayAssign input_name : {0}, input_value : {1}, out_name: \
#                 {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, in_value)
#             logicSet().delDelayLogic(name, logicObj)
        else:
            logicSet().addDelayLogic(name, logicObj, datetime.now()+timedelta(seconds=int(interval)))
#                 print "addDelayLogic PositiveDelayAssign:",name,logicObj

@tryException
def RoundCompareDeviation(name, logicObj, midSet, server):
#     print 'RoundCompareDeviation Start: ', name
    value = server.getDataValue(name)
    out_value = None
    if value is None:
        SetOutputData(name,value,logicObj.logic_cha,out_value,midSet,server)
        return
    SD,JD = GetGeneralParam(name,server)
    if SD is None:
        return
    if JD is None or JD == 0:
        JD = 1
    out_value = float((value-float(SD))/float(JD))
    if out_value < 0:
        out_value = 0
    SetOutputData(name,value,logicObj.logic_cha,int(out_value),midSet,server)
#     print 'RoundCompareDeviation input_name : {0}, input_value : {1}, out_name: \
#         {2}, out_value: {3}'.format(name, value, logicObj.logic_cha, out_value)

@tryException
def MOV_OnOffState(name, logicObj, midSet, server):
#     print 'MOV_OnOffState Start: ', name
    in_value = server.getDataValue(name)
    ls = logicObj.logic_cha
    out_name = ls + '_KG'
    out_value = -1
    if logicObj.logic_cha+'_K' in server.data_dict and logicObj.logic_cha+'_G' in server.data_dict:
        k_value = server.getDataValue(logicObj.logic_cha+'_K')
        g_value = server.getDataValue(logicObj.logic_cha+'_G')
        if k_value == 1 and k_value <> g_value:
            out_value = 1
        elif k_value == 0 and k_value <> g_value:
            out_value = 0
        else:
            out_value = -1
    else:
        out_value = -255
    SetOutputData(name, in_value, out_name, out_value, midSet, server)
#     print 'MOV_OnOffState input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, out_name, out_value)

tryException
def MOVOnOff_DelayCheck(name, logicObj, midSet, server):
#     print 'MOV_RequireCheck Start: ', name
    in_value = server.getDataValue(name)
    if in_value == 1:
        delay_time = 90
        param = GetStaticParam(logicObj.logic_cha, server)
        if param is not None:
            delay_time = param
        do_t = dody_t = delay_time
        doitem = server.data_dict.get(logicObj.logic_cha + '_DO')
        dodyitem = server.data_dict.get(logicObj.logic_cha + '_DO_DY')
        if doitem is not None and doitem.time is not None:
            do_t = (datetime.now() - doitem.time).total_seconds()
        if dodyitem is not None and dodyitem.time is not None \
        and server.getDataValue(logicObj.logic_cha + '_DO_DY') <> 0:
            dody_t = (datetime.now() - dodyitem.time).total_seconds()
        delay_time = max(do_t, dody_t)
        if delay_time > 0:
#             print 'MOV_RequireCheck addDelayLogic', delay_time, do_t, dody_t
            logicSet().addDelayLogic(logicObj.logic_cha + '_DO_DY' , logicObj, datetime.now()+timedelta(seconds=int(delay_time)))
        else:
            server.sendCtrlCMD(logicObj.logic_cha + '_DO_DY',INSTRUCTIONS.OFF,0)
#             print 'MOV_RequireCheck:', logicObj.logic_cha + '_DO_DY', 'OFF','---------------------------------------'
            kg = server.getDataValue(logicObj.logic_cha + '_KG')
            kg_yq = server.getDataValue(logicObj.logic_cha + '_KG_YQ')
            if kg is not None and kg_yq is not None:
                if kg == kg_yq:
                    SetOutputData(name, in_value, logicObj.logic_cha + '_GZ', 0, midSet, server)
                    SetOutputData(name, in_value, logicObj.logic_cha + '_K_GZ', 0, midSet, server)
                    SetOutputData(name, in_value, logicObj.logic_cha + '_G_GZ', 0, midSet, server)
                else:
                    dy = server.getDataValue(logicObj.logic_cha + '_DY')
                    if dy == 1:
                        SetOutputData(name, in_value, logicObj.logic_cha + '_GZ', 1, midSet, server)
    #                     print 'MOV_RequireCheck input_name : {0}, input_value : {1}, out_name: \
    #                     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha + '_GZ', 1)
                    else:
                        pass
            else:
                pass
    else:
        pass
    
@tryException
def MOV_StateMatchCheck(name, logicObj, midSet, server):
#     print 'MOV_StateMatchRequire Start: ', name
    in_value = server.getDataValue(name)
    if in_value is not None:
        delay_time = 90
        item = server.data_dict.get(logicObj.logic_cha + '_KG_YQ')
        if item.time is not None:
            sumt = delay_time - (datetime.now() - item.time).total_seconds()
            if sumt > 0:
                logicSet().addDelayLogic(logicObj.logic_cha + '_KG_YQ' , logicObj, datetime.now()+timedelta(seconds=int(sumt)))
            else:
                KG_YQ = server.getDataValue(logicObj.logic_cha + '_KG_YQ')
                KG = server.getDataValue(logicObj.logic_cha + '_KG')
                if KG_YQ is not None and KG_YQ == KG:
                    SetOutputData(name, in_value, logicObj.logic_cha+'_GZ', 0, midSet, server)
                    SetOutputData(name, in_value, logicObj.logic_cha+'_K_GZ', 0, midSet, server)
                    SetOutputData(name, in_value, logicObj.logic_cha+'_G_GZ', 0, midSet, server)
                elif KG_YQ == 1 and KG == 0:
                    SetOutputData(name, in_value, logicObj.logic_cha+'_K_GZ', 1, midSet, server)
                    SetOutputData(name, in_value, logicObj.logic_cha+'_G_GZ', 0, midSet, server)
                elif KG_YQ == 0 and KG == 1:
                    SetOutputData(name, in_value, logicObj.logic_cha+'_K_GZ', 0, midSet, server)
                    SetOutputData(name, in_value, logicObj.logic_cha+'_G_GZ', 1, midSet, server)
                else:
                    pass
        else:
            pass
    else:
        pass
    
@tryException
def OPJudgementOfEE(name, logicObj, midSet, server):
#     print 'OPJudgementOfEE Start: ', name
    value = server.getDataValue(name)
    dataitem = server.data_dict.get(name)
    out_value = 0
    if dataitem.value is None:
        return
    if value is not None and value >= 0.1:
        SD,JD = GetGeneralParam(name, server)
#         print 'OPJudgementOfEE SD, JD', name, SD, JD,'---------------------------------'
        if SD is None:
            out_value = None
        elif JD is None or JD == 0:
            JD = 1
        if value > SD * JD:
            out_value = 1
        else:
            pass
    else:
        pass
    if out_value == 0:
        old_value = server.getDataValue(logicObj.logic_cha)
        if old_value == 1:
            ls = logicObj.logic_cha.split('_')
            ls[-1] = 'LXSJ'
            ls_name = '_'.join(ls)
            if ls_name in server.data_dict:
                olddataitem = server.data_dict.get(logicObj.logic_cha)
                lxsj = (dataitem.time - olddataitem.time).total_seconds()
                SetOutputData(name, value, ls_name, lxsj, midSet, server)
#                 print 'OPJudgementOfEE input_name : {0}, input_value : {1}, out_name: \
#                 {2}, out_value: {3}'.format(name, value, ls_name, lxsj)
            else:
                pass
        else:
            pass
    else:
        pass
    SetOutputData(name, value, logicObj.logic_cha, out_value, midSet, server)
#     print 'OPJudgementOfEE input_name : {0}, input_value : {1}, out_name: \
#         {2}, out_value: {3}'.format(name, value, logicObj.logic_cha, out_value)

@tryException
def ERTProcessing(name, logicObj, midSet, server):
#     print 'ERTProcessing Start: ', name,datetime.now()
    out_name = logicObj.logic_cha
    if out_name in server.data_dict:
        value = server.getDataValue(name)
        out_value = 0
        if value >= 1:
            dataitem = server.data_dict.get(name)
            out_value = (datetime.now() - dataitem.time).total_seconds()
            if out_value < 1:
                out_value = 1
            else:
                pass
            interval = GetGeneralParam(out_name, server)[0]
            if interval < 1:
                interval = 5
            logicSet().addDelayLogic(name, logicObj, datetime.now()+timedelta(seconds=int(interval)))
    #         print "addDelayLogic ERTProcessing:",name,logicObj
        else:
            out_value = server.getDataValue(out_name)
            if out_value is None or out_value == 0:
                return
            ls = out_name.split('_')
            ls[-1] = 'LJSJ'
            out_name1 = '_'.join(ls)
            if out_name1 in server.data_dict:
                old_outvalue1 = server.getDataValue(out_name1)
    #             print out_name, 'LXSJ:', out_value
                if old_outvalue1 is None:
                    old_outvalue1 = 0
                out_value1 = old_outvalue1 + out_value
                SetOutputData(name, value, out_name1, out_value1, midSet, server)
    #             print 'ERTProcessing input_name : {0}, input_value : {1}, out_name: \
    #             {2}, out_value1: {3}'.format(name, value, out_name1, out_value1)
            out_value = 0
        SetOutputData(name, value, out_name, out_value, midSet, server)
    #     print 'ERTProcessing input_name : {0}, input_value : {1}, out_name: \
    #             {2}, out_value: {3}'.format(name, value, out_name, out_value)
    else:
        pass
    
@tryException
def ESSAccumulatedTime(name, logicObj, midSet, server):
#     print 'ESSAccumulatedTime Start: ', name
    in_value = server.getDataValue(name)
    if in_value >= 0:
        YX = server.getDataValue(logicObj.logic_cha)
        YQ = server.getDataValue(logicObj.logic_cha+'_YQ')
    if YX < 0:
        YX = 0
    dif = YQ - YX
    if YQ >= 0 and dif != 0:
        datachas = logicObj.getDataSet()
        data_map = {}
        for datacha in datachas:
            value = server.getDataValue(datacha.data_name)
            if value < 0:
                value = 0
            data_map[datacha.data_name] = value
        outvalue = 1
        if dif <= -1:
            outvalue = 0
            new_map = {}
            for name,value in data_map.iteritems():
                ls = name.split('_')
                ls[-1] = 'LXSJ'
                newname = '_'.join(ls)
                newvalue = server.getDataValue(newname)
                if newvalue > 0:
                    value = newvalue + value
                new_map[newname] = value
            dp = sorted(new_map.items,key=lambda d : d[1],reverse=True)
        else:
            dp = sorted(data_map.items,key=lambda d : d[1])
        for name in dp.keys():
            ls = name.split('_')
            ls[-1] = 'YX'
            if server.getDataValue('_'.join(ls)) == 1:
                continue
            ls[-1] = 'YQ'
            if server.getDataValue('_'.join(ls)) == 1:
                continue
            ls[-1] = 'ZK'
            if server.getDataValue('_'.join(ls)) == 0:
                continue
            if outvalue == 1:
                ls[-1] = 'GZ'
                if server.getDataValue('_'.join(ls)) != 1:
                    ls[-1] = 'YQ'
                    SetOutputData(name, in_value, '_'.join(ls), outvalue, midSet, server)
            else:
                SetOutputData(name, in_value, '_'.join(ls), outvalue, midSet, server)
#                 print 'ESSAccumulatedTime input_name : {0}, input_value : {1}, out_name: \
#                 {2}, out_value: {3}'.format(name, value, '_'.join(ls), outvalue)

@tryException
def MOV_ONInstr(name, logicObj, midSet, server):
    value = server.getDataValue(name)
    if value != 1:
        if SearchGeneralDataValue(logicObj.logic_cha + '_ZK', server) == 1:
            KG = server.getDataValue(logicObj.logic_cha + '_KG')
            if KG != value:
                server.sendCtrlCMD(logicObj.logic_cha + '_DO',INSTRUCTIONS.ON,0)
                print 'MOV_ONInstr OutPut:', logicObj.logic_cha + '_DO', INSTRUCTIONS.ON,'---------------------------------------'
                server.sendCtrlCMD(logicObj.logic_cha + '_DO_DY',INSTRUCTIONS.ON,0)
                print 'MOV_ONInstr OutPut:', logicObj.logic_cha + '_DO_DY', INSTRUCTIONS.ON,'---------------------------------------'
            else:
                pass
        else:
            pass
    else:
        pass      
            
@tryException
def MOV_OnOffInstr(name, logicObj, midSet, server):
#     print 'MOV_OnOffInstr Start: ', name
    value = server.getDataValue(name)
    if value is not None:
        if SearchGeneralDataValue(logicObj.logic_cha + '_ZK', server) == 1:
            KG = server.getDataValue(logicObj.logic_cha + '_KG')
            if KG != value:
                DY_KG = server.getDataValue(logicObj.logic_cha + '_DY_KG')
                if DY_KG == 1:
                    item = server.data_dict.get(name)
                    kgitem = server.data_dict.get(logicObj.logic_cha + '_KG')
                    if kgitem.time <= item.time:
                        if value == 1:
                            server.sendCtrlCMD(logicObj.logic_cha + '_DO',INSTRUCTIONS.ON,0)
#                             print 'MOV_OnOffInstr OutPut:', logicObj.logic_cha + '_DO', INSTRUCTIONS.ON,'---------------------------------------'
                            server.sendCtrlCMD(logicObj.logic_cha + '_DO_DY',INSTRUCTIONS.ON,0)
#                             print 'MOV_OnOffInstr OutPut:', logicObj.logic_cha + '_DO_DY', INSTRUCTIONS.ON,'---------------------------------------'
                        else:
                            server.sendCtrlCMD(logicObj.logic_cha + '_DO',INSTRUCTIONS.OFF,0)
#                             print 'MOV_OnOffInstr OutPut:', logicObj.logic_cha + '_DO', INSTRUCTIONS.OFF,'---------------------------------------'
                            server.sendCtrlCMD(logicObj.logic_cha + '_DO_DY',INSTRUCTIONS.ON,0)
#                             print 'MOV_OnOffInstr OutPut:', logicObj.logic_cha + '_DO_DY', INSTRUCTIONS.ON,'---------------------------------------'
                    else:
                        pass
            else:
                pass
    else:
        pass
    
@tryException
def LENRE50P_KTStateOutPut(name, logicObj, midSet, server):
#     print 'LENRE50P_KTStateOutPut Start: ', name
    KT_ZK = server.getDataValue('KT_ZK')
    KT_GK = server.getDataValue('KT_GK')
    KT_MS = server.getDataValue('KT_MS')
    if (KT_ZK == 0 or KT_ZK == 1) and (KT_GK == -1 or KT_GK == 1) and KT_MS >= 1:
        if not logicSet().existDelayLogic(logicObj.logic_cha + '_YX_YQ', logicObj):
            TOUT = 60
            YQ = None
            YX = None
            MS50P = None
            SDWD = None
            Q = []
            value = server.getDataValue(logicObj.logic_cha + '_YX_YQ')
            if value == 0 or value == 1:
                YQ = value
                if YQ == 0:
                    YX = INSTRUCTIONS.OFF
                else:
                    YX = INSTRUCTIONS.ON
                if KT_ZK == 0:
                    param = GetStaticParam(logicObj.logic_cha + '_TOUT')
                    if param is not None:
                        TOUT = param
                    kt_zk_item = server.data_dict.get('KT_ZK')
                    if (datetime.now() - kt_zk_item.time).total_seconds() > TOUT:
                        return
                if YQ == 1:
                    SD = GetGeneralParam(logicObj.logic_cha + '_SDWD', server, 1)
                    if SD is None:
                        if KT_GK == -1:
                            SD = 12.5
                        else:
                            SD = 44.5
                    SDWD = SD
                for datacha in logicObj.getDataSet():
                    name = datacha.data_name
                    ls = name.split('_')
                    ls[-1] = 'TXGZ'
                    TXGZ = server.getDataValue('_'.join(ls))
                    if TXGZ == 0:
                        if YQ == 0:
                            server.sendCtrlCMD(name,YX,0)
                        else:
                            ls[-1] = 'SDWD'
                            sdwd = server.getDataValue('_'.join(ls))
                            if sdwd <> SDWD:
                                server.sendCtrlCMD('_'.join(ls),SDWD,0)
                        value = server.getDataValue(name)
                        if value != YQ:
                            Q.append(name)
                        else:
                            pass
                    else:
                        pass
                random.shuffle(Q)
                if KT_GK == -1:
                    MS50P = INSTRUCTIONS.zhileng
                else:
                    MS50P = INSTRUCTIONS.zhire
                for name in Q:
                    ls = name.split('_')
                    ls[-1] = 'MS50P'
                    value = server.getDataValue('_'.join(ls))
                    if value != MS50P:
                        server.sendCtrlCMD('_'.join(ls),MS50P,0)
                delay_time = 10
                if YX == INSTRUCTIONS.OFF:
                    delay_time = GetStaticParam(logicObj.logic_cha + '_TOFF')
                else:
                    delay_time = GetStaticParam(logicObj.logic_cha + '_TON')
                if delay_time is None:
                    delay_time = 10
                logicSet().addDelayLogic(logicObj.logic_cha + '_YX_YQ', logicObj, datetime.now()+timedelta(seconds=int(delay_time)))
                print "addDelayLogic LENRE50P_KTStateOutPut:",name, int(delay_time), logicObj
            else:
                pass
        else:
            pass
    else:
        pass
    
@tryException
def SXDB_ESS(name, logicObj, midSet, server):
#     print 'SXDB_ESS Start: ', name
    value = server.getDataValue(name)
    if value is not None:
        flag = False
        if int(value) == 0:
            logicSet().delDelayLogic(name, logicObj)
            server.sendCtrlCMD(logicObj.logic_cha,INSTRUCTIONS.OFF,0)
            flag = True
            print 'SXDB_ESS:', logicObj.logic_cha, 'OFF','---------------------------------------'
        elif value >= 1:
            logic_value = server.getDataValue(logicObj.logic_cha)
            if logic_value != 1:
                ls = logicObj.logic_cha.split('_')
                ls[-1] = 'XX_YJ'
                if '_'.join(ls) in server.data_dict:
                    delay_time = GetStaticParam(name)
                    if delay_time is None:
                        delay_time = 10
                    dataitem = server.data_dict.get(name)
                    sumt = (datetime.now() - dataitem.time).total_seconds()
                    if sumt < delay_time:
                        server.sendCtrlCMD('_'.join(ls),INSTRUCTIONS.ON,0)
                        logicSet().addDelayLogic(name, logicObj, datetime.now()+timedelta(seconds=int(delay_time)))
                        print 'SXDB_ESS:', '_'.join(ls), 'ON','---------------------------------------'
                    else:
                        server.sendCtrlCMD(logicObj.logic_cha,INSTRUCTIONS.ON,0)
                        flag = True
                        print 'SXDB_ESS:', logicObj.logic_cha, 'ON','---------------------------------------'
                else:
                    server.sendCtrlCMD(logicObj.logic_cha,INSTRUCTIONS.ON,0)
                    flag = True
                    print 'SXDB_ESS:', logicObj.logic_cha, 'ON','---------------------------------------'
        if flag:
            dataconf = server.dataconf_dict.get(name)
            pri = dataconf.get('pri')
            if pri < 3:
                server.setDataReason(logicObj.logic_cha,dataitem.reason)
            else:
                rs_time = dataitem.time if dataitem.time > dataitem.dis_time else dataitem.dis_time
                data_reason = {'rs_type' : 1,
                               'rs_name' : dataitem.name,
                               'rs_cname': dataconf.get('data_cname'),
                               'rs_value' : float(value) if value is not None else value,
                               'rs_change_flag' : dataitem.change_flag,
                               'rs_time' : rs_time
                               }
                server.setDataReason(logicObj.logic_cha,data_reason)
        else:
            pass
        
@tryException
def Reverse01Assign(name, logicObj, midSet, server):
#     print 'Reverse01Assign Start: ', name
    out_value = None
    in_value = server.getDataValue(name)
    if in_value is not None:
        if in_value >= 1:
            out_value = 0
        else:
            out_value = 1
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'Reverse01Assign input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def CollectOrCmp_ACPermission(name, logicObj, midSet, server):
#     print 'CollectOrCmp_ACPermission Start: ', name
    out_value = 0
    in_value = server.getDataValue(name)
    if SearchGeneralDataValue(logicObj.logic_cha+'_ZK', server) == 1:
        if in_value >= 1:
            out_value = 1
        else:
            for datacha in logicObj.getDataSet():
                other_value = server.getDataValue(datacha.data_name)
                if other_value >= 1:
                    out_value = 1
                    break
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'CollectOrCmp_ACPermission input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def AutoStateCmp(name, logicObj, midSet, server):
#     print 'AutoStateCmp Start: ', name
    in_value = server.getDataValue(name)
    out_value = None
    ls_name = name.split('_')
#     if ls_name[2] == '1':
    print name,'AutoStateCmp', name ,in_value
    if in_value == 1:
        if ls_name[-1] == 'SD':
            out_value = 1
        elif ls_name[-1] == 'ZD':
            out_value = 2
    elif in_value == 0:
        dataitem = server.data_dict.get(name)
        flag = (datetime.now() - dataitem.time).total_seconds() < 2
        if flag:
            logicSet().addDelayLogic(name, logicObj, datetime.now()+timedelta(seconds=2))
#             print "addDelayLogic AutoStateCmp:",name,logicObj
            return
        else:
            out_value = 0
            for datacha in logicObj.getDataSet():
                if server.getDataValue(datacha.data_name) <> 0:
                    out_value = None
                    break
    if out_value is not None:
        ls_name[-1] = 'SZD'
        out_name = '_'.join(ls_name)
#         print '&&&&&&&&&&&', out_name, server.getDataValue(out_name), out_value
        if server.getDataValue(out_name) <> out_value:
            server.setDataValue(out_name,out_value)
#             print 'AutoStateCmp',out_name, server.data_dict.get(out_name),'***************************************'
            midSet.add(out_name)
        else:
            pass
    else:
        pass
#     print 'AutoStateCmp',out_value

@tryException
def AutoCtrlTest(name, logicObj, midSet, server):
#     print 'AutoCtrlTest Start: ', name
    in_value = server.getDataValue(name)
    ls_name = name.split('_')
    counts = len(ls_name)
    if in_value == 2:
        ls_name[counts-1] = 'YJ'
        val = server.getDataValue('_'.join(ls_name))
        if val is not None:
            print '_'.join(ls_name), 'ON','---------------------------------------'
            server.sendCtrlCMD('_'.join(ls_name),INSTRUCTIONS.ON,0)
            server.sendCtrlCMD('_'.join(ls_name),INSTRUCTIONS.OFF,get_refparam('SD_YJSJ'))
        ls_name[counts-1] = 'DO'
        val = server.getDataValue('_'.join(ls_name))
        if val is not None:
#             print '_'.join(ls_name), 'ON','---------------------------------------'
            server.sendCtrlCMD('_'.join(ls_name),INSTRUCTIONS.ON,get_refparam('SD_YJSJ'))
    else:
        ls_name[counts-1] = 'YJ'
        val = server.getDataValue('_'.join(ls_name))
        if val is not None:
#             print '_'.join(ls_name), 'OFF','---------------------------------------'
            server.sendCtrlCMD('_'.join(ls_name),INSTRUCTIONS.OFF,0)
        ls_name[counts-1] = 'DO'
        val = server.getDataValue('_'.join(ls_name))
        if val is not None:
#             print '_'.join(ls_name), 'OFF','---------------------------------------'
            server.sendCtrlCMD('_'.join(ls_name),INSTRUCTIONS.OFF,0)
      
@tryException      
def CondInit(name, logicObj, midSet, server):
#     print 'CondInit Start: ', name
    server_name = server.server_name
    out_name1 = server_name + '_GK'
    if out_name1 not in server.data_dict:
        return
    out_name2 = server_name + '_GK_YB'
    old_out_val1 = server.getDataValue(out_name1)
    if old_out_val1 is None:
        server.setDataValue(out_name1,0)
#         print 'CondInit out_name : {0}, out_value : {1}:'.format(out_name1, 0)
        data_reason = {'rs_type' : 2,
                       'rs_conf' : REASON_DICT[1],
                       }
        server.setDataReason(out_name1,data_reason)
        midSet.add(out_name1)
    else:
        pass
    date1 = date(date.today().year, 5, 14)
    date2 = date(date.today().year, 9, 15)
    date3 = date(date.today().year, 11, 14)
    date4 = date(date.today().year, 3, 15)
    out_val2 = 0
    if date1 <= date.today() <= date2:
        out_val2 = -1
    elif date.today() >= date3 or date.today() <= date4:
        out_val2 = 1
    old_out_val2 = server.getDataValue(out_name2)
    if old_out_val2 <> out_val2:
        server.setDataValue(out_name2,out_val2)
#         print 'CondInit out_name : {0}, out_value2 : {1}:'.format(out_name2, out_val2)
        data_reason = {'rs_type' : 2,
                       'rs_conf' : REASON_DICT[2],
                       }
        server.setDataReason(out_name2,data_reason)
        midSet.add(out_name2)
    else:
        pass
    
@tryException
def ModeInit(name, logicObj, midSet, server):
#     print 'ModeInit Start: ', name
    server_name = server.server_name
    out_name = server_name + '_MS'
    if out_name in server.data_dict:
        old_out_val = server.getDataValue(out_name)
        if old_out_val is None:
            server.setDataValue(out_name,0)
    #         print 'ModeInit out_name : {0}, out_value : {1}:'.format(out_name, 0)
            data_reason = {'rs_type' : 2,
                           'rs_conf' : REASON_DICT[3],
                           }
            server.setDataReason(out_name,data_reason)
            midSet.add(out_name)
        else:
            pass
    else:
        pass

@tryException
def PumpSZDCmp(name, logicObj, midSet, server):
#     print 'PumpSZDCmp Start: ', name
    in_value = server.getDataValue(name)
    out_value = 0
    ls_name = name.split('_')
    if  in_value == 1:
        if ls_name[-1] == 'SD':
            out_value = 1
        elif ls_name[-1] == 'ZD':
            out_value = -1
    elif in_value == 0:
        for datacha in logicObj.getDataSet():
            if server.getDataValue(datacha.data_name) <> 0:
                out_value = None
                break
    if out_value is not None:
        ls_name[-1] = 'SZD'
        out_name = '_'.join(ls_name)
        SetOutputData(name, in_value, out_name, out_value, midSet, server)
#         print 'PumpSZDCmp input_name : {0}, input_value : {1}, out_name: \
#         {2}, out_value: {3}'.format(name, in_value, out_name, out_value)
    else:
        pass

@tryException
def CollectGetMin(name, logicObj, midSet, server):
#     print 'CollectGetMin Start: ', name
    in_value = server.getDataValue(name)
    out_value = None
    for datacha in logicObj.getDataSet():
        other_value = server.getDataValue(datacha.data_name)
        if other_value is not None:
            if out_value is None:
                out_value = other_value
            elif other_value < out_value:
                out_value = other_value
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'CollectGetMin input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def RequireOutputDO(name, logicObj, midSet, server):
#     print 'RequireOutputDO Start: ', name
    value = server.getDataValue(name)
    if value == 0 or value == 1:
        if value == 0:
            server.sendCtrlCMD(logicObj.logic_cha,INSTRUCTIONS.OFF,0)
#             print 'RequireOutputDO:', logicObj.logic_cha, 'OFF','---------------------------------------'
        else:
            server.sendCtrlCMD(logicObj.logic_cha,INSTRUCTIONS.ON,0)
#             print 'RequireOutputDO:', logicObj.logic_cha, 'ON','---------------------------------------'
        dataitem = server.data_dict.get(name)
        dataconf = server.dataconf_dict.get(name)
        pri = dataconf.get('pri')
        if pri < 3:
            server.setDataReason(logicObj.logic_cha,dataitem.reason)
        else:
            rs_time = dataitem.time if dataitem.time > dataitem.dis_time else dataitem.dis_time
            data_reason = {'rs_type' : 1,
                           'rs_name' : dataitem.name,
                           'rs_cname': dataconf.get('data_cname'),
                           'rs_value' : value,
                           'rs_change_flag' : dataitem.change_flag,
                           'rs_time' : rs_time
                           }
            server.setDataReason(logicObj.logic_cha,data_reason)
    else:
        pass
    
@tryException
def CollectGetMax(name, logicObj, midSet, server):
#     print 'CollectGetMax Start: ', name
    out_value = None
    for datacha in logicObj.getDataSet():
        other_value = server.getDataValue(datacha.data_name)
        if other_value > out_value:
            out_value = other_value
    in_value = server.getDataValue(name)
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'CollectGetMax input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def TemperatureCmpCond(name, logicObj, midSet, server):
#     print 'TemperatureCmpCond Start: ', name
    value = server.getDataValue(name)
    if value is not None:
        out_value = None
        SD_GK_WD_1 = get_refparam('SD_GK_WD_1')
        SD_GK_WD_2 = get_refparam('SD_GK_WD_2')
        SD_GK_WD_3 = get_refparam('SD_GK_WD_3')
        SD_GK_WD_4 = get_refparam('SD_GK_WD_4')
        if value > SD_GK_WD_1:
            out_value = -1
        elif value < SD_GK_WD_4:
            out_value = 1
        elif SD_GK_WD_3 <= value <= SD_GK_WD_2:
            out_value = 0
        SetOutputData(name, value, logicObj.logic_cha, out_value, midSet, server)
#         print 'TemperatureCmpCond input_name : {0}, input_value : {1}, out_name: \
#             {2}, out_value: {3}'.format(name, value, logicObj.logic_cha, out_value)
    else:
        pass
    
@tryException
def DelayedReset(name, logicObj, midSet, server):
#     print 'DelayedReset Start: ', name
    out_value = 1
    SD = 60
    in_value = server.getDataValue(name)
    if in_value == 1:
        val = GetGeneralParam(name, server, 1)
        if val is not None:
            SD = val
    dataitem = server.data_dict.get(name)
    if (datetime.now() - dataitem.time).total_seconds() >= int(SD):
        out_value = 0
    else:
        logicSet().addDelayLogic(name, logicObj, datetime.now()+timedelta(seconds=int(SD)))
        return
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'DelayedReset input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, in_value, logicObj.logic_cha, out_value)

@tryException
def ChangedAs1(name, logicObj, midSet, server):
#     print 'ChangedAs1 Start: ', name
    out_value = 0
    dataitem = server.data_dict.get(name)
    if dataitem.change_flag == 1 and (datetime.now() - dataitem.time).total_seconds() <= 10:
        out_value = 1
    else:
        return
    SetOutputData(name, server.getDataValue(name), logicObj.logic_cha, out_value, midSet, server)
#     print 'ChangedAs1 input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, server.getDataValue(name), logicObj.logic_cha, out_value)

@tryException
def One2Many01SYN(name, logicObj, midSet, server):
#     print 'One2Many01SYN Start: ', name
    in_value = server.getDataValue(name)
    if in_value is not None:
        if in_value <= 0.1:
            out_value = 0
        else:
            out_value = 1
        for datacha in logicObj.getDataSet():
#             print 'One2Many01SYN:', datacha
            SetOutputData(name, in_value, datacha.data_name, out_value, midSet, server)
#             print 'One2Many01SYN input_name : {0}, input_value : {1}, out_name: \
#             {2}, out_value: {3}'.format(name, in_value, datacha.data_name, out_value)
    else:
        pass
    
@tryException
def JudgeInfraredYWR(name, logicObj, midSet, server):
#     print 'JudgeInfraredYWR Start: ', name
    T = 10
    ls = name.split('_')
    ls[-1] = 'YWR'
    out_value = server.getDataValue('_'.join(ls))
    if out_value == 0 or out_value == 2:
        param = GetStaticParam(logicObj.logic_cha,server)
        if param is not None:
            T = param
        if T > 3600:
            T = 3600
        ls[-1] = 'SJ'
        sj = server.getDataValue('_'.join(ls))
        if sj <= T:
            out_value = 2
        else:
            out_value = 0
    in_value = server.getDataValue(name)
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'JudgeInfraredYWR input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, server.getDataValue(name), logicObj.logic_cha, out_value)
        
@tryException
def JudgeInfraredYWR_I3(name, logicObj, midSet, server):
#     print 'JudgeInfraredYWR_I3 Start: ', name
    T = 10
    ls = name.split('_')
    ls[-1] = 'YWR'
    out_value = server.getDataValue('_'.join(ls))
    if out_value == 0 or out_value == 2:
        param = GetStaticParam(logicObj.logic_cha,server)
        if param is not None:
            T = param
        if T > 3600:
            T = 3600
        ls[-1] = 'SJ'
        sj = server.getDataValue('_'.join(ls))
        if sj <= T:
            out_value = 1
        else:
            out_value = 0
    in_value = server.getDataValue(name)
    SetOutputData(name, in_value, logicObj.logic_cha, out_value, midSet, server)
#     print 'JudgeInfraredYWR_I3 input_name : {0}, input_value : {1}, out_name: \
#     {2}, out_value: {3}'.format(name, server.getDataValue(name), logicObj.logic_cha, out_value)
    
def_jslogic(u'新数值则赋值',NewDataUpdate)
def_jslogic(u'非空新数则赋值',NotNoneNewDataUpdate)
def_jslogic(u'汇总_正数累加运算', CollectPosSum)
def_jslogic(u'大于零新值赋算法特征值', Greater0AssignByDl_alg)
def_jslogic(u'汇总_取最高_有上限', CollectGetMax_Toplimit)
def_jslogic(u'汇总_累加_有上限', CollectSum_Toplimit)
def_jslogic(u'汇总_或运算', CollectOrCmp)
def_jslogic(u'汇总_与运算', CollectAndCmp)
def_jslogic(u'汇总_平均值', CollectGetAverage)
def_jslogic(u'备用非空新数赋值', PreNotNoneNewDataUpdate)
def_jslogic(u'新数值0/1赋值', New01Assign)
def_jslogic(u'新数值0/1反向赋值', New01ReverseAssign)
def_jslogic(u'双阈值双向判断0/1', BidirectionalJudge01)
def_jslogic(u'异常数据反向赋值', ErrorReverseAssign)
def_jslogic(u'异常数据同步赋值', ErrorAssign)
def_jslogic(u'非空加减运算', SumNotNone)
def_jslogic(u'两数相除', Division)
def_jslogic(u'正数延时赋值', PositiveDelayAssign)
def_jslogic(u'有偏差比较并取整',RoundCompareDeviation)
def_jslogic(u'电动阀开关状态', MOV_OnOffState)
def_jslogic(u'电动阀开关后延时复查', MOVOnOff_DelayCheck)
def_jslogic(u'电动阀状态匹配检查', MOV_StateMatchCheck)
def_jslogic(u'电器设备运行判断',OPJudgementOfEE)
def_jslogic(u'设备运行时间处理',ERTProcessing)
def_jslogic(u'按累计时间启停设备',ESSAccumulatedTime)
def_kzlogic(u'电动阀开指令', MOV_ONInstr)
def_kzlogic(u'电动阀开关指令', MOV_OnOffInstr)
def_kzlogic(u'PHINX50P空调机组启停指令', LENRE50P_KTStateOutPut)
def_kzlogic(u'三相表设备启停',SXDB_ESS)

def_jslogic(u'反向0/1赋值', Reverse01Assign)
def_jslogic(u'汇总_或运算_有自控许可',CollectOrCmp_ACPermission)
def_jslogic(u'泵三相表手自动位置计算',AutoStateCmp)
def_kzlogic(u'泵自动启停测试',AutoCtrlTest)
def_jslogic(u'工况上电初始化',CondInit)
def_jslogic(u'模式上电初始化',ModeInit)
def_jslogic(u'泵手自动位置计算',PumpSZDCmp)
def_jslogic(u'汇总_取最低',CollectGetMin)
def_kzlogic(u'根据要求输出DO',RequireOutputDO)
def_jslogic(u'汇总_取最高',CollectGetMax)
def_jslogic(u'温度算工况', TemperatureCmpCond)
def_jslogic(u'延时自复位', DelayedReset)
def_jslogic(u'变化则为1', ChangedAs1)
def_jslogic(u'一对多非空0/1同步', One2Many01SYN)

def_jslogic(u'红外有无人综合判断', JudgeInfraredYWR)
def_jslogic(u'红外有无人综合判断_忽略3', JudgeInfraredYWR_I3)