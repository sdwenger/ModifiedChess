import serverlogic
import dblogic
import chesslogic
import os
import datetime
import time
import random

STARTPOSITION = "RNBQKBNRPPPPPPPP--------------------------------pppppppprnbqkbnr++++-W"
'''
70 characters long
First 64 (0-63) characters are occupants of each square. In order: a1, b1, ... h1, a2, ... h8.
- means empty, capital means white piece, lowercase means black piece; p=pawn, r=rook, n=knight, b=bishop, q=queen, k=king
Next 4 (64-67) characters are castling rights. + means still there, - means it's not. In order are; white's kingside, white's queenside, black's kingside, black's queenside
Next character (68) is available en passant. If -, no en passant is available. If one is available, this will be the column of the pawn that can be en passanted. If capitalized, it means an en passant move is available in row 2 or 7.
Final character (69) is the turn. (W)hite or (B)lack
'''

def bytewrap(obj):
    if type(obj) == bytes:
        return obj
    else:
        return bytes(str(obj), "UTF-8")

def login(cursor, params, connhandler):
    uname = params[0]
    pwd = params[1]
    if dblogic.auth(cursor, uname, pwd):
        sessionid = os.urandom(32).hex()
        while not serverlogic.pushsessionid(sessionid, uname, connhandler): #loop in case of random collision
            pass
        return b'SUCCESS\r\n'+bytewrap(uname)+b'\r\n'+bytewrap(sessionid)+b'\r\n\r\n'
    else:
        return b'FAILURE\r\nIncorrect username or password\r\n\r\n' #some kind of "authentication failure" error

def newuser(cursor, params, connhandler):
    uname = params[0]
    pwd = params[1]
    retcode = dblogic.newUser(cursor, uname, pwd)
    if retcode == 0:
        return login(cursor, params, connhandler)
    elif retcode == 1:
        return bytewrap('FAILURE\r\nUsername %s already in use.\r\n\r\n'%uname)

def newchallenge(cursor, params, connhandler):
    uname = serverlogic.getunamefromsession(params[2], connhandler, True)
    oppname = params[0]
    if (uname == oppname):
        return b'FAILURE\r\nCannot challenge yourself\r\n\r\n'
    colorselection = params[1].title()
    oppcursor = dblogic.selectCommon(cursor, "Users", {"Name":oppname})
    oppdata = oppcursor.fetchall()
    if len(oppdata) == 0:
        return bytewrap("FAILURE\r\nNo such user %s"%oppname)
    oppid = oppdata[0][0]
    usercursor = dblogic.selectCommon(cursor, "Users", {"Name":uname})
    userdata = usercursor.fetchall()
    uid = userdata[0][0]
    colorcursor = dblogic.selectCommon(cursor, "ColorSelections", {"Name":colorselection})
    colordata = colorcursor.fetchall()
    colorid = colordata[0][0]
    challengecursor = dblogic.insert(cursor, "Challenges", {"Challenger":uid, "Challengee":oppid, "ColorSelection":colorid})
    challengeid = challengecursor.lastrowid
    serverlogic.notifyuser(oppname, bytewrap("NOTIFY\r\nNEWCHALLENGE\r\n%s\r\n%s\r\n%s\r\n\r\n"%(uname, challengeid, colorselection)))
    return bytewrap("SUCCESS\r\n%s\r\n\r\n"%challengeid)

def showchallenges(cursor, params, connhandler):
    if len(params) < 2:
        return (b'FAILURE\r\nInvalid command\r\n\r\n')
    jointemplate = '''Challenges INNER JOIN Users AS CurUser ON CurUser.Id=Challenges.%s
                       INNER JOIN Users AS OppUser ON Challenges.%s=OppUser.Id
                       INNER JOIN ColorSelections ON ColorSelections.Id=Challenges.ColorSelection'''
    curfield, oppfield = "Challengee", "Challenger"
    if params[0] == 'OUT':
        curfield, oppfield = oppfield, curfield
    elif params[0] != "IN":
        return (b'FAILURE\r\nInvalid command\r\n\r\n')
    jointable = jointemplate%(curfield, oppfield)
    uname = serverlogic.getunamefromsession(params[1], connhandler, True)
    print(uname)
    rescursor = dblogic.selectCommon(cursor, jointable, {"CurUser.Name":uname}, "Challenges.Id, OppUser.Name, ColorSelections.Name")
    data = rescursor.fetchall()
    if len(data) == 0:
        return bytewrap("%s\r\n\r\n"%params[0])
    else:
        formatted = "\r\n".join([" ".join([str(j) for j in i]) for i in data])
        return bytewrap("%s\r\n%s\r\n\r\n"%(params[0],formatted))

