import math

NORMAL, CHECK, DOUBLECHECK, STALEMATE, CHECKMATE = range(5)
indeces = set(range(1,9))
directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
knightMoves = [(-2, -1), (-2, 1), (2, -1), (2, 1), (-1, -2), (1, -2), (-1, 2), (1, 2)]

def isValidMove(position, initial, final):
    pass

def pieceValidMoves(position, square):
    turn = position[-1]
    x,y = squareNameToXY(square)
    index = xyToIndex(x,y)
    piece = position[index]
    if piece == '-':
        return None #blank square
    if (turn=="W") != (piece.isupper()):
        return None #out of turn piece
    piecetype = piece.lower()
    check = checkStatus(position)
    if check in [CHECKMATE, STALEMATE]:
        return [[],[]]
    elif check == DOUBLECHECK:
        if piecetype != 'k':
            return [[],[]]
    elif check == CHECK:
        pass
    else:
        if piece == 'P':
            forward = []
            firstindex, secondindex, thirdindex = xyToIndex(x,y+1), xyToIndex(x,y+2), xyToIndex(x,y+3)
            if position[firstindex] == '-':
                forward.append(xyToSquareName(x,y+1))
                if y <= 2 and position[secondindex] == '-':
                    forward.append(xyToSquareName(x,y+2))
                    if y <= 1 and position[secondindex] == '-':
                        forward.append(xyToSquareName(x,y+3))
            attack = []
            if x != 1:
                leftindex = xyToIndex(x-1,y+1)
                if isEnemy(piece, position[leftindex]):
                    attack.append(leftindex)
            if x != 8:
                right = xyToIndex(x+1,y+1)
                if isEnemy(piece, position[rightindex]):
                    attack.append(leftindex)
            enpassant = position[68]
            special = []
            if enpassant != '-':
                enpassantlong = enpassant.isupper()
                enpassantcol = enpassant.lower()
                enpassantcolnum = ord(enpassantcol)-96
                correctColumn = math.fabs(enpassantcolnum-x) == 1
                correctRow = (y==5) or (y==6 and enpassantlong)
                if correctColumn and correctRow:
                    enpassantsquare = xyToSquareName(enpassantcolnum,y+1)
                    special.append(enpassantsquare)
                    
            return [[],forward+attack] if y == 7 else [forward+attack,special]
        elif piece == 'p':
            forward = []
            firstindex, secondindex, thirdindex = xyToIndex(x,y-1), xyToIndex(x,y-2), xyToIndex(x,y-3)
            if position[firstindex] == '-':
                forward.append(xyToSquareName(x,y+1))
                if y >= 7 and position[secondindex] == '-':
                    forward.append(xyToSquareName(x,y+2))
                    if y >= 8 and position[secondindex] == '-':
                        forward.append(xyToSquareName(x,y+3))
            attack = []
            if x != 1:
                leftindex = xyToIndex(x-1,y-1)
                if isEnemy(piece, position[leftindex]):
                    attack.append(leftindex)
            if x != 8:
                right = xyToIndex(x+1,y-1)
                if isEnemy(piece, position[rightindex]):
                    attack.append(leftindex)
            enpassant = position[68]
            special = []
            if enpassant != '-':
                enpassantlong = enpassant.isupper()
                enpassantcol = enpassant.lower()
                enpassantcolnum = ord(enpassantcol)-96
                correctColumn = math.fabs(enpassantcolnum-x) == 1
                correctRow = (y==4) or (y==3 and enpassantlong)
                if correctColumn and correctRow:
                    enpassantsquare = xyToSquareName(enpassantcolnum,y+1)
                    special.append(enpassantsquare)
                    
    return [["e1"],["e8"]]
'''
returns NORMAL, CHECK, STALEMATE, or CHECKMATE
if checkTerminalConditions is False, only returns NORMAL or CHECK
    checkTerminalConditions=False is used for validating that moves keep the king clear
'''
def checkStatus(position, checkTerminalConditions=True):
    turn = position[-1]
    target = "K" if turn=="W" else "k"
    enemyPawnAttackDirection = 1 if turn=="W" else -1 #opposite what seems intuitive. This is because we're checking the king for enemy pawns- this means checking backwards
    index = position.index(target)
    kingx, kingy = indexToXY(index)
    attacks = []
    for dx,dy in knightMoves:
        knightx, knighty = kingx + dx, kingy + dy
        if set([knightx, knighty]).issubset(indeces):
            knight = position[xyToIndex(knightx, knighty)]
            if isEnemy(target, knight) and knight.lower() == 'n':
                attacks.append(xyToSquareName(knightx, knighty))
    for i in directions:
        if len(attacks) == 2: #no use in further checks after finding double check
            break
        linedPiece, distance = findFirstOnLine(position, kingx, kingy, i[0], i[1])
        if linedPiece == "-":
            continue
        if isEnemy(target, linedPiece):
            piecetype = linedPiece.lower()
            enemySquare = xyToSquareName(kingx+i[0]*distance, kingy+i[1]*distance)
            if piecetype == 'q' or \
                    (piecetype == 'k' and distance==1) or \
                    (piecetype == 'r' and (0 in i)) or \
                    (piecetype == 'b' and not (0 in i)) or \
                    (piecetype == 'p' and distance==1 and not (0 in i) and i[1] == enemyPawnAttackDirection):
                attacks.append(enemySquare)
    if not checkTerminalConditions:
        return NORMAL if check==0 else CHECK if check==1 else DOUBLECHECK

def isEnemy(target, attacker):
    if (target=='-' or attacker=='-'):
        return False
    return target.isupper() != attacker.isupper()

def findFirstOnLine(position, startx, starty, dx, dy):
    if dx==0 and dy==0:
        raise ValueError("Please set dx or dy")
    curx = startx + dx
    cury = starty + dy
    occupant = "-"
    distance = 0
    while occupant=="-" and set([curx, cury]).issubset(indeces):
        distance += 1
        occupant = position[xyToIndex(curx, cury)]
        curx += dx
        cury += dy
    return (occupant, distance)

def clearLine(position, x1, y1, x2, y2):
    dx, dy = (0 if x1==x2 else -1 if x1 < x2 else 1, 0 if y1==y2 else -1 if y1 < y2 else 1)
    if len(set([math.fabs(x1-x2), math.fabs(y1-y2), 0])) > 2:
        raise ValueError("Line checking requires orthogonal or diagonal direction")
    curx, cury = x1+dx, y1+dy
    while (curx,cury) != (x2,y2):
        if position[xyToIndex(curx,cury)] != "-":
            return False
        curx += dx
        cury += dy
    return True

def xyToIndex(x, y):
    return 8*y+x-9

def indexToXY(index):
    y = index//8+1
    x = index%8+1
    return (x,y)

def squareNameToXY(squareName):
    x = ord(squareName[0])-96
    y = int(squareName[1])
    return (x,y)

def xyToSquareName(x,y):
    return chr(x+96)+str(y)
