import socket
import threading

def sockExtract(sock, bufsize):
    oldtimeout = sock.gettimeout()
    sock.settimeout(1)
    try:
        data = sock.recv(bufsize)
    except socket.timeout:
        data = b''
    except ConnectionResetError:
        data = None
    except Exception as e:
        print(e)
        exit()
    sock.settimeout(oldtimeout)
    return data

def extract(sock):
    data = b''
    recv = sockExtract(sock, 1024)
    while recv:
        yield recv
        recv = sockExtract(sock, 1024)
    return data

class Receiver(threading.Thread):
    def __init__(self, port, callbackmap):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("localhost", port))
        self.closed = False
        self.sessionid = ""
        self.uname = ""
        self.callbackmap = callbackmap
        
    def run(self):
        global sessionid
        data = b''
        while not self.closed:
            data += sockExtract(self.sock, 1024)
            if self.isEndOfResponse(data):
                resp, data = self.separate(data)
                print(resp)
                print(data)
                lines = resp.decode("UTF-8").split('\r\n')
                func, params = lines[0], lines[1:-2]
                if func in self.callbackmap:
                    self.callbackmap[func](params)
        
    def isEndOfResponse(self, data):
        return b'\r\n\r\n' in data
        
    def separate(self, data):
        split = data.find(b'\r\n\r\n')+4
        command = data[:split]
        trail = data[split:]
        return (command, trail)
    
    def close(self):
        self.closed = True
        self.sock.close()