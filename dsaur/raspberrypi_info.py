#coding=utf-8
#!/usr/bin/env python
import os
import sys
import psutil


reload(sys)

class raspberrypi_info():
    def __init__(self):
        # CPU informatiom
        self.CPU_temp = None
        self.CPU_used = None
        # RAM information
        # Output is in kb, here I convert it in Mb for readability
        self.RAM_stats = None
        self.RAM_total = None
        self.RAM_used =None
        self.RAM_perc =None
        # Disk information
        self.DISK_stats = None
        self.DISK_total = None
        self.DISK_used = None
        self.DISK_perc = None
    
    def startCmp(self):
        self.CPU_temp = self.getCPUtemperature()
        self.CPU_used = self.getCPUuse()
        # RAM information
        # Output is in kb, here I convert it in Mb for readability
        mem = psutil.virtual_memory()
        self.RAM_stats = self.getRAMinfo()
        self.RAM_total = mem.total/1024/1024
        self.RAM_used = mem.used/1024/1024
        self.RAM_perc = mem.percent
        # Disk information
        self.DISK_stats = self.getDiskSpace()
        self.DISK_total = float(self.DISK_stats[0][0:-1])
        self.DISK_used = float(self.DISK_stats[1][0:-1])
        self.DISK_perc = float(self.DISK_stats[3][0:-1])
        return {'CPU_temp' : self.CPU_temp,
                'CPU_used' : self.CPU_used,
                'RAM_total' : self.RAM_total,
                'RAM_used' : self.RAM_used,
                'RAM_perc' : self.RAM_perc,
                'DISK_total' : self.DISK_total,
                'DISK_used' : self.DISK_used,
                'DISK_perc' : self.DISK_perc
                }
        
    # Return CPU temperature as a character string
    def getCPUtemperature(self):
        res = None
        try:
            strtemp = os.popen('vcgencmd measure_temp').readline()
            res = float(strtemp.replace("temp=","").replace("'C\n",""))
        except Exception as e:
            print e
        return res


    # Return RAM information (unit=kb) in a list
    # Index 0: total RAM
    # Index 1: used RAM
    # Index 2: free RAM
    def getRAMinfo(self):
        p = os.popen('free')
        i = 0
        while 1:
            i = i + 1
            line = p.readline()
            if i==2:
                return(line.split()[1:4])
    
    
    # Return % of CPU used by user as a character string
    def getCPUuse(self):
        return float(os.popen("top -bi -n1 | awk '/Cpu\(s\):/ {print $2}'").readline().strip())
    
    
    # Return information about disk space as a list (unit included)
    # Index 0: total disk space
    # Index 1: used disk space
    # Index 2: remaining disk space
    # Index 3: percentage of disk used
    def getDiskSpace(self):
        p = os.popen("df -h | grep root")
        line = p.readline()
        if line != "":
            i = 1
            while 1:
                i = i +1
#                 line = p.readline()
                if i==2:
                    return line.split()[1:5]
        else:
            return ['0 ','0 ','0 ','0 ']
        
if __name__ == '__main__':
    pi_info = raspberrypi_info();
    pi_info.startCmp();
    print('CPU Temperature = '+str(pi_info.CPU_temp))
    print('CPU Use = '+str(pi_info.CPU_used)+'%')
    print('')
    print('RAM Total = '+str(pi_info.RAM_total)+' MB')
    print('RAM Used = '+str(pi_info.RAM_used)+' MB')
    print('RAM Used Percentage = '+str(pi_info.RAM_perc)+'%')
    print('')
    print('DISK Total Space = '+str(pi_info.DISK_total)+'GB')
    print('DISK Used Space = '+str(pi_info.DISK_used)+'GB')
    print('DISK Used Percentage = '+str(pi_info.DISK_perc) + '%')
