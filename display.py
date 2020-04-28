import socket
import time
import threading
import tkinter as tk
import sys
import chesslogic

uicomponents = {}

challengeoptions = [["Play as White", "WHITE"],["Play as Black", "BLACK"],["Select randomly","RANDOM"],["Let opponent decide","OPPONENT"]]
selectedSquare = None
validSquares = []
specialSquares = []
checkSquare = None

selectcolor = "#00FF00"
validcolor = "Blue"
specialcolor = "#FF00FF"
checkcolor = "Red"

def getNormalColor(row, column):
    colors = ["Black", "White"]
    return colors[(row+column)%2]

def genphotoimages():
    return {
        "P": tk.PhotoImage(file="White_Pawn.png"),
        "R": tk.PhotoImage(file="White_Rook.png"),
        "N": tk.PhotoImage(file="White_Knight.png"),
        "B": tk.PhotoImage(file="White_Bishop.png"),
        "Q": tk.PhotoImage(file="White_Queen.png"),
        "K": tk.PhotoImage(file="White_King.png"),
        "p": tk.PhotoImage(file="Black_Pawn.png"),
        "r": tk.PhotoImage(file="Black_Rook.png"),
        "n": tk.PhotoImage(file="Black_Knight.png"),
        "b": tk.PhotoImage(file="Black_Bishop.png"),
        "q": tk.PhotoImage(file="Black_Queen.png"),
        "k": tk.PhotoImage(file="Black_King.png")
    }

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

class GameViewer:
    def __init__(self, gameid):
        self.gameid = gameid

    def __call__(self):
        request = bytes("GETGAMESTATE\r\n%s\r\n%s\r\n\r\n"%(self.gameid, receiver.sessionid), "UTF-8")
        receiver.sock.send(request)

class ResponseHandler:
    def __init__(self, challengeid, selectcolor, responsefunction):
        self.challengeid = challengeid
        self.selectcolor = selectcolor
        self.responsefunction = responsefunction
        
    def __call__(self):
        self.responsefunction(self.challengeid, self.selectcolor)

class SquareClickHandler:
    def __init__(self, square):
        self.square = square
    def __call__(self, event):
        global selectedSquare, validSquares, specialSquares
        priorSelection = selectedSquare
        if priorSelection == None:
            x,y = chesslogic.squareNameToXY(self.square)
            index = chesslogic.xyToIndex(x,y)
            position = uicomponents['/gameframe/position']
            color = uicomponents['/gameframe/gameboard/color']
            piece = position[index]
            if piece != '-' and color==position[69] and ((color == "W") == (piece.isupper())):
                canvas = uicomponents['/gameframe/gameboard/%s'%self.square]
                canvas.config(bg=selectcolor)
                selectedSquare = self.square
                validSquares, specialSquares = chesslogic.pieceValidMoves(position, self.square)
                for i in validSquares:
                    canvas = uicomponents['/gameframe/gameboard/%s'%i]
                    canvas.config(bg=validcolor)
                for i in specialSquares:
                    canvas = uicomponents['/gameframe/gameboard/%s'%i]
                    canvas.config(bg=specialcolor)
        else:
            selectedSquare = None
            unhighlight(priorSelection)
            for i in validSquares+specialSquares:
                unhighlight(i)
            validSquares, specialSquares = [],[]

def unhighlight(square):
    canvas = uicomponents['/gameframe/gameboard/%s'%square]
    if square == checkSquare:
        canvas.config(bg=checkcolor)
    else:
        x,y = chesslogic.squareNameToXY(square)
        canvas.config(bg=getNormalColor(x,y))

def rescindchallenge(challengeid, selectcolor):
    request = bytes("RESPOND\r\n%s\r\nRESCIND\r\n%s\r\n\r\n"%(challengeid, receiver.sessionid), "UTF-8")
    receiver.sock.send(request)
    
def acceptchallenge(challengeid, selectcolor):
    if selectcolor:
        uicomponents['/respondchooseframe/acceptchallenge/challengeid'] = challengeid
        uicomponents['/homeframe'].place_forget()
        uicomponents['/respondchooseframe'].place(relx=0, rely=0, relheight=1, relwidth=1)
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
    uicomponents[path+'frames'] = {}
    uicomponents[path+'rescinds'] = {}
    uicomponents[path+'accepts'] = {}
    uicomponents[path+'rejects'] = {}
    listbase = 40
    entryheight = 40
    uicomponents[path+'/header'].place(relx=0, relwidth=1, y=0, height=listbase)
    for i in challenges:
        challengeid, opponent, selection = i.split()
        container = tk.Frame(uicomponents[path])
        uicomponents[path+'frames'][challengeid] = container
        label = tk.Label(container, text=writeout(isOut, opponent, selection))
        label.place(relx=0, relwidth=1, rely=0, relheight=.5)
        if isOut:
            rescinder = tk.Button(container, text="Rescind", command=ResponseHandler(challengeid, False, rescindchallenge))
            rescinder.place(relx=.35, relwidth=.3, rely=.5, relheight=.5)
            uicomponents[path+'rescinds'][challengeid] = rescinder
        else:
            accepter = tk.Button(container, text="Accept", command=ResponseHandler(challengeid, selection=="Opponent", acceptchallenge))
            accepter.place(relx=.1, relwidth=.3, rely=.5, relheight=.5)
            rejecter = tk.Button(container, text="Reject", command=ResponseHandler(challengeid, False, rejectchallenge))
            rejecter.place(relx=.6, relwidth=.3, rely=.5, relheight=.5)
            uicomponents[path+'accepts'][challengeid] = accepter
            uicomponents[path+'rejects'][challengeid] = rejecter
        container.place(relx=0, relwidth=1, y=listbase, height=entryheight)
        listbase += entryheight
    relx = .35 if not isOut else 0
    uicomponents[path].place(relx=relx, rely=.1, relheight=.8, relwidth=.3)

