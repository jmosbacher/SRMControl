from traits.api import *
from traitsui.api import *
import numpy as np
from scan_axes import BaseScanAxis, AxisTableEditor
from global_state_manager import GlobalStateManager
from global_states import DAQRead
from log_viewer import LogStream
import logging
from time import sleep
import time
from threading import Thread
from measurements import BaseMeasurement,measurement_dict, \
    MeasurementTableEditor, CounterMeasurement, VoltageMeasurement
from auxilary_functions import multi_enum, progress_bar
from manual_controls import ManualAxisControl, XYZStageController
from scan_axes import CartesianScanAxis
from constants import UpdateDataMode, ExperimentStatus
import cfg
GLOBALS = cfg.Globals()


def format_pos(pos):
    if pos is None:
        return ''
    return '  '.join(['%.6f '%p for p in pos])

class BaseExperiment(HasTraits):
    class_name = 'BaseExperiment'
    name = Str('')

    #microscope = Any

    start_time = Float()
    end_time = Float()

    running = Bool(False)
    paused = Bool(False)
    queued = Bool(False)
    status = Enum(ExperimentStatus.IDLE, [es for es in ExperimentStatus])
    ndone = Int(0)
    perc_done = Range(low=0.0, high=100.0, value=0.0)
    perc_done_bar = Unicode()

    user_wants_stop = Bool(False)



    state_manager = Instance(GlobalStateManager, (),transient=True)

    measurements = List(BaseMeasurement)
    measurement = Instance(BaseMeasurement)
    add_meas_type = Enum('Counter Measurement', measurement_dict.keys())
    remove_meas = Button('Remove')
    add_meas = Button('Add')
    log = Instance(LogStream,transient=True)

    start = Button('Run')
    stop = Button('Stop')
    pause = Button('Pause')
    #resume = Button('Resume')

    summary_view = View()


    def _remove_meas_fired(self):
        self.measurements.remove(self.measurement)
        self.measurement = None

    def _add_meas_fired(self):
        if self.add_meas_type:
            self.add_measurement(self.add_meas_type)

    def add_measurement(self, name):
        if name in measurement_dict:
            new = measurement_dict[name]()
            new.experiment = True
            #new.update_mode = UpdateDataMode.BYINDEX
            self.measurements.append(new)

    def _measurements_default(self):
        return []

    def exp_worker(self):
        return NotImplementedError

    def __init__(self,*args,**kwargs):
        super(BaseExperiment,self).__init__(*args,**kwargs)
        #self.microscope = kwargs.get('microscope', None)

    def _log_default(self):
        log = LogStream()
        log.config_logger(__name__)
        return log

    @on_trait_change('start')
    def _start(self):
        if self.status == ExperimentStatus.IDLE:
            self.status = ExperimentStatus.QUEUED

        if self.status == ExperimentStatus.PAUSED:
            self.status = ExperimentStatus.ACTIVE

    @on_trait_change('pause')
    def _pause(self):
        if self.status == ExperimentStatus.ACTIVE:
            self.status = ExperimentStatus.PAUSED

    @on_trait_change('stop')
    def _stop(self):
        if self.status == ExperimentStatus.QUEUED:
            self.status = ExperimentStatus.IDLE

        elif self.status == ExperimentStatus.IDLE:
            pass

        else:
            self.status = ExperimentStatus.CANCELED



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

    ## set new scan area
    set_scan_area = Button('Set')
    get_cursor = Button('Cursor')
    get_current = Button('Current')
    scan_center = Tuple((0.0,0.0,0.0),cols=3,labels=['X','Y','Z'])
    volume = Tuple((0.001,0.001,0.001),cols=3,labels=['X','Y','Z'])
    steps = Tuple((0.00005,0.00005,0.00005),cols=3,labels=['X','Y','Z'])

    positions = Array() #Instance(collections.OrderedDict)
    position = Tuple()  #Instance(collections.OrderedDict)
    pos_idx = Tuple()

    meas_delay = Float(0.03) #in seconds

    #position_text = Property(Str,dependes_on='position')
    npos = Property(Int)
    done_callback = Function()
    every_step_callback = Function()
    debug = Bool(False)

    axis_control = Instance(XYZStageController,())

    traits_view = View(
        Tabbed(
            VGroup(
                HGroup(
                    Item(name='start', show_label=False, visible_when='status != 1'),
                    Item(name='stop', show_label=False, visible_when='status != 0'),
                    Item(name='pause', show_label=False, visible_when='status == 1'),

                    spring,
                    Item(name='position', label='Position', style='readonly',format_func=format_pos),
                    Item(name='perc_done_bar', show_label=False, style='readonly',
                        width=240, enabled_when='False'),
                    show_border=True, label='Scan'),

                Group(
                    HGroup(
                            VGroup(

                                VGroup(
                                    HGroup(
                                        Item(name='get_cursor', show_label=False,
                                             width=-80,),
                                        Item(name='get_current', show_label=False, width=-80),
                                        Item(name='set_scan_area', show_label=False, width=-80),
                                    ),
                                    Item(name='scan_center', label='Center [mm]', width=-250),
                                    Item(name='volume', label='Volume [mm^3]', width=-250),
                                    Item(name='steps', label='Steps', width=-250),

                                    show_border=True, label='Set scan volume around position',
                                    enabled_when='status == 0'),

                                HGroup(VGroup(spring,
                                           Item(name='axis_control', editor=InstanceEditor(view='settings_view'),
                                                width=-200,show_label=False, style='custom'),
                                       spring),
                                    Item(name='axis_control', editor=InstanceEditor(view='button_view'),
                                           width=-200,height=-200,show_label=False, style='custom'),


                                      show_border=True, label='Axis Control'),

                            spring),
                        spring,

                        VGroup(
                            Item(name='measurement', show_label=False, style='custom',
                                 editor=EnumEditor(name='measurements',cols=4),),

                            Item(name='measurement', editor=InstanceEditor(view='data_view')
                                 , show_label=False, style='custom'),
                        ),
                        ),


                    show_border=True, label='Measurement'),

                 label='Control'),


            VGroup(

                VGroup(
                    HGroup(
                        #Item(name='system_state_type', show_label=False),
                        Item(name='state_manager',style='custom',
                             editor=InstanceEditor(view='select_view'), show_label=False),
                        show_border=True, label='System state'),

                    VGroup(
                        HGroup(
                            Item(name='add_meas_type', style='custom', show_label=False),
                            Item(name='add_meas', show_label=False),
                            Item(name='remove_meas', show_label=False, enabled_when='measurement'),
                            Item(name='meas_delay', label='Delay', enabled_when='measurement'),
                        ),
                        VGroup(
                            Item(name='measurements', show_label=False,
                                 editor=MeasurementTableEditor(selected='measurement')),
                            Item(name='measurement', show_label=False,style='custom',),
                            ),

                        show_border=True, label='measurements', scrollable=True),


                    ),


                VGroup(HGroup(Item(name='add_axis', show_label=False),
                              Item(name='remove_axis', show_label=False, enabled_when='sel_axis'), ),

                       Item(name='scan_axes', show_label=False,
                            editor=AxisTableEditor(selected='sel_axis'), height=100),

                       Item(name='sel_axis', show_label=False, style='custom'),
                       Item(label=' ', visible_when='not sel_axis'),
                       show_border=True, label='ScanAxes', scrollable=True),

                spring,

                enabled_when='status == 0',label='Protocol', scrollable=True),
        Group(
            #Item(name='display3d', show_label=False, style='custom', springy=False),
        label='3D Visualization'),
        ),


    scrollable=True,
    resizable=True)


    summary_view = View(
        VGroup(
            HGroup(
                Item(name='npos', label='Positions',style='readonly' ),
                Item(name='meas_per_loc', label='Measurements per location', style='readonly' ),

            )
        ),
    )

    #def _display3d_default(self):
        #return ThreeDPointViewer()

    def _get_cursor_fired(self):
        xyz = [0.0,0.0,0.0]
        xaxis, yaxis, zaxis = self.scan_axes
        for n,axis in enumerate(self.scan_axes):
            if axis.axis_name in ['X', 'x', 0]:
                xyz[0] = axis.start_pos + (axis.stop_pos - axis.start_pos) * self.measurement.display.xpos / axis.nsteps
            elif axis.axis_name in ['Y', 'y', 1]:
                xyz[1] = axis.start_pos + (axis.stop_pos - axis.start_pos) * self.measurement.display.ypos / axis.nsteps
            elif axis.axis_name == 'Z' and hasattr(self.measurement.display, 'zpos'):
                xyz[2] = axis.start_pos + (axis.stop_pos - zaxis.start_pos) * self.measurement.display.zpos / axis.nsteps
        self.scan_center = x0, y0, z0

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
                xyz[2-n] = axis.current_pos()
        self.scan_center = tuple(xyz)


    def _set_scan_area_fired(self):
        x0,y0,z0 = self.scan_center
        dx,dy,dz = self.steps
        for n,axis in enumerate(self.scan_axes):
            if axis.axis_name=='X':
                axis.start_pos, axis.stop_pos = x0 - self.volume[0] / 2, x0 + self.volume[0] / 2
                axis.step_size = dx
            elif axis.axis_name == 'Y':
                axis.start_pos, axis.stop_pos = y0 - self.volume[1] / 2, y0 + self.volume[1] / 2
                axis.step_size = dy
            elif axis.axis_name == 'Z':
                axis.start_pos, axis.stop_pos = z0 - self.volume[2] / 2, z0 + self.volume[2] / 2
                axis.step_size = dz

    def _remove_axis_fired(self):
        self.scan_axes.remove(self.sel_axis)
        self.sel_axis = None

    def _add_axis_fired(self):
        self.scan_axes.append(CartesianScanAxis())

    def _scan_axes_default(self):
        names = ['X', 'Y', 'Z']
        axes = []
        for n,name in enumerate(names):
            new = CartesianScanAxis()
            new.axis_num = n + 1
            new.axis_name = name
            new.step_size = 1e-5
            axes.append(new)
        return list(reversed(axes))

    def _positions_default(self):
        return [(0.0,0.0,0.0)] #collections.OrderedDict()

    def _position_default(self):
        return (0.0,0.0,0.0) #collections.OrderedDict()

    def _pos_idx_default(self):
        return (0,0,0)

    def _get_position_text(self):
        return format_pos(self.position)

    def _get_meas_per_loc(self):
        return len(self.measurements)

    @property_depends_on('scan_axes[]')
    def _get_npos(self):
        return np.product([axis.nsteps+1 for axis in self.scan_axes ])
    
    def nposs(self):
        return np.product([axis.nsteps + 1 for axis in self.scan_axes])

    def shape(self):
        return [axis.nsteps+1 for axis in self.scan_axes]

    def _ndone_changed(self,new):
        if new and self.npos:
            self.perc_done = round(100*new/self.nposs() + 0.5)
            self.perc_done_bar = progress_bar(nsymb=30)(self.perc_done)


    def initialize_display(self):
        for meas in self.measurements:
            meas.initialize_display()
        #self.display.measurements = self.measurements
        pass


    def allocate_memory(self):
        if self.pre_allocate_memory:
            self.positions = np.empty(self.shape()+[len(self.scan_axes)])
            for meas in self.measurements:
                #meas.positions = self.positions
                success = meas.allocate_memory(tuple(self.shape()))
                if not success:
                    raise RuntimeError

    def perform_measurements(self, pos_idx):
        sleep(self.meas_delay)

        for meas in self.measurements:
            success = meas.perform(pos_idx)
            if not success:
                raise RuntimeError('Measurement was not successful')


    def initialize_axes(self):
        if GLOBALS.MOCK_STAGE:
            from controllers import MockMicronixStageController
            controller = MockMicronixStageController()
        else:
            from controllers import MicronixStageController
            controller = MicronixStageController()

        for axis in self.scan_axes:
            axis.controller = controller
            axis.reverse = False
            #axis.initialize()

    def exp_worker(self):
        self.start_time = time.time()
        logger = logging.getLogger('__main__')
        #try:
        self.status = ExperimentStatus.ACTIVE
        self.allocate_memory()

        self.initialize_display()
        self.initialize_axes()
        #except:
            #logger.info('Failed to initialize. Deactivating system.')
            #self.user_wants_stop = True

        if not self.pre_allocate_memory:
            positions = []

        #with self.state_manager as state:
        n=0
        try:
            self.state_manager.activate()
            if self.status == ExperimentStatus.CANCELED:
                raise RuntimeError

            for n, (idx, position) in enumerate(multi_enum(self.scan_axes)):

                if None in position:
                    break

                while self.status == ExperimentStatus.PAUSED:
                    if self.status == ExperimentStatus.CANCELED:
                        logger.info('Stopped by user.')
                        #self.ndone = 0
                        break

                    sleep(0.05)

                if self.status == ExperimentStatus.CANCELED:
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
        except:
            logger.info('Exception raised in scan loop at position {}.'.format(n))

        if not self.pre_allocate_memory:
            self.positions = np.asarray(positions)

        logger.info('Done. Deactivating system.')
        self.state_manager.deactivate()

        logger.info('System deactivated.')
        if callable(self.done_callback):
            self.done_callback(self)
        self.end_time = time.time()

        logger.info('Experiment ran for %f seconds'%(self.end_time-self.start_time))
        self.status = ExperimentStatus.IDLE


