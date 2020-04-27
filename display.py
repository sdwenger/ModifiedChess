import socket
import time
import threading
import tkinter as tk
import sys

uicomponents = {}

challengeoptions = [["Play as White", "WHITE"],["Play as Black", "BLACK"],["Select randomly","RANDOM"],["Let opponent decide","OPPONENT"]]

def handleLogin(params):
    if (params[0] == "SUCCESS"):
        receiver.uname = params[1]
        receiver.sessionid = params[2]
        uicomponents['/homeframe/usernamevar'].set(receiver.uname)
        uicomponents['/login'].pack_forget()
        uicomponents['/homeframe'].place(relx=0, rely=0, relheight=1, relwidth=1)
        servershowchallenges()
        servershowactivegames()
        if '-k' in sys.argv:
            killcommand()

def writeout(isOut, oppname, selection):
    if selection == "Random":
        second = "Colors will be selected randomly."
    else:
        subj = "You" if ((selection == "Opponent") != isOut) else oppname
        predicate = "will choose colors." if (selection == "Opponent") else "will play as %s."%selection
        second = "%s %s"%(subj, predicate)
    firsttemplate = "%s %s challenged %s. "
    subj = "You" if isOut else oppname
    verb = "have" if isOut else "has"
    obj = oppname if isOut else "you"
    first = firsttemplate%(subj, verb, obj)
    return first + second

class ResponseHandler:
    def __init__(self, challengeid, selectcolor, responsefunction):
        self.challengeid = challengeid
        self.selectcolor = selectcolor
        self.responsefunction = responsefunction
        
    def __call__(self):
        self.responsefunction(self.challengeid, self.selectcolor)

def rescindchallenge(challengeid, selectcolor):
    request = bytes("RESPOND\r\n%s\r\nRESCIND\r\n%s\r\n\r\n"%(challengeid, receiver.sessionid), "UTF-8")
    receiver.sock.send(request)
    
def acceptchallenge(challengeid, selectcolor):
    if selectcolor:
        print("Select")
    else:
        request = bytes("RESPOND\r\n%s\r\nACCEPT\r\n%s\r\n\r\n"%(challengeid, receiver.sessionid), "UTF-8")
        receiver.sock.send(request)
    
def rejectchallenge(challengeid, selectcolor):
    request = bytes("RESPOND\r\n%s\r\nREJECT\r\n%s\r\n\r\n"%(challengeid, receiver.sessionid), "UTF-8")
    receiver.sock.send(request)

def handleShowChallenges(params):
    direction = params[0]
    isOut = (direction == "OUT")
    path = '/homeframe/%schallenges'%direction.lower()
    challenges = params[1:]
    uicomponents[path] = tk.Frame(uicomponents['/homeframe'])
    header = "Awaiting your response" if not isOut else "Awaiting opponent's response..."
    uicomponents[path+'/header'] = tk.Label(uicomponents[path], text=header)
    uicomponents[path+'frames'] = []
    uicomponents[path+'rescinds'] = []
    uicomponents[path+'accepts'] = []
    uicomponents[path+'rejects'] = []
    listbase = 40
    entryheight = 40
    uicomponents[path+'/header'].place(relx=0, relwidth=1, y=0, height=listbase)
    for i in challenges:
        challengeid, opponent, selection = i.split()
        container = tk.Frame(uicomponents[path])
        uicomponents[path+'frames'].append(container)
        label = tk.Label(container, text=writeout(isOut, opponent, selection))
        label.place(relx=0, relwidth=1, rely=0, relheight=.5)
        if isOut:
            rescinder = tk.Button(container, text="Rescind", command=ResponseHandler(challengeid, False, rescindchallenge))
            rescinder.place(relx=.35, relwidth=.3, rely=.5, relheight=.5)
            uicomponents[path+'rescinds'].append(rescinder)
        else:
            accepter = tk.Button(container, text="Accept", command=ResponseHandler(challengeid, selection=="OPPONENT", acceptchallenge))
            accepter.place(relx=.1, relwidth=.3, rely=.5, relheight=.5)
            rejecter = tk.Button(container, text="Reject", command=ResponseHandler(challengeid, False, rejectchallenge))
            rejecter.place(relx=.6, relwidth=.3, rely=.5, relheight=.5)
            uicomponents[path+'accepts'].append(accepter)
            uicomponents[path+'rejects'].append(rejecter)
        container.place(relx=0, relwidth=1, y=listbase, height=entryheight)
        listbase += entryheight
    relx = .35 if not isOut else 0
    uicomponents[path].place(relx=relx, rely=.1, relheight=.8, relwidth=.3)

def handleShowActiveGames(params):
    print(params)

def handleNewChallenge(params):
    uicomponents['/newchallengeframe'].place_forget()
    uicomponents['/homeframe'].place(relx=0, rely=0, relheight=1, relwidth=1)
    servershowchallenges()
    servershowactivegames()

functions = {
    "LOGIN" : handleLogin,
    "SHOWCHALLENGES" : handleShowChallenges,
    "SHOWACTIVEGAMES" : handleShowActiveGames,
    "NEWCHALLENGE" : handleNewChallenge,
}

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

class Receiver(threading.Thread):
    def __init__(self, sock):
        threading.Thread.__init__(self)
        self.sock = sock
        self.closed = False
        self.sessionid = ""
        self.uname = ""
        
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
                if func in functions:
                    functions[func](params)
        
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

def extract(sock):
    data = b''
    recv = sockExtract(sock, 1024)
    while recv:
        yield recv
        recv = sockExtract(sock, 1024)
    return data

