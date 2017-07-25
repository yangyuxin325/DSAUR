#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年2月24日

@author: sanhe
'''
from UserDict import UserDict
import struct
from util import crc16, tryException


__all__ = ['device_Dict','sesstype_Dict']


__metaclass__ = type

# 设备类型对照表
device_Dict = {}
device_Dict['infrared'] = u'红外探测器'
device_Dict['co2'] = u'co2探测器'
device_Dict['stc_1'] = u'模块stc_1'
device_Dict['stc_201'] = u'模块stc_201'
device_Dict['plc'] = u'可编程控制器'
device_Dict['sansu'] = u'三速风机'
device_Dict['triplecng'] = u'三联供机组'
device_Dict['voc'] = u'voc探测器'
device_Dict['wenkong'] = u'温控器'
device_Dict['ZMA194E'] = u'三相电表'
device_Dict['WK_DI16'] = u'模块WK_DI16'
device_Dict['MB10TD'] = u'模块MB10TD'
device_Dict['MB8AI'] = u'模块MB8AI'
device_Dict['MB12RO'] = u'模块MB12RO'
device_Dict['RESHUI'] = u'热水机组'
device_Dict['LENRE50P'] = u'冷热风冷模块'
# 通道类型
sesstype_Dict = {}
sesstype_Dict[1] = u'usb转485'

# 设备类对照表
devicecls_dict = UserDict()

def def_deviceClass(name, clsobj):
    devicecls_dict[name] = clsobj
        
class device(UserDict):
    def __init__(self,disCount=0,disMax=10):
        UserDict.__init__(self)
        self.data_dict = {}
        self.write_set = set()
        self.data_linkpara = {}
        self.algorithm_dict = {}
        self.linkset = set()
        self.disCount = disCount
        self.disMax = disMax
        self.state = False
        if disCount <= disMax:
            self.state = True
        else:
            self.state = False
        
    def addDataName(self, conf_name, dataname, link_conf=None, al=None):
        self[conf_name] = [dataname, None]
        if link_conf is not None:
            self.data_linkpara[conf_name] = link_conf
            self.linkset.add(link_conf)
        if al is not None:
            self.algorithm_dict[conf_name] = al
        else:
            pass
                
    @classmethod
    def genPratrolInstr(cls, ID):
        pass
                
    def __setValue(self, conf_name ,value):
        if self.has_key(conf_name):
            self[conf_name][1] = value
        else:
            pass
            
    def setDataValue(self, conf_name ,value):
        if conf_name in self:
            self.__setValue(conf_name, value)
#             if conf_name =='5_1':
#             print self[conf_name]
            if conf_name in self.linkset:
                for k,v in self.data_linkpara.items():
                    if v == conf_name:
                        self.__setValue(k,value)
                    else:
                        pass
            else:
                pass
        else:
            pass
#         if conf_name == 'DisCount' and self[conf_name][0] == 'KT_WJ_1_4_TX':
#             print conf_name, self[conf_name]
        
    def setDisConnect(self, flag):
        if flag:
#             print self.disCount, self.disMax
            if self.disCount <= self.disMax:
                self.disCount = self.disCount + 1
                self.setDataValue('DisCount', self.disCount)
            else:
                if self.state:
                    self.state = False
                else:
                    pass
        else:
            self.disCount = 0
            self.setDataValue('DisCount', self.disCount)
            if not self.state:
                self.state = True
            else:
                pass
        return self.state
        
    def dataParse(self, data):
        pass

class infrared(device):
    SLEEP_TIME = 0.02
    SUPPORTED_INSTRUCTIONS = {
        "LED_AUTO"   : 0 ,
        "LED_ON"     : 1 ,
        "LED_OFF"    : 2 ,
        "LED_URGENT" : 3 ,
                         }
    
    @classmethod
    def getInstrValue(cls, instr):
        return cls.SUPPORTED_INSTRUCTIONS.get(instr)
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'YWren' : None,
                    'LedState' : None,
                    'DoorState' : None,
                    'InfoTime' : None,
                    'Temperature' : None,
                    'Humidity' : None,
                    'Lux' : None,
                    'DisCount' : None,
                    }
        self.write_set = set(['LedState'])
    
    @classmethod
    def checkSum(self, array):
        check_sum = 0
        for data in array:
            check_sum += data
            check_sum &= 0xff
        array.append(check_sum)
        return array
        
    @classmethod
    def genPratrolInstr(cls, ID):
        data = bytearray([0x99, ID, 0x00, 0xff, 0xff])
        return [cls.checkSum(data)]
        
    def genControlInstr(self, ID, conf_name ,instr):
        if self.state is False:
            return
        if conf_name != 'LedState':
            return 
        if instr not in self.SUPPORTED_INSTRUCTIONS.keys():
            err = "There is not a {} in infrared's SUPPORTED_INSTRUCTIONS".format(instr)
            raise Exception(err)
        data = bytearray([0x99, ID, 0x01, 0x00, self.SUPPORTED_INSTRUCTIONS[instr]])
        return {"id" : 0, 'cmd' : self.checkSum(data), 'dev_id' : ID}
    
    @tryException
    def dataParse(self, data):
        if len(data) != 17:
            return False
        YWren = (data[3] & 3)
        LedState = ((data[3] & 12) >> 2)
        DoorState = (data[3] & 16) >> 4
#         device_state = (data[3] & 32) >> 5
        InfoTime = (data[4] * 15000 + data[5] * 70) // 1000
        Temperature = float(data[7]) + float(data[8]) / 100.0
        if 1 == data[6]:
            Temperature = -Temperature
        Humidity = float(data[9]) + float(data[10]) / 100.0
        Lux = data[14] * 256 + data[15]
        self.setDataValue('YWren', YWren)
        self.setDataValue('LedState', LedState)
        self.setDataValue('DoorState', DoorState)
        self.setDataValue('InfoTime', InfoTime)
        self.setDataValue('Temperature', Temperature)
        self.setDataValue('Humidity', Humidity)
        self.setDataValue('Lux', Lux)
        return True
            
def_deviceClass('infrared',infrared)
            
class co2(device):
    SLEEP_TIME = 0.007
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'CO2' : None,
                    'DisCount' : None,
                    }
        
    @classmethod
    def genPratrolInstr(cls, ID):
        data = bytearray([ID,0x04,0x00,0x00,0x00,0x01])
        crc = crc16()
        return [crc.createarray(data)]
    
    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        CO2 = data[3]*256 + data[4]
        self.setDataValue('CO2', CO2)
        return True
            
def_deviceClass('co2',co2)
            
class stc_1(device):
    SLEEP_TIME = 0.001
    INSTRUCTIONS = {
        'DO' : (1, 8),
        'DI' : (2, 8),
        'AO' : (3, 0),
        'AI' : (4, 8),}
    
    SUPPORTED_INSTRUCTIONS = {
        'ON' : 255,
        'OFF': 0,
                }
    
    @classmethod
    def getInstrValue(cls, instr):
        if instr == 'ON':
            return 1
        return cls.SUPPORTED_INSTRUCTIONS.get(instr)
    
    AI_CONVERT_DICT = {
                   1 : lambda x : (x - 4000) / 160.0,                 # /*温度：0——100*/
                   2 : lambda x : (x - 4000) / 160.0 - 50.0,          # /*温度：-50——50*/
                   3 : lambda x : (x - 4000) * 10.197 / 16000.0,      # /*压力：0——10.197*/
                   4 : lambda x : (x - 4000) * 8.0 / 1600.0 - 20.0,   # /*温度：-20——60*/
                   5 : lambda x : (x - 400) / 16.0,                   # /*温度：0——100*/
                   6 : lambda x : (x - 400) / 16.0 - 50.0,            # /*温度：-50——50*/
                   7 : lambda x : (x - 400) * 10.197 / 1600.0,        # /*压力：0——10.197*/
                   8 : lambda x : (x - 400) * 8.0 / 160.0 - 20.0,     # /*温度：-20——60*/
                   }
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'DisCount' : None,
                    }
        self.write_set = set()
        for key in self.INSTRUCTIONS.keys() :
            str_fisrt = key
            if self.INSTRUCTIONS[key][1] > 0 :
                for num in range(self.INSTRUCTIONS[key][1]):
                    str_name = str_fisrt + str(num+1)
                    self.data_dict.update({str_name : None})
                    if str_fisrt == 'DO' or str_fisrt == 'AO':
                        self.write_set.add(str_name)
        
        self.__Parsedict = {
                           1 : self.__D_IOParse,
                           2 : self.__D_IOParse,
                           3 : self.__AOparse,
                           4 : self.__AIParse,
                           }
        
    @classmethod
    def genPratrolInstr(cls, ID):
        instr = []
        for key,val in cls.INSTRUCTIONS.values():
            if val > 0 : 
                data = bytearray([ID,key,0x00,0x00,0x00,val])
                crc = crc16()
                instr.append(crc.createarray(data))
        return instr
        
    def genControlInstr(self, ID, conf_name ,instr):
        if self.state is False:
            return
        if conf_name[:2] not in ('DO', 'AO'):
            err = "There is not a {} in stc_1's INSTRUCTIONS".format(conf_name)
            raise Exception(err)
        if int(conf_name[2:],10) < 1 or int(conf_name[2:],10) > self.INSTRUCTIONS[conf_name[:2]][1] :
            err = "There is not a {} in stc_1's IO_PORT".format(conf_name)
            raise Exception(err)
        data = bytearray([ID,0x05,0x00,int(conf_name[2:],10)-1,0x00,0x00])
        if conf_name[:2] == 'DO':
            data[4] = self.SUPPORTED_INSTRUCTIONS[instr]
        elif conf_name[:2] == 'AO':
            data[1] = 0x06
            data[2] = (40001+int(conf_name[2:],10)) >> 8
            data[3] = (40001+int(conf_name[2:],10)) & 0xff
            data[4] = int(instr,10) >> 8
            data[5] = int(instr,10) & 0xff
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
    
    def __D_IOParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        str_first = None
        if data[1] == 1:
            str_first = 'DO'
        elif data[1] == 2:
            str_first = 'DI'
        val = None
        for i in range(8*data[2]):
            if i < 8 :
                val = (data[3] & (1 << i)) >> i
            else:
                val = (data[4] & (1 << (i - 8))) >> (i - 8)
            str_name = str_first + str(i+1)
#                 print '*****************', data[0], str_name, val
            self.setDataValue(str_name, val)
        return True
            
    def __AOparse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        val1 = data[3] << 8 + data[4]
        val2 = data[5] << 8 + data[6]
        self.setDataValue('AO1', val1)
        self.setDataValue('AO2', val2)
        return True
        
    def __AIParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        str_first = 'AI'
        val = None
        for i in range(data[2]/2):
            val = (data[i*2+3] << 8) + data[i*2+4]
            str_name = str_first + str(i+1)
            if str_name in self.algorithm_dict:
                al = self.algorithm_dict[str_name]
                val = round(self.AI_CONVERT_DICT[al](val),2)
            else:
                pass
            self.setDataValue(str_name, val)
        return True
        
    @tryException
    def dataParse(self, data):
        if data[1] not in [1,2,3,4]:
            return False
        return self.__Parsedict[data[1]](data)
            
def_deviceClass('stc_1',stc_1)
            
class stc_201(device):
    SLEEP_TIME = 0.003
    INSTRUCTIONS = {
        'DO' : (1, 3),
        'DI' : (2, 6),
        'AO' : (3, 15),
        'AI' : (4, 19),}
    
    SUPPORTED_INSTRUCTIONS = {
        'ON' : 255,
        'OFF': 0,
                }
    
    @classmethod
    def getInstrValue(cls, instr):
        if instr == 'ON':
            return 1
        return cls.SUPPORTED_INSTRUCTIONS.get(instr)
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'DisCount' : None,
                    }
        self.write_set = set()
        for key in self.INSTRUCTIONS.keys() :
            str_fisrt = key
            if self.INSTRUCTIONS[key][1] > 0 :
                for num in range(self.INSTRUCTIONS[key][1]):
                    str_name = str_fisrt + str(num+1)
                    self.data_dict.update({str_name : None})
                    if str_fisrt == 'DO' or str_fisrt == 'AO':
                        self.write_set.add(str_name)
        
        self.__Parsedict = {
                           1 : self.__D_IOParse,
                           2 : self.__D_IOParse,
                           3 : self.__AOparse,
                           4 : self.__AIParse,
                           }
        
    @classmethod
    def genPratrolInstr(cls, ID):
        instr = []
        for key,val in cls.INSTRUCTIONS.values():
            if val > 0 : 
                data = bytearray([ID,key,0x00,0x00,0x00,val])
                crc = crc16()
                instr.append(crc.createarray(data))
        return instr
        
    def genControlInstr(self, ID, conf_name ,instr):
        if self.state is False:
            return
        if conf_name[:2] not in ('DO', 'AO'):
            err = "There is not a {} in stc_1's INSTRUCTIONS".format(conf_name)
            raise Exception(err)
        if int(conf_name[2:],10) < 1 or int(conf_name[2:],10) > self.INSTRUCTIONS[conf_name[:2]][1] : 
            err = "There is not a {} in stc_1's IO_PORT".format(conf_name)
            raise Exception(err)
        data = bytearray([ID,0x05,0x00,int(conf_name[2:],10)-1,0x00,0x00])
        if conf_name[:2] == 'DO':
            data[4] = self.SUPPORTED_INSTRUCTIONS[instr]
        elif conf_name[:2] == 'AO':
            data[1] = 0x06
            data[2] = (40001+int(conf_name[2:],10)) >> 8
            data[3] = (40001+int(conf_name[2:],10)) - data[2]*256
            data[4] = int(instr,10) >> 8
            data[5] = int(instr,10) & 0xff
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
    
    def __D_IOParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        str_first = None
        if data[1] == 1:
            str_first = 'DO'
        elif data[1] == 2:
            str_first = 'DI'
        val = None
        port_nums =self.INSTRUCTIONS[str_first][1]
        for i in range(port_nums*data[2]):
            if i < 8 :
                val = (data[3] & (1 << i)) >> i
            else:
                val = (data[4] & (1 << (i - 8))) >> (i - 8)
            str_name = str_first + str(i+1)
            self.setDataValue(str_name, val)
        return True
            
    def __AOparse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        str_first = 'AO'
        val = None
        for i in range(data[2]/2):
            val = (data[i*2+4] << 8) + data[i*2+3]
            str_name = str_first + str(i+1)
            self.setDataValue(str_name, val)
        return True
        
    def __AIParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        str_first = 'AI'
        val = None
        for i in range(data[2]/2):
            val = (data[i*2+3] << 8) + data[i*2+4]
            str_name = str_first + str(i+1)
            if i < 3 :
                val = val / 10.0
            elif 2 < i < 7  or i == 16:
                val = val / 100.0
            elif i == 15 or i > 16 :
                val = val / 1000.0
            self.setDataValue(str_name, val)
        return True
            
    @tryException
    def dataParse(self, data):
        if data[1] not in [1,2,3,4]:
            return False
        return self.__Parsedict[data[1]](data)
            
def_deviceClass('stc_201',stc_201)
            
class plc(device):
    SLEEP_TIME = 0.007
    INSTRUCTIONS = {
        'DO' : (1, 8),
        'DI' : (2, 12),
        'AO' : (3, 2),
        'AI' : (4, 8),}
    
    SUPPORTED_INSTRUCTIONS = {
        'ON' : 255,
        'OFF': 0,
                }
    
    @classmethod
    def getInstrValue(cls, instr):
        if instr == 'ON':
            return 1
        return cls.SUPPORTED_INSTRUCTIONS.get(instr)
    
    AI_CONVERT_DICT = {
                   1 : lambda x : (x - 4000) / 160.0,                 # /*温度：0——100*/
                   2 : lambda x : (x - 4000) / 160.0 - 50.0,          # /*温度：-50——50*/
                   3 : lambda x : (x - 4000) * 10.197 / 16000.0,      # /*压力：0——10.197*/
                   4 : lambda x : (x - 4000) * 8.0 / 1600.0 - 20.0,   # /*温度：-20——60*/
                   5 : lambda x : (x - 400) / 16.0,                   # /*温度：0——100*/
                   6 : lambda x : (x - 400) / 16.0 - 50.0,            # /*温度：-50——50*/
                   7 : lambda x : (x - 400) * 10.197 / 1600.0,        # /*压力：0——10.197*/
                   8 : lambda x : (x - 400) * 8.0 / 160.0 - 20.0,     # /*温度：-20——60*/
                   }
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'DisCount' : None,
                    }
        self.write_set = set()
        for key in self.INSTRUCTIONS.keys() :
            str_fisrt = key
            if self.INSTRUCTIONS[key][1] > 0 :
                for num in range(self.INSTRUCTIONS[key][1]):
                    str_name = str_fisrt + str(num+1)
                    self.data_dict.update({str_name : None})
                    if str_fisrt == 'DO' or str_fisrt == 'AO':
                        self.write_set.add(str_name)

        
        self.__Parsedict = {
                           1 : self.__D_IOParse,
                           2 : self.__D_IOParse,
                           3 : self.__AOparse,
                           4 : self.__AIParse,
                           }
        
    @classmethod
    def genPratrolInstr(cls, ID):
        instr = []
        for key,val in cls.INSTRUCTIONS.values():
            if val > 0 : 
                data = bytearray([ID,key,0x00,0x00,0x00,val])
                crc = crc16()
                instr.append(crc.createarray(data))
        return instr
        
    def genControlInstr(self, ID, conf_name ,instr):
        if self.state is False:
            return
        if conf_name[:2] not in ('DO', 'AO'):
            err = "There is not a {} in stc_1's INSTRUCTIONS".format(conf_name)
            raise Exception(err)
        if int(conf_name[2:],10) < 1 or int(conf_name[2:],10) > self.INSTRUCTIONS[conf_name[:2]][1] : 
            err = "There is not a {} in stc_1's IO_PORT".format(conf_name)
            raise Exception(err)
        data = bytearray([ID,0x05,0x00,int(conf_name[2:],10)-1,0x00,0x00])
        if conf_name[:2] == 'DO':
            data[4] = self.SUPPORTED_INSTRUCTIONS[instr]
        elif conf_name[:2] == 'AO':
            data[1] = 0x06
            data[2] = (40001+int(conf_name[2:],10)) >> 8
            data[3] = (40001+int(conf_name[2:],10)) - data[2]*256
            data[4] = int(instr,10) >> 8
            data[5] = int(instr,10) & 0xff
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
    
    def __D_IOParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        str_first = None
        if data[1] == 1:
            str_first = 'DO'
        elif data[1] == 2:
            str_first = 'DI'
        val = None
        for i in range(8*data[2]):
            if i < 8 :
                val = (data[3] & (1 << i)) >> i
            else:
                val = (data[4] & (1 << (i - 8))) >> (i - 8)
            str_name = str_first + str(i+1)
            self.setDataValue(str_name, val)
        return True
            
    def __AOparse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        val1 = (data[3] << 8) + data[4]
        val2 = (data[5] << 8) + data[6]
        self.setDataValue('AO1', val1)
        self.setDataValue('AO2', val2)
        return True
        
    def __AIParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        str_first = 'AI'
        val = None
        for i in range(data[2]/2):
            val = (data[i*2+3] << 8) + data[i*2+4]
            str_name = str_first + str(i+1)
            if str_name in self.algorithm_dict:
                al = self.algorithm_dict[str_name]
                val = round(self.AI_CONVERT_DICT[al](val),2)
            else:
                pass
            self.setDataValue(str_name, val)
        return True
            
    @tryException
    def dataParse(self, data):
        if data[1] not in [1,2,3,4]:
            return False
        return self.__Parsedict[data[1]](data)
            
def_deviceClass('plc',plc)

class sansu(device):
    SLEEP_TIME = 0.003
    INSTRUCTIONS = {
        "Wind"   : 0x64 ,
        "Fa1"    : 0x65 ,
        "Fa2"    : 0x66 ,}
    
    SUPPORTED_INSTRUCTIONS = {
        'gaosu'   : 3,
        'zhongsu' : 2,
        'disu'    : 1,
        'tingzhi' : 0,
        'fakai'   : 1,
        'faguan'  : 0,}
    
    @classmethod
    def getInstrValue(cls, instr):
        return cls.SUPPORTED_INSTRUCTIONS.get(instr)
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'Wind' : None,
                    'Fa1' : None,
                    'Fa2' : None,
                    'DisCount' : None,
                    }
        self.write_set = set(['Wind','Fa1','Fa2'])

        
    @classmethod
    def genPratrolInstr(cls, ID):
        data = bytearray([ID,0x03,0x00,0x64,0x00,0x03])
        crc = crc16()
        return [crc.createarray(data)]
        
    def genControlInstr(self, ID, conf_name ,instr):
        if self.state is False:
            return
        if conf_name not in self.INSTRUCTIONS.keys():
            err = "There is not a {} in sansu's INSTRUCTIONS".format(conf_name)
            raise Exception(err)
        data = bytearray([ID, 0x06, 0x00, self.INSTRUCTIONS[conf_name], 0x00, self.SUPPORTED_INSTRUCTIONS[instr]])
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}

    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        if data[1] != 0x03:
            return False
        Wind = data[3]*256 + data[4]
        Fa1 = data[5]*256 + data[6]
        Fa2 = data[7]*256 + data[8]
        self.setDataValue('Wind', Wind)
        self.setDataValue('Fa1', Fa1)
        self.setDataValue('Fa2', Fa2)
        return True
            
def_deviceClass('sansu',sansu)
            
class triplecng(device):
    SLEEP_TIME = 0.004
    INSTRUCTIONS = {
        "6_1"   :  (49001,0) ,
        "6_2"    :  (49002,0) ,
        "6_3" :  (49003,1) ,
        "6_4" :  (49004,1) ,
        "6_5":  (49005,1) ,
        "5_4" :  (44313,1) ,
        "5_5" :  (44314,1) ,}
    
    SUPPORTED_INSTRUCTIONS = {
        "ON"      :   1,
        "OFF"     :   0,
        "zhileng" :   0,
        "zhire"   :   1,
        "reshui"  :   2,
        "zl&rs"   :   3,
        "zr&rs"   :   4,}
    
    @classmethod
    def getInstrValue(cls, instr):
        return cls.SUPPORTED_INSTRUCTIONS.get(instr)
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    '1_1' : None,
                    '2_1Error' : None,
                    '2_2Error' : None,
                    '2_3Error' : None,
                    '2_4Error' : None,
                    '2_5Error' : None,
                    '2_6Error' : None,
                    '2_7Error' : None,
                    '2_8Error' : None,
                    '2_9Error' : None,
                    '2_10Error' : None,
                    '2_11Error' : None,
                    '2_12Error' : None,
                    '2_13Error' : None,
                    '2_14Error' : None,
                    '2_15Error' : None,
                    '2_16Error' : None,
                    '2_17Error' : None,
                    '2_18Error' : None,
                    '2_19Error' : None,
                    '2_20Error' : None,
                    '2_21Error' : None,
                    '2_22Error' : None,
                    '2_23Error' : None,
                    '2_24Error' : None,
                    '2_25Error' : None,
                    '2_26Error' : None,
                    '2_27Error' : None,
                    '2_28Error' : None,
                    '2_29Error' : None,
                    '2_30Error' : None,
                    '2_31Error' : None,
                    '2_32Error' : None,
                    '5_1' : None,
                    '5_2' : None,
                    '5_3' : None,
                    '5_4' : None,
                    '5_5' : None,
                    '6_1' : None,
                    '6_2' : None,
                    '6_3' : None,
                    '6_4' : None,
                    '6_5' : None,
                    '15_1' : None,
                    '15_2' : None,
                    '15_3' : None,
                    '15_4' : None,
                    '15_5' : None,
                    '15_6' : None,
                    '15_7' : None,
                    '15_8' : None,
                    '15_9' : None,
                    '15_10' : None,
                    '15_11' : None,
                    '15_12' : None,
                    '15_13' : None,
                    '15_14' : None,
                    '15_15' : None,
                    '16_1' : None,
                    '16_2' : None,
                    '16_3' : None,
                    '16_4' : None,
                    '16_5' : None,
                    '16_6' : None,
                    '16_7' : None,
                    '16_8' : None,
                    '16_9' : None,
                    '16_10' : None,
                    '16_11' : None,
                    '16_12' : None,
                    '16_13' : None,
                    '16_14' : None,
                    '16_15' : None,
                    '16_16' : None,
                    'DisCount' : None,
                    }
        self.write_set = set(['OnOff','Mode','AC_Cool','AC_Warm','HotWater','AC_Diff','WB_Diff'])

    
    @classmethod
    def genPratrolInstr(cls, ID):
        instr = []
        addrs = {
            5:44310,
            1:44370,
            6:49001,
            16:28401,
            15:27901,
            2:28901,
            }
        for addr in addrs.items():
            addr1 = addr[1] >> 8;
            addr2 = addr[1] & 0xff
            data = bytearray([ID,0x03,addr1,addr2,0x00,addr[0]])
            if addr[0] == 15 or addr[0] == 16 or addr[0] == 2 :
                data[1] = 0x04
            crc = crc16()
            instr.append(crc.createarray(data))
        return instr
        
    def genControlInstr(self, ID, conf_name ,instr):
        if self.state is False:
            return
        if conf_name not in self.INSTRUCTIONS.keys():
            err = "There is not a {} in triplecng's INSTRUCTIONS".format(conf_name)
            raise Exception(err)
        Addr = self.INSTRUCTIONS[conf_name][0]
        valtype = self.INSTRUCTIONS[conf_name][1]
        val1 = None
        val2 = None
        if valtype != 1 : 
            val = self.SUPPORTED_INSTRUCTIONS[instr]
            val1 = val >> 8
            val2 = val - val1 * 256
        else : 
            val1 = (int(instr) * 10 + 65536) >> 8
            val2 = (int(instr) * 10 + 65536) & 0xff
        data = bytearray([ID, 0x10, Addr >> 8, Addr & 0xff, 0x00, 0x01, 0x02, val1, val2])
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
    
    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        data_type = data[2]//2
        str_type = str(data_type)
        str_name = str_type + '_'
        if data_type == 1 : 
            str_temp = str_name + str(1)
            self.setDataValue(str_temp, data[3] << 8 + data[4])
        elif data_type == 2 :
            for i in range(32) :
                str_temp = str_name + str(i+1) + 'Error'
                if i < 8:
                    self.setDataValue(str_temp,(data[3] & (1 << i)) >> i) 
                elif i < 16:
                    self.setDataValue(str_temp,(data[4] & (1 << (i-8))) >> (i-8))
                elif i < 24:
                    self.setDataValue(str_temp,(data[5] & (1 << (i-16))) >> (i-16))
                else:
                    self.setDataValue(str_temp,(data[6] & (1 << (i-24))) >> (i-24))
        elif data_type == 5 :
            for i in range(5) :
                str_temp = str_name + str(i+1)
                self.setDataValue(str_temp,((data[i*2+3] << 8) + data[i*2+4])//10)
        elif data_type == 6 :
            for i in range(5) :
                str_temp = str_name + str(i+1)
                if i ==  0 or i == 1 :
                    self.setDataValue(str_temp,(data[i*2+3] << 8) + data[i*2+4])
                else :
                    if 0xff == data[i*2+3]:
                        self.setDataValue(str_temp,((data[i*2+3] << 8) + data[i*2+4] - 65536)//10)
                    else:
                        self.setDataValue(str_temp,((data[i*2+3] << 8) + data[i*2+4])//10)
        elif data_type == 15 : 
            for i in range(15) :
                str_temp = str_name + str(i+1)
                self.setDataValue(str_temp,(data[i*2+3] << 8) + data[i*2+4])
        elif data_type == 16 : 
            for i in range(16) :
                str_temp = str_name + str(i+1)
                self.setDataValue(str_temp,((data[i*2+3] << 8) + data[i*2+4])//10)
        return True
            
def_deviceClass('triplecng',triplecng)

class voc(device):
    SLEEP_TIME = 0.007
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'VOC' : None,
                    'Temperature' : None,
                    'Humidity' : None,
                    'DisCount' : None,
                    }

        
    @classmethod
    def genPratrolInstr(cls, ID):
        data = bytearray([ID,0x04,0x00,0x00,0x00,0x06])
        crc = crc16()
        return [crc.createarray(data)]
    
    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        VOC = (data[3]*256 + data[4])/10.0
        Temperature = (data[5]*256 + data[6])/10.0
        Humidity = data[7]*256+data[8]
        self.setDataValue('VOC', VOC)
        self.setDataValue('Temperature', Temperature)
        self.setDataValue('Humidity', Humidity)
        return True
            
def_deviceClass('voc',voc)
            
class wenkong(device):
    SLEEP_TIME = 0.01
    INSTRUCTIONS = {
        "OnOff"   : 2 ,
        "Mode"    : 3 ,
        "SetTemp" : 4 ,
        "Wind"    : 5 ,}
    
    SUPPORTED_INSTRUCTIONS = {
        "ON"      : 1 ,
        "OFF"     : 0 ,
        "zhileng" : 1 ,
        "zhire"   : 2 ,
        "tongfeng" : 3,
        "zidong"  : 0,
        "gaosu"   : 1,
        "zhongsu" : 2,
        "disu"    : 3,
        }
    
    @classmethod
    def getInstrValue(cls, instr):
        return cls.SUPPORTED_INSTRUCTIONS.get(instr)
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'OnOff' : None,
                    'Mode' : None,
                    'SetTemp' : None,
                    'Wind' : None,
                    'Temperature' : None,
                    'DisCount' : None
                    }
        self.write_set = set(['OnOff','Mode','SetTemp','Wind'])

        
    @classmethod
    def genPratrolInstr(cls, ID):
        data = bytearray([ID,0x03,0x00,0x02,0x00,0x08])
        crc = crc16()
        return [crc.createarray(data)]


    def genControlInstr(self, ID, conf_name ,instr):
        if self.state is False:
            return
        if conf_name not in self.INSTRUCTIONS.keys():
            err = "There is not a {} in wenkong's INSTRUCTIONS".format(conf_name)
            raise Exception(err)
        val = 0
        if self.INSTRUCTIONS[conf_name] != 'SetTemp':
            val = self.SUPPORTED_INSTRUCTIONS[instr]
        else:
            val = int(instr)
        data = bytearray([ID, 0x06, 0x00, self.INSTRUCTIONS[conf_name], 0x00, val])
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
    
    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        if data[1] != 0x03:
            return False
        OnOff = data[4]
        Mode = data[5] * 256 + data[6]
        SetTemp = data[7] + data[8]/10.0
        Wind = data[9]*256 + data[10]
        Temp = data[17] + data[18]/10.0
        self.setDataValue('OnOff', OnOff)
        self.setDataValue('Mode', Mode)
        self.setDataValue('SetTemp', SetTemp)
        self.setDataValue('Wind', Wind)
        self.setDataValue('Temperature', Temp)
        return True
            
def_deviceClass('wenkong',wenkong)
            
class ZMA194E(device):
    SLEEP_TIME = 0.05
    INSTRUCTIONS = ['DO1','DO2','DO3','DO4']
    
    SUPPORTED_INSTRUCTIONS = {
        "ON"      : 1 ,
        "OFF"     : 0 ,}
    
    @classmethod
    def getInstrValue(cls, instr):
        return cls.SUPPORTED_INSTRUCTIONS.get(instr)
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.doarray = None
        self.flag = False
        self.data_dict = {
                          'DO1' : None,
                          'DO2' : None,
                          'DO3' : None,
                          'DO4' : None,
                          'DI1' : None,
                          'DI2' : None,
                          'DI3' : None,
                          'DI4' : None,
                          'RMSUA' : None,
                          'RMSUB' : None,
                          'RMSUC' : None,
                          'Udiff'  : None,
                          'RMSIA' : None,
                          'RMSIB' : None,
                          'RMSIC' : None,
                          'Idiff'  : None,
                          'Psum'  : None,
                          'Pfsum' : None,
                          'FreqA' : None,
                          'WH-1'  : None,
                          'DisCount' : None,
                    }
        self.write_set = set(['DO1','DO2','DO3','DO4'])
        
    @classmethod
    def genPratrolInstr(cls, ID):
        arr = []
        crc = crc16()
        data = bytearray([ID,0x03,0x00,0x14,0x00,0x03])
        arr.append(crc.createarray(data))
        data = bytearray([ID,0x03,0x00,0x17,0x00,0x1A])
        arr.append(crc.createarray(data))
        data = bytearray([ID,0x03,0x00,0x3F,0x00,0x12])
        arr.append(crc.createarray(data))
        data = bytearray([ID,0x03,0x00,0x57,0x00,0x02])
        arr.append(crc.createarray(data))
#         data = [ID,0x06,0x00,0x16,0x00,0x02]
#         arr.append(crc.createarray(data))
        return arr
    
    def genControlInstr(self, ID, conf_name ,instr):
        if self.state is False:
            return
# #         print ID,conf_name,instr
#         self.flag = True
        self.doarray = [0,0,0,0]
#         if self.doarray is None:
#             return
        if conf_name not in self.INSTRUCTIONS:
            err = "There is not a {} in ZMA194E's INSTRUCTIONS".format(conf_name)
            raise Exception(err)
        val = self.SUPPORTED_INSTRUCTIONS[instr]
        self.doarray[int(conf_name[2:]) - 1] = val
        val = 0
        for i, v in enumerate(self.doarray):
            val = val + (v << i)
        data = bytearray([ID, 0x06, 0x00, 0x16, 0x00, val])
        crc = crc16()
#         self.flag = False
#         print ID,conf_name,instr, self.doarray,'~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
    
    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        if data[1] != 0x03:
            return False
        data_type = data[2]//2
        if data_type == 3:
            self.setDataValue('DI4', (data[6] & 0x08) >> 3)
            self.setDataValue('DI3', (data[6] & 0x04) >> 2)
            self.setDataValue('DI2', (data[6] & 0x02) >> 1)
            self.setDataValue('DI1', data[6] & 0x01)
            DO4 = (data[8] & 0x08) >> 3
            DO3 = (data[8] & 0x04) >> 2
            DO2 = (data[8] & 0x02) >> 1
            DO1 =  data[8] & 0x01
            self.setDataValue('DO4', DO4)
            self.setDataValue('DO3', DO3)
            self.setDataValue('DO2', DO2)
            self.setDataValue('DO1', DO1)
            self.doarray = [0,0,0,0]
        elif data_type == 26:
#                 print data
            RMSUA = None
            RMSUB = None
            RMSUC = None
            RMSIA = None
            RMSIB = None
            RMSIC = None
            for i in range(13):
                if i < 4 or 5 < i < 9 or i== 12: 
                    arr = data[3+i*4 : 7+i*4]
                    strdata = ''
                    for j in arr:
                        strdata = strdata + chr(j)
#                         print '三相电表1： ', strdata, 'LENGTH:', len(strdata)
                    value = round(struct.unpack('!f',strdata)[0],2)
                    if i == 0:
                        RMSUA = value
                        self.setDataValue('RMSUA', value)
                    elif i == 1:
                        RMSUB = value
                        self.setDataValue('RMSUB', value)
                    elif i == 2:
                        RMSUC = value
                        self.setDataValue('RMSUC', value)
                    elif i == 6:
                        RMSIA = value
                        self.setDataValue('RMSIA', value)
                    elif i == 7:
                        RMSIB = value
                        self.setDataValue('RMSIB', value)
                    elif i == 8:
                        RMSIC = value
                        self.setDataValue('RMSIC', value)
                    elif i == 12:
                        self.setDataValue('Psum', value)
            import math                            
            Udiff = max(math.fabs(RMSUA - RMSUB), math.fabs(RMSUA - RMSUC), math.fabs(RMSUB - RMSUC))
            Idiff = max(math.fabs(RMSIA - RMSIB), math.fabs(RMSIA - RMSIC), math.fabs(RMSIB - RMSIC))
            self.setDataValue('Udiff', round(Udiff,2))
            self.setDataValue('Idiff', round(Idiff,2))
        elif data_type == 18:
            strdata = ''
            for j in data[3:7]:
                strdata = strdata + chr(j)
#                 print '三相电表2： ', strdata, 'LENGTH:', len(strdata)
            value = round(struct.unpack('!f',strdata)[0],2)
            self.setDataValue('Pfsum', value)
            strdata = ''
            for j in data[23:27]:
                strdata = strdata + chr(j)
#                 print '三相电表3： ', strdata, 'LENGTH:', len(strdata)
            value = round(struct.unpack('!f',strdata)[0],2)
            self.setDataValue('FreqA', value)
        elif data_type == 2:
            strdata = ''
            for j in data[3:7]:
                strdata = strdata + chr(j)
#                 print '三相电表4： ', strdata, 'LENGTH:', len(strdata)
            value = round((struct.unpack('!I',strdata)[0])/100.0,2)
            self.setDataValue('WH-1', value)
        return True
            
def_deviceClass('ZMA194E',ZMA194E)
            
class WK_DI16(device):
    SLEEP_TIME = 0.01
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'DisCount' : None,
                    }
        for i in xrange(16):
            str_name = 'DI' + str(i+1)
            self.data_dict.update({str_name : None})
            
    @classmethod
    def genPratrolInstr(cls, ID):
        data = bytearray([ID,0x02,0x00,0x00,0x00,0x10])
        crc = crc16()
        return [crc.createarray(data)]
    
    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        val = 0
        for i in range(8*data[2]):
            if i < 8 :
                val = (data[3] & (1 << i)) >> i
            else:
                val = (data[4] & (1 << (i - 8))) >> (i - 8)
            str_name = 'DI' + str(i+1)
            self.setDataValue(str_name, val)
        return True
            
def_deviceClass('WK_DI16',WK_DI16)
            
class MB10TD(device):
    SLEEP_TIME = 0.5
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'DisCount' : None,
                    }
        for i in xrange(10):
            self.data_dict.update({'DA' + str(i+1) : None})
            self.data_dict.update({'STATE' + str(i+1) : None})
        
    @classmethod    
    def genSetAddressInstr(cls, ID, newID):
        data = bytearray([ID, 0x10, 0x00, 0x46, 0x00, 0x01, 0x02, 0x00, newID])
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
            
    @classmethod
    def genPratrolInstr(cls, ID):
        arr = []
        crc = crc16()
        data = bytearray([ID,0x04,0x00,0x00,0x00,0x0A])
        arr.append(crc.createarray(data))
        data = bytearray([ID,0x02,0x00,0x00,0x00,0x0A])
        arr.append(crc.createarray(data))
        return arr
    
    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        if data[1] == 0x04:
            for i in xrange(data[2]/2):
                str_name = 'DA' + str(i+1)
                strdata = ''
                strdata = strdata + chr(data[4+i*2])
                strdata = strdata + chr(data[3+i*2])
#                 arrbytes = bytearray([data[4+i*2],data[3+i*2]])
                self.setDataValue(str_name, struct.unpack('h',strdata)[0]/10.0)
        elif data[1] == 0x02:
            val = 0
            for i in xrange(10):
                if i < 8 :
                    val = (data[3] & (1 << i)) >> i
                else:
                    val = (data[4] & (1 << (i - 8))) >> (i - 8)
                str_name = 'STATE' + str(i+1)
                self.setDataValue(str_name, val)
        return True
            
def_deviceClass('MB10TD',MB10TD)
            
            
class MB8AI(device):
    SLEEP_TIME = 0.3
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'DisCount' : None,
                    }
        for i in xrange(8):
            self.data_dict.update({'AI' + str(i+1) : None})
    
    AI_CONVERT_DICT = {
                   9 : lambda x : x * 20 / 4096.0,
#                    10 : lambda x : (x/4096.0*20-4.0)*10.0/16.0,
                   10 : lambda x : x*20.0/4096.0/16.0*10.0,
                   11 : lambda x : x * 5 / 4096.0,
                   12 : lambda x : x * 10 / 4096.0,   
                   }
    
    @classmethod
    def genSetInputTypeInstr(cls, ID, InputType):
        data = bytearray([ID, 0x06, 0x00, 0x4b, 0x00, InputType])
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
        
    @classmethod    
    def genSetAddressInstr(cls, ID, newID):
        data = bytearray([ID, 0x10, 0x00, 0x46, 0x00, 0x01, 0x02, 0x00, newID])
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
            
    @classmethod
    def genPratrolInstr(cls, ID):
        data = bytearray([ID,0x04,0x00,0x00,0x00,0x08])
        crc = crc16()
        return [crc.createarray(data)]
    
    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        if data[1] == 0x04:
            for i in xrange(data[2]/2):
                str_name = 'AI' + str(i+1)
#                 arrbytes = bytearray([data[4+i*2],data[3+i*2]])
                strdata = ''
                strdata = strdata + chr(data[4+i*2])
                strdata = strdata + chr(data[3+i*2])
                val = struct.unpack('h',strdata)[0]
                if str_name in self.algorithm_dict:
                    al = self.algorithm_dict[str_name]
                    val = round(self.AI_CONVERT_DICT[al](val),2)
                self.setDataValue(str_name, val)
        else:
            return False
        return True
            
def_deviceClass('MB8AI',MB8AI)
            
            
class MB12RO(device):
    SLEEP_TIME = 0.01
    SUPPORTED_INSTRUCTIONS = {
        'ON' : 255,
        'OFF': 0,
                }
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    'DisCount' : None,
                    }
        for i in xrange(12):
            self.data_dict.update({'RO' + str(i+1) : None})
        
    @classmethod    
    def genSetAddressInstr(cls, ID, newID):
        data = bytearray([ID, 0x10, 0x00, 0x46, 0x00, 0x01, 0x02, 0x00, newID])
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
    
    @classmethod
    def genPratrolInstr(cls, ID):
        data = bytearray([ID,0x01,0x00,0x00,0x00,0x0B])
        crc = crc16()
        return [crc.createarray(data)]
    
    def genControlInstr(self, ID, conf_name ,instr):
        data = bytearray([ID,0x05,0x00,int(conf_name[2:],10)-1,0x00,0x00])
        if conf_name[:2] == 'RO':
            data[4] = self.SUPPORTED_INSTRUCTIONS[instr]
        else:
            return None
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
            
    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        if data[1] == 0x01:
            val = 0
            for i in xrange(12):
                if i < 8 :
                    val = (data[3] & (1 << i)) >> i
                else:
                    val = (data[4] & (1 << (i - 8))) >> (i - 8)
                str_name = 'RO' + str(i+1)
                self.setDataValue(str_name, val)
        else:
            return False
        return True
            
def_deviceClass('MB12RO',MB12RO)

class RESHUI(device):
    SLEEP_TIME = 0.01
    INSTRUCTIONS = {
        "3_1"   :  (49001,0),
        "3_2"   :  (49002,0),
        "3_3"   :  (49003,1),}
    
    SUPPORTED_INSTRUCTIONS = {
        "ON"      :   1,
        "OFF"     :   0,
        "zhileng" :   0,
        "jjzhire"   :   1,
        "zidong"  :   2,
        "zhire"   :   3,
        "kszhire"    :   4,}
    
    @classmethod
    def getInstrValue(cls, instr):
        return cls.SUPPORTED_INSTRUCTIONS.get(instr)
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    '1_1' : None,
                    '2_1Error' : None,
                    '2_2Error' : None,
                    '2_3Error' : None,
                    '2_4Error' : None,
                    '2_5Error' : None,
                    '2_6Error' : None,
                    '2_7Error' : None,
                    '2_8Error' : None,
                    '2_9Error' : None,
                    '2_10Error' : None,
                    '2_11Error' : None,
                    '2_12Error' : None,
                    '2_13Error' : None,
                    '2_14Error' : None,
                    '2_15Error' : None,
                    '2_16Error' : None,
                    '2_17Error' : None,
                    '2_18Error' : None,
                    '2_19Error' : None,
                    '2_20Error' : None,
                    '2_21Error' : None,
                    '2_22Error' : None,
                    '2_23Error' : None,
                    '2_24Error' : None,
                    '2_25Error' : None,
                    '2_26Error' : None,
                    '2_27Error' : None,
                    '2_28Error' : None,
                    '2_29Error' : None,
                    '2_30Error' : None,
                    '2_31Error' : None,
                    '2_32Error' : None,
                    '3_1' : None,
                    '3_2' : None,
                    '3_3' : None,
                    '6_1' : None,
                    '6_2' : None,
                    '6_3' : None,
                    '6_4' : None,
                    '6_5' : None,
                    '6_6' : None,
                    '5_1' : None,
                    '5_2' : None,
                    '5_3' : None,
                    '5_4' : None,
                    '5_5' : None,
                    '11_1' : None,
                    '11_2' : None,
                    '11_3' : None,
                    '11_4' : None,
                    '11_5' : None,
                    '11_6' : None,
                    '11_7' : None,
                    '11_8' : None,
                    '11_9' : None,
                    '11_10' : None,
                    '11_11' : None,
                    'DisCount' : None,
                    }
    
    @classmethod
    def genPratrolInstr(cls, ID):
        instr = []
        addrs = {
            3:49001,
            11:28401,
            5:27901,
            6:28906,
            2:28902,
            }
        for addr in addrs.items():
            addr1 = addr[1] >> 8;
            addr2 = addr[1] & 0xff
            data = bytearray([ID,0x04,addr1,addr2,0x00,addr[0]])
            if addr[0] == 3:
                data[1] = 0x03
            crc = crc16()
            instr.append(crc.createarray(data))
        return instr
        
    def genControlInstr(self, ID, conf_name ,instr):
        if self.state is False:
            return
        if conf_name not in self.INSTRUCTIONS.keys():
            err = "There is not a {} in triplecng's INSTRUCTIONS".format(conf_name)
            raise Exception(err)
        Addr = self.INSTRUCTIONS[conf_name][0]
        valtype = self.INSTRUCTIONS[conf_name][1]
        val1 = None
        val2 = None
        if valtype != 1 : 
            val = self.SUPPORTED_INSTRUCTIONS[instr]
            val1 = val >> 8
            val2 = val - val1 * 256
        else :
            m = struct.pack('h',int(instr)*10)
            val1 = ord(m[1])
            val2 = ord(m[0])
        data = bytearray([ID, 0x10, Addr >> 8, Addr & 0xff, 0x00, 0x01, 0x02, val1, val2])
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
    
    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        data_type = data[2]//2
        str_type = str(data_type)
        str_name = str_type + '_'
        if data_type == 2 :
            for i in range(32) :
                str_temp = str_name + str(i+1) + 'Error'
                if i < 8:
                    self.setDataValue(str_temp,(data[3] & (1 << i)) >> i) 
                elif i < 16:
                    self.setDataValue(str_temp,(data[4] & (1 << (i-8))) >> (i-8))
                elif i < 24:
                    self.setDataValue(str_temp,(data[5] & (1 << (i-16))) >> (i-16))
                else:
                    self.setDataValue(str_temp,(data[6] & (1 << (i-24))) >> (i-24))
        else:
            for i in xrange(data_type) :
                str_temp = str_name + str(i+1)
#                 arrbytes = bytearray([data[4+i*2],data[3+i*2]])
                strdata = ''
                strdata = strdata + chr(data[4+i*2])
                strdata = strdata + chr(data[3+i*2])
                val = struct.unpack('h',strdata)[0]
                if data_type == 11 or (data_type == 3 and i == 2):
                    val = val/10.0
                self.setDataValue(str_temp,val)
        return True
                
def_deviceClass('RESHUI',RESHUI)

class LENRE50P(device):
    SLEEP_TIME = 0.01
    INSTRUCTIONS = {
        "3_1"   :  (49001,0) ,
        "3_2"    :  (49002,0) ,
        "3_3" :  (49003,1) ,}
    
    SUPPORTED_INSTRUCTIONS = {
        "ON"      :   1,
        "OFF"     :   0,
        "zhileng" :   0,
        "jjzhire" :   1,
        "zidong"  :   2,
        "zhire"   :   3,
        "kszhire" :   4,}
    
    @classmethod
    def getInstrValue(cls, instr):
        return cls.SUPPORTED_INSTRUCTIONS.get(instr)
    
    def __init__(self,disCount=0,disMax=10):
        device.__init__(self,disCount,disMax)
        self.data_dict = {
                    '1_1Error' : None,
                    '1_2Error' : None,
                    '1_3Error' : None,
                    '1_4Error' : None,
                    '1_5Error' : None,
                    '1_6Error' : None,
                    '1_7Error' : None,
                    '1_8Error' : None,
                    '1_9Error' : None,
                    '1_10Error' : None,
                    '1_11Error' : None,
                    '1_12Error' : None,
                    '1_13Error' : None,
                    '1_14Error' : None,
                    '1_15Error' : None,
                    '1_16Error' : None,
                    '2_1Error' : None,
                    '2_2Error' : None,
                    '2_3Error' : None,
                    '2_4Error' : None,
                    '2_5Error' : None,
                    '2_6Error' : None,
                    '2_7Error' : None,
                    '2_8Error' : None,
                    '2_9Error' : None,
                    '2_10Error' : None,
                    '2_11Error' : None,
                    '2_12Error' : None,
                    '2_13Error' : None,
                    '2_14Error' : None,
                    '2_15Error' : None,
                    '2_16Error' : None,
                    '2_17Error' : None,
                    '2_18Error' : None,
                    '2_19Error' : None,
                    '2_20Error' : None,
                    '2_21Error' : None,
                    '2_22Error' : None,
                    '2_23Error' : None,
                    '2_24Error' : None,
                    '2_25Error' : None,
                    '2_26Error' : None,
                    '2_27Error' : None,
                    '2_28Error' : None,
                    '2_29Error' : None,
                    '2_30Error' : None,
                    '2_31Error' : None,
                    '2_32Error' : None,
                    '3_1' : None,
                    '3_2' : None,
                    '3_3' : None,
                    '4_1' : None,
                    '4_2' : None,
                    '4_3' : None,
                    '4_4' : None,
                    '5_1' : None,
                    '5_2' : None,
                    '5_3' : None,
                    '5_4' : None,
                    '5_5' : None,
                    '15_1' : None,
                    '15_2' : None,
                    '15_3' : None,
                    '15_4' : None,
                    '15_5' : None,
                    '15_6' : None,
                    '15_7' : None,
                    '15_8' : None,
                    '15_9' : None,
                    '15_10' : None,
                    '15_11' : None,
                    '15_12' : None,
                    '15_13' : None,
                    '15_14' : None,
                    '15_15' : None,
                    '9_1' : None,
                    '9_2' : None,
                    '9_3' : None,
                    '9_4' : None,
                    '9_5' : None,
                    '9_6' : None,
                    '9_7' : None,
                    '9_8' : None,
                    '9_9' : None,
                    'DisCount' : None,
                    }
    
    @classmethod
    def genPratrolInstr(cls, ID):
        instr = []
        addrs = {
            3:49001,
            15:28401,
            9:27901,
            5:27911,
            4:46503,
            1:28901,
            2:28902,
            }
        for addr in addrs.items():
            addr1 = addr[1] >> 8;
            addr2 = addr[1] & 0xff
            data = bytearray([ID,0x04,addr1,addr2,0x00,addr[0]])
            if addr[0] == 3 or addr[0] == 4:
                data[1] = 0x03
            crc = crc16()
            instr.append(crc.createarray(data))
        return instr
        
    def genControlInstr(self, ID, conf_name ,instr):
        if self.state is False:
            return
        if conf_name not in self.INSTRUCTIONS.keys():
            err = "There is not a {} in triplecng's INSTRUCTIONS".format(conf_name)
            raise Exception(err)
        Addr = self.INSTRUCTIONS[conf_name][0]
        valtype = self.INSTRUCTIONS[conf_name][1]
        val1 = None
        val2 = None
        if valtype != 1 : 
            val = self.SUPPORTED_INSTRUCTIONS[instr]
            val1 = val >> 8
            val2 = val - val1 * 256
        else : 
            m = struct.pack('h',int(instr)*10)
            val1 = ord(m[1])
            val2 = ord(m[0])
        data = bytearray([ID, 0x10, Addr >> 8, Addr & 0xff, 0x00, 0x01, 0x02, val1, val2])
        crc = crc16()
        return {"id" : 0, 'cmd' : crc.createarray(data), 'dev_id' : ID}
    
    @tryException
    def dataParse(self, data):
        if len(data) - 5 <> data[2]:
            return False
        data_type = data[2]//2
        str_type = str(data_type)
        str_name = str_type + '_'
        if data_type == 1 : 
            for i in range(16) :
                str_temp = str_name + str(i+1) + 'Error'
                if i < 8:
                    self.setDataValue(str_temp,(data[3] & (1 << i)) >> i) 
                else:
                    self.setDataValue(str_temp,(data[4] & (1 << (i-8))) >> (i-8))
        elif data_type == 2 :
            for i in range(32) :
                str_temp = str_name + str(i+1) + 'Error'
                if i < 8:
                    self.setDataValue(str_temp,(data[3] & (1 << i)) >> i) 
                elif i < 16:
                    self.setDataValue(str_temp,(data[4] & (1 << (i-8))) >> (i-8))
                elif i < 24:
                    self.setDataValue(str_temp,(data[5] & (1 << (i-16))) >> (i-16))
                else:
                    self.setDataValue(str_temp,(data[6] & (1 << (i-24))) >> (i-24))
        elif data_type == 3 :
            for i in range(3) :
                str_temp = str_name + str(i+1)
                if i == 2:
#                     arrbytes = bytearray([data[4+i*2],data[3+i*2]])
                    strdata = ''
                    strdata = strdata + chr(data[4+i*2])
                    strdata = strdata + chr(data[3+i*2])
                    val = struct.unpack('h',strdata)[0]/10.0
                    self.setDataValue(str_temp,val)
                else:
                    self.setDataValue(str_temp,(data[i*2+3] << 8) + data[i*2+4])
        elif data_type == 4 :
            for i in range(4) :
                str_temp = str_name + str(i+1)
#                 arrbytes = bytearray([data[4+i*2],data[3+i*2]])
                strdata = ''
                strdata = strdata + chr(data[4+i*2])
                strdata = strdata + chr(data[3+i*2])
                val = struct.unpack('h',strdata)[0]/10.0
                self.setDataValue(str_temp,val)
        elif data_type == 5 :
            for i in range(5) :
                str_temp = str_name + str(i+1)
                self.setDataValue(str_temp,(data[i*2+3] << 8) + data[i*2+4])
        elif data_type == 9 : 
            for i in range(9) :
                str_temp = str_name + str(i+1)
                self.setDataValue(str_temp,(data[i*2+3] << 8) + data[i*2+4])
        elif data_type == 15 : 
            for i in range(15) :
                str_temp = str_name + str(i+1)
#                 arrbytes = bytearray([data[4+i*2],data[3+i*2]])
                strdata = ''
                strdata = strdata + chr(data[4+i*2])
                strdata = strdata + chr(data[3+i*2])
                val = struct.unpack('h',strdata)[0]/10.0
                self.setDataValue(str_temp,val)
        return True

def_deviceClass('LENRE50P',LENRE50P)
