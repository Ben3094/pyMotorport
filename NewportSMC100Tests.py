from NewportSMC100 import MainController
import numpy

mainController = MainController('com3')
xController = mainController.NewController()
yController = mainController.NewController(2)
zController = mainController.NewController(3)
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