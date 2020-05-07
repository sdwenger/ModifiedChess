import socket
import time
import threading
import tkinter as tk
import sys
import chesslogic

uicomponents = {}

challengeoptions = [["Play as White", "WHITE"],["Play as Black", "BLACK"],["Select randomly","RANDOM"],["Let opponent decide","OPPONENT"]]
imagecodes = {'queen':'q', 'knight':'n', 'rook':'r', 'bishop':'b'}
selectedSquare = None
validSquares = []
specialSquares = []
checkSquare = None
promotionInProgress = False

selectcolor = "#00FF00"
validcolor = "Blue"
specialcolor = "#FF00FF"
checkcolor = "Red"

def blankFunction(*param):
    pass

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
        uicomponents['/newuser'].pack_forget()
        uicomponents['/homeframe'].place(relx=0, rely=0, relheight=1, relwidth=1)
        servershowchallenges()
        servershowactivegames()

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
        uicomponents['/gameframe/gameboard/gameid'] = self.gameid
        request = bytes("GETGAMESTATE\r\n%s\r\n%s\r\n\r\n"%(self.gameid, receiver.sessionid), "UTF-8")
        receiver.sock.send(request)
        count = 1
        finished = False
        while not finished:
            pathtemplate = '/gameframe/movepanel/%s%%s'%count
            for i in ('label','white','black'):
                path = pathtemplate%i
                if path in uicomponents:
                    uicomponents[path].place_forget()
                    del uicomponents[path]
                else:
                    finished = True
            count += 1
        request = bytes("SHOWMOVEHISTORY\r\n%s\r\n%s\r\n\r\n"%(self.gameid, receiver.sessionid), "UTF-8")
        receiver.sock.send(request)

class ResponseHandler:
    def __init__(self, challengeid, selectcolor, responsefunction):
        self.challengeid = challengeid
        self.selectcolor = selectcolor
        self.responsefunction = responsefunction
        
    def __call__(self):
        self.responsefunction(self.challengeid, self.selectcolor)

class PromotionHandler:
    def __init__(self, promoteType):
        self.promoteType = promoteType
        
    def __call__(self):
        request = bytes("PROMOTE\r\n%s\r\n%s\r\n%s\r\n\r\n"%(uicomponents['/gameframe/gameboard/gameid'], imagecodes[self.promoteType], receiver.sessionid), "UTF-8")
        receiver.sock.send(request)

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
            if piece != '-' and color==position[69] and ((color == "W") == (piece.isupper())) and not promotionInProgress:
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
            if self.square in (validSquares+specialSquares):
                servermove(uicomponents['/gameframe/gameboard/gameid'], priorSelection, self.square, receiver.sessionid)
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

def servermove(gameid, init, final, sessionid):
    request = bytes("MOVE\r\n%s\r\n%s\r\n%s\r\n%s\r\n\r\n"%(gameid, init, final, sessionid), "UTF-8")
    receiver.sock.send(request)

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

