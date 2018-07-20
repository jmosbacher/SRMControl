from traits.api import *
from traitsui.api import *
from cameras import BaseCamera, OpenCVCamera, MockCamera, camera_dict
#from axis_settings import MicronixAxisSettings
from controllers import MicronixStageController, MockMicronixStageController, BaseStageController
from measurements import BaseMeasurement, MeasurementTableEditor, \
    measurement_dict, CounterMeasurement, VoltageMeasurement
from data_viewers import OneDViewer, ImageViewer
from pyface.timer.api import Timer
from global_state_manager import GlobalStateManager
from device_manager import DeviceManager, BaseDevice
import numpy as np
from pyface.api import ImageResource
import os
from repeat_button import AutoRepeatButtonEditor
import logging
import time
from xyz_navigator import XYZNavigator
import cfg
from constants import IOService
GLOBALS = cfg.Globals()


class BaseManualControl(HasTraits):

    name = Str('Base Manual Control')
    requires = Set()
    provides = Set()

    view = View()

###### Stage axis control view groups #####
properties_gr = HGroup(

                Item(name='axis_num', label='Axis', width=-40),
                Item(name='name', label='Name', width=-40, style='readonly'),
                show_border=True, label='Properties'),

position_gr = VGroup(
                Item(name='zero', show_label=False, width=-100),
                Item(name='position', show_label=False, format_func = lambda x:'%.6f, %.6f'%x,
                     width=-120, style='readonly'),
                Item(name='home', show_label=False),
                Item(name='refresh_pos', show_label=False),
                Item(name='stop', show_label=False),

            show_border=True, label='Position'),


move_relative_gr = HGroup(

                Item(name='move_down',show_label=False,width=-50,
                     editor=AutoRepeatButtonEditor(label='', width_padding = 0, height_padding = 0,
                    image=ImageResource(os.path.join(GLOBALS.ICON_DIR,'L.png')))),
                Item(name='step_size', show_label=False,width=-60),
                Item(name='move_up', show_label=False,width=-50,
                     editor=AutoRepeatButtonEditor(label='', width_padding = 0, height_padding = 0,
                    image=ImageResource(os.path.join(GLOBALS.ICON_DIR,'R.png')))),

            show_border=True,label='Move Relative'),

move_absolute_gr = VGroup(

                Group(
                    Item(name='pos_mm', label='mm', width=500,
                         editor=RangeEditor(mode='slider', low=-10, high=10)),
                    Item(name='pos_um', label='um', width=500,
                         editor=RangeEditor(mode='xslider', low=0, high=1000)),
                    Item(name='pos_nm', label='nm', width=500,
                         editor=RangeEditor(mode='xslider', low=0, high=1000)),

                    show_left=False),
                HGroup(
                    spring,
                    Item(name='move_to_pos',show_label=False,),
                    spring,
    ),


                show_border=True, label='Move Absolute'),