def showactivegames(cursor, params, connhandler):
    jointable = '''Games INNER JOIN (SELECT Id, Name FROM Users) AS WhiteUser ON WhiteUser.Id=Games.White
                    INNER JOIN (SELECT Id, Name FROM Users) AS BlackUser ON BlackUser.Id=Games.Black
                    INNER JOIN GameStatuses ON GameStatuses.Id=Games.Status'''
    uname = serverlogic.getunamefromsession(params[0], connhandler, True)
    whereprep = " WHERE (WhiteUser.Name=? OR BlackUser.Name=?) AND GameStatuses.Description='In Progress'"
    selectclause = "SELECT Games.Id, WhiteUser.Name, BlackUser.Name, SUBSTR(Games.Position,70), Games.AwaitingPromote FROM "
    rescursor = cursor.execute(selectclause + jointable + whereprep, (uname,uname))
    data = dblogic.unwrapCursor(rescursor)
    if len(data) == 0:
        return b'\r\n'
    else:
        formatted = "\r\n".join([" ".join([str(j) for j in i]) for i in data])
        return bytewrap("%s\r\n\r\n"%(formatted))
    
def respond(cursor, params, connhandler):
    challengeid = params[0]
    responsetype = params[1]
    if len(params) >= 4:
        sessionid = params[3]
        colorselection = params[2]
    else:
        sessionid = params[2]
    uname = serverlogic.getunamefromsession(sessionid, connhandler, True)
    rescursor = dblogic.selectCommon(cursor, "Challenges INNER JOIN ColorSelections ON Challenges.ColorSelection=ColorSelections.Id INNER JOIN (SELECT Id, Name FROM Users) AS ChallengerUser ON Challenges.Challenger=ChallengerUser.Id INNER JOIN (SELECT Id, Name FROM Users) AS ChallengeeUser ON Challenges.Challengee=ChallengeeUser.Id", {"Challenges.Id":challengeid}, "Challenger, Challengee, ColorSelections.Name, ChallengerUser.Name, ChallengeeUser.Name")
    challengedata = dblogic.unwrapCursor(rescursor, False)
    if responsetype == "ACCEPT":
        if uname != challengedata[4]:
           return bytewrap("Failure\r\nNot your challenge to accept.\r\n\r\n")
        if challengedata[2] == "White":
            blackindex = 1
        elif challengedata[2] == "Black":
            blackindex = 0
        elif challengedata[2] == "Random":
            blackindex = random.randrange(2)
        elif challengedata[2] == "Opponent":
            if colorselection == "WHITE":
                blackindex = 0
            elif colorselection == "BLACK":
                blackindex = 1
            elif colorselection == "RANDOM":
                blackindex = random.randrange(2)
                
        whiteid, blackid = challengedata[1-blackindex], challengedata[blackindex]
        whitename, blackname = (challengedata[challengedata.index(i)+3] for i in (whiteid, blackid))
        cursor.execute("DELETE FROM Challenges WHERE Id=?", (challengeid,))
        cursor.connection.commit()
        rescursor = dblogic.selectCommon(cursor, "GameSubstatuses", {"Description": "In Progress"}, "Id, Superstatus")
        substatus = dblogic.unwrapCursor(rescursor, False)
        gamecursor = dblogic.insert(cursor, "Games", {"White": whiteid, "Black": blackid, "Status": substatus[1], "Substatus": substatus[0], "Position": STARTPOSITION, "AwaitingPromote": 0})
        serverlogic.notifyuser(challengedata[3], bytewrap("NOTIFY\r\nACCEPTCHALLENGE\r\n%s\r\n%s\r\n%s\r\n%s\r\n\r\n"%(challengeid, gamecursor.lastrowid, whitename, blackname)))
        return bytewrap("SUCCESS\r\nACCEPT\r\n%s\r\n%s\r\n%s\r\n%s\r\n\r\n"%(challengeid, gamecursor.lastrowid, whitename, blackname))
    elif responsetype == "REJECT":
        if uname != challengedata[4]:
           return bytewrap("Failure\r\nNot your challenge to reject.\r\n\r\n")
        cursor.execute("DELETE FROM Challenges WHERE Id=?", (challengeid,))
        cursor.connection.commit()
        serverlogic.notifyuser(challengedata[3], bytewrap("NOTIFY\r\nREJECTCHALLENGE\r\n%s\r\n\r\n"%(challengeid)))
        return bytewrap("SUCCESS\r\nREJECT\r\n%s\r\n\r\n"%challengeid)
    elif responsetype == "RESCIND":
        if uname != challengedata[3]:
           return bytewrap("Failure\r\nNot your challenge to rescind.\r\n\r\n")
        cursor.execute("DELETE FROM Challenges WHERE Id=?", (challengeid,))
        cursor.connection.commit()
        serverlogic.notifyuser(challengedata[4], bytewrap("NOTIFY\r\nRESCINDCHALLENGE\r\n%s\r\n\r\n"%(challengeid)))
        return bytewrap("SUCCESS\r\nRESCIND\r\n%s\r\n\r\n"%challengeid)
    
