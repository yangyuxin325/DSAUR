#coding=utf-8
#!/usr/bin/env python
'''
Created on 2016年8月5日

@author: sanhe
'''
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import xlrd

from readconf import getSqlUrl, period_var, sess_timeout, timeout_level, timeout_level0, timeout_level1, local_name
from models import *


engine = create_engine(getSqlUrl(),echo=True)
DBSession = sessionmaker(bind=engine)


    
def ReadAndWriteTables():
    dbsession = DBSession()
    filename = 'database_' + local_name + '.xls'
    data = xlrd.open_workbook(filename)
    #read table ipcinfo
    table = data.sheet_by_name('ipcinfo')
    for i in range(table.nrows-1):
        name = table.row(i+1)[0].value.strip()
        cname = table.row(i+1)[1].value.strip()
        ip = table.row(i+1)[2].value.strip()
        rtsp_type = table.row(i+1)[3].value.strip()
        fps = int(table.row(i+1)[4].value)
        resolution = table.row(i+1)[5].value.strip()
        streamsize = int(table.row(i+1)[6].value)
        state = False
        dbsession.add(IPCInfo(name,cname,ip,rtsp_type,fps,resolution,streamsize,state))
    dbsession.commit()
    #read table areainfo
    table = data.sheet_by_name('areainfo')
    for i in range(table.nrows-1):
        a_id = int(table.row(i+1)[0].value)
        name = table.row(i+1)[1].value.strip()
        dbsession.add(AreaInfo(a_id,name))
    dbsession.commit()
    #read table refparaminfo
    table = data.sheet_by_name('refparaminfo')
    for i in range(table.nrows-1):
        name = table.row(i+1)[0].value.strip()
        cname = table.row(i+1)[1].value.strip()
        value = table.row(i+1)[2].value
        dbsession.add(RefParamInfo(name,cname,value))
    dbsession.commit()
    #read table refmodeparaminfo
    table = data.sheet_by_name('refmodeparaminfo')
    for i in range(table.nrows-1):
        name = table.row(i+1)[0].value.strip()
        mode = int(table.row(i+1)[1].value)
        cname = table.row(i+1)[2].value.strip()
        value = table.row(i+1)[3].value
        dbsession.add(RefModeParamInfo(name,mode,cname,value))
        dbsession.commit()
    #read table refcondmodeparaminfo
    table = data.sheet_by_name('refcondmodeparaminfo')
    for i in range(table.nrows-1):
        name = table.row(i+1)[0].value.strip()
        cond = int(table.row(i+1)[1].value)
        mode = int(table.row(i+1)[2].value)
        cname = table.row(i+1)[3].value.strip()
        value = table.row(i+1)[4].value
        dbsession.add(RefCondModeParamInfo(name,cond,mode,cname,value))
    dbsession.commit()
    #read table logicinfo
    table = data.sheet_by_name('logicinfo')
    for i in range(table.nrows-1):
        name = table.row(i+1)[0].value.strip()
        dbsession.add(LogicInfo(name,True))
    dbsession.commit()
    #read table serverinfo,mepdataconstraintconf
    table1 = data.sheet_by_name('serverinfo')
    table2 = data.sheet_by_name('mepdataconstraintconf')
    servers = []
    for i in range(table1.nrows-1):
