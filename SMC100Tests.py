from pyMotorport.SMC100 import MainController, ControllerState
from numpy import arange, around
from time import sleep

# Set variables
xMin = 0 # mm
xMax = 10 # mm
xStep = 1 # mm
yMin = 0 # mm
yMax = 10 # mm
yStep = 1 # mm
zMin = 0 # mm
zMax = 0 # mm
zStep = 0.05 # mm

# Prepare variables for numpy
xStep = 1 if xStep == 0 else xStep
xMax = xMax + xStep
xDecimal = str(xStep)[::-1].find('.')
xDecimal = 0 if xDecimal < 0 else xDecimal
yStep = 1 if yStep == 0 else yStep
yMax = yMax + yStep
yDecimal = str(yStep)[::-1].find('.')
yDecimal = 0 if yDecimal < 0 else yDecimal
zStep = 1 if zStep == 0 else zStep
zMax = zMax + zStep
zDecimal = str(zStep)[::-1].find('.')
zDecimal = 0 if zDecimal < 0 else zDecimal

# Set actuators
actuatorsCOMPort = 'COM5'
zController = MainController()
yController = zController.NewController(2)
xController = zController.NewController(3)
zController.ConnectAll(actuatorsCOMPort, homeIsHardwareDefined=True, wait=True)

zController.SetAllState(ControllerState.Disable, wait=True)

zController.SetHomeIsHardwareDefined(False, wait=False)
yController.SetHomeIsHardwareDefined(False, wait=False)
xController.SetHomeIsHardwareDefined(False, wait=False)
while xController.State != ControllerState.Configuration or yController.State != ControllerState.Configuration or zController.State != ControllerState.Configuration:
	sleep(0.1)

zController.SetAllState(ControllerState.Ready, wait=True)

yPositions = around(arange(yMin, yMax, yStep), yDecimal)
zPositions = around(arange(zMin, zMax, zStep), zDecimal)
y = yController.Position
z = zController.Position
for x in around(arange(xMin, xMax, xStep), xDecimal):
	xController.GoTo(x, wait=False)
	isYCloserToMin = abs(y - yController.MinPosition) < abs(y - yController.MaxPosition)
	for y in (yPositions if isYCloserToMin else yPositions[::-1]):
		yController.GoTo(y, wait=False)
		isZCloserToMin = abs(z - zController.MinPosition) < abs(z - zController.MaxPosition)
		for z in (zPositions if isZCloserToMin else zPositions[::-1]):
			zController.GoTo(z, wait=False)
			while xController.State != ControllerState.Ready or yController.State != ControllerState.Ready or zController.State != ControllerState.Ready:
				sleep(0.1)
print("Done")