def handleRespond(params):
    if params[0] == "SUCCESS":
        response = params[1]
        notifparams = params[2:]
        if response=="ACCEPT":
            chooseframe = uicomponents['/respondchooseframe']
            if chooseframe.winfo_ismapped() != 0:
                chooseframe.place_forget()
                uicomponents['/homeframe'].place(relx=0, rely=0, relheight=1, relwidth=1)
            challengeid, gameid, whitename, blackname = notifparams
            challengepath = '/homeframe/inchallenges'
            challengecontainers = uicomponents[challengepath+'frames']
            challengecontainer = challengecontainers[challengeid]
            oldy = challengecontainer.winfo_y()
            [challengecontainers[i].place(relx=0, relwidth=1, y=challengecontainers[i].winfo_y()-40, height=40) for i in challengecontainers if challengecontainers[i].winfo_y() > oldy]
            challengecontainer.place_forget()
            del challengecontainers[challengeid]
            
            gamepath = '/homeframe/activegames'
            gamecontainer = tk.Frame(uicomponents[gamepath])
            uicomponents[gamepath+'frames'][gameid] = gamecontainer
            label = tk.Label(gamecontainer, text="%s vs. %s"%(whitename, blackname))
            label.place(relx=0, relwidth=1, rely=0, relheight=.5)

            viewer = tk.Button(gamecontainer, text="View", command=GameViewer(gameid) )
            viewer.place(relx=.35, relwidth=.3, rely=.5, relheight=.5)

            isactiveplayer = receiver.uname == whitename
            possessive = "Your" if isactiveplayer else ("%s's"%whitename)
            turnlabel = "%s move." % possessive

            uicomponents[gamepath+'viewbuttons'][gameid] = viewer
            gamecontainer.place(relx=0, relwidth=1, y=len(uicomponents[gamepath+'frames'])*40, height=40)
        elif response=="REJECT":
            challengeid, = notifparams
            path = '/homeframe/inchallenges'
            containers = uicomponents[path+'frames']
            container = containers[challengeid]
            oldy = container.winfo_y()
            [containers[i].place(relx=0, relwidth=1, y=containers[i].winfo_y()-40, height=40) for i in containers if containers[i].winfo_y() > oldy] #bring up everything below
            container.place_forget()
            del containers[challengeid]
        elif response=="RESCIND":
            challengeid, = notifparams
            path = '/homeframe/outchallenges'
            containers = uicomponents[path+'frames']
            container = containers[challengeid]
            oldy = container.winfo_y()
            [containers[i].place(relx=0, relwidth=1, y=containers[i].winfo_y()-40, height=40) for i in containers if containers[i].winfo_y() > oldy] #bring up everything below
            container.place_forget()
            containers[challengeid]
            del containers[challengeid]

def handleGetGameState(params):
    uicomponents['/homeframe'].place_forget()
    uicomponents['/gameframe'].place(relx=0, rely=0, relheight=1, relwidth=1)
    position = params[1]
    uicomponents['/gameframe/gameboard/color'] = params[2]
    packsquares(params[2]=="B")
    whitename = params[3]
    blackname = params[4]
    uicomponents['/gameframe/gameheader/playersstring'].set("%s vs %s"%(whitename, blackname))
    squares = position[:64]
    turn = position[69]
    setboard(squares, turn)
    uicomponents['/gameframe/position'] = position