class ManualAxisControl(BaseManualControl):
    class_name = 'ManualAxisControl'
    axis_num = Int(1)
    name = Str('Manual Axis Control')
    controller = Instance(BaseStageController)

    position = Tuple((0.0,0.0),labels=['Calculated','Encoder'],cols=1)
    pos_mm = Float(0.)
    pos_um = Float(0.)
    pos_nm = Float(0.)
    enable_mov = Bool(False)
    zero = Button('Zero')
    
    home = Button('Home')
    refresh_pos = Button('Position')
    target_pos = Float(0.0)
    move_to_pos = Button('Move')
    stop = Button('Stop')
    up_name = Str('>')
    down_name = Str('<')
    step_size = Float(0.001)   #mm
    move_up = Button()
    move_down = Button()

    traits_view = View(
        HGroup(
        VGroup(properties_gr, move_relative_gr,),
            move_absolute_gr,position_gr,
        scrollable=True,),

        resizable=True)

    vert_view = View(
        VGroup(
            properties_gr,

            VGroup(
                move_relative_gr,

                move_absolute_gr,
            ),
            position_gr,
        scrollable=True),
    resizable=True)
    def __init__(self,**kwargs):
        super(ManualAxisControl, self).__init__(**kwargs)

    def _controller_default(self):
        if GLOBALS.MOCK_STAGE:
            return MockMicronixStageController()
        else:
            return MicronixStageController()

    def _refresh_pos_fired(self):
        self.refresh()


    #@on_trait_change('pos_mm, pos_um, pos_nm')
    def _move_to_pos_fired(self):
        pos = self.pos_mm + self.pos_um*(1e-3) + self.pos_nm*(1e-6)
        self.controller.move_abs(self.axis_num, pos)
        self.refresh()

    def _move_up_fired(self):
        ret = self.controller.move_rel(self.axis_num, self.step_size)
        if ret:
            self.refresh()

    def _move_down_fired(self):
        ret = self.controller.move_rel(self.axis_num, -self.step_size)
        if ret:
            self.refresh()

    def _zero_fired(self):
        self.controller.send_cmd(self.axis_num, 'zero', response=False)
        self.refresh()

    def _home_fired(self):
        self.controller.send_cmd(self.axis_num, 'home', response=False)
        self.refresh()

    def _stop_fired(self):
        self.controller.send_cmd(self.axis_num, 'stop', response=False)
        self.refresh()

    #def _feedback_changed(self,new):
        #self.controller.send_cmd(self.axis_num, 'feedback', value=new, response=False)

    def refresh(self):
        self.position = self.controller.position(self.axis_num)


class ManualStageControl(BaseManualControl):
    name = Str('Stage Position')
    x_axis = Instance(ManualAxisControl)
    y_axis = Instance(ManualAxisControl)
    z_axis = Instance(ManualAxisControl)
    #camera = Instance(BaseCamera)

    #controller = Instance(BaseSerialController)
    view = View(
        VGroup(

            VGroup(
                Group(Item(name='x_axis',style='custom',show_label=False),
                      show_border=False,label='X Axis'),
                Group(Item(name='y_axis', style='custom', show_label=False),
                      show_border=False, label='Y Axis'),
                Group(Item(name='z_axis', style='custom', show_label=False),
                      show_border=False, label='Z Axis'),
            show_border=True,label='XYZ Stage'),
            Group(
                #Item(name='camera', style='custom', show_label=False),
            ),
        ),

        height=700,
        width=1200,
        resizable=True,

    )

    #def _camera_default(self):
        #return IDSCamera()

    def __init__(self, **kwargs):
        super(ManualStageControl, self).__init__(**kwargs)


    def _x_axis_default(self):
        return ManualAxisControl(axis_num=1, name='X',up_name='Right',down_name='Left')

    def _y_axis_default(self):
        return ManualAxisControl(axis_num=2, name='Y',up_name='Back',down_name='Forward')

    def _z_axis_default(self):
        return ManualAxisControl(axis_num=3, name='Z',up_name='Down',down_name='Up')



############## NEW XYZ stage control ##########################
# class XYZStageAbsolutePosition(BaseManualControl):
#     name = Str('Stage Position')
#     current_pos = Tuple
#
#     saved_positions = List([])
#     controller = Instance(BaseSerialController, transient=True)
#
#     def _controller_default(self):
#         if GLOBALS.MOCK_STAGE:
#             return MockMicronixStageController()
#         else:
#             return MicronixStageController()

