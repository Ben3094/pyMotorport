# pyMotorport library

> **⚠️ Warning ⚠️**
> 
> Disclaimer: The author cannot be hold responsible for any damage caused by the use of pyMotorport

The pyMotorport API abstracts the Newport SMC100 (for the moment) and provides two main objects : the "Controller", and the "MainController" (python object, "child" of Controller).

## MainController object

This object manages the serial connection from the host PC to the physical Newport controller and should be instantiated first.
```python
xAxisController = MainController()
xAxisController.Connect('COM6', wait=True)
```

MainController can abort all motors (connected through RS-485) activity using the ```Abort``` method.

In order to use other controllers chained to the main controller using RS-485 ports, you can obtain new Controller objects using the ```NewController``` method of the ```MainController```. The only parameter of this method is the address of the targeted controller.
```python
yAxisController = xAxisController.NewController(2)
```

## Controller object

The ```Connect``` and ```Disconnect``` methods are used to set correctly motors before operation (check ```IsConnected``` property).

The ```Connect``` method defines a ```homeIsHardwareDefined``` that directly set the same-name property (as this operation automaticaly set the controller to "Configuration" state).

The ```HomeIsHardwareDefined``` property defines whether the zero-position (home) corresponds to its default position. Setting ```HomeIsHardwareDefined``` to ```False``` set home to the current position. After this operation, ```State``` property must be set to another state that "Configuration". To set manually the position, controller state must be "Disabled".
```python
xAxisController.State = ControllerState.Disable
input("Set X-axis home position") # Wait for user to confirm in terminal
xAxisController.HomeIsHardwareDefined = False
xAxisController.SetState(ControllerState.Ready, wait=True)
```

In order to check or set the state of the controller, it defines a ```State``` property. This property return or accept a ```ControllerState``` enumeration. Setting the ```State``` manage all operations needed to set a state while another (of any sort) is currently applied. 

All time-consumming method (like ```Connect```, ```GoTo```, ```GoHome```, or ```SetState```) defines a ```wait``` parameter in order to stop execution while the physical operation is not completed.

>  **⚠️ Warning ⚠️**
> 
> Do not try to use the ```SetState``` method (or to set the ```State``` property) on several controller without waiting for an individual commmand to finish (i.e., by threading, or by setting the ```wait``` argument to ```False```).
> 
> As the ```HomeIsHardwareDefined``` use the ```State``` property, you need to wait here too.
>
> ```python
> xAxisController.HomeIsHardwareDefined = False
> xAxisController.SetState(ControllerState.Ready, wait=True)
> ```
> 
> This library is still in development.