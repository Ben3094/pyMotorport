from pyNewportController.NewportSMC100 import MainController, ControllerState
import numpy
from time import sleep

zController = MainController()
yController = zController.NewController(2)
xController = zController.NewController(3)
zController.Connect('COM6', wait=True)
yController.Connect(homeIsHardwareDefined=True, wait=False)
xController.Connect(homeIsHardwareDefined=False, wait=False)
while xController.State != ControllerState.Ready or yController.State != ControllerState.Ready or zController.State != ControllerState.Ready:
    sleep(0.1)
y = yController.Position
yPositions = numpy.arange(yController.MinPosition, yController.MaxPosition, 1)
z = zController.Position
zPositions = numpy.arange(zController.MinPosition, zController.MaxPosition, 1)
for x in numpy.arange(xController.MinPosition, xController.MaxPosition, 1):
    xController.GoTo(x, wait=True)

    isYCloserToMin = abs(y - yController.MinPosition) < abs(y - yController.MaxPosition)
    for y in (yPositions if isYCloserToMin else yPositions[::-1]):
        yController.GoTo(y, wait=True)

        isZCloserToMin = abs(z - zController.MinPosition) < abs(z - zController.MaxPosition)
        for z in (zPositions if isZCloserToMin else zPositions[::-1]):
            zController.GoTo(z, wait=True)