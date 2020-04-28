import socket
import time
import threading
import datetime
import random
import chesslogic

sessions = {}

def getunamefromsession(sessionid, refresh=False):
    if not sessionid in sessions:
        return None
        
    if refresh:
        sessions[sessionid][1] = datetime.datetime.now() + datetime.timedelta(0,1800)

    return sessions[sessionid][0]

def pushsessionid(sessionid, uname):
    if not sessionid in sessions:
        sessions[sessionid] = [uname, datetime.datetime.now() + datetime.timedelta(0,1800)]

def sockExtract(sock, bufsize):
    try:
        oldtimeout = sock.gettimeout()
        sock.settimeout(1)
        try:
            data = sock.recv(bufsize)
        except socket.timeout:
            data = b''
        except ConnectionResetError:
            data = 1
        except Exception as e:
            if (type(e) == OSError):
                raise
            exit()
        sock.settimeout(oldtimeout)
        return data
    except OSError:
        return 2

class ConnectionHandler(threading.Thread):
    def __init__(self, sock, conn, addr, handler=None):
        self.closed = False
        threading.Thread.__init__(self)
        self.sock = sock
        self.conn = conn
        self.addr = addr
        self.handler = handler
        
    def run(self):
        data = b''
        while not self.closed:
            while not self.isEndOfCommand(data):
                rec = sockExtract(self.conn, 1024)
                if rec == 1:
                    self.close()
                elif rec == 2:
                    return None
                else:
                    data += rec
            command, data = self.separate(data)
            self.handleCommand(command)
        
    def isEndOfCommand(self, data):
        return b'\r\n\r\n' in data
        
    def separate(self, data):
        split = data.find(b'\r\n\r\n')+4
        command = data[:split]
        trail = data[split:]
        return (command, trail)
        
    def handleCommand(self, data):
        if self.handler == None:
            global acceptConnections
            if (data == b'KILLSERVER\r\n\r\n'):
                acceptConnections = False
            else:
                print(data)
        else:
            self.handler(self, data)
        
    def close(self):
        self.closed = True
        self.conn.close()
        allconnections.remove(self)

class ServerThread(threading.Thread):
    def __init__(self, host, port, connectionHandler=None):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.finished = False
        self.connectionHandler = connectionHandler
        
    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            s.settimeout(5)
            while not self.finished:
                try:
                    conn, addr = s.accept()
                    handler = ConnectionHandler(s, conn, addr, self.connectionHandler)
                    allconnections.append(handler)
                    handler.start()
                except socket.timeout:
                    pass
                
    def kill(self):
        self.finished = True

def mainloop(connHandler=None, loopHandler=None):
    global serverThread
    if loopHandler == None:
        def loopHandler():
            pass
    port = random.randrange(8000, 9000)
    serverThread = ServerThread('127.0.0.1', port, connHandler)
    print("Port %s"%port)
    serverThread.start()

    global acceptConnections
    while acceptConnections:
        loopHandler()

def closeServer():
    global serverThread
    [i.close() for i in allconnections]
    serverThread.kill()
    
def main(connHandler=None, loopHandler=None):
    mainloop(connHandler, loopHandler)
    closeServer()
    
allconnections = []

acceptConnections = True
    
if __name__=='__main__':
    try:
        main()
    except Exception as e:
        print(e)
        acceptConnections = False
