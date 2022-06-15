from NewportSMC100 import MainController

mainController = MainController('com5')
controller = mainController.NewController()
controller.GoTo(controller.MinPosition)
controller.GoTo(0)
print(controller.Position)