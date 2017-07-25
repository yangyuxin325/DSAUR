#coding=utf-8
#!/usr/bin/env python
'''
Created on 2017年4月24日

@author: sanhe
'''

import vlc
from datetime import datetime,timedelta
from UserDict import UserDict
import os
import threading
import time
import subprocess
import signal
from util import tryException

STREAM_INTERVAL = 5

# rtsp://admin:admin@172.16.1.11:554/cam/realmonitor?channel=1&subtype=1

def gen_media_mrl(ip, rtsp_type, user='admin', pwd='admin'):
    str_ip = ip.encode('gbk')
    if rtsp_type == "Dahua":
        return 'rtsp://{0}:{1}@{2}:554/cam/realmonitor?channel=1&subtype=0'.format(user,pwd,str_ip)
    else:
        return None

class ipc_stream(object):
    def __init__(self, name, ip, rtsp_type, user='admin', pwd='admin'):
        self.name = name
        self.mrl = gen_media_mrl(ip, rtsp_type, user, pwd)
        self.inst = vlc.Instance()
        self.player = self.inst.media_player_new()
        self.media = self.inst.media_new(self.mrl,"sout=file/mp4:"+self.name+'.mp4')
        self.player.set_media(self.media)
        self.interval = STREAM_INTERVAL
        self.recordname = None
        self.filename = None
        self.start = None
        self.end = None
        self.flag = False
        self.updatetime = None
        self.reflag = False
        
    def resetMedia(self):
        self.start = datetime.now()
        self.end = self.start + timedelta(seconds=self.interval)
        subdir = self.start.year*1000000 + self.start.month*10000 + self.start.day*100 + self.start.hour
        subname = '{0}/{1}'.format(self.name, subdir)
        if not os.path.exists(subname):
            os.makedirs(subname)
        else:
            pass
        self.filename = '{0}/{1}-{2}.mp4'.format(subname,self.start.strftime('%Y-%m-%d %H:%M:%S'),
                                                 self.end.strftime('%Y-%m-%d %H:%M:%S'))
#         self.filename = subname + '/' + \
#         self.start.strftime('%Y-%m-%d %H:%M:%S') + '-' + self.end.strftime('%Y-%m-%d %H:%M:%S')+'.mp4'
#         print '*********', self.filename
        self.player.release()
        del self.player
        self.media.release()
        del self.media
        self.player = self.inst.media_player_new()
        self.media = self.inst.media_new(self.mrl,"sout=file/mp4:"+self.filename)
        self.player.set_media(self.media)
        
#     def set_media(self):
#         self.media = self.inst.media_new(self.mrl,"sout=file/mp4:"+self.name+'.mp4')
#         self.player.set_media(self.media)
        
    def is_playing(self):
        return self.player.is_playing()
    
    def play(self):
        return self.player.play()
    
    def stop(self):
        return self.player.stop()
    
class StreamRecordService(object):
    def __init__(self, ipc_dict):
        self.server_ip = None
        self.local_name = None
        self.ipc_dict = ipc_dict
        self.stream_dict = UserDict()
        self.livestream_dict = UserDict()
        self.localstream_dict = UserDict()
        for name,ipc in self.ipc_dict.items():
            self.stream_dict[name] = ipc_stream(name,ipc[1],ipc[2])
        self.start_flag = True
        self.reconnect = False
        self.th_onlineTest = None
        
    def checkFlag(self):
        pass
        
    @tryException
    def startLiveStream(self,ipc_name,local_name):
        if ipc_name not in self.livestream_dict:
            mrl = self.getIPC_Stream(ipc_name).mrl[0:-1]
#             print mrl
#             cmd = "avconv -i '" + mrl + "' -vcodec copy -acodec copy -f flv -y 'rtmp://172.16.1.16:1935/" + local_name + "/" + ipc_name + "'>/dev/null 2>&1"
            cmd = "avconv -i '" + mrl + "1' -vcodec copy -acodec copy -f flv -y 'rtmp://thic.cn:1935/" + local_name + "/" + ipc_name + "'>/dev/null 2>&1"
            print cmd
            p = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,preexec_fn=os.setsid)
            time.sleep(1)
            if p.poll() is None:
                self.livestream_dict[ipc_name] = p
                return True
            else:
                print ipc_name,local_name,'failed!!!!'
        return False
    
    def stopLiveStream(self,ipc_name):
        if ipc_name in self.livestream_dict:
            p = self.livestream_dict[ipc_name]
            if p.poll() is None:
                p.terminate()
                p.wait()
                os.killpg(p.pid, signal.SIGTERM)
                del self.livestream_dict[ipc_name]
                return True
        return False
        
    def recordFileName(self, stream):
        pass
