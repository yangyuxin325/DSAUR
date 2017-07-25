#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年1月26日

@author: sanhe
'''
import asyncore
import socket
import struct
from util import tryException
import time
from Queue import Queue
import threading
from UserDict import UserDict

__all__ = ['AsyncSession', 'AsyncClient', 'AsyncServer']

INTERAVAL = 3
TOTAL = 50

class Timer():
    def __init__(self, interval, handle):
        self.interval = interval
        self.handle = handle
        self.count = 0
        self.timer = threading.Timer(self.interval, self.func)
        
    def func(self):
        if self.handle():
            self.start()
        self.count += 1
        
    def start(self):
        self.timer.cancel()
        del self.timer
        self.timer = threading.Timer(self.interval, self.func)
        self.timer.daemon = True
        self.timer.start()
        
    def cancel(self):
        self.timer.cancel()
        self.count = 0
        
class AsyncSession(asyncore.dispatcher_with_send):
    def __init__(self, host, port, handleData, doConnect = None, doClose = None):
        asyncore.dispatcher_with_send.__init__(self)
        self.addr = (host, port)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.count = 0
        self.snd_time = time.time()
        self.handleData = handleData
        self.doConnect = doConnect
        self.doClose = doClose
#         self.timer = Timer(INTERAVAL, self.sendHeartBeat)
        self.lock = threading.Lock()
        self.readbuf = ''
        self.bufsize = 16
        self.head = None
        self.dataSet = set()
        self.sendQueue = Queue()
        self.snd_len = 0
        self.connect(self.addr)
        
    @tryException
    def sndThread(self):
        while self.connected:
            if not self.sendQueue.empty():
                data = self.sendQueue.get()
#                 print self.addr, data
                total_len = len(data)
                err_num = 0
                while self.snd_len < total_len:
                    buf = data[self.snd_len:]
                    m = 0
                    try:
                        m = self.socket.send(buf)
                        err_num = 0
#                         print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!', self.sendQueue.qsize(), self.addr, total_len, len(buf)
                    except socket.error, why:
                        if why.args[0] in asyncore._DISCONNECTED:
                            self.handle_close()
#                             print self.snd_len, why.args[0], '&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&'
                            break
                        elif why.args[0] in (asyncore.EAGAIN, asyncore.EWOULDBLOCK):
                            err_num = err_num + 1
                            if err_num > 20:
                                time.sleep(1)
                            else:
                                time.sleep(0.1)
#                             print 'asyncore.EAGAIN','**********************************************************'
                        else:
                            raise
#                             print '^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^'
                    if m == 0:
#                         print '#########################################################################################'
                        time.sleep(0.01)
                    else:
                        self.snd_len = self.snd_len + m
#                     print '@@@@@@@@@@@@@@@@@@@@@@@@@@@@', self.snd_len, total_len
                self.snd_len = 0
                time.sleep(0.001)
                         
        
#     def (self):
#         if self.timer.count == TOTAL:
# #             print self.addr, 'HeartBeat Count Finished,close connection.'
#             self.handle_close()
#             return False
#         if self.connected and self.sendQueue.empty():
#             self.sendData(struct.pack('!4i', 1, 0, 0, 0))
# #             self.lock.acquire()
# # #             print 'sendHeartBeat',self.timer.count
# #             self.send(struct.pack('!4i', 1, 0, 0, 0))
# #             self.lock.release()
#         else:
#             pass
#         return True
    
    def recv(self, buffer_size):
        try:
            data = self.socket.recv(buffer_size)
            if not data:
                # a closed connection is indicated by signaling
                # a read condition, and having recv() return 0.
                print 'a read condition, and having recv() return 0.'
                self.handle_close()
                return ''
            else:
                return data
        except socket.error, why:
            # winsock sometimes throws ENOTCONN
            print 'winsock sometimes throws ENOTCONN'
            if why.args[0] in asyncore._DISCONNECTED:
                self.handle_close()
                return ''
            elif why.args[0] in (asyncore.EAGAIN, asyncore.EWOULDBLOCK):
                return ''
            else:
                raise
    
    def handle_write(self):
        sent = asyncore.dispatcher.send(self, self.out_buffer)
        self.out_buffer = self.out_buffer[sent:]
        
    @tryException
    def handle_read(self):
        asyncore.dispatcher_with_send.handle_read(self)
        self.count = 0
#         self.timer.count = 0
        if self.connected:
            if self.handleData:
                self.handleData(self)
            else:
                buf = self.recv(100)
                print 'AsyncSession handle_read:', buf.strip()
        else:
            pass
        
    @tryException
    def handle_connect_event(self):
        err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err != 0:
            print 'socket got err :', err, self.addr
            self.handle_close()
        else:
            self.connected = True
            self.connecting = False
            self.handle_connect()
        
    @tryException
    def handle_connect(self):
        asyncore.dispatcher_with_send.handle_connect(self)
        if self.connected:
#             threading.Thread(target=self.sndThread).start()
            if self.doConnect:
                self.doConnect(self)
#                 self.timer.start()
            else:
                pass
        else:
            pass
        
    @tryException
    def handle_close(self):
        asyncore.dispatcher_with_send.handle_close(self)
#         self.timer.cancel()
        if self.doClose:
            self.doClose(self)
        else:
            pass
        
    def sendData(self,data):
        if self.connected:
            self.lock.acquire()
            self.sendQueue.put_nowait(data)
            self.lock.release()
            return True
        else:
            return False

class AsyncClient(asyncore.dispatcher_with_send):
    def __init__(self, sock, handleData, doClose = None):
        asyncore.dispatcher_with_send.__init__(self, sock)
        self.handleData =handleData
        self.count = 0
        self.snd_time = time.time()
#         self.timer = Timer(INTERAVAL, self.sendHeartBeat)
#         if self.connected:
#             self.timer.start()
        self.doClose = doClose
        self.lock = threading.Lock()
        self.readbuf = ''
        self.bufsize = 16
        self.head = None
#         self.dbsession = DBSession()
        self.dataSet = set()
        self.sendQueue = Queue()
        self.snd_len = 0
#         threading.Thread(target=self.sndThread).start()
        
        
    @tryException
    def sndThread(self):
        while self.connected:
            if not self.sendQueue.empty():
                data = self.sendQueue.get()
                total_len = len(data)
                err_num = 0
                while self.snd_len < total_len:
                    buf = data[self.snd_len:]
                    m = 0
                    try:
                        m = self.socket.send(buf)
                        err_num = 0
#                         print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!', self.addr, total_len, len(buf)
                    except socket.error, why:
                        if why.args[0] in asyncore._DISCONNECTED:
                            self.handle_close()
#                             print '&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&'
                            break
                        elif why.args[0] in (asyncore.EAGAIN, asyncore.EWOULDBLOCK):
                            err_num = err_num + 1
                            if err_num > 20:
                                time.sleep(1)
                            else:
                                time.sleep(0.1)
#                             print 'asyncore.EAGAIN','**********************************************************'
                        else:
                            raise
#                             print '^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^'
                    if m == 0:
                        time.sleep(0.001)
                    else:
                        self.snd_len = self.snd_len + m
#                     print '@@@@@@@@@@@@@@@@@@@@@@@@@@@@', self.snd_len, total_len
                self.snd_len = 0
                time.sleep(0.001)
        
#     def sendHeartBeat(self):
#         if self.timer.count == TOTAL:
# #             print self.addr,'HeartBeat Count Finished,close connection.'
#             self.handle_close()
#             return False
#         if self.connected and self.sendQueue.empty():
#             self.sendData(struct.pack('!4i', 1, 0, 0, 0))
#         else:
#             pass
#         return True
    
    def recv(self, buffer_size):
        try:
            data = self.socket.recv(buffer_size)
            if not data:
                # a closed connection is indicated by signaling
                # a read condition, and having recv() return 0.
                print 'a read condition, and having recv() return 0.'
                self.handle_close()
                return ''
            else:
                return data
        except socket.error, why:
            # winsock sometimes throws ENOTCONN
            print 'winsock sometimes throws ENOTCONN'
            if why.args[0] in asyncore._DISCONNECTED:
                self.handle_close()
                return ''
            elif why.args[0] in (asyncore.EAGAIN, asyncore.EWOULDBLOCK):
                return ''
            else:
                raise
    
    def handle_write(self):
        sent = asyncore.dispatcher.send(self, self.out_buffer)
        self.out_buffer = self.out_buffer[sent:]
        
    @tryException
    def handle_read(self):
        asyncore.dispatcher_with_send.handle_read(self)
        self.count = 0
#         self.timer.count = 0
        if self.connected:
            if self.handleData:
                self.handleData(self)
            else:
                buf = self.recv(100)
                print 'AsyncClient handle_read:', buf.strip()
        else:
            pass
        
    @tryException
    def sendData(self,data):
        if self.connected:
            self.lock.acquire()
            self.sendQueue.put_nowait(data)
            self.lock.release()
            return True
        else:
            return False
        
    @tryException
    def handle_close(self):
        asyncore.dispatcher_with_send.handle_close(self)
#         self.timer.cancel()
        if self.doClose:
            self.doClose(self)
        else:
            pass

        
class AsyncServer(asyncore.dispatcher):
    def __init__(self, host, port, handleConnect):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host,port))
        self.handleConnect = handleConnect
        self.snd_dict = UserDict()
        self.snd_lock = threading.Lock()
        
    def addSocket(self, snd_socket):
        self.snd_lock.acquire()
        self.snd_dict[id(snd_socket)] = snd_socket
        self.snd_lock.release()
        
    @tryException
    def sndThread(self):
        while True:
            self.snd_lock.acquire()
#             print len(self.snd_dict),'888888888888888888888888888888888888888888888888888'
            for k ,sess in self.snd_dict.iteritems():
#                 print k, sess.addr
                if sess.connected:
#                     print k, sess.addr,'77777777'
                    if sess.sendQueue.empty() and (time.time() - sess.snd_time) > INTERAVAL:
                        sess.sendData(struct.pack('!4i', 1, 0, 0, 0))
                        sess.count = sess.count + 1
#                         print sess.count, sess.addr
                    if not sess.sendQueue.empty():
                        data = sess.sendQueue.get()
                        total_len = len(data)
                        err_num = 0
                        while sess.snd_len < total_len:
                            buf = data[sess.snd_len:]
                            m = 0
                            try:
                                m = sess.socket.send(buf)
                                err_num = 0
#                                 print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!', self.addr, total_len, len(buf)
                            except socket.error, why:
                                if why.args[0] in asyncore._DISCONNECTED:
                                    sess.handle_close()
        #                             print '&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&'
                                    break
                                elif why.args[0] in (asyncore.EAGAIN, asyncore.EWOULDBLOCK):
                                    err_num = err_num + 1
                                    if err_num > 20:
                                        time.sleep(1)
                                    else:
                                        time.sleep(0.1)
        #                             print 'asyncore.EAGAIN','**********************************************************'
                                else:
                                    raise
        #                             print '^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^'
                            if m == 0:
                                time.sleep(0.001)
                            else:
                                sess.snd_len = sess.snd_len + m
        #                     print '@@@@@@@@@@@@@@@@@@@@@@@@@@@@', self.snd_len, total_len
                        sess.snd_len = 0
                        sess.snd_time = time.time()
                        if sess.count >= TOTAL:
                            print sess.count, sess.addr 
                            sess.handle_close()
                else:
                    print 'del socket:', k,sess.connected
                    del self.snd_dict[k]
                    break
            self.snd_lock.release()
            time.sleep(0.001)
        
    def run(self):
        self.listen(5)
        
    @tryException
    def handle_accept(self):
        asyncore.dispatcher.handle_accept(self)
        pair = self.accept()
        if self.handleConnect:
            self.handleConnect(pair)
