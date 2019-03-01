from traits.api import *
from traitsui.api import *
import visa
from cmd_dictionaries import micronix_cmds, oxxius_cmds
import ast
import numpy as np
from time import sleep
import logging
import cfg
import os
import ctypes
from constants import LdcnConstants, IOService
GLOBALS = cfg.Globals()

class BaseController(SingletonHasTraits):
    name = Str('Controller')
    provides = Set()
    requires = Set()

    def __repr__(self):
        return self.name

class ZIDemodController(SingletonHasTraits):
    class_name = 'ZIDemodController'
    #daq = Instance(zi.ziDAQServer)
    hostname = Str('localhost')
    api_level = Int(5)
    port = Int(8004)
    dev_name = Str()

    view = View(
        VGroup(
            Item(name='hostname', label='Hostname', ),
            Item(name='dev_name', label='Device name'),
            HGroup(
                Item(name='port', label='Port', width=-80),

                Item(name='api_level', label='API level', width=-60),
            ),


        ),

    )

    @on_trait_change('hostname','port','api_level')
    def initialize(self):
        self.daq = zi.ziDAQServer(self.hostname, self.port,self.api_level)
        self.dev_name = zhinst.utils.autoDetect(self.daq)

    def subscribe(self,demod_num=0):
        path = '/{}/demod/{}/sample'.format(self.dev_name,demod_num)
        self.daq.subscribe(path)
        self.daq.sync()

    def unsubscribe(self,demod_num=0):
        path = '/{}/demod/{}/sample'.format(self.dev_name, demod_num)
        self.daq.unsubscribe(path)
        self.daq.sync()

    def sync(self):
        self.daq.sync(self.daq)

    def poll(self,duration,timeout=500,fill_flag=0, flat_dict=True):
        data = self.daq.poll(duration,timeout,fill_flag,flat_dict)
        return data


class BaseSerialController(BaseController):
    name = 'Base Serial Controller'
    com_port = Str()
    id_str = Str('')
    id_message = Str('*IDN?')
    baud_rate = Int(38400)
    data_bits = Int(8)
    stop_bits = Enum(visa.constants.StopBits.one,[bit for bit in visa.constants.StopBits])
    parity = Bool(False)
    handshake = Bool(False)
    write_termination = Str('\r')
    read_termination = Str('\r')
    rm = Instance(visa.ResourceManager,transient=True)
    backend = Enum(['@py', '@ni'])
    cntrlr = Any(transient=True)
    initialized = Bool(False,transient=True)
    force_initialize = Button('Initialize')
    timeout = Int(1000)  # milliseconds

    def __init__(self, *args, **kwargs):
        super(BaseSerialController, self).__init__(*args, **kwargs)
        self.find_device()

    def _backend_default(self):
        import os
        if os.name == 'posix':
            return '@py'
        elif os.name == 'nt':
            return '@ni'
        else:
            raise RuntimeError("Platform not supported")

    def find_device(self,timeout=2.0):
        if self.id_str:
            from com_ports import serial_ports
            com_ports = serial_ports()
            rm=visa.ResourceManager(self.backend)
            for com in com_ports:
                try:
                #if True:
                    c = rm.open_resource(com,
                                         read_termination=self.read_termination,
                                         write_termination=self.write_termination)
                    c.timeout = timeout
                    #c.baud_rate = self.baud_rate
                    #c.data_bits = self.data_bits
                    #c.stop_bits = self.stop_bits
                    if self.id_str in c.query(self.id_message):
                        self.com_port = com
                        self.cntrlr = c
                        self.initialized = True
                        break

                except:
                    pass

    def initialize(self):
        try:
            self.cntrlr = self.rm.open_resource(self.com_port,
                                                read_termination=self.read_termination,
                                                write_termination=self.write_termination)
            self.cntrlr.timeout = self.timeout
            self.cntrlr.baud_rate = self.baud_rate
            #self.cntrlr.data_bits = self.data_bits
            #self.cntrlr.stop_bits = self.stop_bits
            self.initialized = True
        except:
            return False
        return True

    #def _com_port_changed(self):
        #self.initialize()

    def decode_reply(self,message):
        raise NotImplementedError

    def _rm_default(self):
        return visa.ResourceManager(self.backend)


    def write(self, message):
        if not self.initialized:
            success = self.initialize()
            if not success:
                return None
        try:
            self.cntrlr.write(message)
            return True
        except:
            return None


    def read(self):
        if not self.initialized:
            success = self.initialize()
            if not success:
                return None
        try:
            return self.cntrlr.read()
        except:
            return None


    def query(self, message):
        if not self.initialized:
            success = self.initialize()
            if not success:
                return None
        try:
            response = self.cntrlr.query(message)
        except:
            response = None
        return response


