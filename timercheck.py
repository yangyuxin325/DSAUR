#coding=utf-8
#!/usr/bin/env python
'''
Created on 2017年6月26日

@author: sanhe
'''

from dsaur.util import singleton, tryException
from datetime import datetime
        
@singleton
class TimerCheck(object):
    def __init__(self):
        t_init = datetime.now()
        self.sendgpio_check= [t_init,5]
        self.super_check = [t_init,1]
        self.remote_check = [t_init,1]
        self.videoremote_check = [t_init,1]
        self.videolocal_check = [t_init,1]
        
    @tryException
    def excuteCheck(self):
#         print datetime.now(), 'excuteCheck!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
        from sendgpio import SendGPIO
        if (datetime.now() - self.sendgpio_check[0]).total_seconds() > self.sendgpio_check[1]:
            SendGPIO().sendSignal()
            self.sendgpio_check[0] = datetime.now()
        from server import Server
        if Server().superserver is not None and \
        (Server().superserver.socksession is None or \
         (Server().superserver.socksession.connected is False and \
          Server().superserver.socksession.connecting is False)):
            if (datetime.now() - self.super_check[0]).total_seconds() > self.super_check[1]:
#                 print datetime.now(), Server().superserver.socksession.connecting
                Server().superReconnect()
                self.super_check[0] = datetime.now()
        if (Server().remote_session is not None and Server().remote_session.connected is False and \
        Server().remote_session.connecting is False) or (Server().superserver is None and \
                                                          Server().remote_session is None):
            if (datetime.now() - self.remote_check[0]).total_seconds() > self.remote_check[1]:
                del Server().remote_session
                Server().remote_session = None
                Server().remoteReconnect()
                self.remote_check[0] = datetime.now()
            
        if (Server().video_remote_main is not None and Server().video_remote_main.connected is False and \
        Server().video_remote_main.connecting is False) or (Server().streamService is not None and \
                                                          Server().video_remote_main is None):
            if (datetime.now() - self.videoremote_check[0]).total_seconds() > self.videoremote_check[1]:
                del Server().video_remote_main
                Server().video_remote_main = None
                Server().videoRemoteReconnect()
                self.videoremote_check[0] = datetime.now()
        if (Server().video_local_main is not None and Server().video_local_main.connected is False and \
        Server().video_local_main.connecting is False) or (Server().streamService is not None and \
                                                          Server().video_local_main is None):
            if (datetime.now() - self.videolocal_check[0]).total_seconds() > self.videolocal_check[1]:
                del Server().video_local_main
                Server().video_local_main = None
                Server().videoLocalReconnect()
                self.videolocal_check[0] = datetime.now()