import serial
from time import sleep
import threading

class MainController(object):
	def __init__(self, port):
		""":param port: Serial port connected to the main controller."""
		self.ser = serial.Serial(port=port, baudrate=56700, timeout=20)
		self.ser.setDTR(False)
		self.Abort = self.Stop

	def __del__(self):
		self.ser.close()

	def Read(self):
		str = self.ser.readline()
		return str[0:-2]

	def Write(self, string):
		self.ser.write((string + "\r\n").encode(encoding='ascii'))

	def Query(self, string, check_error=False):
		with threading.Lock():
			if check_error:
				self.raise_error()
			self.Write(string)
			if check_error:
				self.raise_error()
			return self.Read().decode()

	def Stop(self):
		"""The ST command is a safety feature. It stops a move in progress by decelerating the positioner immediately with the acceleration defined by the AC command until it stops."""
		self.Write('ST')

	def read_error(self):
		"""Return the last error as a string."""
		return self.Query('TB')
		
	def raise_error(self):
		"""Check the last error message and raise a NewportError."""
		err = self.read_error()
		if err[0] != "0":
			raise Exception(err)
	
	def NewController(self, address=1):
		return Controller(self, address=address)

ADDRESS_RANGE = range(32)

class Controller(object):
	def __init__(self, mainController, address=1):
		"""
		:param mainController: The main controller connected to the computer 
		:type controller: :class:`MainController`
		:param address: the address of the new controller
		:type axis: int
		"""
		self._mainController = mainController
		if address in ADDRESS_RANGE:
			self._address = address

		self.Read = self.MainController.Read   
		self.read_error = self.MainController.read_error

		self.UpdateStageSettings()
		if self.IsInConfigurationState:
			self.IsInConfigurationState = False
		if self.IsNotReferenced:
			self.GoHome(True)

	@property
	def Address(self):
		return self._address

	@property
	def MainController(self):
		return self._mainController

	def Write(self, string):
		self.MainController.Write((str(self._address) if self._address is not None else "") + string)
	
	def Query(self, string, check_error=False):
		query = (str(self._address) if self._address is not None else "") + string
		reply =  self.MainController.Query(query + '?', check_error)
		return reply[len(query):]
	
	@property
	def id(self):
		"""The axis model and serial number."""
		return self.Query('ID')

	@property
	def IsEnabled(self):
		return self.Query('MM') == 1
	@IsEnabled.setter
	def IsEnabled(self, value):
		self.Write('MM' + str(int(bool(value))))

	def GoHome(self, wait=True):
		self.Write('OR')
		if wait:
			while(self.IsMoving):
				sleep(0.1)

	def GoTo(self, position, wait=True):
		self.Position = position
		if wait:
			while(self.IsMoving):
				sleep(0.1)

	@property
	def Position(self):
		"""The TP command returns the value of the current position.
			This is the position where the positioner actually is according to his encoder value.
			In MOVING state, this value always changes.
			In READY state, this value should be equal or very close to the set point and target position.
			Together with the TS command, the TP command helps evaluating whether a motion is completed"""
		return float(self.Query('TP'))
	@Position.setter
	def Position(self, value):
		if self.MinPosition <= value <= self.MaxPosition:
			self.Write('PA' + str(float(value)))
		else:
			raise Exception('Position cannot be reached')

	@property
	def IsInConfigurationState(self):
		return self.State[-2:] == '14'
	@IsInConfigurationState.setter
	def IsInConfigurationState(self, value):
		self.Write('PW' + str(int(bool(value))))
		if self.IsInConfigurationState != value:
			raise Exception('Configuration mode cannot be changed')

	@property
	def MinPosition(self):
		return float(self.Query('SL'))

	@property
	def MaxPosition(self):
		return float(self.Query('SR'))

	def Stop(self):
		"""The ST command is a safety feature. It stops a move in progress by decelerating the positioner immediately with the acceleration defined by the AC command until it stops."""
		self.Write('ST')

	@property
	def State(self):
		return self.Query('TS')
	@property
	def IsMoving(self):
		return self.State[-2:] in ['28', '1E', '1F', '46', '47']
	@property
	def IsNotReferenced(self):
		return self.State[-2:] in ['0A', '0B', '0C', '0D', '0E', '0F', '10', '1F']

	@property
	def Velocity(self):
		return float(self.Query('VA'))

	@property
	def Version(self):
		"""Get controller revision information"""
		return self.Query('VE')

	@property
	def Stage(self):
		""""Get the current connected stage reference"""
		return self.Query('ZX')
	
	def SetAutoStageCheck(self, value):
		return self.Write('ZX' + ('3' if bool(value) else '1'))
	
	def UpdateStageSettings(self):
		return self.Write('ZX2')