#coding=utf-8
#!/usr/bin/env python
'''
Created on 2017年6月26日

@author: sanhe
'''
import time
from dsaur.util import singleton
import RPi.GPIO as GPIO
   
@singleton
class SendGPIO(object):
    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(18, GPIO.OUT)
                   
    def sendSignal(self):
        GPIO.output(18, GPIO.HIGH)  
        time.sleep(0.02)
        GPIO.output(18, GPIO.LOW)
 
# @singleton
# class SendGPIO(object):
#     def __init__(self):
#         pass
#                 
#     def sendSignal(self):
#         pass