class XYZStageController(BaseManualControl, XYZNavigator):
    name = Str('Stage Navigator')

    controller = Instance(BaseStageController, transient=True)

    position_mapping = {
        'RL':0,
        'FB':1,
        'UD':2,
    }


    def step_mm(self):
        return self.step_nm*(1e-6)

    @on_trait_change('U,D,R,L,F,B,FR,FL,BR, BL')
    def move(self, obj, name, old, new):
        pos = list(self.position)
        for d in name:
            axis = getattr(self,self.mapping[d])
            stp = self.step_mm()*self.step_factor
            if getattr(self,self.mapping[d]+'_rev'):
                stp = -stp
            if d in ['D', 'L','B']:
                stp = -stp
            self.controller.move_rel(axis, stp)
            pos[self.position_mapping[self.mapping[d]]] = round(self.controller.position(axis)[1],6)
            self.position = tuple(pos)


    def _controller_default(self):
        if GLOBALS.MOCK_STAGE:
            return MockMicronixStageController()
        else:
            return MicronixStageController()


class ManualDAQControl(BaseManualControl):
    class_name = 'DAQManualControl'

class ManualMeasurementHandler(Handler):

    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """

        info.object.stop()
        return


class ManualMeasurement(BaseManualControl):
    name = Str('Measurement')

    measurements = List(BaseMeasurement)
    measurement = Instance(BaseMeasurement)
    state_manager = Instance(GlobalStateManager,(),transient=True)
    add_type = Enum('Counter Measurement',measurement_dict.keys())
    remove_meas = Button('Remove')
    add_meas = Button('Add')
    timer = Instance(Timer,transient=True)
    #viewer = Instance(OneDViewer, transient=True)

    sample_rate = Int(20)
    max_num_points = Int(1000)
    meas_time = Float(12)
    dt = Property(depends_on='sample_rate')
    num_ticks = Int(0)
    start_time = Any(time.time(), transient=True)
    running = Bool(False)
    user_wants_stop = Bool(False)
    paused = Bool(False)

    mode = Enum('Rolling',['Rolling','Looping','N samples'])

    apply = Enum('mean', ['mean', 'median', 'diff', 'None'])
    start = Button('Start')
    stop_button = Button('Stop')
    clear = Button('Clear')

    view = View(
        Tabbed(
            VGroup(


                HGroup(
                    Item(name='start', style='custom', show_label=False,
                         visible_when='not running', enabled_when='measurement'),
                    Item(name='stop_button', style='custom', show_label=False, visible_when='running'),
                    # Item(name='mode', label='Mode'),
                ),
                Item(name='measurement', editor=EnumEditor(name='measurements',cols=6),
                     style='custom', show_label=False),
                Item(name='measurement', editor=InstanceEditor(view='data_view'),
                     style='custom', show_label=False),


        scrollable=True),
            Group(
                VGroup(
                    HGroup(
                        HGroup(
                            # Item(name='system_state_type', show_label=False),
                            Item(name='state_manager', style='custom',
                                 editor=InstanceEditor(view='select_view'), show_label=False),
                            show_border=True, label='System state'),
                        HGroup(

                            Item(name='sample_rate', label='Sample Rate'),
                            Item(name='max_num_points', label='Max Display'),
                            Item(name='meas_time', label='Measure Time [ms]'),
                            # Item(name='apply', label='Apply'),
                            spring,
                        ),

                    ),

                    HGroup(

                        Item(name='add_type', style='simple', show_label=False, ),
                        Item(name='add_meas', style='custom', show_label=False, ),
                        Item(name='remove_meas', style='custom', show_label=False, visible_when='measurement'),

                    ),
                    HGroup(
                        Item(name='measurements',
                             editor=MeasurementTableEditor(selected='measurement'), show_label=False),
                    ),

                    HGroup(
                        Item(name='measurement',
                             style='custom', show_label=False),
                    ),
                    show_border=True, label='Configure'),

            label='Setup'),




            ),


    resizable=True,
    handler=ManualMeasurementHandler,
    )

    @property_depends_on('sample_rate')
    def _get_dt(self):
        return 1.0/self.sample_rate


    def _remove_meas_fired(self):
        self.measurements.remove(self.measurement)
        self.measurement = None

    def _add_meas_fired(self):
        if self.add_type:
            self.measurements.append(measurement_dict[self.add_type]())

    def _measurements_default(self):
        return [CounterMeasurement(), VoltageMeasurement()]

    def _measurement_default(self):
        if self.measurements:
            return self.measurements[0]

    def _start_fired(self):
        if not self.state_manager.global_state:
            return
        if not self.measurements:
            return
        for meas in self.measurements:
            meas.allocate_memory((self.max_num_points,))
            meas.initialize_display()
        self.state_manager.activate()
        self.start_time = time.time()
        self.start_timer()


    def _stop_button_fired(self):
        self.user_wants_stop = True

    def stop(self):
        if self.running:
            self.timer.Stop()
            self.state_manager.deactivate()
            self.paused = False
            self.user_wants_stop = False
            self.running = False
            stop_time = time.time()
            elapsed = stop_time - self.start_time
            logger = logging.getLogger('__main__')
            logger.info('Done. Time elapsed: %f' % elapsed)

    def timer_tick(self, *args):
        """
        Callback function that should get called based on a timer tick.  This
        will generate a new random data point and set it on the `.data` array
        of our viewer object.
        """
        # Generate a new number and increment the tick count
        if self.num_ticks >= self.max_num_points:
            self.num_ticks = 0

        if self.user_wants_stop:
            self.stop()
            return

        # arr_dict = self.system_state.in_task.read_data()

        for meas in self.measurements:
            meas.perform((self.num_ticks,))
        self.num_ticks += 1
        try:
            pass
        except:
            self.stop()
            self.state_manager.deactivate()

    def start_timer(self):
        self.running = True
        self.num_ticks = 0
        delay = max(self.dt*1000.0-2-self.meas_time, self.meas_time+2)    #in millisec
        self.timer = Timer(delay, self.timer_tick)


class ManualCameraMeasurementHandler(Handler):
    def close(self, info, is_ok):
        info.object.user_wants_stop = True
        if info.object.timer:
            info.object.timer.Stop()
        if info.object.cam:
            info.object.cam.close()
        #super(ManualCameraMeasurementHandler,self).close( info, is_ok)


    #def closed(self, info, is_ok):

        #info.object.user_wants_stop = True
        #if info.object.timer:
            #info.object.timer.Stop()
        #info.object.cam.close()



from data_viewers import TwoDViewer
class ManualCameraMeasurement(BaseManualControl):

    name = Str('Camera and Stage')
    requires = {IOService.CAM_READ}
    ### Camera ###
    #camera_name = Enum(camera_dict.keys())
    cameras = Property(List)
    cam = Instance(BaseDevice,transient=True)
    axis_control = Instance(XYZStageController,(),transient=True)
    initialized = Bool(False)

    timer = Instance(Timer,transient=True)
# viewer is Camera and Stage viewer, without him you won't see anything on that option
    viewer = Instance(ImageViewer,(), transient=True)
#   I am important as well, without me you won't see anything on Camera and Stage. Why am I important?
    state_manager = Instance(GlobalStateManager,(),transient=True)

    fps = Int(10)
    ncapt = Int(100)
    meas_time = Int(10)

    dt = Property(depends_on='fps')
    ndone = Int(0)

    captured = List([])

    running = Bool(False)
    user_wants_stop = Bool(False)
    paused = Bool(False)

    mode = Enum('Live',['Live','Capture'])
    start = Button('Start')
    stop = Button('Stop')
    clear = Button('Clear')

    view = View(
        VGroup(
            HGroup(Item(name='cam', editor=EnumEditor(name='cameras', cols=5),
                         style='custom', width=-0.7, show_label=False, springy=True),
                   spring, label='Available Cameras', show_border=True),
            HGroup(
            VGroup(
                #Item(name='ncapt', label='Images to Capture'),
                Item(name='fps', label='FPS',width=-50),
                Item(name='start', style='custom', show_label=False,visible_when='not running'),
                Item(name='stop', style='custom', show_label=False, visible_when='running'),
                Item(name='clear', style='custom', show_label=False, visible_when='not running'),
                spring,),
                Item(name='cam', style='custom',
                     editor=InstanceEditor(view='control_view'),
                     show_label=False, springy=True),

            label='Control', show_border=True),
            HGroup(
                VGroup(

                    Item(name='viewer', style='custom', width=-0.7,
                         show_label=False, springy=True),

                scrollable=True,label='Viewer', show_border=True),

                spring,
                VGroup(
                VGroup(
                       Item(name='axis_control', editor=InstanceEditor(view='button_view'),
                            width=-200, height=-200, show_label=False, style='custom'),
                    VGroup(

                           Item(name='axis_control', editor=InstanceEditor(view='settings_view'),
                                width=-200, height=-200, show_label=False, style='custom'),
                           ),
                       show_border=True, label='Stage Control'),
                    HGroup(
                        # Item(name='system_state_type', show_label=False),
                        Item(name='state_manager', style='custom',
                             editor=InstanceEditor(view='select_view'), show_label=False),
                        show_border=True, label='System state'),

                ),
                scrollable=True,),



        ),


    resizable=True,
    handler=ManualCameraMeasurementHandler,
    )

    @property_depends_on('fps')
    def _get_dt(self):
        return 1.0/self.fps

    def _get_cameras(self):
        dev_manager = DeviceManager()
        cams = []
        if not dev_manager.devices:
            return []
        for dev in dev_manager.devices:
            if dev is Undefined:
                continue
            if not hasattr(dev, 'provides'):
                continue
            if IOService.services_all(self.requires, dev.provides):
                cams.append(dev)
        return cams

    def _cam_default(self):
        if self.cameras:
            return self.cameras[0]

    #def _camera_name_changed(self,new):
        #self.cam = camera_dict[new]()


    def _start_fired(self):
        if self.cam is None:
            return
        if not self.initialized:
            self.initialize_cam()
        self.cam.start()
        self.start_timer()
        self.start_time = time.time()

    def _stop_fired(self):
        self.user_wants_stop = True

    def _clear_fired(self):
        self.viewer.data = np.zeros((500,500))
        self.captured = []
        self.ndone = 0

    def initialize_cam(self):
        initialized = self.cam.initialize()
        if initialized:
            return True
        else:
            return False

    def timer_tick(self, *args):
        """
        Callback function that should get called based on a timer tick.  This
        will generate a new random data point and set it on the `.data` array
        of our viewer object.
        """
        # Generate a new number and increment the tick count
        if self.mode=='Capture' and self.ndone>=self.ncapt:
            self.user_wants_stop=True

        if self.user_wants_stop:
            stop_time=time.time()
            elapsed = stop_time-self.start_time
            logger = logging.getLogger('__main__')
            logger.info('Done. Time elapsed: %f'%elapsed)
            self.timer.Stop()
            self.cam.stop()
            self.paused = False
            self.user_wants_stop = False
            self.running = False
            return
        new_img = self.cam.read_data()
        if new_img is None:
            return
        self.viewer.data = new_img
        #self.viewer.update_data()
        if self.mode=='Capture':
            self.captured.append(new_img)
        self.ndone+=1
        return

    def start_timer(self):
        self.cam.start()
        self.running = True
        delay = max(self.dt*1000.0-2-self.meas_time, self.meas_time+2)    #in millisec
        self.timer = Timer(delay, self.timer_tick)


class ManualOxxiusLaserControl(BaseManualControl):
    class_name = 'ManualOxxiusLaserControl'


manual_controls_dict = {
    'Stage Position': ManualStageControl,
    'XYZ Stage Controller': XYZStageController,
    'Camera and Stage': ManualCameraMeasurement,
    'Manual Measurement': ManualMeasurement,
}


if __name__ == '__main__':

    app = XYZStageController()
    app.configure_traits(view='button_view')
    #app = ManualCameraMeasurement()
    #app.configure_traits()
    """
    controller = MicronixStageController(com_port=5)
    app = StageManualControl(controller=controller)
    app.configure_traits()

    """

