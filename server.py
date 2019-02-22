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
from pyserver import logger



#A wrapper function to be used as a decorator
# to catch errors originating from
# the socket module

def catch_socket_error(func):
    """A wrapper to catch socket errors from functions"""
    def func_wrapper(*args,**kwargs):
        #Try to call the function
        try:
            func(*args,**kwargs)
        #If we get a socket error
        except socket.error as e:
            #If arguments were passed (it's an instance method, with "self" as arg 0)
            if len(args) and isinstance(args[0],ServerClientBase):
                self = args[0]
                mssg = 'Socket error in {}: {}'.format(self.__class__.__name__,e)
                self.handle_exception(mssg,code=1,exception=exc.ServerClientError())
            else:
                mssg = 'Socket error: {}'.format(e)
                raise exc.ServerClientError(mssg)
    return func_wrapper






class ServerClientBase(object):
    
    
    RECEIVELEN = 4096
    
    def __init__(self,*args,**kwargs):
        self.__children = []
        
        #Kill = true when we want to end the listening thread
        self.__kill = False
        self.__host = kwargs.get('host')
        self.__port = kwargs.get('port')
        
    
    def get_connection_info(self):
        return self.__host,self.__port
    
    def get_children(self):
        return self.__children
    
    def bind(self,handler_func,error_func=None):
        """ 
            Bind a child object to the client or server. 
            Pass a callable to be called  whenever the server receives
            a message. Optionally, pass a function to be called to handle 
            an error
        """
        if not callable(handler_func):
            raise TypeError("Argument to 'bind' must be a callable")
        if not callable(error_func):
            if error_func is not None:
                logger.warn("Argument 'error_func' must be a callable. Setting to None")
            error_func = None
        logger.debug("Binding child {},{}".format(handler_func,error_func))
        self.__children.append({'message':handler_func,'error':error_func})
        
    
    
    @catch_socket_error
    def send_data(self,dataobj,message):
        """Send a message to the connected socket, either a client or the server"""
        mssg = Message(message)
        mssg_string = mssg.encode()
        
        dataobj.send(mssg_string)
                
    @catch_socket_error
    def __receive_message__(self,dataobj,timeout=1):
        """Receive a message from the server or from a client
        'dataobj' can be either"""
        
        #TODO
        #Make sure I understnad this and that it's fireproof
        #Wait for new data
        data = dataobj.recv(self.RECEIVELEN)

        logger.debug("Got data: {}".format(data) )
        if data is None:
            return data
        
        #How long do we expect the message to be?
        
        messg_len_tot = Message.get_length(data)
        
        #Get the message minus the start byte
        messg = Message.trim(data)
        
        #Start the timer to receive the message
        tstart = time.time()
        
        while len(messg) < messg_len_tot:
            if time.time() - tstart >= timeout:
                raise exc.ReadMessageError("Timeout while reading message")
                
            #how many chars are we missing?
            diff = messg_len_tot - len(messg)
            
            #Why would this happen?
            if diff <= 0:
                break
            
            new_data = dataobj.recv(diff)
            messg = messg + new_data
            
        return messg
        
    def __handle_data__(self,data):
        """Pass received data to all bound children"""
        logger.debug("Handling received message")
        for child in self.__children:
            logger.debug("Calling child func {}".format(child['message']))
            child ['message'] (data)
            
            
    def __listen__(self,dataobj,kill_on_disconnect=False):
        """Listen for data from either the client or server"""
        while not self.__kill:
            logger.debug("Waiting for data from {}".format(dataobj))
            data = self.__receive_message__(dataobj)
            logger.debug("Received data from {}: {}".format(dataobj,data))
            #Server/client has disconnected
            if data is None:
                if kill_on_disconnect:
                    self.__kill = True
                break

            logger.debug("Passing data on to handler func")
            self.__handle_data__(data)
    
    def handle_exception(self,message="", code=None, exception=None):
        """Handle an exception"""
        
        if code is not None:
            message = '{}\nError Code = {}'.format(message,code)
            
        
        if exception is  None:
            logger.error(message)
            for child in self.__children:
                error_func = child ['error']
                if error_func is not None:
                    error_func(message)
        else:
            logger.critical(message)
            if isinstance(exception,Exception):
                exception.args += (message,)
                raise exception


