from NewportSMC100 import MainController

mainController = MainController('com3')
xController = mainController.NewController()
yController = mainController.NewController(2)
zController = mainController.NewController(3)
xController.GoTo(xController.MaxPosition, wait=False)
zController.GoTo(zController.MaxPosition, wait=False)
yController.GoTo(yController.MaxPosition, wait=True)
xController.GoTo(0, wait=False)
zController.GoTo(0, wait=False)
yController.GoTo(0, wait=True)