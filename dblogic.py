import sqlite3
import os
import hashlib
import itertools

baseInsertQuery = "INSERT INTO %s (%s) VALUES (%s)"
baseUpdateQuery = "UPDATE %s SET %s WHERE %s"
baseSelectQuery = "SELECT %s FROM %s WHERE %s"

conn = None

def connect():
    global conn
    if conn == None:
        conn = sqlite3.connect("chessdata.db")
    return conn

def closeConnection():
    global conn
    conn.close()
    conn = None

def byteAdd(arr1, arr2):
    res = []
    for i in range(min(len(arr1),len(arr2))):
        res.append((arr1[i] + arr2[i]) % 256)
    return bytes(res)

def newUser(cursor, uname, pwd):
    salt = os.urandom(32)
    hashpass = pwdSaltToHash(pwd, salt)
    try:
        insert(cursor, "Users", {
            "Name": uname,
            "HashPass": hashpass,
            "Salt": salt
        })
        return 0
    except sqlite3.IntegrityError as e:
        if str(e) == 'UNIQUE constraint failed: Users.Name':
            return 1
        else:
            raise

def auth(cursor, uname, pwd):
    res = selectCommon(cursor, "Users", {"Name":uname}).fetchall()
    if (len(res) == 0):
        return False
    usertuple = res[0]
    hashpass = pwdSaltToHash(pwd, usertuple[3])
    return hashpass == usertuple[2]

def pwdSaltToHash(pwd, salt):
    hashpass = hashlib.sha256(bytes(pwd, "UTF-8")+salt).digest()
    for i in range(1024):
        bytesum = byteAdd(hashpass, salt)
        hashpass = hashlib.sha256(bytesum).digest()
    return hashpass

def insert(cursor, table, data):
    cols = [i for i in data] #force order matching
    columnstring = ', '.join(cols)
    prepvalues = ', '.join(['?']*len(data))
    valtuple = tuple(data[i] for i in cols)
    insertprep = baseInsertQuery%(table, columnstring, prepvalues)
    cursor.execute(insertprep, valtuple)
    cursor.connection.commit()
    return cursor
    
def updateCommon(cursor, table, data, rowid):
    if len(data) == 0:
        return cursor
    cols = [i for i in data] #force order matching
    setstring = ', '.join("%s=?"%i for i in cols)
    wherestring = " Id=?"
    valtuple = tuple(data[i] for i in cols) + (rowid,)
    updateprep = baseUpdateQuery%(table, setstring, wherestring)
    cursor.execute(updateprep, valtuple)
    cursor.connection.commit()
    return cursor

def selectCommon(cursor, table, data, getcols='*'):
    cols = [i for i in data] #force order matching
    colmatchstrings = [i+'=?' for i in cols]
    columnstring = ' AND '.join(colmatchstrings)
    valtuple = tuple(data[i] for i in cols)
    selectprep = baseSelectQuery%(getcols, table, columnstring)
    if len(data) == 0:
        selectprep = selectprep.replace(' WHERE ', '')
    cursor.execute(selectprep, valtuple)
    return cursor

def selectGameWithPlayer(cursor, playerid, otherdata, jointables={}, getcols='*'):
    if type(playerid) != list:
        playerid = [playerid]
    othercols = [i for i in otherdata] #force order matching
    othercolmatchstrings = [i+'=?' for i in othercols]
    othercolumnstring = ' AND '.join(othercolmatchstrings)
    playerstring = ' OR '.join(["White=? OR Black=?"]*len(playerid))
    if len(otherdata) == 0:
        totalcolumnstring = "(%s)"%(othercolumnstring, playerstring)
        valtuple = tuple(sum(((i,i) for i in playerid), ()))
    else:
        totalcolumnstring = "%s AND (%s)"%(othercolumnstring, playerstring)
        valtuple = tuple(otherdata[i] for i in othercols) + tuple(sum(((i,i) for i in playerid), ()))
    tablestring = "Games"
    joinstring = ' INNER JOIN '.join(["%s ON %s"%(i, jointables[i]) for i in jointables])
    if len(joinstring) != '':
        tablestring += " INNER JOIN "+joinstring
    selectprep = baseSelectQuery%(getcols, tablestring, totalcolumnstring)
    cursor.execute(selectprep, valtuple)
    return cursor

def unwrapCursor(cursor, asList=True, keyset=None):
    data = cursor.fetchall()
    if len(data) == 0:
        return [] if asList else None
    if keyset != None:
        if len(data[0]) != len(keyset):
            raise ValueError("Keyset must be the same length as set of returned columns")
        formatted = [{j:k for j,k in itertools.zip_longest(keyset,i)} for i in data]
    else:
        formatted = data
    return formatted if asList else formatted[0]
