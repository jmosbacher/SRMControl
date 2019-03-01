from traits.api import *
from traitsui.api import *
from traitsui.extras.checkbox_column \
    import CheckboxColumn
import numpy as np
from controllers import BaseStageController
from device_manager import DeviceManager
import logging
import math
import cfg
from constants import IOService
GLOBALS = cfg.Globals()

class BaseScanAxis(HasTraits):
    class_name = 'BaseScanAxis'
    axis_name = Str('')
    controller = Any

    def move_to_next_pos(self):
        raise NotImplementedError

    def initialize(self):
        raise NotImplementedError


class CartesianScanAxis(BaseScanAxis):
    axis_name = Str('X')
    phy_name = Str
    axis_num = Int(1)
    mode = Enum('move_abs', ['move_rel','move_abs'])
    reverse_at_end = Bool(True)

    requires = Set({IOService.AXIS_MOVE_RELATIVE,
                    IOService.AXIS_MOVE_ABSOLUTE,
                    IOService.AXIS_POSITION})

    provides = Set({IOService.AXIS_SCAN})
    # Postions #
    start_pos = Float(0.1) #Range(-14.0,14.0,-0.1)
    stop_pos = Float(0.2) #Range(-14.0,14.0,0.1)
    #resolution = Float(0.00002)
    reverse = Bool(False)
    step_size = Float(0.002) #millimeter
    step = Property(Float)
    scan_length = Property(Float)  #millimeter

    nsteps = Property(Int)

    pos_indx = Int(0)
    next_pos = Property(Float)
    controller = Instance(BaseStageController)
    controllers = Property(List)
    #current_pos = Property()

    traits_view = View(
        HGroup(
            # Item(name='axis_name', label='Name',width=-60),
            # Item(name='axis_num', label='Channel',width=-60),
            # Item(name='start_pos', label='Start at [mm]', width=-60),
            # Item(name='stop_pos', label='End at [mm]', width=-60),
            # Item(name='step_size', label='Step size [mm]', width=-60),
            Item(name='controller', label='Device',
                 editor=EnumEditor(name='controllers')),
        ),

    )

    def __iter__(self):
        self.initialize()
        for step in xrange(self.nsteps+1):
            self.pos_indx = step
            yield self.move_to_next_pos()
        if self.reverse_at_end:
            self.reverse = not self.reverse

    def __str__(self):
        return '%s Axis [%d]' %(self.axis_name,self.axis_num)

    def __repr__(self):
        return '%s Axis [%d]' %(self.axis_name,self.axis_num)

    def _controller_default(self):
        cntrl = None
        for cntrlr in self.find_devices():
            if GLOBALS.STAGE_DEFAULT in cntrlr.name:
                return cntrlr
            else:
                cntrl = cntrlr
        return cntrl

    def _get_controllers(self):
        cntrlrs = []
        cntrlrs.extend([controller for controller in self.find_devices()])
        return cntrlrs

    @property_depends_on('step_size,stop_pos,start_pos')
    def _get_nsteps(self):
        if self.step_size:
            return abs(int(self.scan_length/self.step_size))
        else:
            return 1

    @property_depends_on('start_pos,stop_pos')
    def _get_scan_length(self):
        return abs(self.stop_pos-self.start_pos)

    @property_depends_on('step_size,stop_pos,start_pos')
    def _get_step(self):
        return math.copysign(self.step_size,self.stop_pos-self.start_pos)

    def current_pos(self):
        return self.controller.position(self.axis_num)[1]

    def _get_next_pos(self):
        if self.reverse:
            return self.stop_pos - self.pos_indx*self.step
        return self.start_pos + self.pos_indx*self.step

    def initialize(self):
        success = self.controller.move_abs(self.axis_num, self.start_pos)
        if not success:
            logger = logging.getLogger('__main__')
            logger.info('Axis %d failed to move to start position %g'%(self.axis_num, self.start_pos ))
            return None

    def move_abs(self,pos=None):
        if pos is None:
            next_pos = self.next_pos
        else:
            next_pos = pos
        success = self.controller.move_abs(self.axis_num, next_pos)
        if not success:
            logger = logging.getLogger('__main__')
            logger.info('Axis %d failed to move to position %g' % (self.axis_num, self.next_pos))
            return None
        return success

    def move_rel(self,stp=None):
        if stp is None:
            step = self.step
        else:
            step = stp
        success = self.controller.move_rel(self.axis_num, self.step)

        if not success:
            logger = logging.getLogger('__main__')
            logger.info('Axis %d failed to move to by %g' % (self.axis_num, self.step))
            return None
        return success

    def move_to_next_pos(self):
        success = getattr(self, self.mode)()
        if success is None:
            return None
        return self.current_pos()

    def find_devices(self):
        dev_manager = DeviceManager()
        cntrlrs = []
        if not dev_manager.devices:
            return []
        for dev in dev_manager.devices:
            if dev is Undefined:
                continue
            if not hasattr(dev, 'controller'):
                continue
            if not hasattr(dev, 'provides'):
                continue
            if IOService.services_all(self.requires, dev.controller.provides):
                cntrlrs.append(dev.controller)
        return cntrlrs




class AxisTableEditor(TableEditor):
    columns = [

        ObjectColumn(name='axis_name',label='Name', width=0.20),
        ObjectColumn(name='axis_num',label='#', width=0.10),
        ObjectColumn(name='start_pos', label='Start [mm]', width=0.20),
        ObjectColumn(name='stop_pos', label='Stop [mm]', width=0.20),
        ObjectColumn(name='step_size', label='Step [mm]', width=0.20),
        CheckboxColumn(name='reverse_at_end', label='Snake', width=0.20),
        ObjectColumn(name='nsteps', label='# Steps',style='readonly', width=0.20),


    ]
    #deletable = True
    #row_factory = CartesianScanAxis
    reorderable = True
    show_toolbar = True
    auto_size = True