class BaseStageController(BaseController):
    name = 'Base Stage Controller'
    provides = Set()

    def position(self, axis_num):
        raise NotImplementedError

    def move_rel(self, axis_num, step_size):
        raise NotImplementedError

    def move_abs(self, axis_num, position):
        raise NotImplementedError


class MicronixStageController(BaseSerialController, BaseStageController):
    name = 'Micronix Controller'
    provides = {IOService.AXIS_MOVE_ABSOLUTE,
                IOService.AXIS_MOVE_RELATIVE,
                IOService.AXIS_POSITION}
    id_str = 'MMC-110'
    id_message = '1VER?'
    ntries = Int(100)
    query_status_every = Float(0.01)    #s
    com_port = Str(GLOBALS.STAGE_DEFAULT_COM)
    write_termination = '\n\r'
    read_termination = '\n\r'


    view = View(

        HGroup(
            VGroup(
                Item(name='name', label='Type', style='readonly'),
                Item(name='com_port', label='COM', width=-80,editor=EnumEditor(values=GLOBALS.COM_PORTS)),
                Item(name='initialized', label='Initialized', width=-60, enabled_when='False'),

                ),
            Item(label='     '),
            VGroup(
                Item(name='query_status_every', label='Query Interval', width=-60,
                     tooltip='Delay between status queries when waiting for command to complete'),
                Item(name='ntries', label='Status Queries', width=-60,
                     tooltip='Max number of status queries when waiting for command to complete'),
            ),
            Item(label='     '),
            VGroup(
                Item(name='timeout', label='Time out [ms]',width=-60 ),
                Item(name='baud_rate', label='Baud rate', width=-60),
                Item(name='data_bits', label='Data status_bits', width=-60,),

            ),

        ),
    )

#   def _get_com_port(self):
#        return cfg.devices['micronix_stage'].com_port


    def has_errors(self, status_byte):
        try:
            bits = np.unpackbits(np.uint8(status_byte))
            return bits[0]
        except:
            return 1


    def has_stopped(self, status_byte):
        try:
            bits = np.unpackbits(np.uint8(status_byte))
            return bits[4]
        except:
            return 1

    def decode_reply(self,message):
        if message is None:
            return None
        string = message.strip().replace('#','')
        if '\n' in string:
            return string.split()
        try:
            value = ast.literal_eval(string)
        except:
            value = string
        return value

    def read_errors(self, axis_num):
        if not hasattr(self, 'controller'):
            return []
        errors = self.controller.send_cmd(axis_num, 'read_errors', value='?', response=True)
        if not isinstance(errors, list):
            errors = [errors]
        return errors

    def position(self, axis_num):
        message = '%d%s?'%(axis_num, micronix_cmds['position'])
        for n in range(self.ntries):
            sleep(self.query_status_every)
            status = self.send_cmd(axis_num, 'status_byte', value='?', response=True)
            if self.has_errors(status):
                errs = self.read_errors(axis_num)
            if self.has_stopped(status):
                try:
                    calc, enc = self.query(message).strip().replace('#', '').split(',')
                    return float(calc), float(enc)
                except:
                    pass
        return 0.0,0.0


    def send_cmd(self, axis_num, cmd, value='', response = True):
        val = str(value)
        if axis_num is None:
            return None
        message = '%d%s%s'%(axis_num, micronix_cmds[cmd], val)
        if response:
           # print answer
            return self.decode_reply(self.query(message))
        else:
            return self.write(message)

    def move_rel(self,axis_num, step_size):
        """
        :param axis_num: integer : stage number
        :param step_size: float : amount to move in mm
        :return: success
        """

        ret = self.write('%d%s%.6f' % (axis_num, micronix_cmds['move_rel'], step_size))

        if ret is not None:

            for n in range(self.ntries):
                status = self.send_cmd(axis_num, 'status_byte', value='?', response=True)
                sleep(self.query_status_every)
                if self.has_errors(status):
                    errs = self.read_errors(axis_num)
                if self.has_stopped(status):
                    return True
        return False

    def move_abs(self, axis_num, position):
        ret = self.write('%d%s%.6f' % (axis_num, micronix_cmds['move_abs'], position))
        if ret is not None:
            for n in range(self.ntries):
                status = self.send_cmd(axis_num, 'status_byte', value='?', response=True)
                sleep(self.query_status_every)
                if self.has_stopped(status):
                    return True
        return False


