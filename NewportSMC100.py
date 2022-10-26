from aenum import MultiValueEnum
import serial
from time import sleep
import threading

ADDRESS_RANGE = range(32)

class ControllerState(MultiValueEnum):
	NotReferenced = '0A', '0B', '0C', '0D', '0E', '0F', '10', '11'
	Configuration = '14'
	Homing = '1E', '1F'
	Moving = '28'
	Ready = '32', '33', '34', '35'
	Disable = '3C', '3D', '3E'
	Jogging = '46', '47'

class Controller():
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

		self.IsConnected = False

	def __getNone__():
		return None

	@property
	def Address(self):
		return self._address

	@property
	def MainController(self):
		return self._mainController

	def Connect(self, homeIsHardwareDefined=True):
		self.IsConnected = True
		try:
			# self.UpdateStageSettings()
			self.HomeIsHardwareDefined = homeIsHardwareDefined
			self.State = ControllerState.Ready
		except Exception as err:
			self.IsConnected = False

	def Disconnect(self):
		self.IsConnected = False

	def Write(self, string):
		self.MainController.SuperWrite((str(self._address) if self._address is not None else "") + string)
	
	def Query(self, string, check_error=False):
		query = (str(self._address) if self._address is not None else "") + string
		reply = self.MainController.SuperQuery(query + '?', check_error)
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

	@property
	def HomeIsHardwareDefined(self):
		return self.Query('HT') != '1'
	@HomeIsHardwareDefined.setter
	def HomeIsHardwareDefined(self, value):
		value = bool(value)
		if value != self.HomeIsHardwareDefined:
			self.State = ControllerState.Configuration
			self.Write('HT' + ('2' if value else '1'))

	def GoHome(self, wait=True):
		self.Write('OR')
		if wait:
			while(self.State == ControllerState.Moving):
				sleep(0.1)

	def GoTo(self, position, wait=True):
		self.Position = position
		if wait:
			while(self.State == ControllerState.Moving):
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
		return ControllerState(self.Query('TS')[-2:])
	@State.setter
	def State(self, value):
		if value is not self.State:
			match ControllerState(value):
				case ControllerState.NotReferenced:
					self.Reset()

				case ControllerState.Configuration:
					self.State = ControllerState.NotReferenced
					self.Write('PW1')

				case ControllerState.Ready:
					if self.State is ControllerState.Configuration:
						self.Write('PW0')
						self.Version
					if self.State is ControllerState.Disable:
						self.Write('MM1')
					if self.State is ControllerState.Jogging or ControllerState.Moving or ControllerState.Homing:
						while(self.State == ControllerState.Moving):
							sleep(0.1)
					if self.State is not ControllerState.Ready:
						self.GoHome(True)

				case ControllerState.Disable:
					self.State = ControllerState.Ready
					self.Write('MM0')
					
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
		return self.Query('ZX2')
	
	def Reset(self):
		savedVersion = self.Version
		savedTimeout = self.MainController._serialPort.timeout
		self.MainController._serialPort.timeout = 0.1
		self.Write('RS')
		sleep(0.5)
		while self.Version != savedVersion:
			pass
		self.MainController._serialPort.timeout = savedTimeout

class MainController(Controller):
	def __init__(self, address=1):
		super().__init__(self, address)
		self._slaveControllers = list()

	def Connect(self, port, homeIsHardwareDefined=True):
		""":param port: Serial port connected to the main controller."""
		if not self.IsConnected:
			self.ser = serial.Serial(port=port, baudrate=56700, timeout=20)
			self.ser.setDTR(False)
			super().Connect(homeIsHardwareDefined)

	def Disconnect(self):
		if self.IsConnected:
			super().Disconnect()
			self.ser.close()
	
	@property
	def IsAllConnected(self):
		for controller in self.SlaveControllers:
			if not controller.IsConnected:
				return False
		return True

	def __del__(self):
		self.ser.close()

	def Read(self):
		str = self.ser.readline()
		str = str.replace(b'\r', b'')
		str = str.replace(b'\n', b'')
		return str

	def SuperWrite(self, string):
		self.ser.write((string + '\r\n').encode(encoding='ascii'))

	def SuperQuery(self, string, check_error=False):
		with threading.Lock():
			if check_error:
				self.raise_error()
			self.SuperWrite(string)
			if check_error:
				self.raise_error()
			return self.Read().decode()

	def Abort(self):
		"""The ST command is a safety feature. It stops a move in progress by decelerating the positioner immediately with the acceleration defined by the AC command until it stops."""
		self.SuperWrite('ST')

	def read_error(self):
		"""Return the last error as a string."""
		return self.SuperQuery('TB')
		
	def raise_error(self):
		"""Check the last error message and raise a NewportError."""
		err = self.read_error()
		if err[0] != "0":
			raise Exception(err)

	@property
	def SlaveControllers(self):
		return self._slaveControllers
	
	def NewController(self, address=1):
		newController = Controller(self, address=address)
		self._slaveControllers.append(newController)
		return newController