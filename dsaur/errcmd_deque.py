#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年1月22日

@author: sanhe1
'''
from collections import deque


class errcmd_deque():
    def __init__(self):
        self.__errcmd = {}
        self.__id_deque = deque()
        
    def errcmdPrint(self):
        print self.__errcmd
        print self.__id_deque

    def push(self , cmd):
        if cmd['dev_id'] not in self.__id_deque:
            self.__id_deque.append(cmd['dev_id'])
            self.__errcmd[cmd['dev_id']] = deque()
            self.__errcmd[cmd['dev_id']].append(cmd)
        else:
            self.__errcmd[cmd['dev_id']].append(cmd)
            
    def popcmd(self):
        if self.empty() is False:
            dev_id = self.__id_deque.popleft()
            cmd = self.__errcmd[dev_id].popleft()
            if len(self.__errcmd[dev_id]) > 0:
                self.__id_deque.append(dev_id)
            else:
                self.__errcmd.pop(dev_id)
            return cmd
        else:
            return None
                
    def popcmdset(self, dev_id):
        if dev_id in self.__errcmd:
            self.__id_deque.remove(dev_id)
            return self.__errcmd.pop(dev_id)
        else:
            return deque()
    
    def empty(self):
        if len(self.__id_deque) > 0:
            return False
        else:
            return True
            
            
            
if __name__ == '__main__':
    q = errcmd_deque()
    cmd = {"id" : 1, "cmd" : '1111111111111111', "dev_id" : 11}
    q.push(cmd)
    cmd = {"id" : 2, "cmd" : '2222222222222222', "dev_id" : 12}
    q.push(cmd)
    cmd = {"id" : 3, "cmd" : '3333333333333333', "dev_id" : 13}
    q.push(cmd)
    cmd = {"id" : 4, "cmd" : '4444444444444444', "dev_id" : 14}
    q.push(cmd)
    cmd = {"id" : 5, "cmd" : '5555555555555555', "dev_id" : 15}
    q.push(cmd)
    cmd = {"id" : 6, "cmd" : '6666666666666666', "dev_id" : 15}
    q.push(cmd)
    cmd = {"id" : 7, "cmd" : '7777777777777777', "dev_id" : 15}
    q.push(cmd)
    cmd = {"id" : 8, "cmd" : '8888888888888888', "dev_id" : 15}
    q.push(cmd)
    cmd = {"id" : 9, "cmd" : '9999999999999999', "dev_id" : 12}
    q.push(cmd)
    q.errcmdPrint()
    print q.popcmdset(15)
    print q.popcmdset(12)
#     while q.empty() is False:
#         print '------', q.popcmd()
#         q.errcmdPrint()