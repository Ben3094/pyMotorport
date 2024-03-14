from aenum import MultiValueEnum
from serial import Serial, SerialTimeoutException
from time import sleep, time
from threading import Thread
from multiprocessing import Lock
from re import split, match

ADDRESS_RANGE = range(32)
QUERY_REGEX = "(\\d+[A-Z]{2})\\?"
QUERY_RESPONSE_REGEX = "(\\d+[A-Z]{2})(.+)?"
FLOAT_PARAMETER_REGEX = "([+-]?\\d+(?:\\.\\d+)?).*"

class QueryNotAnswered(Exception):
	pass

class ControllerState(MultiValueEnum):
	NotReferenced = '0A', '0B', '0C', '0D', '0E', '0F', '10', '11'
	Configuration = '14'
	Homing = '1E', '1F'
	Moving = '28'
	Ready = '32', '33', '34', '35'
	Disable = '3C', '3D', '3E'
	Jogging = '46', '47'
	Unknown = 'Unknown'


class Controller:
	def __init__(self, mainController, address=1):
		"""
		:param mainController: The main controller connected to the computer 
		:type controller: :class:`MainController`
		:param address: the address of the new controller
		:type axis: int
		"""
		self.__mainController__ = mainController
		if address in ADDRESS_RANGE:
			self._address = address

		self.Read = self.MainController.Read
		self.read_error = self.MainController.read_error

		self.IsConnected:bool = False

		self.__setStateLock__ = Lock()

	@property
	def Address(self):
		return self._address

	@property
	def MainController(self):
		return self.__mainController__
	
	def __connect__(self, homeIsHardwareDefined:bool=True):
		self.IsConnected = True
		try:
			# self.UpdateStageSettings() # Too long to execute
			self.HomeIsHardwareDefined = homeIsHardwareDefined
			self.SetState(ControllerState.Ready, wait=True)
			return True
		except Exception as e:
			self.IsConnected = False
	CONECTION_TIMEOUT:float = 60
	def Connect(self, homeIsHardwareDefined:bool=True, wait:bool=True):
		thread = Thread(target=self.__connect__, args=[homeIsHardwareDefined], name=f"Connect controller {self.Address}")
		thread.start()
		if wait:
			thread.join(timeout=Controller.CONECTION_TIMEOUT)
			if thread.is_alive():
				raise TimeoutError(f"Connect controller {self.Address} took too long")

	def Disconnect(self):
		self.IsConnected = False

	def Write(self, string, retry: int = 10):
		self.MainController.SuperWrite((str(self._address) if self._address is not None else "") + string, retry)

	def Query(self, string):
		query = (str(self._address) if self._address is not None else "") + string
		return self.MainController.SuperQuery(query + '?')

	@property
	def id(self):
		"""The axis model and serial number."""
		return self.Query('ID')

	@property
	def IsEnabled(self) -> bool:
		return self.Query('MM') == 1

	@IsEnabled.setter
	def IsEnabled(self, value: bool):
		self.Write('MM' + str(int(bool(value))))

	def GetHomeIsHardwareDefined(self) -> bool:
		match self.Query('HT'):
			case '1':
				return False
			case '2':
				return True
			case _:
				sleep(0.1)
				return self.HomeIsHardwareDefined
			
	SET_HOME_IS_HARDWARE_DEFINED_TIMEOUT:float = 20.0
	def __setHomeIsHardwareDefined__(self, value:bool):
		value = bool(value)
		if value != self.HomeIsHardwareDefined:
			self.State = ControllerState.Configuration
			self.Write('HT' + ('2' if value else '1'))
	def SetHomeIsHardwareDefined(self, value:bool, wait:bool=True):
		thread = Thread(target=self.__setHomeIsHardwareDefined__, args=[value], name=f"SetHomeIsHardwareDefined(Controller{self.Address}, {str(value)})")
		thread.start()
		if wait:
			thread.join(timeout=Controller.SET_HOME_IS_HARDWARE_DEFINED_TIMEOUT)
			if thread.is_alive():
				raise TimeoutError("Set HomeIsHardwareDefined took too long")
			
	HomeIsHardwareDefined = property(GetHomeIsHardwareDefined, SetHomeIsHardwareDefined)

	@property
	def IsHome(self) -> bool:
		return True if self.Position == 0 else False

	@property
	def HomeSearchTimeout(self) -> float:
		return float(match(FLOAT_PARAMETER_REGEX, self.Query('OT'))[1])
	@HomeSearchTimeout.setter
	def HomeSearchTimeout(self, value: float):
		self.Write('PA' + str(float(value)))

	def GoHome(self, wait:bool=True):
		self.Write('OR')
		if wait:
			startTime = time()
			while (time() - startTime) < self.HomeSearchTimeout:
				if self.IsHome:
					return True
				else:
					sleep(0.1)
			raise TimeoutError("Going home took too long")

	def GoTo(self, position:float, wait:bool=True):
		self.Position = position
		if wait:
			while (self.State == ControllerState.Moving):
				sleep(0.1)

	GET_POSITION_RETRIES:int = 5
	@property
	def Position(self) -> float:
		"""The TP command returns the value of the current position.
			This is the position where the positioner actually is according to his encoder value.
			In MOVING state, this value always changes.
			In READY state, this value should be equal or very close to the set point and target position.
			Together with the TS command, the TP command helps evaluating whether a motion is completed"""
		retriesLeft = Controller.GET_POSITION_RETRIES
		while retriesLeft > -1:
			try:
				return float(match(FLOAT_PARAMETER_REGEX, self.Query('TP'))[0])
			except TypeError:
				pass
			retriesLeft = retriesLeft - 1
		raise TimeoutError(f"Error while getting minimal position on motor {self.Address}")
	@Position.setter
	def Position(self, value:float, check:bool=False):
		if check:
			if not (self.MinPosition <= value <= self.MaxPosition):
				raise Exception('Position cannot be reached')
			
		self.Write('PA' + str(float(value)))
		
	@property
	def MinPosition(self) -> float:
		retriesLeft = Controller.GET_POSITION_RETRIES
		while retriesLeft > -1:
			try:
				return float(match(FLOAT_PARAMETER_REGEX, self.Query('SL'))[0])
			except TypeError:
				pass
			retriesLeft = retriesLeft - 1
		raise TimeoutError(f"Error while getting minimal position on motor {self.Address}")

	@property
	def MaxPosition(self) -> float:
		retriesLeft = Controller.GET_POSITION_RETRIES
		while retriesLeft > -1:
			try:
				return float(match(FLOAT_PARAMETER_REGEX, self.Query('SR'))[0])
			except TypeError:
				pass
			retriesLeft = retriesLeft - 1
		raise TimeoutError(f"Error while getting maximal position on motor {self.Address}")

	def Stop(self):
		"""The ST command is a safety feature. It stops a move in progress by decelerating the positioner immediately with the acceleration defined by the AC command until it stops."""
		self.Write('ST')

	def GetState(self) -> ControllerState:
		try:
			state = self.Query('TS')[-2:]
			state = ControllerState(state)
			return state
		except:
			return ControllerState.Unknown

	def __setState__(self, value:ControllerState, retries:int=10, safeconduct:bool=False):
		if not safeconduct:
			self.__setStateLock__.acquire()

		retriesLeft = retries
		while retriesLeft > -1:
			retriesLeft = retriesLeft - 1
			try:
				match ControllerState(value):
					case ControllerState.NotReferenced:
						self.Reset()
						sleep(0.5)

					case ControllerState.Configuration:
						self.__setState__(ControllerState.NotReferenced, safeconduct=True)
						self.Write('PW1')
						sleep(0.3)

					case ControllerState.Ready:
						match self.State:
							case ControllerState.Configuration:
								self.Write('PW0')
							case ControllerState.NotReferenced:
								self.GoHome(wait=True)
							case ControllerState.Disable:
								self.Write('MM1')
							case ControllerState.Jogging | ControllerState.Moving | ControllerState.Homing:
								sleep(0.1)

					case ControllerState.Disable:
						while self.State != ControllerState.Disable:
							self.Write('MM0')
							sleep(0.3)

				if self.State == value:
					if not safeconduct:
						self.__setStateLock__.release()
					return True
				else:
					sleep(0.2)
			except:
				pass

		if not safeconduct:
			self.__setStateLock__.release()
		raise TimeoutError(f"{value} cannot be set")

	SET_STATE_TIMEOUT = 30
	def SetState(self, value:ControllerState, wait:bool=True):
		thread = Thread(target=self.__setState__, args=[value], name=f"SetState(Controller{self.Address}, {value.name})")
		thread.start()
		if wait:
			try:
				thread.join(timeout=Controller.SET_STATE_TIMEOUT)
				if thread.is_alive():
					raise TimeoutError(f"Set {value} on controller {self.Address} took too long")
			except Exception as e:
				self.__setStateLock__.release()
				raise e

	State = property(GetState, SetState)

	@property
	def Velocity(self) -> float:
		return float(self.Query('VA'))

	@property
	def Version(self) -> str:
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

	RESET_TIMEOUT = 15
	def Reset(self, retries:int=2):
		while retries > -1:
			self.Write('RS', retry=0)
			startTime = time()
			while time() - startTime < Controller.RESET_TIMEOUT:
				if self.State == ControllerState.NotReferenced:
					return True
				else:
					sleep(0.1)
			retries = retries - 1
		raise TimeoutError("Reset was too long")


