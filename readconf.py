#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年8月10日

@author: sanhe
'''

import ConfigParser

cf = ConfigParser.ConfigParser()
cf.read('/home/pi/DSAUR/app.conf')
# cf.read('./dsaur/app.conf')
# cf.read('app.conf')
DBname = cf.get('DB', 'name')
DBpassword = cf.get('DB', 'password')
period_var = cf.get('period','min_variation')
sess_timeout = cf.get('session','timeout')
local_name = cf.get('server','local_name')
expiredays = cf.get('server','expiredays')
timeout_level = cf.get('server','timeout_level')
timeout_level0 = cf.get('server','timeout_level0')
timeout_level1 = cf.get('server','timeout_level1')
remote_ip = cf.get('server','remote_ip')
video_ip = cf.get('server','video_ip')
video_port = cf.get('server','video_port')
timeout_refparam = cf.get('server', 'timeout_refparam')
remote_port = cf.get('server','remote_port')
     
 
def getRemoteUrl(ip):
    return "mysql://root:" + DBpassword + "@" + ip + "/" + DBname + "?charset=utf8"
  
def getSqlUrl():
        return "mysql://root:" + DBpassword + "@localhost/" + DBname + "?charset=utf8"