class StatusColumn(ObjectColumn):
    editable = False

    def is_editable( self, object ):
        return False

    #def get_width(self, object ):
       # return 40

    def get_value(self, object):
        return object.status.name

    def get_cell_color( self, object ):
        if object.status == ExperimentStatus.ACTIVE:
            return '#66ff66' #Green
        elif object.status == ExperimentStatus.PAUSED:
            return '#ffb732' #orange
        elif object.status == ExperimentStatus.QUEUED:
            return '#e5e500' #yellow
        elif object.status == ExperimentStatus.CANCELED:
            return '#990000' # red
        else:
            return 255,255,255

from progress_column import ProgressColumn
def format_time(secs):
    if secs:
        return time.ctime(secs)
    else:
        return 'Unavailable'

class ExperimentTableEditor(TableEditor):
    columns = [
        ObjectColumn(name='name', label='Name', width=0.2),
        #ObjectColumn(name='system_state', label='System State', width=0.250),
        StatusColumn(name='status', label='Status', width=0.15, style='readonly'),
        ProgressColumn(name='perc_done', label='progress', width=0.35),
        ObjectColumn(name='start_time', label='Started', width=0.15,
                     format_func=format_time,style='readonly'),
        ObjectColumn(name='end_time', label='Ended', width=0.15,
                     format_func=format_time, style='readonly'),

    ]

experiment_dict ={
    'SW Synchronized Scan':SWSynchronizedScan,


}

if __name__=='__main__':
    from controllers import MockMicronixStageController
    from scan_axes import CartesianScanAxis
    #from global_states import MockGlobalState

    def callback(exp):
        logger = logging.getLogger(__name__)
        logger.info(exp.position_text)


    naxes = 3
    controller = MockMicronixStageController()
    exp = SWSynchronizedScan()
    # names = ['X','Y','Z']
    # for n in range(naxes):
    #     new = CartesianScanAxis()
    #     new.controller = controller
    #     new.axis_num = n+1
    #     new.axis_name = names[n]
    #     new.step_size = 0.1
    #     exp.scan_axes.append(new)

    #exp.system_state = MockGlobalState()
    exp.every_step_callback = callback
    exp.configure_traits()