def handleNotify(params):
    notification = params[0]
    notifparams = params[1:]
    if notification=="STATUSCHANGE":
        print(params)
        gameid, gamestatus, gamesubstatus = params[1:]
        if gameid == uicomponents['/gameframe/gameboard/gameid']:
            uicomponents['/gameframe/gameheader/turnstring'].set("%s by %s"%(gamestatus, gamesubstatus))
    elif notification=="OPPMOVE" or notification=="ENEMYPROMOTE":
        gameid, annotation, strsequence, newposition, gamestatus, gamesubstatus = notifparams
        print(gamestatus, gamesubstatus)
        movesequence = int(strsequence)
        if '/gameframe/gameboard/gameid' in uicomponents and gameid == uicomponents['/gameframe/gameboard/gameid']:
            squares = newposition[:64]
            turn = newposition[69]
            setboard(squares, turn)
            uicomponents['/gameframe/position'] = newposition
            if uicomponents['/gameframe/gameboard/color'] == 'B':
                labelpath = '/gameframe/movepanel/%slabel'%movesequence
                whitepath = '/gameframe/movepanel/%swhite'%movesequence
                if whitepath in uicomponents:
                    uicomponents[whitepath].place_forget()
                uicomponents[labelpath] = tk.Label(uicomponents['/gameframe/movepanel'], text="%s. "%movesequence)
                uicomponents[labelpath].place(relx=.1, relwidth=.25, height=30, y=30*movesequence+70)
                uicomponents[whitepath] = tk.Label(uicomponents['/gameframe/movepanel'], text=annotation)
                uicomponents[whitepath].place(relx=.35, relwidth=.25, height=30, y=30*movesequence+70)
            else:
                blackpath = '/gameframe/movepanel/%sblack'%movesequence
                if blackpath in uicomponents:
                    uicomponents[blackpath].place_forget()
                uicomponents[blackpath] = tk.Label(uicomponents['/gameframe/movepanel'], text=annotation)
                uicomponents[blackpath].place(relx=.6, relwidth=.25, height=30, y=30*movesequence+70)
        if gamestatus != "In Progress":
            '''basepath = '/gameframe/gameboard'
            for i in range(64):
                square = chesslogic.indexToSquareName(i)
                path = basepath + '/' + square
                uicomponents[path].bind("<Button-1>", blankFunction)'''
            uicomponents['/gameframe/gameheader/turnstring'].set("%s by %s"%(gamestatus, gamesubstatus))
    elif notification=="RESCINDCHALLENGE":
        challengeid, = notifparams
        path = '/homeframe/inchallenges'
        containers = uicomponents[path+'frames']
        container = containers[challengeid]
        oldy = container.winfo_y()
        [containers[i].place(relx=0, relwidth=1, y=containers[i].winfo_y()-40, height=40) for i in containers if containers[i].winfo_y() > oldy] #bring up everything below
        container.place_forget()
        del containers[challengeid]
    elif notification=="ACCEPTCHALLENGE":
        challengeid, gameid, whitename, blackname = notifparams
        challengepath = '/homeframe/outchallenges'
        challengecontainers = uicomponents[challengepath+'frames']
        challengecontainer = challengecontainers[challengeid]
        oldy = challengecontainer.winfo_y()
        [challengecontainers[i].place(relx=0, relwidth=1, y=challengecontainers[i].winfo_y()-40, height=40) for i in challengecontainers if challengecontainers[i].winfo_y() > oldy]
        challengecontainer.place_forget()
        del challengecontainers[challengeid]
        
        gamepath = '/homeframe/activegames'
        gamecontainer = tk.Frame(uicomponents[gamepath])
        uicomponents[gamepath+'frames'][gameid] = gamecontainer
        label = tk.Label(gamecontainer, text="%s vs. %s"%(whitename, blackname))
        label.place(relx=0, relwidth=1, rely=0, relheight=.5)

        viewer = tk.Button(gamecontainer, text="View", command=GameViewer(gameid) )
        viewer.place(relx=.35, relwidth=.3, rely=.5, relheight=.5)

        isactiveplayer = receiver.uname == whitename
        possessive = "Your" if isactiveplayer else ("%s's"%whitename)
        turnlabel = "%s move." % possessive

        uicomponents[gamepath+'viewbuttons'][gameid] = viewer
        gamecontainer.place(relx=0, relwidth=1, y=len(uicomponents[gamepath+'frames'])*40, height=40)
    elif notification=="REJECTCHALLENGE":
        challengeid, = notifparams
        path = '/homeframe/outchallenges'
        containers = uicomponents[path+'frames']
        container = containers[challengeid]
        oldy = container.winfo_y()
        [containers[i].place(relx=0, relwidth=1, y=containers[i].winfo_y()-40, height=40) for i in containers if containers[i].winfo_y() > oldy] #bring up everything below
        container.place_forget()
        del containers[challengeid]
    elif notification=="NEWCHALLENGE":
        oppname, challengeid, colorselection = notifparams
        path = '/homeframe/inchallenges'
        containers = uicomponents[path+'frames']
        lowesty = 0 if len(containers) == 0 else max([containers[i].winfo_y() for i in containers]) #lowest on screen, not lowest number
        height = lowesty+40
        container = tk.Frame(uicomponents[path])
        label = tk.Label(container, text=writeout(False, oppname, colorselection))
        label.place(relx=0, relwidth=1, rely=0, relheight=.5)
        accepter = tk.Button(container, text="Accept", command=ResponseHandler(challengeid, colorselection=="Opponent", acceptchallenge))
        accepter.place(relx=.1, relwidth=.3, rely=.5, relheight=.5)
        rejecter = tk.Button(container, text="Reject", command=ResponseHandler(challengeid, False, rejectchallenge))
        rejecter.place(relx=.6, relwidth=.3, rely=.5, relheight=.5)
        uicomponents[path+'accepts'][challengeid] = accepter
        uicomponents[path+'rejects'][challengeid] = rejecter
        container.place(relx=0, relwidth=1, y=height, height=40)
        containers[challengeid] = container

