#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年2月24日

@author: sanhe
'''
'''
class: 
min_count 计算平均值类
instance method: 
addValue(self, value) 设置真实值后，返回平均计算值
'''

from datetime import datetime
import math
import copy

__all__ = ['dataObj', 'dataCalObj']

class min_count():
    def __init__(self, minute):
        self.__minute = minute
        self.__total = 0
        self.__count = 0
        self.__start_time = None
        self.__min = None
        
    def addValue(self, value):
        if value is None:
            if self.__start_time is None or (datetime.now() - self.__start_time).total_seconds() > self.__minute * 60:
                self.__min = None
                self.__total = 0
                self.__count = 0
                self.__start_time = None
            else:
                pass
        else:
            self.__total += value
            self.__count += 1
            if self.__start_time is None:
                self.__start_time = datetime.now()
            else:
                if (datetime.now() - self.__start_time).total_seconds() >= self.__minute * 60:
                    self.__min = round(self.__total/self.__count,2)
                    self.__total = 0
                    self.__count = 0
                    self.__start_time = datetime.now()
                else:
                    pass
        return self.__min
    
    
#attribute 0:transmitdata 1:devicedata 2:udevdata 3:mepdata 4:perioddata
class dataObj(object):
    def __init__(self, name, value, error_flag, time, dis_flag, dis_time, change_flag, reason, attribute=0):
        self.name = name
        self.value = value
        self.error_flag = error_flag
        self.time = time
        self.dis_flag = dis_flag
        self.dis_time = dis_time
        self.change_flag = change_flag
        self.reason = reason
        self.attribute = attribute
        
    def setData(self,data):
        self.__init__(data.name,data.value,data.error_flag,data.time,
                         data.dis_flag,data.dis_time,data.change_flag,data.reason,self.attribute)
        
    def __repr__(self):
        return "<%r : %r,%r,%r,%r,%r,%r,%r>" % (self.name,self.value,self.error_flag,self.time,
                                             self.dis_flag,self.dis_time,self.change_flag,self.attribute)
    
    def getValue(self):
        if not self.error_flag:
            return self.value
        
    def encodeReason(self):
        if self.reason is not None:
            rs = copy.deepcopy(self.reason)
            if rs['rs_type'] == 1:
                rs['rs_time'] = str(rs['rs_time'])[:19]
            return rs
        else:
            return None
            
class dataCalObj(object):
    def  __init__(self, dataobj, constraint, minute=None):
        self.__dataobj = dataobj
        self.__constraint = constraint
        self.__minobj = None
        if minute is not None:
            self.__minobj = min_count(minute)
            
    def getValue(self):
        if not self.error_flag:
            return self.value
        
    @property
    def constraint(self):
        return self.__constraint
    
    @constraint.setter
    def constraint(self, dataconstraint):
        self.__constraint = dataconstraint
        
    @property
    def attribute(self):
        return self.__dataobj.attribute
            
    @property
    def name(self):
        return self.__dataobj.name
    
    @name.setter
    def name(self, name):
        self.__dataobj = name
    
    @property
    def value(self):
        return self.__dataobj.value
    
    @value.setter
    def value(self, value):
        self.__dataobj.value = value
    
    @property
    def error_flag(self):
        return self.__dataobj.error_flag
    
    @error_flag.setter
    def error_flag(self, error_flag):
        self.__dataobj.error_flag = error_flag
    
    @property
    def time(self):
        return self.__dataobj.time
    
    @time.setter
    def time(self, time):
        self.__dataobj.time = time
    
    @property
    def dis_flag(self):
        return self.__dataobj.dis_flag
    
    @dis_flag.setter
    def dis_flag(self, dis_flag):
        self.__dataobj.dis_flag = dis_flag
    
    @property
    def dis_time(self):
        return self.__dataobj.dis_time
    
    @dis_time.setter
    def dis_time(self, dis_time):
        self.__dataobj.dis_time = dis_time
    
    @property
    def change_flag(self):
        return self.__dataobj.change_flag
            
    @change_flag.setter
    def change_flag(self, change_flag):
        self.__dataobj.change_flag = change_flag

    @property
    def reason(self):
        return self.__dataobj.reason
    
    @reason.setter
    def reason(self, rs):
        self.__dataobj.reason = rs
        
    def encodeReason(self):
        if self.reason is not None:
            rs = copy.deepcopy(self.reason)
            if rs['rs_type'] == 1 and rs['rs_time'] is not None:
                rs['rs_time'] = str(rs['rs_time'])[:19]
            return rs
        else:
            return None
        
    def __repr__(self):
        return "<%r : %r,%r,%r,%r,%r,%r,%r>" % (self.name,self.value,self.error_flag,self.time,
                                             self.dis_flag,self.dis_time,self.change_flag,self.attribute)
            
    def setValue(self, value):
        error_flag = self.error_flag
        min_val = self.__constraint['min_val']
        max_val = self.__constraint['max_val']
#         if self.name.split('_')[-1] <> 'period' and self.name.split('_')[-1] <> 'TX':
#             print self.name, value, min_val, max_val
        if value is not None:
            if min_val is not None and max_val is not None:
                if value > max_val or value < min_val:
                    error_flag = True
                else:
                    error_flag = False
            elif min_val is not None:
                if value < min_val:
                    error_flag = True
                else:
                    error_flag = False
            elif max_val is not None:
                if value > max_val:
                    error_flag = True
                else:
                    error_flag = False
            else:
                error_flag = False
        else:
            if min_val is not None or max_val is not None:
                error_flag = True
            else:
                error_flag = False
                if self.value <> value:
                    self.value = value
                    self.change_flag = 1
                else:
                    self.change_flag = 0
        if self.__minobj is not None:
            if error_flag is True:
                value = self.__minobj.addValue(None)
                if value is not None:
                    error_flag = False
                else:
                    pass
            else:
                value = self.__minobj.addValue(value)
        else:
            pass
        if error_flag != self.error_flag:
            self.value = value
            self.time = datetime.now()
            self.error_flag = error_flag
            if self.error_flag:
                self.change_flag = 11
            else:
                self.change_flag = 10
        else:
            if value is None:
                return self.change_flag
            if error_flag is False:
                if (self.value is None and value is not None) or \
                math.fabs(value - self.value) > self.__constraint['min_variation']:
                    self.value = value
                    self.change_flag = 1
                    self.time = datetime.now()
                else:
                    if self.change_flag == 1:
                        self.change_flag = 0
                    else:
                        if self.change_flag > 1 and self.dis_flag == True:
                            self.change_flag = self.change_flag - 1
                        else:
                            self.change_flag = 0
                if self.dis_flag == True:
                    self.dis_flag = False
                    self.dis_time = datetime.now()
                else:
                    pass
            else:
                if self.dis_flag == True:
                    self.dis_flag = False
                    self.dis_time = datetime.now()
                    self.change_flag = self.change_flag - 1
                else:
                    self.change_flag = 0
        return self.change_flag