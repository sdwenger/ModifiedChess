import math
import itertools

NORMAL, CHECK, DOUBLECHECK, STALEMATE, CHECKMATE = range(5)
indeces = set(range(1,9))
directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
knightMoves = [(-2, -1), (-2, 1), (2, -1), (2, 1), (-1, -2), (1, -2), (-1, 2), (1, 2)]

#move is already assumed to be valid; input here is screened through isValidMove
def move(position, initial, final):
    data = list(position)
    turn = data[69]
    initialIndex = squareNameToIndex(initial)
    finalIndex = squareNameToIndex(final)
    mover = data[initialIndex]
    target = data[finalIndex]
    data[finalIndex] = mover
    if isAlly(mover, target):
        data[initialIndex] = target
    else:
        data[initialIndex] = '-'
    #castle rights
    squares = set([initial, final])
    castledata = (("e1","h1",True,True),("e1","a1",False,True),("e8","h8",True,False),("e8","a8",False,False))
    for i in castledata:
        if set((i[0],i[1])) in squares:
            data[castleRightIndex(i[2], i[3])] = '-'
    #begin- remove en passanted enemy pawn if applicable
    xi, yi = indexToXY(initialIndex)
    xf, yf = indexToXY(finalIndex)
    if mover.lower() == 'p' and xi != xf and target == '-': #is en passant
        shortrow = 5 if mover.isupper() else 4
        longrow = 6 if mover.isupper() else 3
        longindex = xyToIndex(xf, longrow)
        index = longindex if position[longindex] != '-' else xyToIndex(xf, shortrow)
        data[index] = '-'
    #end- remove en passanted enemy pawn if applicable
    
    #begin- calculating if OPPONENT will have en passant available
    enpassant = '-'
    if mover.lower() == 'p':
        xi,yi = indexToXY(initialIndex)
        xf,yf = indexToXY(finalIndex)
        shortrow = 4 if mover.isupper() else 5
        longrow = 3 if mover.isupper() else 6
        step = math.fabs(yf-yi)
        if step >= 2:
            validlong = False
            if yi in (1,8):
                cols = [i for i in (xi-1,xi+1) if i in range(1,9)]
                candidates = [xyToIndex(i,longrow) for i in cols]
                pawnindeces = [i for i in candidates if (position[i].lower()=='p' and isEnemy(mover, position[i]))]
                testenpassant = data[:]
                testenpassant[68] = chr(xi+64)
                testenpassant[69] = 'B' if turn=='W' else 'W'
                validlong = any(enpassantischecksafe(''.join(testenpassant), indexToSquareName(i), xyToSquareName(xi,longrow), xyToSquareName(xf,yf)) for i in pawnindeces)
                enpassant = chr(xi+64)
            if not validlong:
                cols = [i for i in (xi-1,xi+1) if i in range(1,9)]
                candidates = [xyToIndex(i,shortrow) for i in cols]
                pawnindeces = [i for i in candidates if (position[i].lower()=='p' and isEnemy(mover, position[i]))]
                testenpassant = data[:]
                testenpassant[68] = chr(xi+96)
                testenpassant[69] = 'B' if turn=='W' else 'W'
                validshort = any(enpassantischecksafe(''.join(testenpassant), indexToSquareName(i), xyToSquareName(xi,shortrow), xyToSquareName(xf,yf)) for i in pawnindeces)
                enpassant = chr(xi+96)
    #end- calculating if OPPONENT will have en passant available
    data[68] = enpassant
    data[69] = 'B' if turn=='W' else 'W'
    return ''.join(data)

def enpassantischecksafe(position, initial, final, captured):
    data = list(position)
    indexi = squareNameToIndex(initial)
    indexf = squareNameToIndex(final)
    indexc = squareNameToIndex(captured)
    mover = data[indexi]
    data[indexc] = '-'
    data[indexi] = '-'
    data[indexf] = mover
    return len(checkStatus(''.join(data), False)) == 0