def handleMove(params):
    if params[0] == "SUCCESS":
        gameid, annotation, strsequence, newposition, gamestatus, gamesubstatus = params[1:]
        movesequence = int(strsequence)
        if gameid == uicomponents['/gameframe/gameboard/gameid']:
            squares = newposition[:64]
            turn = newposition[69]
            ischeck = len(chesslogic.checkStatus(newposition, False)) != 0
            setboard(squares, turn)
            uicomponents['/gameframe/position'] = newposition
            if uicomponents['/gameframe/gameboard/color'] == 'W':
                labelpath = '/gameframe/movepanel/%slabel'%movesequence
                whitepath = '/gameframe/movepanel/%swhite'%movesequence
                if whitepath in uicomponents:
                    uicomponents[whitepath].place_forget()
                uicomponents[labelpath] = tk.Label(uicomponents['/gameframe/movepanel'], text="%s. "%movesequence)
                uicomponents[labelpath].place(relx=.1, relwidth=.25, height=30, y=30*movesequence+70)
                uicomponents[whitepath] = tk.Label(uicomponents['/gameframe/movepanel'], text=annotation)
                uicomponents[whitepath].place(relx=.35, relwidth=.25, height=30, y=30*movesequence+70)
            else:
                blackpath = '/gameframe/movepanel/%sblack'%movesequence
                if blackpath in uicomponents:
                    uicomponents[blackpath].place_forget()
                uicomponents[blackpath] = tk.Label(uicomponents['/gameframe/movepanel'], text=annotation)
                uicomponents[blackpath].place(relx=.6, relwidth=.25, height=30, y=30*movesequence+70)
            if gamestatus != "In Progress":
                '''basepath = '/gameframe/gameboard'
                for i in range(64):
                    square = chesslogic.indexToSquareName(i)
                    path = basepath + '/' + square
                    uicomponents[path].bind("<Button-1>", blankFunction)'''
                uicomponents['/gameframe/gameheader/turnstring'].set("%s by %s"%(gamestatus, gamesubstatus))

handlePromote = handleMove

def handleShowMoveHistory(params):
    if params[0] == "SUCCESS":
        gameid = params[1]
        movedata = params[2] if len(params) >= 3 else None
        if gameid == uicomponents['/gameframe/gameboard/gameid']:
            moves = [] if movedata==None else movedata.split()
            whitemoves = moves[::2]
            blackmoves = moves[1::2]
            for i in range(len(whitemoves)):
                seq = i+1
                labelpath = '/gameframe/movepanel/%slabel'%seq
                whitepath = '/gameframe/movepanel/%swhite'%seq
                blackpath = '/gameframe/movepanel/%sblack'%seq
                uicomponents[labelpath] = tk.Label(uicomponents['/gameframe/movepanel'], text="%s. "%seq)
                uicomponents[labelpath].place(relx=.1, relwidth=.25, height=30, y=30*i+100)
                uicomponents[whitepath] = tk.Label(uicomponents['/gameframe/movepanel'], text=whitemoves[i])
                uicomponents[whitepath].place(relx=.35, relwidth=.25, height=30, y=30*i+100)
                if len(blackmoves) > i:
                    uicomponents[blackpath] = tk.Label(uicomponents['/gameframe/movepanel'], text=blackmoves[i])
                    uicomponents[blackpath].place(relx=.6, relwidth=.25, height=30, y=30*i+100)

def handleResign(params):
    if params[0] == "SUCCESS":
        print(params)
        gamestatus, gamesubstatus = params[1:]
        uicomponents['/gameframe/gameheader/turnstring'].set("%s by %s"%(gamestatus, gamesubstatus))

