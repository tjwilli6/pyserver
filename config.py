#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 17 17:17:35 2019

@author: tjwilliamson
"""

import configobj
import os


basedir = os.path.abspath( os.path.dirname(__file__) )
cfgname = os.path.join( basedir, 'server.cfg' )

class Config(configobj.ConfigObj):
    
    def __init__(self,**kwargs):

        super(Config,self).__init__(cfgname,create_empty=True)
        
    def set_option(self,key,value):
        self[key] = value
        self.write() 