class Server(ServerClientBase):
    """
    A class to create a multithreaded server
    to allow multiple clients at once
    """
    
    
    def __init__(self,host,port=10000):
        """Configure the server"""
        
        
        #If we couldnt read the host or port
        if host is None or port is None:
            raise TypeError("Error configuring server: invalid host,port: {},{}".format(host,port))
            
        #Create the socket object
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind( (host,port) )
        except Exception as e:
            raise exc.ServerError(e)
            
        self.__socket = sock
        self.__clients = []
        self.__kill = False
        
        logger.info("Initializing server at {}:{}".format(host,port) )
        super(Server,self).__init__(host=host,port=port)


    def listen(self,maxq=10):
        """Started the listening thread"""
        logger.debug("Starting the listening thread!")
        threading.Thread(target=self.__listen_server__,args=(maxq,) ).start()

    @catch_socket_error
    def __listen_server__(self,maxq=10):
        """Wait for new clients to connect"""
        
        self.__socket.listen(maxq)
        
        while not self.__kill:
            logger.debug("Now listening for new clients")
            client,address = self.__socket.accept()
            logger.info("Accepting new client from address {}".format(address))
            
            #Start a new thread dedicated to this client
            logger.debug("Starting thread to listen to client")
            threading.Thread(target=self.__listen__,args=(client,)).start()
        
        logger.info("Server is not longer listening")
        
    def __start_local_client__(self):
        """This is called when we want to shut down the server.
        The while loop can't finish because it is waiting for
        accept, this will cause accept to return and break out of
        the while loop in 'listen'"""
        
        host,port =  self.get_connection_info()
        logger.debug("Starting dummy client at {}:{}".format(host,port))
        isock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        isock.connect( self.get_connection_info() )
        isock.close()
        
    def send_to_client(self,client,message):
        """Send a message to a connected client"""
        super(Server,self).send_data(client,message)        
    
    @catch_socket_error
    def close(self):
        """Try to properly close the socket"""
        
        #self.__socket.shutdown(socket.SHUT_RDWR)
        #Exit the while loop at the next iteration
        self.__kill = True
        
        #Start a dummy client so the while loop iterates
        self.__start_local_client__()
        
        self.__socket.close()
        
        
        
        

#TODO
#Client needs some work
#Maker better send_data
#Listening thread timed out (not what we want)
#Logging

class Client(ServerClientBase):
    """A class to interface directly with the server"""
    
    def __init__(self,host,port=10000,timeout=-1):
        """Initialize the object. Add a timeout option so we don't 
        hang forever if the server is down"""
        
        #If we couldnt read the host or port
        if host is None or port is None:
            raise TypeError("Error configuring client: invalid host,port: {},{}".format(host,port))

        #Initialize the socekt
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        #self.__socket.settimeout(timeout)
        
        super(Client,self).__init__(host=host,port=port)
        
    @catch_socket_error
    def connect(self):
        """Try to establish a connection to the server"""
        
        #Establish connection to the server
        self.__socket.connect( self.get_connection_info() )
        
        #If we haver a connection
        # Start a dedicated thread to run in the background and listen for 
        # data from the server
        threading.Thread( target=self.__listen__,args=(self.__socket,True) ).start()
        
        
    def send_data(self,message):
        """Send a message to the server"""
        super(Client,self).send_data(self.__socket,message)




class Message(dict):
    """A class to hold a message sent between client and server"""
    protocol = (4,16) #Number of start bits, base
    base2str = {2:'b',8:'o',10:'d',16:'x'}
    
    def __init__(self,data,error=False,priority=None,error_code=None,
                 title="",description="",flag=None,metadata={}):
        """Initialize a Message object. If 'data' is a string, try and decode it.
        If it is a dict, initialize a dictionary"""
        
        if isinstance(data,str):
            message_dict = Message.decode_message(data)
        elif isinstance(data,dict):
            message_dict = data
        else:
            raise TypeError("'Message' object must be initialized with a dict or an encoded str")
        
        #There should be an easier way to do this so we can easily add kwargs
        for key,val in zip( ('error','priority','error_code','title','description','flag','metadata'), 
                               (error,priority,error_code,title,description,flag,metadata) ):
            if key in message_dict.keys():
                continue
            message_dict[key] = val
            
        
        super(Message,self).__init__(message_dict)
      
        
        
    def encode(self):
        
        return Message.encode_message(self)
        
    @classmethod
    def decode_message(cls,mssg_str):
        """Decode a message and return it as a message object"""
        
        message_dict = {}
        try:
            #The string should be an encoded dict
            message_dict = pickle.loads( mssg_str )
            return cls(message_dict)
        except Exception as e:
            raise exc.ReadMessageError ( "Unrecognized encoding for server message: {}".format(e) )
            
    @staticmethod
    def encode_message(dict_like):
        """Encode a message"""
        #Encode the dict into a pickled string
        message_str = pickle.dumps(dict_like)
        
        #Encode the first four characters to 
        # specify the length of the message
        numbits,base = Message.protocol
        base_prefix = Message.base2str [base]
        
        fmt = '0{}{}'.format(numbits,base_prefix)
        
        mlen = format( len(message_str) ,fmt )
        
        message_str = '{}{}'.format(mlen,message_str)
        
        return message_str
        
        
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
            raise exc.ReadMessageError("Cannot read incoming message")
            
    @staticmethod
    def trim(message):
        numbits,base = Message.protocol
        return message[numbits:]