def getgamestate(cursor, params, connhandler):
    gameid, sessionid = params
    uname = serverlogic.getunamefromsession(sessionid, connhandler, True)
    usercursor = dblogic.selectCommon(cursor, "Users", {"Name":uname}, "Id")
    userdata = dblogic.unwrapCursor(usercursor, False, ["Id"])
    uid = userdata['Id']
    gamecursor = dblogic.selectGameWithPlayer(cursor, uid, {"Games.Id":gameid}, {"(SELECT Id, Name FROM Users) AS BlackUser":"Games.Black=BlackUser.Id", "(SELECT Id, Name FROM Users) AS WhiteUser":"Games.White=WhiteUser.Id"}, "Position, White, Black, WhiteUser.Name, BlackUser.Name")
    gamedata = dblogic.unwrapCursor(gamecursor, False, ["Position", "WhiteId", "BlackId", "WhiteName", "BlackName"])
    if (gamedata == None): #invalid game id for user
        return b"FAILURE\r\nCouldn't find game with specified Id\r\n\r\n"
    else:
        return bytewrap("SUCCESS\r\n%s\r\n%s\r\n%s\r\n%s\r\n\r\n"%(gamedata["Position"],'W' if uid==gamedata["WhiteId"] else 'B', gamedata["WhiteName"], gamedata["BlackName"]))

def move(cursor, params, connhandler):
    gameid, initial, final, sessionid = params
    uname = serverlogic.getunamefromsession(sessionid, connhandler, True)
    usercursor = dblogic.selectCommon(cursor, "Users", {"Name":uname}, "Id")
    userdata = dblogic.unwrapCursor(usercursor, False, ["Id"])
    uid = userdata['Id']
    gamecursor = dblogic.selectGameWithPlayer(cursor, uid, {"Games.Id":gameid}, {"(SELECT Id, Name FROM Users) AS BlackUser":"Games.Black=BlackUser.Id", "(SELECT Id, Name FROM Users) AS WhiteUser":"Games.White=WhiteUser.Id", "GameStatuses":"GameStatuses.Id=Games.Status"}, "Position, White, Black, WhiteUser.Name, BlackUser.Name, DeferredClaim, ClaimIs3x, OfferRecipient, GameStatuses.Description")
    gamedata = dblogic.unwrapCursor(gamecursor, False, ["Position", "WhiteId", "BlackId", "WhiteName", "BlackName", "DeferredClaim", "ClaimIs3x", "OfferRecipient", "GameStatus"])
    if gamedata["GameStatus"] != "In Progress":
        return b"FAILURE\r\nGame is over.\r\n\r\n"
    position = gamedata['Position']
    if chesslogic.promoteSquare(position) != None:
        return b"FAILURE\r\nPawn must be promoted before any further moves\r\n\r\n"
    turn = position[69]
    if (turn == 'W') != (gamedata['WhiteId'] == uid):
        return b"FAILURE\r\nOut of turn play\r\n\r\n"
    if chesslogic.isValidMove(position, initial, final):
        newposition, captured, isEnPassant, mover = chesslogic.move(position, initial, final)
        gamestatus = chesslogic.terminalStatus(newposition, gamedata['WhiteId'], gamedata['BlackId'], gamedata["OfferRecipient"], gamedata["DeferredClaim"], bool(gamedata["ClaimIs3x"]), gameid, cursor)
        status, substatus = chesslogic.unwrapStatus(gamestatus, turn=='W')
        statuscursor = dblogic.selectCommon(cursor, "GameStatuses INNER JOIN GameSubstatuses ON GameStatuses.Id=GameSubstatuses.Superstatus", {"GameStatuses.Description":status, "GameSubstatuses.Description":substatus}, "GameStatuses.Id, GameSubstatuses.Id")
        statusdata = dblogic.unwrapCursor(statuscursor, False, ["StatusId","SubstatusId"])
        dblogic.updateCommon(cursor, "Games", {"Position": newposition, "Status":statusdata["StatusId"], "Substatus":statusdata["SubstatusId"]}, gameid)
        movecountcursor = dblogic.selectCommon(cursor, "Moves", {"Game": gameid, "Player": uid}, "COUNT(Id)")
        sequence = dblogic.unwrapCursor(movecountcursor, False)[0] + 1
        annotation = chesslogic.annotateMove(position, newposition, initial, final, mover, captured)
        dblogic.insert(cursor, "Moves", {"SqFrom": initial, "SqTo": final,
                                        "Captured": captured, "isEnPassant": int(isEnPassant),
                                        "Player": uid, "Piece": mover,
                                        "Game": gameid, "Sequence": sequence,
                                        "PosBefore": position, "PosAfter": newposition,
                                        "Annotated": annotation})
        oppname = gamedata['BlackName'] if turn == 'W' else gamedata['WhiteName']
        serverlogic.notifyuser(oppname, bytewrap("NOTIFY\r\nOPPMOVE\r\n%s\r\n%s\r\n%s\r\n%s\r\n%s\r\n%s\r\n\r\n"%(gameid, annotation, sequence, newposition, status, substatus)))
        return bytewrap("SUCCESS\r\n%s\r\n%s\r\n%s\r\n%s\r\n%s\r\n%s\r\n\r\n"%(gameid, annotation, sequence, newposition, status, substatus))
    return b"Failure\r\nNot yet implemented\r\n\r\n"