def setboard(squares, turn):
    global checkSquare, promotionInProgress
    oldchecksquare = checkSquare
    fauxboard = ''.join(squares)+'-----'+turn
    ischeck = len(chesslogic.checkStatus(fauxboard, False)) != 0
    if ischeck:
        king = 'K' if turn == 'W' else 'k'
        checkindex = squares.index(king)
        checkSquare = chesslogic.indexToSquareName(checkindex)
    else:
        checkSquare = None
    unhighlight(checkSquare) if checkSquare != None else None
    unhighlight(oldchecksquare) if oldchecksquare != None else None
    for i in range(64):
        rawrow = i//8
        row = (rawrow)+1
        rawcol = i%8
        column = chr(rawcol+97)
        square = str(column)+str(row)
        canvas = uicomponents['/gameframe/gameboard/'+square]
        canvas.delete("all")
        if squares[i] in photoimages:
            canvas.create_image(0, 0, image=photoimages[squares[i]], anchor=tk.NW)
    promotesquare = chesslogic.promoteSquare(fauxboard)
    if promotesquare == None:
        promotionInProgress = False
        uicomponents['/gameframe/gamecontrol/promotion'].place_forget()
    elif uicomponents['/gameframe/gameboard/color']==turn:
        promotionInProgress = True
        uicomponents['/gameframe/gamecontrol/promotion'].place(relx=0, relwidth=1, y=350, height=300)
        execGen(uicomponents['/gameframe/gamecontrol/promotion/%s'%i].config(image=photoimages[imagecodes[i].__getattribute__('upper' if turn=='W' else 'lower')()]) for i in imagecodes)
    uicomponents['/gameframe/gameheader/turnstring'].set("%s to move."%("White" if turn=="W" else "Black"))

functions = {
    "LOGIN" : handleLogin,
    "NEWUSER" : handleLogin,
    "SHOWCHALLENGES" : handleShowChallenges,
    "SHOWACTIVEGAMES" : handleShowActiveGames,
    "NEWCHALLENGE" : handleNewChallenge,
    "RESPOND" : handleRespond,
    "GETGAMESTATE" : handleGetGameState,
    "NOTIFY" : handleNotify,
    "MOVE" : handleMove,
    "PROMOTE" : handlePromote,
    "SHOWMOVEHISTORY": handleShowMoveHistory,
    "RESIGN": handleResign
}

def execGen(gen):
    for i in gen:
        pass

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

def newuserscreen():
    uicomponents['/login'].pack_forget()
    uicomponents['/newuser'].pack()

def servercreateuser():
    global uicomponents, receiver
    uname = uicomponents['/newuser/uname'].get()
    pwd = uicomponents['/newuser/pwd'].get()
    pwdcfm = uicomponents['/newuser/pwdcfm'].get()
    if pwd == pwdcfm:
        receiver.sock.send(bytes('NEWUSER\r\n%s\r\n%s\r\n\r\n'%(uname, pwd), "UTF-8"))
    
def returntologin():
    uicomponents['/newuser'].pack_forget()
    uicomponents['/login'].pack()

def killcommand():
    global receiver, uicomponents
    print(bytes('KILLSERVER\r\n%s\r\n\r\n'%(receiver.sessionid), "UTF-8"))
    receiver.sock.send(bytes('KILLSERVER\r\n%s\r\n\r\n'%(receiver.sessionid), "UTF-8"))
    #receiver.sock.close()
    uicomponents['/'].destroy()
    exit()

def servershowchallenges():
    receiver.sock.send(bytes('SHOWCHALLENGES\r\nOUT\r\n%s\r\n\r\n'%(receiver.sessionid), "UTF-8"))
    #time.sleep(.5)
    receiver.sock.send(bytes('SHOWCHALLENGES\r\nIN\r\n%s\r\n\r\n'%(receiver.sessionid), "UTF-8"))
    #time.sleep(.5)

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

def serverresign():
    receiver.sock.send(bytes('RESIGN\r\n%s\r\n%s\r\n\r\n'%(uicomponents['/gameframe/gameboard/gameid'], receiver.sessionid), "UTF-8"))

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

