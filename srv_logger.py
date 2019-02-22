#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 17 17:01:51 2019

@author: tjwilliamson
"""

import logging,os


def getlogger(**kwargs):
    
    logger = logging.getLogger( kwargs.get('__name__',__name__) )
    level = kwargs.get('LOGLEVEL','DEBUG')
    log_format="%(levelname)s [%(asctime)s] %(funcName)s(): %(message)s"
    datefmt='%m/%d/%Y %I:%M:%S %p'
    
    formatter = logging.Formatter(fmt=log_format,datefmt=datefmt)
    
    stdout_logger = logging.StreamHandler()
    stdout_logger.setFormatter(formatter)
    stdout_logger.setLevel(level)
    
    logger.addHandler(stdout_logger)

    fname = kwargs.get('FNAME',None)
    if not fname in (None,"None",""):
        
        logdir = os.path.split(fname)[0]
        if not os.path.isdir(logdir):
            os.makedirs(logdir)
        file_logger = logging.FileHandler(fname)
        file_logger.setFormatter(formatter)
        file_logger.setLevel(level)
        logger.addHandler(file_logger)
        
    logger.setLevel(level)


    if not fname in (None,"None",""):
        logger.info("Writing log file to {}".format(fname))
    return logger

    
    
    
    
    