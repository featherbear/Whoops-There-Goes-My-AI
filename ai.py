import wx
from pykeyboard import *
from pymouse import *

app = wx.App()
screen = wx.ScreenDC()

m = PyMouse()
k = PyKeyboard()


class KeyBoardEventListener(PyKeyboardEvent):
    def __init__(self):
        self.end = False
        self.pressed_c = False
        super(KeyBoardEventListener, self).__init__()

    def tap(self, keycode, character, press):  # press is boolean; True for press, False for release
        if character == 'q':
            self.end = True

        elif character == 'c':
            self.pressed_c = True


class MouseClickEventListener(PyMouseEvent):
    def __init__(self):
        self.clicked_positions = []
        # self.clicked = False
        # self.clicked_time = time.time()
        super(MouseClickEventListener, self).__init__()

    def click(self, x, y, button, press):
        if len(self.clicked_positions) < 2 and (x, y) not in self.clicked_positions:
            print('Point {} - x: {}, y: {}'.format(len(self.clicked_positions) + 1, x, y))
            self.clicked_positions.append((x, y))
            if len(self.clicked_positions) == 2:
                self.stop()
        # self.clicked = True
        # self.clicked_time = time.time()


def screenshot(anchor: tuple, width, height):
    global screen

    assert type(anchor) is tuple
    assert len(anchor) == 2

    x = anchor[0]
    y = anchor[1]
    w = width
    h = height

    # Construct a bitmap
    bmp = wx.Bitmap(w, h)

    # Fill bitmap delete memory (don't want memory leak)
    mem = wx.MemoryDC(bmp)
    mem.Blit(0, 0, w, h, screen, x, y)
    del mem

    # Convert bitmap to image
    wxB = bmp.ConvertToImage()

    # Get data buffer
    img_data = wxB.GetData()

    # Construct np array from data buffer and reshape it to img
    img_data_str = np.frombuffer(img_data, dtype = 'uint8')
    img: np.ndarray = img_data_str.reshape((h, w, 3))
    return img


# ke = KeyBoardEventListener()
me = MouseClickEventListener()

me.start()

import time

print("== Select game window ==".upper())
while len(me.clicked_positions) < 2:
    time.sleep(0.05)

print("\n== Region Captured ==".upper())
topLeft, bottomRight = me.clicked_positions
# topLeft = (3250, 98)
# bottomRight = (3796, 1075)


class regionConst:
    height = bottomRight[1] - topLeft[1]

    width = bottomRight[0] - topLeft[0]
    middleWidth = int(width / 2)

    effectiveWidth = int(94.93 / 100 * width)
    effectiveHalfWidth = int(effectiveWidth / 2)

    effectiveLeft = int(width / 2 - effectiveHalfWidth)
    effectiveRight = int(width / 2 + effectiveHalfWidth)


print("Region width: %d" % regionConst.width)
print("Region height: %d" % regionConst.height)

print("\n== Calculations ==".upper())


class playerConst:
    y = int(30.87 / 100 * regionConst.height)
    radius = int(8.85 / 100 * regionConst.width)
    diameter = radius * 2
    speedX = int(3.60 / 100 * regionConst.effectiveWidth)
    speedY = int(1.78 / 100 * regionConst.height)


print(
    """Player y-coordinate: {}
    Player radius: {} px
    Effective player space: {} px

      (Assuming 60fps)
    Horizontal Speed: {} px/tick
    Vertical Speed: {} px/tick

    Pixels to death: {} px
    Time to death: 36.36 ticks
    """.format(
        playerConst.y,
        playerConst.radius,
        regionConst.effectiveWidth,
        playerConst.speedX,
        playerConst.speedY,
        int(64.72 / 100 * regionConst.height)
    ))

import numpy as np
import cv2 as cv

gameEnd = True

increment = int(regionConst.effectiveWidth / 20 / 2)


class playerObj:
    mouse = PyMouse()
    clickLeft = topLeft[0] + int(regionConst.width / 4)
    clickRight = topLeft[0] + int(regionConst.width / 4 * 3)
    clickY = playerConst.y

    def __init__(self):
        self.x = int(regionConst.width / 2)

    def willTouch(self, boundL, boundR, pos):
        return not not range(max(pos - playerConst.radius, boundL), min(pos + playerConst.radius, boundR) + 1)

    def moveLeft(self):
        print("LEFT")
        self.mouse.press(self.clickLeft, self.clickY)

    def moveRight(self):
        print("RIGHT")
        self.mouse.press(self.clickRight, self.clickY)


OBSTACLE = 0
BLACK = 0

readyForNewObstacle = True
player = None
lastObstacle = None

subscribers = []

FORWARDS = "/"
BACKWARDS = "\\"


