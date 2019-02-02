#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sat Nov 17 13:31:45 2018

@author: tjwilliamson
"""

import socket
import threading
import exc
import time
import pickle

class Server(object):
    """
    A class to create a multithreaded server
    to allow multiple clients at once
    """
    
    __RECEIVELEN = 4096
    
    def __init__(self,host,port):
        """Configure the server"""
        
        
        #If we couldnt read the file
        if host is None or port is None:
            raise exc.ServerError('Error configuring server')
            
        #Create the socket object
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(host,port)
        except Exception as e:
            raise exc.ServerError(e)
            
        self.__socket = sock
        self.__clients = []
        self.__children = []
        self.__kill = False
    
    
    def __receive_message__(self,client,timeout=1):
        """Receive a message from a client"""
        
        #Wait for new data
        data = client.recv(self.__RECEIVELEN)
        
        if not data:
            return data
        
        #How long do we expect the message to be?
        
        messg_len_tot = Message.get_length(data)
        messg = Message.trim(data)
        
        #Start the timer to receive the message
        tstart = time.time()
        
        while len(messg) < messg_len_tot:
            if time.time() - tstart >= timeout:
                raise exc.MessageError("Message to server timed out")
                
            #how many chars are we missing?
            diff = messg_len_tot - len(messg)
            
            #Why would this happen?
            if diff <= 0:
                break
            
            new_data = client.recv(diff)
            messg = messg + new_data
            
        return messg


    def listen(self,maxq=10):
        """Wait for new clients to connect"""
        self.__socket.listen(maxq)
        
        while not self.__kill:
            client,address = self.__socket.accept()
            
            #Start a new thread dedicated to this client
            threading.Thread(target=self.__listen_to_client__,args=(client,)).start()
        
        self.close()


    def __listen_to_client__(self,client):
        """Dedicated thread to listen to client"""
        
        while not self.__kill:
            try:
                data = self.__receive_message__(client)
                #Client has disconnected
                if data is None:
                    break
    
                self.__handle_message__(data)
                
            except socket.error as e:
                #TODO: handle socket exception
                pass
    
    
    def __handle_message__(self,message):
        """Receive a message from a client and send it to any
        children with a receive method"""
        
        for child in self.__children:
            child.receive(message)
    
    def close(self):
        """Try to properly close the socket"""
        
        self.__socket.shutdown(socket.SHUT_RDWR)
        self.__socket.close()
        

class Client(object):
    """A class to interface directly with the server"""
    pass


class Message(object):
    """A class to hold a message sent between client and server"""
    protocol = (4,16) #Number of start bits, base
    
    @staticmethod
    def get_length(message):
        """To be called on a message just received from
        the TCP connection. The message is encoded with the first
        few bits specifying the length of the completed message.
        Woe to ye who call this on an already received message."""
        numbits,base = Message.protocol
        try:
            #The length of the message
            mssglen = int(message[0:numbits],base)
            return mssglen
        except ValueError:
            raise exc.MessageError("Cannot read incoming message")
            
    @staticmethod
    def trim(message):
        numbits,base = Message.protocol
        return message[numbits:]