def promote(cursor, params, connhandler):
    gameid, promoteType, sessionid = params
    uname = serverlogic.getunamefromsession(sessionid, connhandler, True)
    usercursor = dblogic.selectCommon(cursor, "Users", {"Name":uname}, "Id")
    userdata = dblogic.unwrapCursor(usercursor, False, ["Id"])
    uid = userdata['Id']
    gamecursor = dblogic.selectGameWithPlayer(cursor, uid, {"Games.Id":gameid}, {"(SELECT Id, Name FROM Users) AS BlackUser":"Games.Black=BlackUser.Id", "(SELECT Id, Name FROM Users) AS WhiteUser":"Games.White=WhiteUser.Id"}, "Position, White, Black, WhiteUser.Name, BlackUser.Name")
    gamedata = dblogic.unwrapCursor(gamecursor, False, ["Position", "WhiteId", "BlackId", "WhiteName", "BlackName"])
    position = gamedata['Position']
    turn = position[69]
    if (turn == 'W') != (gamedata['WhiteId'] == uid):
        return b"FAILURE\r\nOut of turn play\r\n\r\n"
    promotesquare = chesslogic.promoteSquare(position)
    if promotesquare == None:
        print(gamedata)
        return b"FAILURE\r\nNo pending promotion\r\n\r\n"
    newposition = chesslogic.promote(position, promotesquare, promoteType)
    gamestatus = chesslogic.terminalStatus(newposition, gamedata['WhiteId'], gamedata['BlackId'], None, None, False, gameid, cursor)
    status, substatus = chesslogic.unwrapStatus(gamestatus, turn=='W')
    dblogic.updateCommon(cursor, "Games", {"Position": newposition}, gameid)
    movecountcursor = dblogic.selectCommon(cursor, "Moves", {"Game": gameid, "Player": uid}, "Id, Sequence, SqFrom, SqTo, Piece, Captured", suffix=" ORDER BY Sequence DESC LIMIT 1")
    movedata = dblogic.unwrapCursor(movecountcursor, False, ["Id","Sequence","Initial","Final","Piece","Captured"])
    moveid = movedata["Id"]
    dblogic.insert(cursor, "Promotions", {"Move": moveid,
                                          "Piece": promoteType.__getattribute__('upper' if turn=='W' else 'lower')(),
                                          "PosBefore": position,
                                          "PosAfter": newposition})
    newannotation = chesslogic.annotateMove(position, newposition, movedata['Initial'], movedata['Final'], movedata['Piece'], movedata['Captured'], promoteType)
    dblogic.updateCommon(cursor, "Moves", {"Annotated":newannotation}, moveid)
    oppname = gamedata['BlackName'] if turn == 'W' else gamedata['WhiteName']
    serverlogic.notifyuser(oppname, bytewrap("NOTIFY\r\nENEMYPROMOTE\r\n%s\r\n%s\r\n%s\r\n%s\r\n%s\r\n%s\r\n\r\n"%(gameid, newannotation, movedata["Sequence"], newposition, status, substatus)))
    return bytewrap("SUCCESS\r\n%s\r\n%s\r\n%s\r\n%s\r\n%s\r\n%s\r\n\r\n"%(gameid, newannotation, movedata["Sequence"], newposition, status, substatus))

