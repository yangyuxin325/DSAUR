#coding=utf-8
#!/usr/bin/env python
'''
Created on 2015年12月24日

@author: sanhe
'''
from models import SerialSearch

__all__ = ['Session_SerailMap', 'InitSerialNo']

Session_SerailMap = {}

def getSerialCOM():
    import commands;
    comArr = {}
    status, str1 = commands.getstatusoutput('ls /dev/serial/by-path')
    if status == 0:
        arr = str1.splitlines()
        for strtemp in arr:
            cmd = "ls -la /dev/serial/by-path | grep " + strtemp + " | cut -d '/' -f3"
            comArr[strtemp] = commands.getoutput(cmd)
        return comArr
    
def ReInitSerial():
    dit = getSerialCOM()
    if dit is None:
        return
    mdit = sorted(dit.items(), key=lambda dit:dit[0])
    if len(mdit) == 12:
        i = 1
        for item in mdit:
            Session_SerailMap[i] = item[1]
            i = i+1
    print 'ReInitSerial：', Session_SerailMap

def InitSerialNo(db):
    dit = getSerialCOM()
    print 'InitSerialNo: ', dit
    if dit is None:
        return
    mdit = sorted(dit.items(), key=lambda dit:dit[0])
    first_index = None
    second_index = None
    if len(mdit) == 12:
        i = 1
        for item in mdit:
            Session_SerailMap[i] = item[1]
            i = i+1
        i = 0
        strtemp = mdit[1][0]
        for c in strtemp:
            if c != mdit[0][0][i]:
                second_index = i
                db.query(SerialSearch).filter(SerialSearch.index_name=='second_index').delete()
                db.add(SerialSearch('second_index',second_index))
            i = i+1
        db.commit()
        i = 0
        strtemp = mdit[4][0]
        for c in strtemp:
            if c != mdit[0][0][i]:
                first_index = i
                db.query(SerialSearch).filter(SerialSearch.index_name=='first_index').delete()
                db.add(SerialSearch('first_index',first_index))
            i = i+1
        db.commit()
    elif 0 < len(mdit) < 12:
        first_index = db.query(SerialSearch).filter_by(index_name='first_index').one_or_none()
        first = first_index.value
        second_index = db.query(SerialSearch).filter_by(index_name='second_index').one_or_none()
        second = second_index.value
        for item in mdit:
#             print item[0][first], item[0][second], item[1]
            Session_SerailMap[(int(item[0][first]) - 1) * 4 + int(item[0][second])] = item[1]
    print '--------------', Session_SerailMap