class watcherObj:
    gEdgeL = None
    gEdgeR = None
    watchFinish = False
    type = None

    @property
    def edges(self):
        return (self.gEdgeL, self.gEdgeR)

    def fire(self, lastRow: np.ndarray):
        global readyForNewObstacle
        if self.watchFinish: return

        if OBSTACLE not in lastRow:
            self.watchFinish = True
            readyForNewObstacle = True
            return

        lastRowList: list = lastRow.tolist()
        edgeL = lastRowList.index(OBSTACLE)
        edgeR = regionConst.width - lastRowList[::-1].index(OBSTACLE) - 1

        # threshold
        edgeL -= 20
        edgeR += 20

        if not self.gEdgeL:
            self.gEdgeL = edgeL
        if not self.gEdgeR:
            self.gEdgeR = edgeR

        if edgeL < self.gEdgeL:
            # /
            self.gEdgeL = edgeL
            self.type = FORWARDS
        elif edgeR > self.gEdgeR:
            # \
            self.gEdgeR = edgeR
            self.type = BACKWARDS
        return self.type


def getPlayerCentre(imgPreview: np.ndarray):
    a1 = np.array([73, 181, 255])
    a2 = np.array([30, 72, 116])

    playerScreen = cv.bitwise_not(cv.inRange(imgPreview, a2, a1))[playerConst.y]
    cv.imshow("PLAYER SCREEN", cv.rotate(playerScreen, 2))
    playerScreen.tolist()

    playerScreenList: list = playerScreen.tolist()
    edgeL = playerScreenList.index(BLACK)
    edgeR = len(playerScreenList) - playerScreenList[::-1].index(BLACK) - 1

    width = edgeR - edgeL
    missingDistance = abs(playerConst.diameter - width)

    if missingDistance < 4:
        return int(edgeL + width / 2)
    else:
        if edgeR < regionConst.middleWidth:
            return playerConst.radius - missingDistance
        elif edgeL > regionConst.middleWidth:
            return regionConst.width - (playerConst.radius - missingDistance)
        else:
            return -1
            # raise Exception()


input("Press enter to begin")


while True:
    npImg: np.ndarray = screenshot(topLeft, regionConst.width, regionConst.height)

    gray = cv.cvtColor(npImg, cv.COLOR_RGB2GRAY)
    ret, thr1 = cv.threshold(gray, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
    thr1: np.ndarray

    imgPreview = cv.cvtColor(npImg, cv.COLOR_BGR2RGB)

    gameOverTextPosition = int(26.0 / 100 * regionConst.height)
    gameOverTextColour = np.array([49, 128, 255])
    gameEndScreen = cv.bitwise_not(cv.inRange(imgPreview, gameOverTextColour, gameOverTextColour))
    # cv.imshow("GAME END", gameEndScreen)

    # lastRow: np.ndarray = npImg[region.height - 1]
    # print(np.unique(lastRow, axis=0))

    if gameEnd and BLACK not in gameEndScreen[gameOverTextPosition]:
        print("GAME START")
        subscribers = []
        player = playerObj()
        gameEnd = False

        readyForNewObstacle = True

    elif not gameEnd:
        if BLACK in gameEndScreen[gameOverTextPosition]:
            print("END GAME")
            lastObstacle = None
            player = None
            gameEnd = True
        else:

            ########### GAME RUNNING
            lastRow: np.ndarray = thr1[regionConst.height - 1]

            if readyForNewObstacle and OBSTACLE in lastRow:
                print("DETECT OBSTACLE")
                readyForNewObstacle = False
                if len(subscribers) > 0: del subscribers[0]
                subscribers.append(watcherObj())

            # Tick last watcher
            if len(subscribers) > 0: subscribers[-1].fire(lastRow)

            # if (willCollide): dont()
            playerXpos = getPlayerCentre(imgPreview)

            avoidSuccess = False
            if len(subscribers) > 0 and playerXpos > -1:

                watcher: watcherObj = subscribers[0]
                collision = player.willTouch(*watcher.edges, playerXpos)
                if collision:
                    if watcher.type == FORWARDS:
                        # /
                        if not player.willTouch(*watcher.edges, regionConst.effectiveRight):
                            player.moveRight()
                        else:
                            player.moveLeft()
                    elif watcher.type == BACKWARDS:
                        # \
                        if not player.willTouch(*watcher.edges, regionConst.effectiveLeft):
                            player.moveLeft()
                        else:
                            player.moveRight()
                else:
                    player.mouse.release(0, 0)
                    avoidSuccess = True

            # Draw danger zone
            if len(subscribers) > 0:
                alpha = 0.3
                imgPreview: np.ndarray
                overlay = imgPreview.copy()
                cv.rectangle(overlay, (subscribers[0].gEdgeL, 0), (subscribers[0].gEdgeR, regionConst.height),
                             (0, 255, 0) if avoidSuccess else (0, 0, 255), -1)
                cv.addWeighted(overlay, alpha, imgPreview, 1 - alpha, 0, imgPreview)

    # cv.imshow("GREYSCALE", thr1)
    cv.imshow("Visualisation", imgPreview)
    cv.waitKey(1)

# ROI_GAME = get_roi_from_mouse(mouseevents.clicked_positions)

# player hitbox - circle of radius 8.85% W
# player y-coordinate - 30.87% H
# effective player space - 94.93% W (47% from centre to side)
# vertical speed - 1.78% / tick (60)
# horizontal speed - 3.60% / tick (60)
# death speed - 64.72% H, 36.36t, 0.6s
