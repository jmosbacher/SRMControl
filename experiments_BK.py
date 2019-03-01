from traits.api import *
from traitsui.api import *
import numpy as np
#from measurements import BaseMeasurement
from scan_axes import BaseScanAxis, AxisTableEditor, CartesianScanAxis
from global_states import BaseGlobalState, global_states_dict
import collections
from log_viewer import LogStream
import logging
from time import sleep
import time
from threading import Thread
from measurements import BaseMeasurement, measurement_dict, MeasurementTableEditor, CounterMeasurement, VoltageMeasurement
from auxilary_functions import multi_enum, progress_bar
#from data_viewers import BaseViewer
from manual_controls import ManualAxisControl

class BaseExperiment(HasTraits):
    class_name = 'BaseExperiment'
    name = Str('')

    microscope = Any

    start_time = Float()
    end_time = Float()

    running = Bool(False)
    paused = Bool(False)
    status = Property(Str)
    user_wants_stop = Bool(False)
    system_state_type = Enum('MockGlobalState',global_states_dict.keys())
    states = Dict()
    system_state = Instance(BaseGlobalState)

    log = Instance(LogStream,transient=True)

    start = Button('Start')
    stop = Button('Stop')
    pause = Button('Pause')
    resume = Button('Resume')

    def _get_status(self):
        if self.running:
            return 'Running'
        elif self.paused:
            return 'Paused'
        else:
            return 'Idle'

    def exp_worker(self):
        return NotImplementedError

    def __init__(self,*args,**kwargs):
        super(BaseExperiment,self).__init__(*args,**kwargs)
        self.microscope = kwargs.get('microscope', None)

    def _log_default(self):
        log = LogStream()
        log.config_logger(__name__)
        return log

    def _start_fired(self):
        t = Thread(target=self.exp_worker)
        t.setDaemon(True)
        t.start()

    def _stop_fired(self):
        self.user_wants_stop = True

    def _pause_fired(self):
        self.paused = True

    def _resume_fired(self):
        self.paused = False

    def _system_state_type_changed(self,new):
        self.system_state = self.states[new]

    def _states_default(self):
        return {key:value() for key, value in global_states_dict.items() }

    def _system_state_default(self):
        return global_states_dict[self.system_state_type]()

def format_pos(pos):
    if pos is None:
        return ''
    return '  '.join(['%.6f '%p for p in pos])