class PicomotorController(BaseStageController):
    name = 'Picomotor Controller'
    ldcn = Any(transient=True)
    initialized = Bool(False)
    provides = {IOService.AXIS_MOVE_ABSOLUTE,
                IOService.AXIS_MOVE_RELATIVE,
                IOService.AXIS_POSITION}
    com_port = Str('COM1')
    mod_version = Int()
    mod_type = Int()
    baud_rate = Enum(19200,[9600, 14400, 19200, 28800, 38400, 57600])
    address = Int(0)
    LINUX_LIBRARY_NAME = "libLdcn.so"
    WIN_LIBRARY_NAME = "Ldcnlib.dll"


    def initialize(self):
        try:
            
            this_dir = os.path.dirname(os.path.realpath(__file__))
            if os.name == 'posix':
                lib_path = os.path.sep.join((this_dir, self.LINUX_LIBRARY_NAME))
                self.ldcn = ctypes.cdll.LoadLibrary(str(lib_path))
            elif os.name == 'nt':
                lib_path = os.path.sep.join((this_dir, self.WIN_LIBRARY_NAME))
                self.ldcn = ctypes.WinDLL(str(lib_path))
            else:
                raise RuntimeError("Platform not supported")
            
            num_modules = self.ldcn.LdcnInit(self.com_port, self.baud_rate)

            if num_modules == 0:
                num_modules = self.ldcn.LdcnFullInit(ctypes.c_char_p(self.com_port),
                                                     ctypes.c_long(self.baud_rate))
            if num_modules == 0:
                print("No Modules found at %s" % self.com_port)
                raise Exception
            # look for pico motor drivers
            pico_addr = 0
            for addr in range(1, num_modules + 1):
                self.ldcn.LdcnReadStatus(addr,LdcnConstants.SEND_ID)
                self.mod_type = self.ldcn.LdcnGetModType(addr)
                self.mod_version = self.ldcn.LdcnGetModVer(addr)
                # print("mod_type: ", mod_type)
                # print("mod_version: ", mod_version)
                if (self.mod_type == LdcnConstants.STEPMODTYPE)\
                        and (self.mod_version >= 50)\
                        and (self.mod_version < 60):
                    pico_addr = addr
                    break
            if pico_addr:
                self.address = pico_addr
            else:
                raise Exception
            self.initialized = True
            return True
        except:
            self.initialized = False
            return False
    # def set_param(self,name, value):
    #     success = self.ldcn.StepSetParam(self.address,self.mode, min_speed,
    #                                      run_current, hld_current, ADLimit, em_acc)

    def position(self, axis_num):
        if not self.initialized and not self.initialize():
            return
        self.ldcn.LdcnReadStatus(self.address,LdcnConstants.SEND_POS)
        return 4*self.ldcn.StepGetPos(self.address)/1e5

    def move_rel(self, axis_num, step_size):
        if not self.initialized and not self.initialize():
            return
        pos = step_size*1e5/4 + self.ldcn.StepGetPos(self.address)
        return self.move_abs(0, pos)

    def move_abs(self, axis_num, position):
        if not self.initialized and not self.initialize():
            return
        self.ldcn.StepStopMotor(self.address, LdcnConstants.STOP_SMOOTH | LdcnConstants.STP_ENABLE_AMP)

        # Load Trajectory ---------------------------------------
        # Position mode (Velocity mode: mode = START_NOW | LOAD_SPEED | LOAD_ACC)
        mode = LdcnConstants.START_NOW | LdcnConstants.LOAD_SPEED | LdcnConstants.LOAD_ACC | LdcnConstants.LOAD_POS
        pos = position*1e5/4 #convert mm to steps
        speed = 250  # 2000 Hz
        acc = 255  # max. acc.
        self.ldcn.StepLoadTraj(self.address, mode, pos, speed, acc, 0)

        # wait end of the motion
        while True:
            self.ldcn.LdcnReadStatus(self.address, LdcnConstants.SEND_POS)
            # read device status and current position
            pos = self.ldcn.StepGetPos(self.address) / 25  # read steps
            #print("Position: %d" % pos)
            status_byte = self.ldcn.LdcnGetStat(self.address)
            if not (self.ldcn.LdcnGetStat(self.address) & LdcnConstants.MOTOR_MOVING):
                break
        # Disable driver amp (STOP_ABRUPT can also be used instead of STOP_SMOOTH)
        self.ldcn.StepStopMotor(self.address, LdcnConstants.STOP_SMOOTH)
        return pos

    def __del__(self):
        self.ldcn.LdcnShutdown()
        super(PicomotorController,self).__del__()
    
