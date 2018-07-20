from __future__ import print_function
from enum import IntEnum
from enum import Enum as PyEnum


class DataDimension(IntEnum):
    D0 = 0
    D1 = 1
    D2 = 2
    D3 = 3
    DN = 999


class UpdateDataMode(PyEnum):
    DEFAULT = 0
    REPLACE = 1
    ROLLING = 2
    LOOPING = 3
    BYINDEX = 4

class ExperimentStatus(IntEnum):
    IDLE = 0
    ACTIVE = 1
    QUEUED = 2
    PAUSED = 3
    CANCELED = -1

class ReadMode(IntEnum):
    LIVE = 0
    FIFO = 1
    LIFO = 2



    """
    CONTINOUS = (1,0,0)
    CONTINOUS_BUFFERED = (1,1,0)
    CONTINOUS_BUFFERED_FIFO = (1,1,1)
    CONTINOUS_BUFFERED_LIFO = (1,1,2)
    CONTINOUS_LIVE = (1,2,0)

    NSAMPLES = (2,0,0)
    ON_DEMAND = (3,0,0)
    
    """



class IOService(PyEnum):
    DAQ = (1,0,0)
    DAQ_READ = (1,1,0)
    DAQ_WRITE = (1,2,0)
    DAQ_READ_VOLTAGE = (1,1,1)
    DAQ_READ_DIGITAL = (1,1,2)
    DAQ_READ_FREQUENCY = (1,1,3)
    DAQ_READ_COUNT = (1,1,4)
    DAQ_WRITE_VOLTAGE = (1,2,1)

    CAM = (2,0,0)
    CAM_READ = (2,1,0)

    AXIS = (3,0,0)
    AXIS_POSITION = (3,1,0)
    AXIS_MOVE = (3,2,0)
    AXIS_MOVE_RELATIVE = (3, 2, 1)
    AXIS_MOVE_ABSOLUTE = (3, 2, 2)
    AXIS_SCAN = (3, 3, 0)

    def __init__(self, instrument, direction, service):
        self.instrument = instrument
        self.direction = direction
        self.service = service

    def __iter__(self):
        yield self.instrument
        yield self.direction
        yield self.service

    def subservice_of(self, service):
        return all([(not s) or (s == ss) for s, ss in zip(service, self)])

    def has_subservice(self, service):
        return all([(not s) or (s == ss) for s, ss in zip(self, service)])

    @staticmethod
    def services_all(rset, pset):
        # rset: required set of services
        # pset: provided set of services
        return all([any([req.has_subservice(s) for s in pset]) for req in rset])

    @staticmethod
    def services_any(rset, pset):
        return any([any([req.has_subservice(s) for s in pset]) for req in rset])

    @staticmethod
    def service_score(rset, pset):
        return len([any([req.has_subservice(s) for s in pset]) for req in rset])



class LdcnConstants(IntEnum):
    STEPMODTYPE     = 3
    SEND_ID         = 0x20
    SPEED_8X        = 0x00      #use 8x timing
    IGNORE_LIMITS   = 0x04      #Do not stop automatically on limit switches
    POWER_ON        = 0x08      #set when motor power is on
    STOP_SMOOTH     = 0x08      #set to decelerate motor smoothly
    STP_ENABLE_AMP  = 0x01      #raise amp enable output
    STP_DISABLE_AMP = 0x00      #lower amp enable output
    STP_AMP_ENABLED = 0x04      #set if amplifier is enabled
    MOTOR_MOVING    = 0x01      #set if motot is moving
    START_NOW       = 0x80
    LOAD_SPEED      = 0x02
    LOAD_ACC        = 0x04
    LOAD_POS        = 0x01
    SEND_POS        = 0x01
    STEP_REV        = 0x10      #reverse dir
    TYPE_TINY       = 0x10
    TYPE_STD        = 0x00
    SET_CH_A        = 0x00
    SET_CH_B        = 0x01

if __name__ == '__main__':
    print('True',IOService.DAQ_READ_COUNT.subservice_of(IOService.DAQ))
    print('False',IOService.DAQ.subservice_of(IOService.DAQ_READ_COUNT))

    print('True',IOService.DAQ.subservice_of(IOService.DAQ))
    print('True',IOService.DAQ.has_subservice(IOService.DAQ))
    print('True',IOService.DAQ_READ_COUNT.subservice_of(IOService.DAQ_READ))
    print('False',IOService.DAQ.subservice_of(IOService.DAQ_READ_COUNT))
    print('False',IOService.CAM.subservice_of(IOService.DAQ_READ_COUNT))
    print('False',IOService.CAM_READ.subservice_of(IOService.DAQ_READ_COUNT))
