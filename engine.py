import serverlogic
import dblogic
import os
import datetime
import time
import random

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
        return b'\r\n'
    else:
        formatted = "\r\n".join([" ".join([str(j) for j in i]) for i in data])
        return bytes("%s\r\n%s\r\n\r\n"%(params[0],formatted), "UTF-8")

def showactivegames(cursor, params):
    jointable = '''Games INNER JOIN Users AS WhiteUser ON WhiteUser.Id=Games.White
                    INNER JOIN Users AS BlackUser ON BlackUser.Id=Games.Black
                    INNER JOIN GameStatuses ON GameStatuses.Id=Games.Status'''
    uname = serverlogic.getunamefromsession(params[0], True)
    whereprep = " WHERE (WhiteUser.Name=? OR BlackUser.Name=?) AND GameStatuses.Description='In Progress'"
    selectclause = "SELECT * FROM "
    rescursor = cursor.execute(selectclause + jointable + whereprep, (uname,uname))
    data = rescursor.fetchall()
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
    rescursor = dblogic.selectWithColumnsMatch(cursor, "Challenges INNER JOIN ColorSelections ON Challenges.ColorSelection=ColorSelections.Id", {"Id":challengeid}, "Challenger, Challengee, ColorSelections.Name")
    challenge = rescursor.fetchall()[0]
    if challenge[2] == "WHITE":
        blackindex = 1
    elif challenge[2] == "BLACK":
        blackindex = 0
    elif challenge[2] == "RANDOM":
        blackindex = randrange(2)
    elif challenge[2] == "OPPONENT":
        if colorselection == "WHITE":
            blackindex = 0
        elif colorselection == "BLACK":
            blackindex = 1
        elif colorselection == "RANDOM":
            blackindex = randrange(2)
            
    whiteid, blackid = challenge[1-blackindex], challenge[blackindex]
    cursor.execute("DELETE FROM Challenges WHERE Id=?", (challengeid,))
    cursor.commit()
    rescursor = dblogic.selectWithColumnsMatch(cursor, "GameSubstatuses", {"Description": "In Progress"}, "Id, Superstatus")
    substatus = rescursor.fetchall()[0]
    dblogic.insert(cursor, "Games", {"White": whiteid, "Black": blackid, "Status": substatus[1], "Substatus": substatus[0], "Turn": 'W', "AwaitingPromote": 0})
    return b'SUCCESS\r\n\r\n'
    
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
    finally:
        dblogic.closeConnection()
    print("Data: "+str(data))
    print("Response: "+str(response))
    connhandler.conn.send(bytes(cmd, "UTF-8")+b'\r\n'+response)

serverlogic.main(handler)