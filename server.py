#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sat Nov 17 13:31:45 2018

@author: tjwilliamson
"""

import socket
import threading
import random
import time
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
            return func(*args,**kwargs)
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





def get_random_byte_array(nbytes=56):
    
    lbyte = []
    for i in xrange(nbytes):
        lbyte.append( int(random.uniform(0,255)) )
    
    return lbyte






class ServerClientBase(object):
    """
    Base class for both server and client
    """
    
    RECEIVELEN = 4096
    
    def __init__(self,*args,**kwargs):
        
        self.__children = []
        
        #Kill = true when we want to end the listening thread
        self.__kill = False
        self.__host = kwargs.get('host')
        self.__port = kwargs.get('port')
        
        #A list of open connections
        #For the client, just the 'socket' object
        self.__connections = list() 
        
        #Whether or not to call close() on open connections
        #I don't think this is currently needed?
        self.__open = False
        
        self.__recping = True
        
    
    def __add_connection__(self,connection):
        
        if not connection in self.get_connections():
            self.__connections.append(connection)
            



#    def ping(self,target,nbytes=56,timeout=5):
#        
#        self.__recping = False
#        byte_array = get_random_byte_array(nbytes)
#        data = {'ping':byte_array,'type':'request'}
#        self.send_data(target,data)
        

    def get_connections(self):
        return self.__connections



#    def __wait_for_ping__(self,timeout=5):
#        t0 = time.time()
#        while not self.__recping:
#            time.sleep(timeout / 100.)
#            if time.time() - t0 > timeout:
#                self.handle_exception("Ping timed out")
#        return
                

    def __remove_connection__(self,connection):
        if connection in self.get_connections():
            return self.__connections.pop ( self.__connections.index(connection) )
        

        
    def set_kill(self,bKill=True):
        """
        End the listening loop at the 
        next iteration
        """
        self.__kill = bKill

    def get_kill(self):
        return self.__kill
    
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
        
    
    @property
    def is_open(self):
        return self.__open
    
    @is_open.setter
    def is_open(self,val):
        self.__open = bool( val )
    
    @catch_socket_error
    def send_data(self,dataobj,message):
        """Send a message to the connected socket, either a client or the server"""
        mssg = Message(message)
        mssg_string = mssg.encode()
        
        dataobj.send(mssg_string)
                
    @catch_socket_error
    def __receive_message__(self,dataobj,timeout=1):
        """
        Receive a message from the server or from a client
        'dataobj' can be either
        """
        
        logger.debug("Waiting to receive data from {}".format(dataobj))
        data = dataobj.recv(self.RECEIVELEN)

        logger.debug("Got data: {}".format(data) )
        
        #The sender has disconnected
        if not data:
            logger.debug("Data is None, returning")
            return data
        
        #How long do we expect the message to be?
        messg_len_tot = Message.get_length(data)
        
        logger.debug("Expecting message with {} characters".format(messg_len_tot))
        
        
        #Get the message minus the start byte
        messg = Message.trim(data)
        
        logger.debug("Current message string has {} characters".format(len(messg)))
        #logger.debug("Trimmed message: {}".format(messg))
        #Start the timer to receive the message
        tstart = time.time()
        
        while len(messg) < messg_len_tot:
            logger.debug("Looping to get full message")
            
            if time.time() - tstart >= timeout:
                raise exc.ReadMessageError("Timeout while reading message")
                
            #how many chars are we missing?
            diff = messg_len_tot - len(messg)
            logger.debug("Waiting on {} characters".format(diff))
            #Why would this happen?
            #if diff <= 0:
            #    break
            
            new_data = dataobj.recv(diff)
            if new_data is None:
                return new_data
            messg = messg + new_data

        logger.debug("Returning message {}".format(messg))
        
        return messg
        
    def __handle_data__(self,data):
        """Pass received data to all bound children"""
        logger.debug("Handling received message")
        
        if data.get('request'):
            self.__handle_internal_request__(data)
            return
        
        for child in self.__children:
            logger.debug("Calling child func {}".format(child['message']))
            child ['message'] (data)
            
            
            
    #TODO:
    #How do we exit this thread?
    def __listen__(self,dataobj,kill_on_disconnect=False):
        """
        Listen for data from either the client or server. Runs as 
        a dedicated thread to communicate with a server or a client
        ( a socket object )
        """
        
        #While we still want to listen
        while not self.get_kill():
            #Wait for a new message
            #This will hang until the object either sends 
            #a message or disconnects
            data = self.__receive_message__(dataobj)
            logger.debug("Received data from {}: {}".format(dataobj,data))
            #If the data is null/None, then
            # the server/client has disconnected
            if not data:
                logger.debug("Received data None, {} has disconnected".format(dataobj))
                #This connection is already closed
                # Remove it from active connections
                self.__remove_connection__(dataobj)
                break
            
            #We've received data from the connected object
            logger.debug("Passing data on to handler func")
            
            data = Message(data,origin=dataobj)
            self.__handle_data__(data)
        logger.debug("Leaving the listening thread for object {}".format(dataobj) )

    
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
        self.set_kill(False)
        
        logger.info("Initializing server at {}:{}".format(host,port) )
        super(Server,self).__init__(host=host,port=port)


    def listen(self,maxq=10):
        """Started the listening thread"""
        logger.debug("Starting the listening thread!")
        threading.Thread(target=self.__listen_server__,args=(maxq,) ).start()
        self.is_open = True

    @catch_socket_error
    def __listen_server__(self,maxq=10):
        """Wait for new clients to connect"""
        
        self.__socket.listen(maxq)
        
        while not self.get_kill():
            logger.debug("Now listening for new clients")
            client,address = self.__socket.accept()
            logger.info("Accepting new client from address {}".format(address))
            
            #Start a new thread dedicated to this client
            logger.debug("Starting thread to listen to client")
            threading.Thread(target=self.__listen__,args=(client,)).start()
            self.__add_connection__(client)
        
        logger.info("Server is no longer accepting new clients")
        
    
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
        
        
    def __del__(self,*args,**kwargs):
        
        self.close()
    
    @catch_socket_error
    def close(self):
        """Try to properly close the socket"""
        
        logger.debug("Calling close: open = {}".format(self.is_open))
        if not self.is_open:
            return
        
        #Exit the while loop at the next iteration
        self.set_kill(True)
        
        #Start a dummy client to stop the __listen_server__ loop
        self.__start_local_client__()
        
        client_list = self.get_connections()
        #Close our connection to each client
        for client in client_list:
            client.shutdown(socket.SHUT_RDWR)
            client.close()
            self.__remove_connection__(client)
            
        self.__socket.close()
        
        self.is_open = False
        
        

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
        
        
        super(Client,self).__init__(host=host,port=port)
    
    
    @catch_socket_error
    def connect(self):
        """Try to establish a connection to the server"""
        
        #Establish connection to the server
        self.__socket.connect( self.get_connection_info() )
        
        #If we haver a connection
        # Start a dedicated thread to run in the background and listen for 
        # data from the server
        
        #To kill this thread, we need to receive data from the server
        threading.Thread( target=self.__listen__,args=(self.__socket,True) ).start()
        self.is_open = True
        
        self.__add_connection__(self.__socket)
        
        
    def send_data(self,message):
        """Send a message to the server"""
        super(Client,self).send_data(self.__socket,message)
       

    def __del__(self,*args,**kwargs):
        
        self.close()
        
        
    @catch_socket_error
    def close(self):
        """Try to properly close the socket"""
        
        #self.__socket.shutdown(socket.SHUT_RDWR)
        #Exit the while loop at the next iteration
        if not self.is_open:
            return
        
        self.set_kill(True)
        
        connex_list = self.get_connections()
        #Close our connection to each client
        for connex in connex_list:
            connex.shutdown(socket.SHUT_RDWR)
            connex.close()
            self.__remove_connection__(connex)
            
        self.is_open = False

            
            
            
            
            

class Message(dict):
    """A class to hold a message sent between client and server"""
    protocol = (4,16) #Number of start bits, base
    base2str = {2:'b',8:'o',10:'d',16:'x'}
    
    def __init__(self,data,request=False,error=False,priority=None,error_code=None,
                 title="",description="",flag=None,origin=None,metadata={},**kwargs):
        """Initialize a Message object. If 'data' is a string, try and decode it.
        If it is a dict, initialize a dictionary"""
        
        if isinstance(data,str):
            message_dict = Message.decode_message(data)
        elif isinstance(data,dict):
            message_dict = data
        else:
            raise TypeError("'Message' object must be initialized with a dict or an encoded str")
        
        #There should be an easier way to do this so we can easily add kwargs
        for key,val in zip( ('request','error','priority','error_code','title','description','flag','origin','metadata'), 
                               (request,error,priority,error_code,title,description,flag,origin,metadata) ):
            if key in message_dict.keys():
                continue
            message_dict[key] = val
            
        message_dict.update(kwargs)
        
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