def isValidMove(position, initial, final, knownSafe=False):
    if initial == final:
        return False #non-move
    xi, yi = squareNameToXY(initial)
    xf, yf = squareNameToXY(final)
    dx, dy = xf-xi,yf-yi
    mover = position[xyToIndex(xi,yi)]
    turn = position[69]
    if mover == '-':
        return False #blank start
    if mover.isupper() != (turn=='W'):
        return False #out of turn move
    movetype = mover.lower()
    receiver = position[xyToIndex(xf,yf)]
    if isAlly(mover, receiver) and movetype != 'k':
        return False #only king can swap
    if movetype == 'n':
        return (dx,dy) in knightMoves
    deltas = set( (int(math.fabs(i)) for i in (dx,dy)) )
    if len(deltas.union(set([0]))) > 2:
        return False #perfect orthogonal or diagonal
    distance = max(deltas)
    if movetype == 'k':
        if distance == 1:
            if knownSafe:
                return True
            else:
                testdata = list(position[:])
                indexi = squareNameToIndex(initial)
                indexf = squareNameToIndex(final)
                captured = testdata[indexf]
                testdata[indexf] = testdata[indexi]
                testdata[indexi] = captured if isAlly(mover, captured) else '-'
                return len(checkStatus(''.join(testdata), False)) == 0
        elif distance == 2 and dy == 0:
            return validateCastle(position, xi, yi, xf, yf)
    if (movetype, 0 in deltas) in [('r', False), ('b', True)]:
        return False #rook moving diagonal, or bishop orthogonal
    if movetype == 'p':
        if math.fabs(dx) >= 2 or dy == 0:
            return False #invalid lateral motion
        if (dy >= 0) != (turn == 'W'):
            return False #backward motion
        if math.fabs(dy) >= 2 and ( dx != 0 or ((yf <= 4) != (turn == 'W'))  ):
            return False #multistep non-forward or ahead of midline
        if dx == 0 and receiver != '-':
            return False #forward motion to occupied square
        if dx != 0 and receiver == '-': #diagonal motion to empty square; may be valid if en passant
            enpassantcolumn = position[68]
            numcolumn = ord(enpassantcolumn.lower())-96
            if xf != numcolumn:
                return False #wrong column for en passant
            shortrow = 5 if turn == 'W' else 4
            if shortrow != yi: #not a short en passant
                if not enpassantcolumn.upper():
                    return False #only short en passant available
                longrow = 6 if turn == 'W' else 3
                if longrow != yi:
                    return False #not an attempted en passant
    #at this point, the following has been ruled out
    xstep, ystep = (i//distance for i in (dx,dy))
    for i in range(1, distance):
        xmid, ymid = (xi+xstep*i, yi+ystep*i)
        if position[xyToIndex(xmid, ymid)] != '-':
            return False #obstruction
    if knownSafe:
        return True
    testdata = list(position[:])
    indexi = squareNameToIndex(initial)
    indexf = squareNameToIndex(final)
    captured = testdata[indexf]
    testdata[indexf] = testdata[indexi]
    testdata[indexi] = captured if isAlly(mover, captured) else '-'
    return len(checkStatus(''.join(testdata), False)) == 0

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
    threats = checkStatus(position)
    check = threats if (type(threats) == int) else NORMAL if len(threats)==0 else CHECK if len(threats)==1 else DOUBLECHECK
    if piecetype == 'k':
        if check in [CHECKMATE, STALEMATE]:
            return [[],[]]
        prechecksquares = getnormalkingmoves(position, turn=="W", x, y)
        safesquares = []
        for xf,yf in prechecksquares:
            data = list(position)
            findex = xyToIndex(xf,yf)
            target = data[findex]
            data[findex],data[index] = data[index],(target if isAlly(piece,target) else "-")
            hypstate = checkStatus(''.join(data), False)
            if len(hypstate) == 0:
                safesquares.append(xyToSquareName(xf,yf))
        return [safesquares, []]
    else:
        ((pxta, pyta), pindistance) = pinStatus(position, x,y, piece) #pxta is for "pin x-direction threat arrow"
        allyKing = 'K' if piece.isupper() else 'k'
        kingindex = position.index(allyKing)
        kingx,kingy = indexToXY(kingindex)
        if check in [CHECKMATE, STALEMATE, DOUBLECHECK]:
            return [[],[]]
        elif check == CHECK and pindistance != 0: #pinned pieces can't help with check
            return [[],[]]
        elif check == CHECK and pindistance == 0:
            attacksquare = threats[0]
            attackx, attacky = squareNameToXY(attacksquare)
            prelim = validMovesNotKingCheckNoPin(position, square, (kingx, kingy), (attackx, attacky))
        elif pindistance != 0:
            pxtp, pytp = x+pxta, y+pyta #pxtp is "pin x-direction threat position"
            prelim = validMovesNotKingNoCheckPin(position, (x,y), piece, (kingx, kingy), (pxtp, pytp), (pxta, pyta), pindistance)
        else:
            prelim = validMovesNotKingNoCheckNoPin(position, piece, x,y)
        enpassant = position[68]
        if piecetype == 'p' and enpassant != '-':
            enpassantlong = enpassant.isupper()
            enpassantcolumn = (ord(enpassant.lower())-96)
            if math.fabs(enpassantcolumn-x) == 1:
                shortrow = 5 if turn == 'W' else 4
                longrow = 6 if turn == 'W' else 3
                direc = 1 if turn == 'W' else -1
                validenpassant = (y==shortrow) or (enpassantlong and y==longrow)
                longindex = xyToIndex(enpassantcolumn, longrow)
                index = longindex if position[longindex] != '-' else xyToIndex(enpassantcolumn, shortrow)
                target = indexToSquareName(index)
                dest = xyToSquareName(enpassantcolumn, y+direc)
                if enpassantischecksafe(position, square, dest, target):
                    prelim[1].append(dest)
        return prelim

#valid moves for a king piece
def validMovesKing(position, square):
    pass

#valid moves for non-pinned non-king when king is in check
def validMovesNotKingCheckNoPin(position, square, kingsquare, threatsquare):
    kingx, kingy = kingsquare
    threatx, threaty = threatsquare
    deltas = set((math.fabs(threatx-kingx), math.fabs(threaty-kingy), 0))
    if len(deltas) == 3:
        targetxys = [threatsquare] #knight threat; can only be suppressed by capture
    else:
        distance = int(max(deltas))
        xstep = (kingx-threatx)//distance
        ystep = (kingy-threaty)//distance
        xvals = [kingx]*distance if xstep==0 else [i for i in range(threatx, kingx, xstep)] #threatx first neatly includes capturing the threat while excluding landing on the king
        yvals = [kingy]*distance if ystep==0 else [i for i in range(threaty, kingy, ystep)]
        targetxys = list(itertools.zip_longest(xvals, yvals))
    targets = [xyToSquareName(i,j) for i,j in targetxys]
    valids = [i for i in targets if isValidMove(position, square, i, True)]
    return [valids, []]

#valid moves for pinned piece when king is not in check
def validMovesNotKingNoCheckPin(position, square, piece, kingsquare, threatsquare, pindirection, pindistance):
    isWhite = piece.isupper()
    piecetype = piece.lower()
    if piecetype == 'n':
        return [[],[]] #pinned knights cannot move
    if 0 in pindirection and piecetype == 'b':
        return [[],[]] #bishop on an orthogonal pin
    if not 0 in pindirection and piecetype == 'r':
        return [[],[]] #rook on a diagonal pin
    squarename = xyToSquareName(square[0], square[1])
    squaresInPin = getopendirection(position, isWhite, square[0], square[1], pindirection[0], pindirection[1]) + \
                    getopendirection(position, isWhite, square[0], square[1], -pindirection[0], -pindirection[1])
    if piecetype == 'p':
        return [[i for i in squaresInPin if isValidMove(position, xyToSquareName(square[0], square[1]), i, True)],[]]
    return [squaresInPin,[]]

#valid moves normally- not pinned and no check
def validMovesNotKingNoCheckNoPin(position, piece, x,y):
    piecetype = piece.lower()
    if piecetype == 'p':
        return getpawnmoves(position, piece.isupper(), x,y)
    elif piecetype == 'r':
        return getrookmoves(position, piece.isupper(), x,y)
    elif piecetype == 'n':
        return getknightmoves(position, piece.isupper(), x,y)
    elif piecetype == 'b':
        return getbishopmoves(position, piece.isupper(), x,y)
    elif piecetype == 'q':
        return getqueenmoves(position, piece.isupper(), x,y)

def pinStatus(position, x,y, piece):
    allyKing = 'K' if piece.isupper() else 'k'
    kingindex = position.index(allyKing)
    kingx,kingy = indexToXY(kingindex)
    dx,dy = (x-kingx),(y-kingy)
    deltas = (set([math.fabs(i) for i in (dx,dy,0)]))
    if len(deltas) == 2: #orthogonal or diagonal from friendly king
        distance = max(deltas)
        xstep,ystep = (int(i//distance) for i in (dx,dy)) #king to current-piece line, or current-piece to threat line
        clearToKing = clearLine(position, x, y, kingx, kingy)
        if clearToKing:
            opposite, distance = findFirstOnLine(position, x, y, xstep, ystep)
            if isEnemy(allyKing, opposite):
                threatdirection = (-xstep, -ystep)
                piecetype = opposite.lower()
                nonqueenthreat = 'r' if 0 in threatdirection else 'b'
                if piecetype in ['q', nonqueenthreat]: 
                    return (threatdirection, distance)
    return ((0,0), 0)
    
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
        return attacks
    #processing to determine checkmate/stalemate
    return attacks

def isEnemy(target, attacker):
    if type(target) == bool:
        target = 'A' if target else 'a'
    if (target=='-' or attacker=='-'):
        return False
    return target.isupper() != attacker.isupper()

def isAlly(target, attacker):
    if type(target) == bool:
        target = 'A' if target else 'a'
    if (target=='-' or attacker=='-'):
        return False
    return target.isupper() == attacker.isupper()

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
    dx, dy = (0 if x1==x2 else -1 if x1 > x2 else 1, 0 if y1==y2 else -1 if y1 > y2 else 1)
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

def squareNameToIndex(squareName):
    x,y = squareNameToXY(squareName)
    return xyToIndex(x,y)

def indexToSquareName(index):
    x,y = indexToXY(index)
    return xyToSquareName(x,y)

def getpawnmoves(position, iswhite, x, y):
    beforewrapper = lambda method: (lambda y,row: int(y).__getattribute__(method)(row))
    forward = []
    init,back,goal,direc,enpassant,secondenpassant,semifinal,isbehind = (2,1,8,1,5,6,7,beforewrapper("__le__")) if iswhite else (7,8,1,-1,4,3,2,beforewrapper("__ge__"))
    firstindex, secondindex, thirdindex = xyToIndex(x,y+direc), xyToIndex(x,y+2*direc), xyToIndex(x,y+3*direc)
    if position[firstindex] == '-':
        forward.append(xyToSquareName(x,y+direc))
        if isbehind(y,init) and position[secondindex] == '-':
            forward.append(xyToSquareName(x,y+2*direc))
            if isbehind(y,back) and position[thirdindex] == '-':
                forward.append(xyToSquareName(x,y+3*direc))
    attack = []
    if x != 1:
        leftindex = xyToIndex(x-1,y+direc)
        if isEnemy(iswhite, position[leftindex]):
            attack.append(indexToSquareName(leftindex))
    if x != 8:
        rightindex = xyToIndex(x+1,y+direc)
        if isEnemy(iswhite, position[rightindex]):
            attack.append(indexToSquareName(rightindex))
    enpassant = position[68]
    special = []
    if enpassant != '-':
        enpassantlong = enpassant.isupper()
        enpassantcol = enpassant.lower()
        enpassantcolnum = ord(enpassantcol)-96
        correctColumn = math.fabs(enpassantcolnum-x) == 1
        correctRow = (y==enpassant) or (y==secondenpassant and enpassantlong)
        if correctColumn and correctRow:
            enpassantsquare = xyToSquareName(enpassantcolnum,y+direc)
            special.append(enpassantsquare)
            
    return [[],forward+attack] if y == semifinal else [forward+attack,special]

def getrookmoves(position, iswhite, x,y):
    rdirections = [i for i in directions if 0 in i]
    moves = []
    for dx,dy in rdirections:
        moves += getopendirection(position, iswhite, x, y, dx, dy)
    return [moves, []]

def getknightmoves(position,iswhite,x,y):
    alltargets = [(x+i,y+j) for i,j in knightMoves]
    validtargets = [i for i in alltargets if min(i)>=1 and max(i)<=8]
    squares = [xyToSquareName(x,y) for x,y in validtargets if not(isAlly(iswhite,position[xyToIndex(x,y)]))]
    return [squares,[]]

def getbishopmoves(position, iswhite, x,y):
    bdirections = [i for i in directions if not 0 in i]
    moves = []
    for dx,dy in bdirections:
        moves += getopendirection(position, iswhite, x, y, dx, dy)
    return [moves, []]

def getqueenmoves(position, iswhite, x,y):
    moves = []
    for dx,dy in directions:
        moves += getopendirection(position, iswhite, x, y, dx, dy)
    return [moves, []]

def getnormalkingmoves(position,iswhite,x,y):
    alltargets = [(x+i,y+j) for i,j in directions]
    validtargets = [i for i in alltargets if min(i)>=1 and max(i)<=8]
    #squares = [xyToSquareName(x,y) for x,y in validtargets] #no limitations for friendly pieces- swapping is allowed
    return validtargets

def getopendirection(position,iswhite,x,y,dx,dy):
    linedPiece, distance = findFirstOnLine(position, x, y, dx, dy)
    intermediates = [(x+i*dx,y+i*dy) for i in range(1,distance)]
    if distance > 0 and not isAlly(iswhite, linedPiece):
        intermediates.append((x+dx*distance, y+dy*distance))
    return [xyToSquareName(ix,iy) for ix,iy in intermediates]

def validateCastle(position, xi, yi, xf, yf):
    turn = position[69]
    castlerow = 1 if turn == 'W' else 8
    if not (xi == 5 and yi == castlerow):
        return False
    if yf == yi:
        if xf == 3:
            isKingSide = False
        elif xf == 7:
            isKingSide = True
        else:
            return False #wrong column
    else:
        return False #wrong row
    rightIndex = castleRightIndex(isKingSide, turn == 'W')
    if position[rightIndex] != '+':
        return False #castle right does not exist
    checkclearcols = (6,7) if isKingSide else (2,3,4)
    checksafecols = (5,6,7) if isKingSide else (3,4,5)
    clearpath = all([position[xyToIndex(castlerow, i)]=='-' for i in checkclearcols])

def castleRightIndex(isKingSide, isWhite):
    return 64 + (0 if isKingSide else 1) + (0 if isWhite else 2)