#         print stream.name,stream.recordname,stream.start,stream.end
        
    def streamState(self, stream):
        pass
#         print stream.name,stream.flag,stream.updatetime
        
    def getIPC_Stream(self,name):
        return self.stream_dict.get(name)
        
    @tryException
    def startService(self, local_name, server_ip):
        self.server_ip = server_ip
        self.local_name = local_name
        threading.Thread(target=self.start).start()

    def onlineTest(self):
        if self.reconnect:
            return
        self.reconnect = True
        for stream in self.stream_dict.values():
            if not stream.flag and not stream.reflag:
                stream.resetMedia()
                stream.play()
            else:
                pass
        time.sleep(1)
        for name, stream in self.stream_dict.items():
            if name in self.localstream_dict:
                if name in self.livestream_dict:
                    if self.livestream_dict[name].poll() is not None:
                        del self.livestream_dict[name]
#                 if self.localstream_dict[name].poll() is not None:
#                     del self.livestream_dict[name]
#                     print self.localstream_dict[name].poll() ,'---------------------------------------------'
#                     cmd = "avconv -i '" + stream.mrl + "' -vcodec copy -acodec copy -f flv -y 'rtmp://" + \
#                     self.server_ip + ":1935/" + self.local_name + "/" + name + "'"
#                     p = subprocess.Popen(cmd,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,preexec_fn=os.setsid)
#                     if p.poll() is None:
#                         self.localstream_dict[name] = p
#                     else:
#                         print name,'failed!!!!'
            if not stream.reflag and not stream.flag and stream.is_playing():
                stream.stop()
                if os.path.exists(stream.filename):
                    os.remove(stream.filename)
#                     print 'onlineTest, delete filename:',stream.filename
                stream.reflag = True
        self.reconnect = False
        
    def start(self):
        for name in self.stream_dict.keys():
            if not os.path.exists(name):
                os.makedirs(name)
            else:
                pass
        for stream in self.stream_dict.values():
            if not stream.flag:
                stream.resetMedia()
                stream.play()
            else:
                pass
        time.sleep(2)
        for stream in self.stream_dict.values():
            if not stream.flag:
                if stream.is_playing():
                    stream.stop()
                    stream.flag = True
                    stream.updatetime = datetime.now()
                    self.streamState(stream)
                    stream.resetMedia()
                    stream.play()
                if os.path.exists(stream.filename):
                    os.remove(stream.filename)
#                     print 'delete filename:',stream.filename
        while self.start_flag:
            time.sleep(STREAM_INTERVAL)
            self.checkFlag()
            for stream in self.stream_dict.values():
                if name in self.livestream_dict:
                    if self.livestream_dict[name].poll() is not None:
                        self.livestream_dict[name].communicate()
                if stream.is_playing():
#                     print stream.name, '-------------------------------------------'
                    if stream.flag:
                        stream.stop()
                        stream.recordname = stream.filename
                        self.recordFileName(stream)
#                         print 'start', stream.name,stream.recordname
                        stream.resetMedia()
                        stream.play()
                    else:
                        pass
                else:
                    if not stream.reflag:
                        if stream.recordname <> stream.filename:
                            if os.path.exists(stream.filename):
                                os.remove(stream.filename)
                        if stream.flag:    
                            stream.flag = False
                            print '%%%%%%%%%%%%%%%%%%%%%%%%',stream.name, stream.flag
                            stream.updatetime = datetime.now()
                            self.streamState(stream)
                    else:
                        if not stream.flag:
                            print '$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$',stream.name, stream.flag
                            stream.flag = True
                            stream.updatetime = datetime.now()
                            self.streamState(stream)
                        stream.resetMedia()
                        stream.play()
                    flag = False
                    for stream in self.stream_dict.values():
                        if not stream.flag:
                            flag = True
                    del self.th_onlineTest
                    if flag:
                        self.th_onlineTest = threading.Thread(target=self.onlineTest)
                        self.th_onlineTest.start()
        
    def stop(self):
        self.start_flag = False
#         time.sleep(2)
#         for stream in self.stream_dict.values():
#             if stream.is_playing():
#                 stream.stop()
#                 if stream.recordname != stream.filename:
#                     os.remove(stream.filename)
#                 else:
#                     pass
#             else:
#                 pass