from cmd_dictionaries import oxxius_cmds
class OxxiusLaserController(BaseSerialController):
    name = Str('Oxxius Laser Controller')
    #com_port = Str()
    baud_rate = 19200
    write_termination = '\n'
    read_termination = '\r\n'
    settable = List([])

    view = View(

        HGroup(
            VGroup(
                Item(name='name', label='Type', style='readonly'),
                Item(name='com_port', label='COM', width=-80,editor=EnumEditor(values=GLOBALS.COM_PORTS)),
                Item(name='initialized', label='Initialized', width=-60, enabled_when='False'),

                ),
            VGroup(
                Item(name='timeout', label='Time out [ms]',width=-60 ),
                Item(name='baud_rate', label='Baud rate', width=-60),
                Item(name='data_bits', label='Data status_bits', width=-60,),

            ),

        show_border=True,label='Controller'),
    )
    def _settable_default(self):
        return oxxius_cmds.get('settable',[])

    def decode_reply(self, message):
        if message is None:
            return None
        string = message.strip()
        if '=' in string:
            string = string.split('=')[-1]
        try:
            value = ast.literal_eval(string)
        except:
            value = string
        return value

    def read_value(self, value_name):
        if value_name not in oxxius_cmds.keys():
            return None
        message = '?'+oxxius_cmds[value_name]
        response = self.query(message)
        return self.decode_reply(response)

    def write_value(self,value_name, value):
        if value_name not in oxxius_cmds.keys():
            return None
        txt_val = str(value)
        message = '%s=%s'%(oxxius_cmds[value_name],txt_val)
        response = self.query(message).strip()
        if oxxius_cmds[value_name] in response:
            return True
        else:
            return False


class MockMicronixStageController(BaseStageController):
    name = 'Mock Micronix Stage Controller'
    _positions = Dict({})
    provides = {IOService.AXIS_MOVE_ABSOLUTE,
                IOService.AXIS_MOVE_RELATIVE,
                IOService.AXIS_POSITION}
    logger = Any(transient=True)

    def __init__(self,*args, **kwargs):
        super(MockMicronixStageController,self).__init__(*args, **kwargs)
        self.logger = logging.getLogger('__main__')


    def decode_reply(self,message):
        return 1

    def _rm_default(self):
        return visa.ResourceManager()

    def write(self, message):
        return 1

    def read(self):
        return 1

    def query(self, message):
        return 1

    def position(self, axis_num):
        if axis_num in self._positions.keys():
            return (self._positions[axis_num],)*2
        else:
            self._positions[axis_num] = 0.0
            return (0.0,0.0)

    def move_rel(self, axis_num, step_size):
        if axis_num in self._positions.keys():
            self._positions[axis_num]+=step_size
        else:
            self._positions[axis_num]=step_size
        self.logger.info('Mock Axis {} moved {} mm'.format(axis_num, step_size))
        return True

    def move_abs(self, axis_num, position):
        self._positions[axis_num] = position
        self.logger.info('Mock Axis {} moved to position {} mm'.format(axis_num, position))
        return True

if __name__ == '__main__':
    pm = PicomotorController()
    pm.initialize()