class SWSynchronizedScan(BaseExperiment):
    class_name = 'SWSynchronizedScan'
    name = Str('SW Synchronized Scan')
    meas_per_loc = Property()

    pre_allocate_memory = Bool(True)
    # Data display
    # display_mode = Enum('Live',['Live', 'When Done' ])
    # display_every = Int(1)
    # display = Instance(BaseViewer)
    # display3d = Instance(BaseViewer)
    #display_options = List()
    scan_axes = List(BaseScanAxis)
    sel_axis = Instance(BaseScanAxis)
    remove_axis = Button('Remove')
    add_axis = Button('Add')

    measurements = List(BaseMeasurement)
    measurement = Instance(BaseMeasurement)
    add_meas_type = Enum(measurement_dict.keys())
    remove_meas = Button('Remove')
    add_meas = Button('Add')

    ## set new scan area
    set_scan_area = Button('Set')
    get_cursor = Button('Cursor')
    get_current = Button('Current')
    move_to_cursor = Button('Move to cursor')
    scan_center = Tuple((0.0,0.0,0.0),cols=3,labels=['X','Y','Z'])
    volume = Tuple((0.001,0.001,0.001),cols=3,labels=['X','Y','Z'])
    steps = Tuple((0.00005,0.00005,0.00005),cols=3,labels=['X','Y','Z'])

    #positions = Array() #Instance(collections.OrderedDict)
    position = Tuple()  #Instance(collections.OrderedDict)
    pos_idx = Tuple()
    ndone = Int(0)
    perc_done = Range(low=0,high=100,value=0)
    position_text = Property(Str,dependes_on='position')
    #npos = Property(Int)
    done_callback = Function()
    every_step_callback = Function()
    debug = Bool(False)

    axis_control = Instance(ManualAxisControl,())

    view = View(
        Tabbed(
            VGroup(
                HGroup(
                    Item(name='start', show_label=False, visible_when='not running'),
                    Item(name='stop', show_label=False, visible_when='running'),
                    Item(name='pause', show_label=False, visible_when='running and not paused'),
                    Item(name='resume', show_label=False, visible_when='paused'),
                    spring,
                    Item(name='position', label='Position', style='readonly',format_func=format_pos),
                    Item(name='perc_done', label='Done',style='readonly',
                         format_func=progress_bar(nsymb=40,left_symb='- ',done_symb='#'),
                         width=240,enabled_when='False'),
                    show_border=True, label='Scan'),

                Group(
                    HGroup(
                            VGroup(
                                HGroup(
                                    Item(name='measurement', label='Measurement Preview',
                                         editor=EnumEditor(name='measurements')),
                                    Item(name='measurement', show_label=False,
                                         editor=InstanceEditor(view='data_view'),
                                         enabled_when='measurement',),
                                ),


                                VGroup(
                                    HGroup(
                                        Item(name='get_cursor', show_label=False, width=-80),
                                        Item(name='get_current', show_label=False, width=-80),
                                        Item(name='set_scan_area', show_label=False, width=-80),
                                    ),
                                    Item(name='scan_center', label='Center [mm]', width=-250),
                                    Item(name='volume', label='Volume [mm^3]', width=-250),
                                    Item(name='steps', label='Steps', width=-250),

                                    show_border=True, label='Set scan volume around  cursor position',
                                    enabled_when='not running'),

                                Group(Item(name='axis_control', editor=InstanceEditor(view='vert_view'),
                                           show_label=False, style='custom'),
                                      show_border=True, label='Axis Control'),

                            ),
                        spring,
                            VGroup(
                                #Item(name='display', label='Display Mode',
                                     #editor=EnumEditor(name='display_options'),
                                     #style='simple', springy=False),
                                #Item(name='display', show_label=False, style='custom', springy=False),
                            show_border=False,),

                        ),

                    show_border=True, label='Measurement'),



                 label='Control'),


            VGroup(
                VGroup(
                    Item(name='system_state_type', show_label=False),
                    Item(name='system_state', style='custom', show_label=False),
                    show_border=True, label='System state'),

                HGroup(
                    VGroup(
                        HGroup(
                            Item(name='add_meas_type', show_label=False),
                            Item(name='add_meas', show_label=False),
                            Item(name='remove_meas', show_label=False, enabled_when='measurement'), ),

                        Item(name='measurements', show_label=False,
                             editor=MeasurementTableEditor(selected='measurement'), height=100,width=-400),
                    ),
                    Item(name='measurement', show_label=False, style='custom'),
                    show_border=True, label='measurements', scrollable=True),

                VGroup(HGroup(Item(name='add_axis', show_label=False),
                              Item(name='remove_axis', show_label=False, enabled_when='sel_axis'), ),

                       Item(name='scan_axes', show_label=False,
                            editor=AxisTableEditor(selected='sel_axis'), height=100),

                       Item(name='sel_axis', show_label=False, style='custom'),
                       Item(label=' ', visible_when='not sel_axis'),
                       show_border=True, label='ScanAxes', scrollable=True),

                spring,

                enabled_when='not running',label='Scan Settings'),
        Group(
            #Item(name='display3d', show_label=False, style='custom', springy=False),
        label='3D Visualization'),
        ),


    scrollable=True,
    resizable=True)

    #def _display3d_default(self):
        #return ThreeDPointViewer()

    # def _get_cursor_fired(self):
    #     x0, y0 = tuple(self.display.cursor.current_position)
    #     z0 = 0.0
    #     zaxis = self.display.zaxis
    #     if zaxis:
    #         z0 = zaxis.start_pos + (zaxis.stop_pos - zaxis.start_pos) * self.display.zpos / zaxis.nsteps
    #     self.scan_center = x0, y0, z0

    def _get_current_fired(self):
        xyz = [0.0,0.0,0.0]
        for n,axis in enumerate(self.scan_axes):
            if axis.axis_name=='X':
                xyz[0] = axis.current_pos()
            elif axis.axis_name == 'Y':
                xyz[1] = axis.current_pos()

            elif axis.axis_name == 'Z':
                xyz[2] = axis.current_pos()
            else:
                xyz[n] = axis.current_pos()
        self.scan_center = tuple(xyz)

    def _move_to_cursor_fired(self):
        logger = logging.getLogger('__main__')
        if self.measurement and self.measurement.initialized:
            self.xaxis.move_abs(pos=self.measurement.display.xpos)
            self.yaxis.move_abs(pos=self.measurement.display.ypos)
            logger.info('x: {} y: {}'.format(self.xaxis.current_pos(),self.yaxis.current_pos()))
        else:
            logger.info('Measurement not initialized')

    def _set_scan_area_fired(self):
        x0,y0, z0 = self.scan_center
        xaxis,yaxis,zaxis = self.display.xaxis, self.display.yaxis, self.display.zaxis,
        if xaxis:
            xaxis.start_pos, xaxis.stop_pos = x0-self.volume[0]/2, x0+self.volume[0]/2
        if yaxis:
            yaxis.start_pos, yaxis.stop_pos = y0-self.volume[1]/2, y0+self.volume[1]/2
        if zaxis:
            #z0 = zaxis.start_pos+(zaxis.stop_pos-zaxis.start_pos)*self.display.zpos/zaxis.nsteps
            zaxis.start_pos, zaxis.stop_pos = z0 - self.volume[2] / 2, z0 + self.volume[2] / 2

    def _remove_axis_fired(self):
        self.scan_axes.remove(self.sel_axis)
        self.sel_axis = None

    def _add_axis_fired(self):
        self.scan_axes.append(CartesianScanAxis())

    def _remove_meas_fired(self):
        self.measurements.remove(self.measurement)
        self.measurement = None

    def _add_meas_fired(self):
        if self.add_meas_type:
            self.measurements.append(measurement_dict[self.add_meas_type]())

    def _measurements_default(self):
        return [CounterMeasurement()]

    #def _display_default(self):
     #   display = XYSliceBrowser()

      #  return display


    def _scan_axes_default(self):
        names = ['X', 'Y', 'Z']
        axes = []
        for n,name in enumerate(names):
            new = CartesianScanAxis()
            new.axis_num = n + 1
            new.axis_name = name
            new.step_size = 0.01
            axes.append(new)
        return list(reversed(axes))

    def _positions_default(self):
        return [(0.0,0.0,0.0)] #collections.OrderedDict()

    def _position_default(self):
        return (0.0,0.0,0.0) #collections.OrderedDict()

    def _get_position_text(self):
        return str(self.position)

    def _get_meas_per_loc(self):
        return len(self.measurements)


    def npos(self):
        return np.product([axis.nsteps+1 for axis in self.scan_axes ])

    def shape(self):
        return [axis.nsteps+1 for axis in self.scan_axes]

    def _ndone_changed(self, new):
        self.perc_done = int(round(100 * new / self.npos() + 0.5))


    def initialize_display(self):
        for meas in self.measurements:
            meas.initialize_display()

    # def initialize_display3d(self):
    #     #self.display3d = ThreeDPointViewer()
    #     self.display3d.measurements = self.measurements
    #     if len(self.measurements):
    #         self.display3d.measurement = self.measurements[0]
    #     self.display3d.positions = self.positions
        #self.display3d.edit_traits()
        #self.display3d.plot_measurement()

        #self.display3d.update_data()


    def allocate_memory(self):
        if self.pre_allocate_memory:
            self.positions = np.empty(self.shape()+[len(self.scan_axes)])
        for meas in self.measurements:
            success = meas.allocate_memory(self.shape())
            if not success:
                raise RuntimeError

    def perform_measurements(self, pos_idx):
        for meas in self.measurements:
            success = meas.perform(pos_idx)
            if not success:
                raise RuntimeError

    def initialize_axes(self):
        from controllers import MockMicronixStageController
        controller = MockMicronixStageController()
        # try:
        #     import cfg
        #     test = cfg.devices.micronix_stage.controller
        #     if test.initialize():
        #         controller = test
        # except:
        #     pass
        for axis in self.scan_axes:
            axis.controller = controller
            axis.reverse = False
            #axis.initialize()

    def exp_worker(self):
        self.start_time = time.time()
        logger = logging.getLogger('__main__')
        #try:
        self.running = True
        self.allocate_memory()
        self.system_state.activate()
        self.initialize_display()
        self.initialize_axes()
        #except:
            #logger.info('Failed to initialize. Deactivating system.')
            #self.user_wants_stop = True
        n=0
        try:
            if self.user_wants_stop:
                raise RuntimeError

            if not self.pre_allocate_memory:
                positions = []
            for n, (idx,position) in enumerate(multi_enum(self.scan_axes)):

                if None in position:
                    break

                while self.paused:
                    if self.user_wants_stop:
                        logger.info('Stopped by user.')
                        break
                    sleep(0.05)

                if self.user_wants_stop:
                    logger.info('Stopped by user.')
                    break

                self.position = position
                index = []
                for i, axis in enumerate(self.scan_axes):
                    if axis.reverse:
                        index.append(axis.nsteps-idx[i])
                    else:
                        index.append(idx[i])
                ##Testing
                index = tuple(index)
                if self.pre_allocate_memory:
                    self.positions[index] = position
                else:
                    positions.append(position)

                self.perform_measurements(index)

                #logger.info(' , '.join(['%.6f'%p for p in position]))
                #sleep(0.02)
                if callable(self.every_step_callback):
                    self.every_step_callback(self)
                self.pos_idx = index
                self.ndone = n


            if not self.pre_allocate_memory:
                self.positions = np.asarray(positions)

            logger.info('Done. Deactivating system.')

        except:
            logger.info('Failed at location number %d. Deactivating system.'%n)

        self.system_state.deactivate()
        self.running = False
        self.paused = False
        logger.info('System deactivated.')
        if callable(self.done_callback):
            self.done_callback(self)
        self.user_wants_stop = False
        self.end_time = time.time()
        logger.info('Experiment ran for %f seconds'%(self.end_time-self.start_time))
        if len(self.scan_axes)==3:
            self.initialize_display3d()

if __name__=='__main__':
    from controllers import MockMicronixStageController
    from scan_axes import CartesianScanAxis
    from global_states import MockGlobalState

    def callback(exp):
        logger = logging.getLogger(__name__)
        logger.info(exp.position_text)


    naxes = 3
    controller = MockMicronixStageController()
    exp = SWSynchronizedScan()
    names = ['X','Y','Z']
    for n in range(naxes):
        new = CartesianScanAxis()
        new.controller = controller
        new.axis_num = n+1
        new.axis_name = names[n]
        new.step_size = 0.1
        exp.scan_axes.append(new)

    exp.system_state = MockGlobalState()
    exp.every_step_callback = callback
    exp.configure_traits()