def serverlogin():
    global uicomponents, receiver
    uname = uicomponents['/login/uname'].get()
    pwd = uicomponents['/login/pwd'].get()
    receiver.sock.send(bytes('LOGIN\r\n%s\r\n%s\r\n\r\n'%(uname, pwd), "UTF-8"))

def killcommand():
    global receiver, uicomponents
    print(bytes('KILLSERVER\r\n%s\r\n\r\n'%(receiver.sessionid), "UTF-8"))
    receiver.sock.send(bytes('KILLSERVER\r\n%s\r\n\r\n'%(receiver.sessionid), "UTF-8"))
    #receiver.sock.close()
    uicomponents['/'].destroy()
    exit()

def servershowchallenges():
    receiver.sock.send(bytes('SHOWCHALLENGES\r\nOUT\r\n%s\r\n\r\n'%(receiver.sessionid), "UTF-8"))
    time.sleep(1)
    receiver.sock.send(bytes('SHOWCHALLENGES\r\nIN\r\n%s\r\n\r\n'%(receiver.sessionid), "UTF-8"))
    time.sleep(1)

def servershowactivegames():
    receiver.sock.send(bytes('SHOWACTIVEGAMES\r\n%s\r\n\r\n'%(receiver.sessionid), "UTF-8"))

def newchallengescreen():
    uicomponents['/homeframe'].place_forget()
    uicomponents['/newchallengeframe'].place(relx=.3, rely=.3, relheight=.7, relwidth=.4)

def servernewchallenge():
    selection = uicomponents['/newchallengeframe/challengetype'].curselection()
    if len(selection) != 1:
        print("One selection")
        return None
    index = selection[0]
    challengetype = challengeoptions[index][1]
    oppname = uicomponents['/newchallengeframe/oppname'].get()
    receiver.sock.send(bytes('NEWCHALLENGE\r\n%s\r\n%s\r\n%s\r\n\r\n'%(oppname, challengetype, receiver.sessionid), "UTF-8"))

def cancelchallenge():
    uicomponents['/homeframe/usernamevar'].set(receiver.uname)
    uicomponents['/newchallengeframe'].place_forget()
    uicomponents['/homeframe'].place(relx=0, rely=0, relheight=1, relwidth=1)
    servershowchallenges()
    servershowactivegames()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.connect(("localhost", 8888))

receiver = Receiver(s)
receiver.start()

uicomponents['/'] = tk.Tk()
uicomponents['/login'] = tk.Frame(uicomponents['/'])
uicomponents['/login/uname'] = tk.Entry(uicomponents['/login'])
uicomponents['/login/pwd'] = tk.Entry(uicomponents['/login'], show="*")
uicomponents['/login/auth'] = tk.Button(uicomponents['/login'], text="Log in", command=serverlogin)
uicomponents['/login/uname'].pack()
uicomponents['/login/pwd'].pack()
uicomponents['/login/auth'].pack()
uicomponents['/login'].pack()
uicomponents['/killframe'] = tk.Frame(uicomponents['/'])
uicomponents['/killframe/killserver'] = tk.Button(uicomponents['/killframe'], text="KILL", command=killcommand)
uicomponents['/killframe/killserver'].pack()
if ('-k' in sys.argv):
    uicomponents['/killframe'].pack()

uicomponents['/homeframe'] = tk.Frame(uicomponents['/'])
uicomponents['/homeframe/usernamevar'] = tk.StringVar()
uicomponents['/homeframe/username'] = tk.Label(uicomponents['/homeframe'], textvariable=uicomponents['/homeframe/usernamevar'])
uicomponents['/homeframe/newchallenge'] = tk.Button(uicomponents['/homeframe'], text="New Challenge", command=newchallengescreen)
uicomponents['/homeframe/username'].pack()
uicomponents['/homeframe/newchallenge'].place(relx=.42, relwidth=.16, rely=.93, relheight=.04)

uicomponents['/newchallengeframe'] = tk.Frame(uicomponents['/'])
uicomponents['/newchallengeframe/opplabel'] = tk.Label(uicomponents['/newchallengeframe'], text="Opponent")
uicomponents['/newchallengeframe/opplabel'].place(relx=.35, relwidth=.15, rely=0)
uicomponents['/newchallengeframe/oppname'] = tk.Entry(uicomponents['/newchallengeframe'])
uicomponents['/newchallengeframe/oppname'].place(relx=.5, relwidth=.15, rely=0)
uicomponents['/newchallengeframe/challengetype'] = tk.Listbox(uicomponents['/newchallengeframe'])
uicomponents['/newchallengeframe/challengetype'].place(relx=.35, relwidth=.3, rely=.2)

[uicomponents['/newchallengeframe/challengetype'].insert(tk.END,i[0]) for i in challengeoptions]

uicomponents['/newchallengeframe/confirmchallenge'] = tk.Button(uicomponents['/newchallengeframe'], text="Confirm Challenge", command=servernewchallenge)
uicomponents['/newchallengeframe/confirmchallenge'].place(relx=.18, relwidth=.32, rely=.93, relheight=.04)
uicomponents['/newchallengeframe/cancel'] = tk.Button(uicomponents['/newchallengeframe'], text="Cancel", command=cancelchallenge)
uicomponents['/newchallengeframe/cancel'].place(relx=.5, relwidth=.32, rely=.93, relheight=.04)

uicomponents['/'].geometry("1200x800")
uicomponents['/'].mainloop()
receiver.close()