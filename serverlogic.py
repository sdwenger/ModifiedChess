import socket
import time
import threading
import datetime
import random
import chesslogic

sessionsdata = {}
unametosessions = {}

def getunamefromsession(sessionid, connhandler, refresh=False):
    if not sessionid in sessionsdata:
        return None

    session = sessionsdata[sessionid]
    if session.isExpired():
        del sessionsdata[sessionid]
        return None

    session.addconnection(connhandler)
    if refresh:
        session.refresh()

    return sessionsdata[sessionid].uname

def notifyuser(uname, data):
    if not uname in unametosessions:
        return None
    sessions = unametosessions[uname]
    for i in sessions:
        session = sessionsdata[i]
        if session.isExpired():
            sessions.remove(i)
        else:
            for j in session.connections:
                try:
                    j.conn.send(data)
                except BrokenPipeError:
                    j.close()

def pushsessionid(sessionid, uname, connhandler):
    if not sessionid in sessionsdata:
        session = Session(sessionid, uname)
        session.addconnection(connhandler)
        sessionsdata[sessionid] = session
        if not uname in unametosessions:
            unametosessions[uname] = []
        unametosessions[uname].append(sessionid)
        return True
    return False

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

class Session:
    def __init__(self, sessionid, uname, maxage=1800):
        self.sessionid, self.uname = sessionid, uname
        self.expiration = datetime.datetime.now() + datetime.timedelta(0,maxage)
        self.connections = []

    def refresh(self, exptime=1800):
        self.expiration = max(self.expiration, datetime.datetime.now() + datetime.timedelta(0,exptime))

    def isExpired(self):
        return datetime.datetime.now() >= self.expiration

    def addconnection(self, conn):
        if not conn in self.connections:
            self.connections.append(conn)
            return True
        return False

    def removeconnection(self, conn):
        if conn in self.connections:
            self.connections.remove(conn)
            return True
        return False

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
        try:
            self.conn.close()
        except:
            pass
        allconnections.remove(self)
        [sessionsdata[i].removeconnection(self) for i in sessionsdata]

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