def showmovehistory(cursor, params, connhandler):
    gameid, sessionid = params
    uname = serverlogic.getunamefromsession(sessionid, connhandler, True)
    usercursor = dblogic.selectCommon(cursor, "Users", {"Name":uname}, "Id")
    userdata = dblogic.unwrapCursor(usercursor, False, ["Id"])
    uid = userdata['Id']
    gamecursor = dblogic.selectGameWithPlayer(cursor, uid, {"Games.Id":gameid}, {}, "Id, White, Black")
    gamedata = dblogic.unwrapCursor(gamecursor, False, ['Id', 'White', 'Black'])
    blackid = gamedata['Black']
    if len(gamedata) == 0:
        return b"FAILURE\r\nNo such game or you are not part of it\r\n\r\n"
    movescursor = dblogic.selectCommon(cursor, "Moves LEFT OUTER JOIN Promotions ON Promotions.Move=Moves.Id", {"Moves.Game": gameid}, 'Moves.Id, Moves.SqFrom, Moves.SqTo, Moves.Captured, Moves.Piece, Moves.Sequence, Moves.PosBefore, Moves.PosAfter, Promotions.Piece, Moves.Player=%s AS Color, Moves.Annotated'%blackid, " ORDER BY Moves.Sequence, Color")
    movesdata = dblogic.unwrapCursor(movescursor, True, ['Id', 'From','To','Captured','Piece','Sequence','PosBefore','PosAfter','PromotedTo','Color','Annotation'])
    for i in movesdata:
        if not i['Annotation']:
            i['Annotation'] = chesslogic.annotateMove(i['PosBefore'],i['PosAfter'],i['From'],i['To'],i['Piece'],i['Captured'],i['PromotedTo'])
            dblogic.updateCommon(cursor, "Moves", {"Annotated": i["Annotation"]}, i["Id"])
    movestring = ' '.join([i['Annotation'] for i in movesdata])
    if movestring=='':
        return bytewrap("SUCCESS\r\n%s\r\n\r\n"%(gameid))
    return bytewrap("SUCCESS\r\n%s\r\n%s\r\n\r\n"%(gameid, movestring))

def resign(cursor, params, connhandler):
    gameid, sessionid = params
    uname = serverlogic.getunamefromsession(sessionid, connhandler, True)
    usercursor = dblogic.selectCommon(cursor, "Users", {"Name":uname}, "Id")
    userdata = dblogic.unwrapCursor(usercursor, False, ["Id"])
    uid = userdata['Id']
    gamecursor = dblogic.selectGameWithPlayer(cursor, uid, {"Games.Id":gameid}, {"(SELECT Id, Name FROM Users) AS BlackUser":"Games.Black=BlackUser.Id", "(SELECT Id, Name FROM Users) AS WhiteUser":"Games.White=WhiteUser.Id", "GameStatuses":"GameStatuses.Id=Games.Status"}, "Games.Id, Position, White, Black, WhiteUser.Name, BlackUser.Name, GameStatuses.Description")
    gamedata = dblogic.unwrapCursor(gamecursor, False, ['Id', 'Position', 'White', 'Black', 'WhiteName', 'BlackName', 'PrevStatus'])
    if gamedata["PrevStatus"] != "In Progress":
        return b"FAILURE\r\nGame is over\r\n\r\n"
    blackid = gamedata['Black']
    if len(gamedata) == 0:
        return b"FAILURE\r\nNo such game or you are not part of it\r\n\r\n"
    position = gamedata['Position']
    isblackplayer = blackid==uid
    textstatus = 'White win' if isblackplayer else 'Black win'
    isWinnerNonKing = (lambda x: (x!='K' and x.isupper())) if isblackplayer else (lambda x: (x!='k' and x.islower()))
    winningPieceGen = (i for i in position[:64] if isWinnerNonKing(i))
    try:
        next(winningPieceGen)
        textsubstatus = "Resign"
    except StopIteration:
        textstatus = "Draw"
        textsubstatus = "Autoaccept"
    statuscursor = dblogic.selectCommon(cursor, "GameStatuses INNER JOIN GameSubstatuses ON GameStatuses.Id=GameSubstatuses.Superstatus", {"GameStatuses.Description":textstatus, "GameSubstatuses.Description":textsubstatus}, "GameStatuses.Id, GameSubstatuses.Id")
    statusdata = dblogic.unwrapCursor(statuscursor, False, ["StatusId", "SubstatusId"])
    statusid, substatusid = statusdata["StatusId"], statusdata["SubstatusId"]
    dblogic.updateCommon(cursor, "Games", {"Status":statusid, "Substatus": substatusid}, gameid)
    oppname = gamedata['WhiteName'] if isblackplayer else gamedata['BlackName']
    serverlogic.notifyuser(oppname, bytewrap("NOTIFY\r\nSTATUSCHANGE\r\n%s\r\n%s\r\n%s\r\n\r\n"%(gameid, textstatus, textsubstatus)))
    return bytewrap("SUCCESS\r\n%s\r\n%s\r\n\r\n"%(textstatus, textsubstatus))
        