class MainController(Controller):
	__serialPort__:Serial = None

	def __init__(self, address=1):
		super().__init__(self, address)
		self.__slaveControllers__:list[Controller] = list()
		self.__receivedMessages__:dict[str, str] = dict()
		self.__serialPortLock__ = Lock()
		self.__messageBuffer__ = Lock()

	def Connect(self, port, homeIsHardwareDefined:bool=True, wait:bool=True):
		""":param port: Serial port connected to the main controller."""
		if not self.IsConnected:
			self.__serialPort__ = Serial(port=port, baudrate=57600, timeout=0.1, write_timeout=5)
			self.__serialPort__.setDTR(False)
			super().Connect(homeIsHardwareDefined=homeIsHardwareDefined, wait=wait)
			
	CONNECT_ALL_TIMEOUT:float = 30 # s
	def ConnectAll(self, port, homeIsHardwareDefined:bool=True, wait:bool=True):
		mainControllerThread = Thread(target=self.Connect, args=[port, homeIsHardwareDefined, True], name=f"Connect controller {self.Address}")
		mainControllerThread.start()
		controllerThreads = [mainControllerThread] + [Thread(target=controller.Connect, args=[homeIsHardwareDefined, True], name=f"Connect controller {controller.Address}") for controller in self.SlaveControllers]
		sleep(0.1)
		[controllerThread.start() for controllerThread in controllerThreads[1:]]
		if wait:
			startTime = time()
			while (time() - startTime) < MainController.CONNECT_ALL_TIMEOUT:
				if all([not controllerThread.is_alive() for controllerThread in controllerThreads]):
					return True
				else:
					sleep(0.1)
			raise TimeoutError("Connect all controllers took too long")
	
	SET_ALL_STATE_TIMEOUT:float = 30 # s
	def SetAllState(self, value:ControllerState, wait:bool=True):
		mainControllerThread = Thread(target=self.SetState, args=[value, True], name=f"SetState(Controller{self.Address}, {value.name})")
		controllerThreads = [mainControllerThread] + [Thread(target=controller.SetState, args=[value, True], name=f"SetState(Controller{controller.Address}, {value.name})") for controller in self.SlaveControllers]
		[controllerThread.start() for controllerThread in controllerThreads]
		if wait:
			startTime = time()
			while (time() - startTime) < MainController.SET_ALL_STATE_TIMEOUT:
				if all([not controllerThread.is_alive() for controllerThread in controllerThreads]):
					return True
				else:
					sleep(0.1)
			raise TimeoutError(f"Set {value} on all controllers took too long")

	def Disconnect(self):
		if self.IsConnected:
			super().Disconnect()
			self.__serialPort__.close()

	@property
	def IsAllConnected(self):
		for controller in self.SlaveControllers:
			if not controller.IsConnected:
				return False
		return True

	def __del__(self):
		self.__serialPort__.close()

	def ReadMessages(self) -> dict[str, str]:
		with self.__serialPortLock__:
			incommingMessages = self.__serialPort__.read_all()
		incommingMessages = incommingMessages.decode(encoding="ascii", errors="ignore")
		incommingMessages = split('\r|\n', incommingMessages)
		
		for incommingMessage in incommingMessages:
			correctMessage = match(QUERY_RESPONSE_REGEX, incommingMessage)
			if correctMessage:
				if correctMessage[2] != None:
					with self.__messageBuffer__:
						self.__receivedMessages__[correctMessage[1]] = correctMessage[2]

		return self.__receivedMessages__

	READ_TIMEOUT = 2
	def Read(self, messagePrefix:str) -> str:
		if not self.IsConnected:
			raise Exception("The main controller is not connected")
		
		startTime = time()
		while time() - startTime < MainController.READ_TIMEOUT:
			try:
				answer = self.ReadMessages()[messagePrefix]
				return answer
			except KeyError:
				pass
		raise TimeoutError("Read took too long")

	def SuperWrite(self, value:str, retries:int=10):
		if not self.IsConnected:
			raise Exception("The main controller is not connected")

		retriesLeft = retries
		while retriesLeft > -1:
			try:
				with self.__serialPortLock__:
					return self.__serialPort__.write((value + '\r\n').encode(encoding='ascii'))
			except SerialTimeoutException:
				pass
			sleep(0.1)
			retriesLeft = retriesLeft - 1

		raise TimeoutError("Message cannot be sent")

	def SuperQuery(self, value:str, retries:int=10):
		retriesLeft = retries

		# Messages processing
		toBeReceivedMessagePrefix = match(QUERY_REGEX, value)[1]
		if toBeReceivedMessagePrefix in self.__receivedMessages__:
			with self.__messageBuffer__:
				del self.__receivedMessages__[toBeReceivedMessagePrefix]  # Delete old response

		while retriesLeft > -1:
			self.SuperWrite(value)
			try:
				return self.Read(toBeReceivedMessagePrefix)
			except TimeoutError:
				pass
			retriesLeft = retriesLeft - 1

		raise TimeoutError("No response")

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
	def SlaveControllers(self) -> list[Controller]:
		return self.__slaveControllers__

	def NewController(self, address:int=1):
		newController = Controller(self, address=address)
		self.__slaveControllers__.append(newController)
		return newController