def backtomenu():
    uicomponents['/gameframe'].place_forget()
    uicomponents['/homeframe'].place(relx=0, rely=0, relheight=1, relwidth=1)
    servershowchallenges()
    servershowactivegames()

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
uicomponents['/login/newuser'] = tk.Button(uicomponents['/login'], text="New User", command=newuserscreen)
uicomponents['/login/uname'].pack()
uicomponents['/login/pwd'].pack()
uicomponents['/login/auth'].pack()
uicomponents['/login/newuser'].pack()
uicomponents['/login'].pack()
uicomponents['/newuser'] = tk.Frame(uicomponents['/'])
uicomponents['/newuser/uname'] = tk.Entry(uicomponents['/newuser'])
uicomponents['/newuser/pwd'] = tk.Entry(uicomponents['/newuser'], show="*")
uicomponents['/newuser/pwdcfm'] = tk.Entry(uicomponents['/newuser'], show="*")
uicomponents['/newuser/new'] = tk.Button(uicomponents['/newuser'], text="Create User", command=servercreateuser)
uicomponents['/newuser/return'] = tk.Button(uicomponents['/newuser'], text="Return", command=returntologin)
uicomponents['/newuser/uname'].pack()
uicomponents['/newuser/pwd'].pack()
uicomponents['/newuser/pwdcfm'].pack()
uicomponents['/newuser/new'].pack()
uicomponents['/newuser/return'].pack()
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
uicomponents['/respondchooseframe/oppnamevar'] = tk.StringVar()
uicomponents['/respondchooseframe/opplabel'] = tk.Label(uicomponents['/respondchooseframe'], textvariable=uicomponents['/respondchooseframe/oppnamevar'])
uicomponents['/respondchooseframe/opplabel'].place(relx=.35, relwidth=.35, rely=0)
uicomponents['/respondchooseframe/decision'] = tk.Listbox(uicomponents['/respondchooseframe'])
uicomponents['/respondchooseframe/decision'].place(relx=.35, relwidth=.3, rely=.2)

[uicomponents['/respondchooseframe/decision'].insert(tk.END,i[0]) for i in challengeoptions if i[1]!="OPPONENT"]

uicomponents['/respondchooseframe/acceptchallenge'] = tk.Button(uicomponents['/respondchooseframe'], text="Confirm Selection", command=serveracceptandselect)
uicomponents['/respondchooseframe/acceptchallenge'].place(relx=.18, relwidth=.32, rely=.93, relheight=.04)
uicomponents['/respondchooseframe/cancel'] = tk.Button(uicomponents['/respondchooseframe'], text="Cancel", command=cancelresponse)
uicomponents['/respondchooseframe/cancel'].place(relx=.5, relwidth=.32, rely=.93, relheight=.04)