def drawgame(cursor, params, connhandler):
    gameid, sessionid, drawtype = params[:3]
    uname = serverlogic.getunamefromsession(sessionid, connhandler, True)
    usercursor = dblogic.selectCommon(cursor, "Users", {"Name":uname}, "Id")
    userdata = dblogic.unwrapCursor(usercursor, False, ["Id"])
    uid = userdata['Id']
    gamecursor = dblogic.selectGameWithPlayer(cursor, uid, {"Games.Id":gameid}, {"(SELECT Id, Name FROM Users) AS BlackUser":"Games.Black=BlackUser.Id", "(SELECT Id, Name FROM Users) AS WhiteUser":"Games.White=WhiteUser.Id", "GameStatuses":"GameStatuses.Id=Games.Status"}, "Games.Id, Position, White, Black, WhiteUser.Name, BlackUser.Name, GameStatuses.Description")
    gamedata = dblogic.unwrapCursor(gamecursor, False, ['Id', 'Position', 'White', 'Black', 'WhiteName', 'BlackName', 'PrevStatus'])
    if gamedata["PrevStatus"] != "In Progress":
        return b"FAILURE\r\nGame is over\r\n\r\n"
    if drawtype == "CLAIM":
        claimtype = params[3]
        claimtime = params[4]
        
def killserver(cursor, params, connhandler):
    return b"FAILURE\r\nYou really need to debug this function better before trying to use it.\r\n\r\n"
    if len(params) == 0:
        return b"FAILURE\r\n\r\n"
    sessionid = params[0]
    uname = serverlogic.getunamefromsession(sessionid)
    if uname == 'Sullivan':
        response = b"SUCCESS\r\n\r\n"
        print("Kill received")
        serverlogic.acceptConnections = False
    else:
        response = b"FAILURE\r\n\r\n"
    return response

cmdfunctions = {
    "LOGIN" : login,
    "NEWUSER" : newuser,
    "NEWCHALLENGE" : newchallenge,
    "SHOWCHALLENGES" : showchallenges,
    "SHOWACTIVEGAMES" : showactivegames,
    "RESPOND" : respond,
    "GETGAMESTATE" : getgamestate,
    "MOVE" : move,
    "PROMOTE" : promote,
    "SHOWMOVEHISTORY": showmovehistory,
    "RESIGN" : resign,
    "KILLSERVER" : killserver
}

def handler(connhandler, data):
    strdata = data[:-4].decode("UTF-8")
    lines = strdata.split("\r\n")
    cmd = lines[0].upper()
    params = lines[1:]
    try:
        dbconn = dblogic.connect()
        if cmd in cmdfunctions:
            response = cmdfunctions[cmd](dbconn.cursor(), params, connhandler)
        else:
            response = b'Invalid Command\r\n\r\n'
    except Exception as e:
        response = bytewrap(e)
        serverlogic.acceptConnections = False
        raise
    finally:
        dblogic.closeConnection()
        print("Data: "+str(data))
        print("Response: "+str(response))
        connhandler.conn.send(bytewrap(cmd)+b'\r\n'+response)

serverlogic.main(handler)