def handleShowActiveGames(params):
    games = params
    path = '/homeframe/activegames'
    uicomponents[path] = tk.Frame(uicomponents['/homeframe'])
    listbase = 40
    entryheight = 40
    uicomponents[path+'/header'] = tk.Label(uicomponents[path], text="Active games")
    uicomponents[path+'/header'].place(relx=0, relwidth=1, y=0, height=listbase)
    uicomponents[path+'frames'] = {}
    uicomponents[path+'viewbuttons'] = {}

    listbase = 40
    entryheight = 40
    uicomponents[path+'/header'].place(relx=0, relwidth=1, y=0, height=listbase)
    for i in games:
        gameid, white, black, turn, promoteBit = i.split()
        awaitingPromote = (promoteBit == 1)
        container = tk.Frame(uicomponents[path])
        uicomponents[path+'frames'][gameid] = container
        label = tk.Label(container, text="%s vs. %s"%(white, black))
        label.place(relx=0, relwidth=1, rely=0, relheight=.5)

        viewer = tk.Button(container, text="View", command=GameViewer(gameid) )
        viewer.place(relx=.35, relwidth=.3, rely=.5, relheight=.5)

        players = {"W":white, "B":black}
        isactiveplayer = receiver.uname == players[turn]
        turntemplate = "%s pawn is awaiting promotion." if awaitingPromote else "%s move."
        possessive = "Your" if isactiveplayer else ("%s's"%players[turn])
        turnlabel = turntemplate % possessive

        uicomponents[path+'viewbuttons'][gameid] = viewer
        container.place(relx=0, relwidth=1, y=listbase, height=entryheight)
        listbase += entryheight
    uicomponents[path].place(relx=.65, rely=.1, relheight=.8, relwidth=.3)

def handleNewChallenge(params):
    uicomponents['/newchallengeframe'].place_forget()
    uicomponents['/homeframe'].place(relx=0, rely=0, relheight=1, relwidth=1)
    servershowchallenges()
    servershowactivegames()

def handleGetGameState(params):
    uicomponents['/homeframe'].place_forget()
    uicomponents['/gameframe'].place(relx=0, rely=0, relheight=1, relwidth=1)
    position = params[1]
    uicomponents['/gameframe/gameboard/color'] = params[2]
    squares = position[:64]
    for i in range(64):
        rawrow = i//8
        row = (rawrow)+1
        rawcol = i%8
        column = chr(rawcol+97)
        square = str(column)+str(row)
        if squares[i] in photoimages:
            uicomponents['/gameframe/gameboard/'+square].create_image(0, 0, image=photoimages[squares[i]], anchor=tk.NW)
    uicomponents['/gameframe/position'] = position

