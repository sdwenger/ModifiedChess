import serverlogic
import dblogic
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

def login(cursor, params):
    uname = params[0]
    pwd = params[1]
    if dblogic.auth(cursor, uname, pwd):
        sessionid = os.urandom(32).hex()
        serverlogic.pushsessionid(sessionid, uname)
        return b'SUCCESS\r\n'+bytes(uname, "UTF-8")+b'\r\n'+bytes(sessionid, "UTF-8")+b'\r\n\r\n'
    else:
        return b'FAILURE\r\nIncorrect username or password\r\n\r\n' #some kind of "authentication failure" error

def newuser(cursor, params):
    uname = params[0]
    pwd = params[1]
    retcode = dblogic.newUser(cursor, uname, pwd)
    if retcode == 0:
        return login(params)
    elif retcode == 1:
        return bytes('FAILURE\r\nUsername %s already in use.\r\n\r\n'%uname, "UTF-8")

def newchallenge(cursor, params):
    uname = serverlogic.getunamefromsession(params[2], True)
    oppname = params[0]
    if (uname == oppname):
        return b'FAILURE\r\nCannot challenge yourself\r\n\r\n'
    colorselection = params[1].title()
    oppcursor = dblogic.selectWithColumnsMatch(cursor, "Users", {"Name":oppname})
    oppdata = oppcursor.fetchall()
    if len(oppdata) == 0:
        return bytes("FAILURE\r\nNo such user %s"%oppname, "UTF-8")
    oppid = oppdata[0][0]
    usercursor = dblogic.selectWithColumnsMatch(cursor, "Users", {"Name":uname})
    userdata = usercursor.fetchall()
    uid = userdata[0][0]
    colorcursor = dblogic.selectWithColumnsMatch(cursor, "ColorSelections", {"Name":colorselection})
    colordata = colorcursor.fetchall()
    colorid = colordata[0][0]
    challengecursor = dblogic.insert(cursor, "Challenges", {"Challenger":uid, "Challengee":oppid, "ColorSelection":colorid})
    challengeid = challengecursor.lastrowid
    return bytes("SUCCESS\r\n%s\r\n\r\n"%challengeid, "UTF-8")

def showchallenges(cursor, params):
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
    uname = serverlogic.getunamefromsession(params[1], True)
    rescursor = dblogic.selectWithColumnsMatch(cursor, jointable, {"CurUser.Name":uname}, "Challenges.Id, OppUser.Name, ColorSelections.Name")
    data = rescursor.fetchall()
    if len(data) == 0:
        return bytes("%s\r\n\r\n"%params[0], "UTF-8")
    else:
        formatted = "\r\n".join([" ".join([str(j) for j in i]) for i in data])
        return bytes("%s\r\n%s\r\n\r\n"%(params[0],formatted), "UTF-8")

def showactivegames(cursor, params):
    jointable = '''Games INNER JOIN (SELECT Id, Name FROM Users) AS WhiteUser ON WhiteUser.Id=Games.White
                    INNER JOIN (SELECT Id, Name FROM Users) AS BlackUser ON BlackUser.Id=Games.Black
                    INNER JOIN GameStatuses ON GameStatuses.Id=Games.Status'''
    uname = serverlogic.getunamefromsession(params[0], True)
    whereprep = " WHERE (WhiteUser.Name=? OR BlackUser.Name=?) AND GameStatuses.Description='In Progress'"
    selectclause = "SELECT Games.Id, WhiteUser.Name, BlackUser.Name, Games.Turn, Games.AwaitingPromote FROM "
    rescursor = cursor.execute(selectclause + jointable + whereprep, (uname,uname))
    data = dblogic.unwrapCursor(rescursor)
    if len(data) == 0:
        return b'\r\n'
    else:
        formatted = "\r\n".join([" ".join([str(j) for j in i]) for i in data])
        return bytes("%s\r\n\r\n"%(formatted), "UTF-8")
    
def respond(cursor, params):
    challengeid = params[0]
    responsetype = params[1]
    if len(params) >= 4:
        sessionid = params[3]
        colorselection = params[2]
    else:
        sessionid = params[2]
    uname = serverlogic.getunamefromsession(sessionid, True)
    rescursor = dblogic.selectWithColumnsMatch(cursor, "Challenges INNER JOIN ColorSelections ON Challenges.ColorSelection=ColorSelections.Id", {"Challenges.Id":challengeid}, "Challenger, Challengee, ColorSelections.Name")
    challenge = dblogic.unwrapCursor(cursor, False)
    print(challenge)
    if challenge[2] == "White":
        blackindex = 1
    elif challenge[2] == "Black":
        blackindex = 0
    elif challenge[2] == "Random":
        blackindex = random.randrange(2)
    elif challenge[2] == "Opponent":
        if colorselection == "WHITE":
            blackindex = 0
        elif colorselection == "BLACK":
            blackindex = 1
        elif colorselection == "RANDOM":
            blackindex = random.randrange(2)
            
    whiteid, blackid = challenge[1-blackindex], challenge[blackindex]
    cursor.execute("DELETE FROM Challenges WHERE Id=?", (challengeid,))
    cursor.connection.commit()
    rescursor = dblogic.selectWithColumnsMatch(cursor, "GameSubstatuses", {"Description": "In progress"}, "Id, Superstatus")
    substatus = dblogic.unwrapCursor(cursor, False)
    gamecursor = dblogic.insert(cursor, "Games", {"White": whiteid, "Black": blackid, "Status": substatus[1], "Substatus": substatus[0], "Turn": 'W', "Position": STARTPOSITION, "AwaitingPromote": 0})
    return bytes("SUCCESS\r\n%s\r\n%s\r\n\r\n"%(challengeid, gamecursor.lastrowid), "UTF-8")
    
def getgamestate(cursor, params):
    gameid, sessionid = params
    uname = serverlogic.getunamefromsession(sessionid, True)
    usercursor = dblogic.selectWithColumnsMatch(cursor, "Users", {"Name":uname}, "Id")
    userdata = dblogic.unwrapCursor(usercursor, False, ["Id"])
    uid = userdata['Id']
    gamecursor = dblogic.selectGameWithPlayer(cursor, uid, {"Id":gameid}, "Position, White")
    gamedata = dblogic.unwrapCursor(gamecursor, False, ["Position", "White"])
    if (gamedata == None): #invalid game id for user
        return b"FAILURE\r\nCouldn't find game with specified Id\r\n\r\n"
    else:
        return bytes("SUCCESS\r\n%s\r\n%s\r\n\r\n"%(gamedata["Position"],'W' if uid==gamedata["White"] else 'B'), "UTF-8")

def move(cursor, params):
    gameid, initial, final, sessionid = params
    uname = serverlogic.getunamefromsession(sessionid, True)
    print("Attempting move: %s->%s"%(initial, final))
    return b"Failure\r\nNot yet implemented\r\n\r\n"

def killserver(cursor, params):
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
            response = cmdfunctions[cmd](dbconn.cursor(), params)
        else:
            response = b'Invalid Command\r\n\r\n'
    except Exception as e:
        response = bytes(str(e), "UTF-8")
        serverlogic.acceptConnections = False
        raise
    finally:
        dblogic.closeConnection()
        print("Data: "+str(data))
        print("Response: "+str(response))
        connhandler.conn.send(bytes(cmd, "UTF-8")+b'\r\n'+response)

serverlogic.main(handler)
