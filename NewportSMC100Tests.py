from NewportSMC100 import MainController

mainController = MainController('com5')
controller1 = mainController.NewController()
controller1.GoTo(controller1.MinPosition)
controller2 = mainController.NewController(2)
controller2.GoTo(controller2.MinPosition)
controller3 = mainController.NewController(3)
controller3.GoTo(controller3.MinPosition)