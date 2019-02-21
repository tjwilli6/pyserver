# pyserver
## A simple server and client package

### The basics
#### Server objects
```
>>> from pyserver import server
>>> ip,port = '127.0.0.1', 10000
>>> my_server = server.Server(ip,port)
>>> my_server.listen()
```
This will start a dedicated thread to run in the background and wait for new clients to connect. 
For each new client that connects, a seperate thread is started to listen to that individual client.

#### Client objects
```
>>> from pyserver import server
>>> ip,port = '127.0.0.1', 10000 #IP,port where the server is listening
>>> my_client = server.Client(ip,port)
>>> my_client.send_data({'message':'hello world!'})
```

### Interacting with your code
The ultimate goal is to naturally tie together other elements of your code to the server and client.
If you want to do something when data is received by either server or client, you can bind a ```callable``` which will be called whenever data is received by the server/client object.
```
>>> def my_func(data):
>>>... print "I have received a message!"
>>>... print data
>>> my_client.bind(my_func)
```
Now whenever ```my_client``` receives a message from the server, it will call your function with this message as the argument.
So what is the message? A dict-like wrapper class ```pyserver.server.Message```. This is simple wrapper class that inherits from ```dict``` and is used for encoding/decoding data during transfer between client and server. Your function can access the data in this ```Message``` object the same way you would a ```dict```.

Optionally, you can also use the ```bind``` method to pass an error handling function. If you prefer to handle any exceptions raised in the server/client communication process, simply pass a ```callable``` as the second argument to ```bind```.