functions = {
    "LOGIN" : handleLogin,
    "SHOWCHALLENGES" : handleShowChallenges,
    "SHOWACTIVEGAMES" : handleShowActiveGames,
    "NEWCHALLENGE" : handleNewChallenge,
    "GETGAMESTATE" : handleGetGameState
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
    time.sleep(.5)
    receiver.sock.send(bytes('SHOWCHALLENGES\r\nIN\r\n%s\r\n\r\n'%(receiver.sessionid), "UTF-8"))
    time.sleep(.5)

def servershowactivegames():
    receiver.sock.send(bytes('SHOWACTIVEGAMES\r\n%s\r\n\r\n'%(receiver.sessionid), "UTF-8"))

def serveracceptandselect():
    decision = uicomponents['/respondchooseframe/decision'].curselection()
    challengeid = uicomponents['/respondchooseframe/acceptchallenge/challengeid']
    if len(decision) != 1:
        print("One selection")
        return None
    index = decision[0]
    responsetype = challengeoptions[index][1]
    receiver.sock.send(bytes('RESPOND\r\n%s\r\nACCEPT\r\n%s\r\n%s\r\n\r\n'%(challengeid, responsetype, receiver.sessionid), "UTF-8"))

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

def packsquares(blackview=False):
    basepath = '/gameframe/gameboard'
    initpath = "%s/%s"%(basepath, "squaresInitialized")
    if not uicomponents[initpath]:
        uicomponents[initpath] = True
        for i in range(64):
            rawrow = i//8
            row = (rawrow)+1
            rawcol = i%8
            column = chr(rawcol+97)
            square = str(column)+str(row)
            squarepath = "%s/%s"%(basepath, square)
            squarecolor = getNormalColor(rawrow,rawcol)
            uicomponents[squarepath] = tk.Canvas(uicomponents[basepath], bg=squarecolor)
            uicomponents[squarepath].bind("<Button-1>", SquareClickHandler(square))
    for i in range(64):
        rawrow = i//8
        row = (rawrow)+1
        rawcol = i%8
        column = chr(rawcol+97)
        square = str(column)+str(row)
        uicol = rawcol/8
        uirow = rawrow/8
        if blackview:
            uicol = .875 - uicol
        else:
            uirow = .875 - uirow
        squarepath = "%s/%s"%(basepath, square)
        uicomponents[squarepath].place(relwidth=.125, relheight=.125, relx=uicol, rely=uirow)

def cancelresponse():
    uicomponents['/respondchooseframe'].place_forget()
    uicomponents['/homeframe'].place(relx=0, rely=0, relheight=1, relwidth=1)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

if ("-p" in sys.argv):
    port = int(sys.argv[sys.argv.index("-p")+1])
else:
    port = 8888

s.connect(("localhost", port))

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

uicomponents['/respondchooseframe'] = tk.Frame(uicomponents['/'])
uicomponents['/respondchooseframe/opplabel'] = tk.Label(uicomponents['/respondchooseframe'], text="Opponent")
uicomponents['/respondchooseframe/opplabel'].place(relx=.35, relwidth=.15, rely=0)
uicomponents['/respondchooseframe/oppname'] = tk.Entry(uicomponents['/respondchooseframe'])
uicomponents['/respondchooseframe/oppname'].place(relx=.5, relwidth=.15, rely=0)
uicomponents['/respondchooseframe/decision'] = tk.Listbox(uicomponents['/respondchooseframe'])
uicomponents['/respondchooseframe/decision'].place(relx=.35, relwidth=.3, rely=.2)

[uicomponents['/respondchooseframe/decision'].insert(tk.END,i[0]) for i in challengeoptions if i[1]!="OPPONENT"]

uicomponents['/respondchooseframe/acceptchallenge'] = tk.Button(uicomponents['/respondchooseframe'], text="Confirm Selection", command=serveracceptandselect)
uicomponents['/respondchooseframe/acceptchallenge'].place(relx=.18, relwidth=.32, rely=.93, relheight=.04)
uicomponents['/respondchooseframe/cancel'] = tk.Button(uicomponents['/respondchooseframe'], text="Cancel", command=cancelresponse)
uicomponents['/respondchooseframe/cancel'].place(relx=.5, relwidth=.32, rely=.93, relheight=.04)

uicomponents['/gameframe'] = tk.Frame(uicomponents['/'])
uicomponents['/gameframe/gameheader'] = tk.Frame(uicomponents['/gameframe'])
uicomponents['/gameframe/gameheader/return'] = tk.Button(uicomponents['/gameframe/gameheader'], text="Back to menu")
uicomponents['/gameframe/gameheader/playerslabel'] = tk.Label(uicomponents['/gameframe/gameheader'], text="White vs Black")
uicomponents['/gameframe/gameheader/turnlabel'] = tk.Label(uicomponents['/gameframe/gameheader'], text="White to Move")
uicomponents['/gameframe/gamecontrol'] = tk.Frame(uicomponents['/gameframe'])
uicomponents['/gameframe/gamecontrol/offerdraw'] = tk.Button(uicomponents['/gameframe/gamecontrol'], text="Offer Draw")
uicomponents['/gameframe/gamecontrol/claimdraw'] = tk.Button(uicomponents['/gameframe/gamecontrol'], text="Claim Draw")
uicomponents['/gameframe/gamecontrol/resign'] = tk.Button(uicomponents['/gameframe/gamecontrol'], text="Resign")
uicomponents['/gameframe/gamecontrol/claimdrawoptions'] = tk.Frame(uicomponents['/gameframe/gamecontrol'])
uicomponents['/gameframe/gamecontrol/claimdrawoptions/reason'] = tk.Listbox(uicomponents['/gameframe/gamecontrol/claimdrawoptions'])
uicomponents['/gameframe/gamecontrol/claimdrawoptions/when'] = tk.Listbox(uicomponents['/gameframe/gamecontrol/claimdrawoptions'])
uicomponents['/gameframe/gameboard'] = tk.Frame(uicomponents['/gameframe'])
uicomponents['/gameframe/gameboard/squaresInitialized'] = False
uicomponents['/gameframe/gameboard'].place(x=300, width=800, height=800, y=100)
packsquares()
photoimages = genphotoimages()
    
uicomponents['/'].geometry("1400x1000")
uicomponents['/'].mainloop()
receiver.close()
