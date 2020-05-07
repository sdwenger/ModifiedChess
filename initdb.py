import sqlite3
import sys
import dblogic
from collections import OrderedDict


metadatastrings = OrderedDict({
        "Users":"(Id INTEGER PRIMARY KEY AUTOINCREMENT, Name VARCHAR(40) UNIQUE, HashPass BLOB, Salt BLOB)",
        "ColorSelections":"(Id INTEGER PRIMARY KEY AUTOINCREMENT, Name VARCHAR(10))",
        "GameStatuses":"(Id INTEGER PRIMARY KEY AUTOINCREMENT, Description VARCHAR(20), WhiteHalfPoints INT, BlackHalfPOints INT)",
        "GameSubstatuses":"(Id INTEGER PRIMARY KEY AUTOINCREMENT, Description VARCHAR(40), Superstatus INTEGER, FOREIGN KEY(Superstatus) REFERENCES GameStatuses(Id))"
        })
datastrings = OrderedDict({
        "Challenges":"(Id INTEGER PRIMARY KEY AUTOINCREMENT, Challenger INTEGER, Challengee INTEGER, ColorSelection INTEGER, FOREIGN KEY(Challenger) REFERENCES Users(Id), FOREIGN KEY(Challengee) REFERENCES Users(Id),  FOREIGN KEY(ColorSelection) REFERENCES ColorSelections(Id))",
        "Games":"(Id INTEGER PRIMARY KEY AUTOINCREMENT, White INTEGER, Black INTEGER, Status INTEGER, Substatus INTEGER, Position CHAR(70), LiveClaim BIT(1), ClaimIsDeferred BIT(1), ClaimIs3x BIT(1), WhiteClaimFaults INTEGER, BlackClaimFaults INTEGER, OfferRecipient INTEGER, FOREIGN KEY(Black) REFERENCES Users(Id), FOREIGN KEY(White) REFERENCES Users(Id), FOREIGN KEY (Status) REFERENCES GameStatuses(Id), FOREIGN KEY (Substatus) REFERENCES GameSubstatuses(Id), FOREIGN KEY(OfferRecipient) REFERENCES Users(Id))",
        "Moves":"(Id INTEGER PRIMARY KEY AUTOINCREMENT, SqFrom CHAR(2), SqTo CHAR(2), Captured CHAR(1), isEnPassant BIT(1), Player CHAR(1), Piece CHAR(1), Sequence INT, Game INTEGER, PosBefore CHAR(70), PosAfter CHAR(70), Annotated CHAR(7), FOREIGN KEY(Game) REFERENCES Games(Id))",
        "Promotions":"(Id INTEGER PRIMARY KEY AUTOINCREMENT, Move INTEGER, Piece CHAR(1), PosBefore CHAR(70), PosAfter CHAR(70), FOREIGN KEY(Move) REFERENCES Moves(Id))"
        })

def connect():
    return sqlite3.connect("chessdata.db")

def retrievedata(includemetadata, conn=None):
    if conn == None:
        conn = connect()
    tables = list(datastrings) + (list(metadatastrings) if includemetadata else [])
    data = {}
    cursor = conn.cursor()
    for i in tables:
        cols = dblogic.getColsFromTable(cursor, i)
        rowscursor = dblogic.selectCommon(cursor, i, {})
        alldata = dblogic.unwrapCursor(rowscursor, True, cols)
        data[i] = alldata
    return data
        
def replacedata(includemetadata, data, conn=None):
    if conn == None:
        conn = connect()
    tables = list(datastrings) + (list(metadatastrings) if includemetadata else [])
    cursor = conn.cursor()
    for i in tables:
        rows = data[i]
        if len(rows) == 0:
            continue
        oldcols = list(rows[0])
        newcols = dblogic.getColsFromTable(cursor, i)
        [dblogic.insert(cursor, i, j) for j in rows]

def dropAll(includemetadata, conn=None):
    if conn == None:
        conn = connect()
    [conn.execute("DROP TABLE IF EXISTS %s"%i) for i in reversed(datastrings)]
    if includemetadata:
        [conn.execute("DROP TABLE IF EXISTS %s"%i) for i in reversed(metadatastrings)]

def initTables(includemetadata, conn=None):
    if conn == None:
        conn = connect()
    if includemetadata:
        [conn.execute("CREATE TABLE IF NOT EXISTS %s %s"%(i, metadatastrings[i])) for i in reversed(metadatastrings)]
    [conn.execute("CREATE TABLE IF NOT EXISTS %s %s"%(i, datastrings[i])) for i in reversed(datastrings)]
    
def initMetadata(conn):
    commands = [
        "INSERT INTO GameStatuses (Description, WhiteHalfPoints, BlackHalfPoints) VALUES ('In Progress', 0, 0)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('In Progress', %s)",
        "INSERT INTO GameStatuses (Description, WhiteHalfPoints, BlackHalfPoints) VALUES ('White win', 2, 0)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('Checkmate', %s)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('Resign', %s)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('Penalty', %s)",
        "INSERT INTO GameStatuses (Description, WhiteHalfPoints, BlackHalfPoints) VALUES ('Black win', 0, 2)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('Checkmate', %s)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('Resign', %s)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('Penalty', %s)",
        "INSERT INTO GameStatuses (Description, WhiteHalfPoints, BlackHalfPoints) VALUES ('Draw', 1, 1)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('Stalemate', %s)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('Insufficient Material', %s)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('3 Fold Rep', %s)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('50 Move', %s)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('Agreement', %s)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('Autoaccept', %s)", #occurs when a player claims or offers a draw while their opponent only has a king
        "INSERT INTO ColorSelections (Name) VALUES ('White')",
        "INSERT INTO ColorSelections (Name) VALUES ('Black')",
        "INSERT INTO ColorSelections (Name) VALUES ('Random')",
        "INSERT INTO ColorSelections (Name) VALUES ('Opponent')", #lets challengee pick the color
    ];
    rowid = 0
    for i in commands:
        if i.startswith("INSERT INTO GameStatuses "):
            query = conn.execute(i)
            rowid = query.lastrowid
        elif i.startswith("INSERT INTO GameSubstatuses"):
            query = conn.execute(i%rowid)
        else:
            query = conn.execute(i)
            
def reset(includemetadata, firstrun, conn=None):
    if (conn==None):
        conn = connect()
    try:
        if not firstrun:
            olddata = retrievedata(includemetadata)
            dropAll(includemetadata, conn)
        initTables(includemetadata or firstrun, conn)
        if firstrun:
            initMetadata(conn)
        else:
            replacedata(includemetadata, olddata)
        conn.commit()
    except Exception as e:
        print(e)
        conn.rollback()
    
if __name__=='__main__':
    dblogic.autoCommit = False
    includemetadata = '-m' in sys.argv
    firstrun = '-f' in sys.argv
    reset(includemetadata, firstrun)
