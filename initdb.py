import sqlite3

def connect():
    return sqlite3.connect("chessdata.db")

def dropAll(conn=None):
    if conn == None:
        conn = connect()
    commands = [
        "DROP TABLE IF EXISTS Moves",
        "DROP TABLE IF EXISTS Games",
        "DROP TABLE IF EXISTS Challenges",
        "DROP TABLE IF EXISTS GameSubstatuses",
        "DROP TABLE IF EXISTS GameStatuses",
        "DROP TABLE IF EXISTS ColorSelections",
        "DROP TABLE IF EXISTS Users"
    ];
    [(conn.execute(i) and None) for i in commands][0]

def initTables(conn=None):
    if conn == None:
        conn = connect()
    commands = [
        "CREATE TABLE IF NOT EXISTS Users (Id INTEGER PRIMARY KEY AUTOINCREMENT, Name VARCHAR(40) UNIQUE, HashPass BLOB, Salt BLOB)",
        "CREATE TABLE IF NOT EXISTS ColorSelections (Id INTEGER PRIMARY KEY AUTOINCREMENT, Name VARCHAR(10))",
        "CREATE TABLE IF NOT EXISTS GameStatuses (Id INTEGER PRIMARY KEY AUTOINCREMENT, Description VARCHAR(20), WhiteHalfPoints INT, BlackHalfPOints INT)",
        "CREATE TABLE IF NOT EXISTS GameSubstatuses (Id INTEGER PRIMARY KEY AUTOINCREMENT, Description VARCHAR(40), Superstatus INTEGER, FOREIGN KEY(Superstatus) REFERENCES GameStatuses(Id))",
        "CREATE TABLE IF NOT EXISTS Challenges (Id INTEGER PRIMARY KEY AUTOINCREMENT, Challenger INTEGER, Challengee INTEGER, ColorSelection INTEGER, FOREIGN KEY(Challenger) REFERENCES Users(Id), FOREIGN KEY(Challengee) REFERENCES Users(Id),  FOREIGN KEY(ColorSelection) REFERENCES ColorSelections(Id))",
        "CREATE TABLE IF NOT EXISTS Games (Id INTEGER PRIMARY KEY AUTOINCREMENT, White INTEGER, Black INTEGER, Status INTEGER, Substatus INTEGER, Turn CHAR(1), AwaitingPromote BIT(1), FOREIGN KEY(Black) REFERENCES Users(Id), FOREIGN KEY(White) REFERENCES Users(Id), FOREIGN KEY (Status) REFERENCES GameStatuses(Id), FOREIGN KEY (Substatus) REFERENCES GameSubstatuses(Id))",
        "CREATE TABLE IF NOT EXISTS Moves (Id INTEGER PRIMARY KEY AUTOINCREMENT, SqFrom CHAR(2), SqTo CHAR(2), Player CHAR(1), Piece CHAR(1), Sequence INT, Game INTEGER, PosBefore CHAR(70), PosAfter CHAR(70),  FOREIGN KEY(Game) REFERENCES Games(Id))"
    ];
    [(conn.execute(i) and None) for i in commands][0]
    initMetadata(conn)
    
def initMetadata(conn):
    commands = [
        "INSERT INTO GameStatuses (Description, WhiteHalfPoints, BlackHalfPoints) VALUES ('In Progress', 0, 0)",
        "INSERT INTO GameSubstatuses (Description, Superstatus) VALUES ('In progress', %s)",
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
            
def reset(conn=None):
    if (conn==None):
        conn = connect()
    dropAll(conn)
    initTables(conn)
    conn.commit()
    
if __name__=='__main__':
    import sys
    if '-r' in sys.argv:
        reset()
    else:
        initTables()