from enum import Enum

class MockDevices(Enum):
    MOCK_Dev1 = 1
    MOCK_Dev2 = 2

class System(object):
    devices = [dev for dev in MockDevices]
    mock = True
    @staticmethod
    def local():
        return System()

