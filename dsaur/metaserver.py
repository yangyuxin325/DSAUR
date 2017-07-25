#coding=utf-8
#!/usr/bin/env python

'''
Created on 2016年12月13日

@author: sanhe
'''

from datetime import datetime

__all__ = ['videoserver', 'subordinate','superior']

class metaserver(object):
    def __init__(self, server_name, state =False, statetime=None):
        self.server_name = server_name
        self.state = state
        self.statetime = statetime
        self.reconnect = False
        self.socksession = None
        
    def setState(self, state, statetime):
        self.state = state
        self.statetime = statetime
        
    def sendData(self, data):
        if self.socksession is not None:
            return self.socksession.sendData(data)
        else:
            return False
        
class videoserver(metaserver):
    def __init__(self, server_name, state =False, statetime=None):
        metaserver.__init__(self, server_name, state, statetime)
        
    def passonData(self, packdata):
        return self.sendData(packdata[1])
        
        
class subordinate(metaserver):
    def __init__(self, server_name, timeout, state=False, statetime=None):
        metaserver.__init__(self, server_name, state, statetime)
        self.timeout = timeout
        self.finish_flag = False
        self.finish_time = None
        self.wait_flag = False
        
    def passonData(self, packdata):
        return self.sendData(packdata[1])
        
    def setFinishFlag(self, flag):
        self.finish_flag = flag
        self.finish_time = datetime.now()
    
    def getFinishState(self):
        if self.finish_flag is True:
            return True
        else:
            if self.wait_flag:
                return False
            else:
                if self.finish_time is not None and \
                (datetime.now() - self.finish_time).total_seconds() - self.timeout > 0.00001:
                    return True
                else:
                    return False
        
class superior(metaserver):
    def __init__(self, server_name, ip, socksession, state =False, statetime=None):
        metaserver.__init__(self, server_name, state, statetime)
        self.ip = ip
        self.socksession = socksession
        
    def reportData(self, packdata):
        return self.sendData(packdata[1])