#     for i in range(1):
        name = table1.row(i+1)[0].value.strip()
        cname = table1.row(i+1)[1].value.strip()
        s_type = table1.row(i+1)[2].value.strip()
        ip = table1.row(i+1)[3].value.strip()
        ipc_name = None if table1.row(i+1)[4].value == '' else table1.row(i+1)[4].value.strip()
        pri = int(table1.row(i+1)[5].value)
        timeout = 0
        if s_type == 'region':
            timeout = int(timeout_level)
        elif s_type == 'node':
            timeout = int(timeout_level0)
        elif s_type == 'unit':
            timeout = int(timeout_level1)
        dbsession.add(ServerInfo(name,cname,s_type,ip,None,pri,False,timeout))
        servers.append((name,cname))
    dbsession.commit()
    for i in range(table2.nrows-1):
        name = table2.row(i+1)[0].value.strip()
        cname = table2.row(i+1)[1].value.strip()
        min_variation = table2.row(i+1)[2].value
        min_val = None if table2.row(i+1)[3].value =='' else table2.row(i+1)[3].value
        max_val = None if table2.row(i+1)[4].value =='' else table2.row(i+1)[4].value
        dis_interval = int(table2.row(i+1)[5].value)
        dbsession.add(MEPDataConstraintConf(name,cname,min_variation,min_val,max_val,dis_interval))
        #attribute 3 mep数据
        for server in servers:
            dbsession.add(DataInfo(server[0]+ '_' + name,server[1]+cname,None,False,None,False,None,0,min_variation,
                                   min_val,max_val,dis_interval,3,0,0,0,server[0]))
            dbsession.add(ReasonDataInfo(server[0]+ '_' +name,None,None,None,None,None,None,None))
            dbsession.add(MepDataType(server[0]+ '_'+ name,name,server[0]))
    dbsession.commit()
    #read table ipcvideoservermap
    table = data.sheet_by_name('ipcvideoservermap')
    for i in range(table.nrows-1):
        ipc_name = table.row(i+1)[0].value.strip()
        sever_name = table.row(i+1)[1].value.strip()
        dbsession.add(IPCVideoServerMap(ipc_name,sever_name))
    dbsession.commit()
    #read table nodeunitmap
    table = data.sheet_by_name('nodeunitmap')
    for i in range(table.nrows-1):
        node_name = table.row(i+1)[0].value.strip()
        unit_name = table.row(i+1)[1].value.strip()
        dbsession.add(NodeUnitMap(node_name,unit_name))
    dbsession.commit()
    #read table sessioninfo
    table = data.sheet_by_name('sessioninfo')
    for i in range(table.nrows-1):
        name = table.row(i+1)[0].value.strip()
        cname = table.row(i+1)[1].value.strip()
        s_type = int(table.row(i+1)[2].value)
        s_id = int(table.row(i+1)[3].value)
        server_name = table.row(i+1)[4].value.strip()
        ipc_name = None if table.row(i+1)[5].value=='' else table.row(i+1)[5].value.strip()
        pri = int(table.row(i+1)[6].value)
        dbsession.add(SessionInfo(name,cname,s_type,s_id,server_name,ipc_name,pri,False,float(sess_timeout)))
        #attribute 4 period数据
        dbsession.add(DataInfo(name+'_period',cname+ u'周期',None,False,None,False,None,0,float(period_var),
                                   None,None,0,4,0,0,0,server_name))
        dbsession.add(PeriodDataType(name+'_period',name))
        dbsession.add(ReasonDataInfo(name+'_period',None,None,None,None,None,None,None))
    dbsession.commit()
    #read table deviceinfo
    table = data.sheet_by_name('deviceinfo')
    for i in range(table.nrows-1):
        name = table.row(i+1)[0].value.strip()
        cname = table.row(i+1)[1].value.strip()
        d_type = table.row(i+1)[2].value.strip()
        d_id = int(table.row(i+1)[3].value)
        area_id = int(table.row(i+1)[4].value)
        session_name = table.row(i+1)[5].value.strip()
        dbsession.add(DeviceInfo(name,cname,d_type,d_id,area_id,session_name))
    dbsession.commit()
    #read table datainfo
    table = data.sheet_by_name('datainfo')
    for i in range(table.nrows-1):
        name = table.row(i+1)[0].value.strip()
        cname = table.row(i+1)[1].value.strip()
        min_variation = table.row(i+1)[2].value
        if min_variation == '':
            min_variation = 0.0
#             raise Exception("%s's min_variation is None,please import again !" % name)
        else:
            pass
        min_val = None if table.row(i+1)[3].value == '' else table.row(i+1)[3].value
        max_val = None if table.row(i+1)[4].value == '' else table.row(i+1)[4].value
        dis_interval = int(table.row(i+1)[5].value)
        attribute = int(table.row(i+1)[6].value)
        pri = int(table.row(i+1)[7].value)
        start_sec = None if table.row(i+1)[8].value=='' else int(table.row(i+1)[8].value)
        end_sec = None if table.row(i+1)[9].value=='' else int(table.row(i+1)[9].value)
        dev_name = None if table.row(i+1)[10].value=='' else table.row(i+1)[10].value.strip()
        conf_name = None if table.row(i+1)[11].value=='' else table.row(i+1)[11].value.strip()
        link_flag = bool(table.row(i+1)[12].value)
        algorithm = None if table.row(i+1)[13].value=='' else int(table.row(i+1)[13].value)
        u_type = None if table.row(i+1)[14].value=='' else str(table.row(i+1)[14].value).strip()
        server_name = table.row(i+1)[15].value.strip()
        dbsession.add(DataInfo(name,cname,None,False,None,False,None,0,min_variation,min_val,max_val,
                               dis_interval,attribute,pri,start_sec,end_sec,server_name))
        dbsession.add(ReasonDataInfo(name,None,None,None,None,None,None,None))
        #attribute 1 dev数据
        if attribute == 1:
            dbsession.add(DevDataType(name,dev_name,conf_name,link_flag,algorithm))