uicomponents['/gameframe'] = tk.Frame(uicomponents['/'])
uicomponents['/gameframe/gameheader'] = tk.Frame(uicomponents['/gameframe'])
uicomponents['/gameframe/gameheader/playersstring'] = tk.StringVar()
uicomponents['/gameframe/gameheader/turnstring'] = tk.StringVar()
uicomponents['/gameframe/gameheader/playerslabel'] = tk.Label(uicomponents['/gameframe/gameheader'], textvariable=uicomponents['/gameframe/gameheader/playersstring'])
uicomponents['/gameframe/gameheader/playerslabel'].place(relx=0, rely=0, relwidth=1, relheight=.5)
uicomponents['/gameframe/gameheader/turnlabel'] = tk.Label(uicomponents['/gameframe/gameheader'], textvariable=uicomponents['/gameframe/gameheader/turnstring'])
uicomponents['/gameframe/gameheader/turnlabel'].place(relx=0, rely=.5, relwidth=1, relheight=.5)
uicomponents['/gameframe/gameheader'].place(x=0, y=0, width=1400, height=100)
uicomponents['/gameframe/gamecontrol'] = tk.Frame(uicomponents['/gameframe'])
uicomponents['/gameframe/gamecontrol/back'] = tk.Button(uicomponents['/gameframe/gamecontrol'], text="Return to Menu", command=backtomenu)
uicomponents['/gameframe/gamecontrol/back'].place(x=75,y=0,width=135,height=40)
uicomponents['/gameframe/gamecontrol/offerdraw'] = tk.Button(uicomponents['/gameframe/gamecontrol'], text="Offer Draw")
uicomponents['/gameframe/gamecontrol/offerdraw'].place(x=75,y=50,width=135,height=40)
uicomponents['/gameframe/gamecontrol/claimdraw'] = tk.Button(uicomponents['/gameframe/gamecontrol'], text="Claim Draw")
uicomponents['/gameframe/gamecontrol/claimdraw'].place(x=75,y=100,width=135,height=40)
uicomponents['/gameframe/gamecontrol/resign'] = tk.Button(uicomponents['/gameframe/gamecontrol'], text="Resign", command=serverresign)
uicomponents['/gameframe/gamecontrol/resign'].place(x=75,y=150,width=135,height=40)
uicomponents['/gameframe/gamecontrol/claimdrawoptions'] = tk.Frame(uicomponents['/gameframe/gamecontrol'])
uicomponents['/gameframe/gamecontrol/claimdrawoptions/reason'] = tk.Listbox(uicomponents['/gameframe/gamecontrol/claimdrawoptions'])
uicomponents['/gameframe/gamecontrol/claimdrawoptions/reason'].place(relx=0,rely=0,relwidth=.5,relheight=1)
uicomponents['/gameframe/gamecontrol/claimdrawoptions/when'] = tk.Listbox(uicomponents['/gameframe/gamecontrol/claimdrawoptions'])
uicomponents['/gameframe/gamecontrol/claimdrawoptions/when'].place(relx=.5,rely=0,relwidth=.5,relheight=1)
uicomponents['/gameframe/gamecontrol/promotion'] = tk.Frame(uicomponents['/gameframe/gamecontrol'])
uicomponents['/gameframe/gamecontrol/promotion/queen'] = tk.Button(uicomponents['/gameframe/gamecontrol/promotion'], command=PromotionHandler("queen"))
uicomponents['/gameframe/gamecontrol/promotion/queen'].place(relx=0, relwidth=.5, rely=0, relheight=.5)
uicomponents['/gameframe/gamecontrol/promotion/knight'] = tk.Button(uicomponents['/gameframe/gamecontrol/promotion'], command=PromotionHandler("knight"))
uicomponents['/gameframe/gamecontrol/promotion/knight'].place(relx=.5, relwidth=.5, rely=0, relheight=.5)
uicomponents['/gameframe/gamecontrol/promotion/rook'] = tk.Button(uicomponents['/gameframe/gamecontrol/promotion'], command=PromotionHandler("rook"))
uicomponents['/gameframe/gamecontrol/promotion/rook'].place(relx=0, relwidth=.5, rely=.5, relheight=.5)
uicomponents['/gameframe/gamecontrol/promotion/bishop'] = tk.Button(uicomponents['/gameframe/gamecontrol/promotion'], command=PromotionHandler("bishop"))
uicomponents['/gameframe/gamecontrol/promotion/bishop'].place(relx=.5, relwidth=.5, rely=.5, relheight=.5)
uicomponents['/gameframe/gamecontrol'].place(x=0, y=100, width=300, height=800)
uicomponents['/gameframe/gameboard'] = tk.Frame(uicomponents['/gameframe'])
uicomponents['/gameframe/gameboard/squaresInitialized'] = False
uicomponents['/gameframe/gameboard'].place(x=300, width=800, height=800, y=100)
uicomponents['/gameframe/movepanel'] = tk.Frame(uicomponents['/gameframe'])
uicomponents['/gameframe/movepanel'].place(x=1100, width=300, height=1400, y=0)
packsquares()
photoimages = genphotoimages()
    
uicomponents['/'].geometry("1400x1000")
uicomponents['/'].mainloop()
receiver.close()
