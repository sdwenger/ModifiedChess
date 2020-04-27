import sqlite3
import os
import hashlib

baseInsertQuery = "INSERT INTO %s (%s) VALUES (%s)"
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
    res = selectWithColumnsMatch(cursor, "Users", {"Name":uname}).fetchall()
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
    
def selectWithColumnsMatch(cursor, table, data, getcols='*'):
    cols = [i for i in data] #force order matching
    colmatchstrings = [i+'=?' for i in cols]
    columnstring = ' AND '.join(colmatchstrings)
    valtuple = tuple(data[i] for i in cols)
    selectprep = baseSelectQuery%(getcols, table, columnstring)
    if len(data) == 0:
        selectprep = selectprep.replace(' WHERE ', '')
    cursor.execute(selectprep, valtuple)
    return cursor