#             dbsession.commit()
        #attribute 2 udev数据
        elif attribute == 2:
            dbsession.add(UDevDataType(name,u_type,server_name))
        dbsession.commit()
    #read table devdatalink
    table = data.sheet_by_name('devdatalink')
    for i in range(table.nrows-1):
        conf_name = table.row(i+1)[0].value.strip()
        dev_name = table.row(i+1)[1].value.strip()
        link_key = table.row(i+1)[2].value.strip()
        link_type = table.row(i+1)[3].value.strip()
        link_para1 = int(table.row(i+1)[4].value)
        dbsession.add(DevDataLink(conf_name,dev_name,link_key,link_type,link_para1))
    dbsession.commit()
    #read table dataipcinfo
    table = data.sheet_by_name('dataipcinfo')
    for i in range(table.nrows-1):
        data_name = table.row(i+1)[0].value.strip()
        ipc_name = table.row(i+1)[1].value.strip()
        dbsession.add(DataIPCInfo(data_name,ipc_name,datetime.now()))
        datainfo = dbsession.query(DataInfo).filter_by(name =data_name).one()
#         if datainfo.start_sec is None or datainfo.end_sec is None:
#             raise Exception("%s's start_sec and end_sec is None,please import again !" % datainfo.name)
#         else:
#             pass
        dbsession.commit()
    #read table cumulativedata
    table = data.sheet_by_name('cumulativedata')
    for i in range(table.nrows-1):
        data_name = table.row(i+1)[0].value.strip()
        server_name = table.row(i+1)[1].value.strip()
        dbsession.add(CumulativeData(data_name,server_name))
    dbsession.commit()
    #read table transmitdata
    table = data.sheet_by_name('transmitdata')
    for i in range(table.nrows-1):
        data_name = table.row(i+1)[0].value.strip()
        server_name = table.row(i+1)[1].value.strip()
        dbsession.add(TransmitData(data_name,server_name))
    dbsession.commit()
    #read table datalogicinfo
    table = data.sheet_by_name('datalogicinfo')
    for i in range(table.nrows-1):
        data_name = None if table.row(i+1)[0].value =='' else table.row(i+1)[0].value.strip()
        logic_name = None if table.row(i+1)[1].value =='' else table.row(i+1)[1].value.strip()
        if table.row(i+1)[2].value == '':
            raise Exception('server_name from table datalogicinfo cannot be None!!!')
        server_name = table.row(i+1)[2].value.strip()
        data_cha = None if table.row(i+1)[3].value =='' else table.row(i+1)[3].value.strip()
        data_onoff = False if table.row(i+1)[4].value =='' else bool(table.row(i+1)[4].value) 
        logic_cha = None if table.row(i+1)[5].value =='' else table.row(i+1)[5].value.strip()
        logic_onoff = False if table.row(i+1)[6].value =='' else bool(table.row(i+1)[6].value)
        dl_alg = None if table.row(i+1)[7].value =='' else float(table.row(i+1)[7].value)
        dbsession.add(DataLogicInfo(data_name,logic_name,server_name,data_cha,data_onoff,logic_cha,logic_onoff,dl_alg))
        dbsession.commit()
    dbsession.close()
    
if __name__ == "__main__":
#     dbsession = DBSession()
#     serverinfo = dbsession.query(ServerInfo).filter_by(name='R').one_or_none()
#     serverinfo.pri = 8
#     dbsession.commit()
#     serverinfo = dbsession.query(ServerInfo).filter_by(name='R').one_or_none()
#     print serverinfo
#     for dataipcinfo in dbsession.query(DataIPCInfo).filter_by(data_name='KT_L_XHB_1_YX').all():
#         print dataipcinfo.ipc_name
#     print dbsession.execute("select ipc_name from dataipcinfo where data_name = '%s'" % 'KT_L_XHB_1_YX').fetchall()
#     dbsession.commit()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        ReadAndWriteTables()
        print 'import database sucessfully!'
    except Exception as e:
        print "ReadAndWriteTable Error : ", e