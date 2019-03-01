from __future__ import print_function
from traits.api import *
from traitsui.api import *
from log_viewer import LogStream, log_editor
from controllers import MicronixStageController,MockMicronixStageController,\
    PicomotorController #, ZIDemodController
import numpy as np
#from daq_channels import BaseDAQChannel
from cmd_dictionaries import micronix_cmds
import os
from auxilary_functions import length_of
import cfg
GLOBALS = cfg.Globals()
if GLOBALS.MOCK_DAQ:
    import mock_nidaqmx as nidaqmx
else:
    import nidaqmx
from daq_control import BaseDAQTask, VITask, MockDAQTask, DAQTaskTable, task_dictionary
import logging
from log_viewer import LogStream
import threading
from time import sleep
from constants import IOService, ReadMode
from collections import deque


class BaseDevice(SingletonHasTraits):
    name = Str('Device')
    provides = Set()
    requires = Set()

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def _anytrait_changed(self, name, old, new):
        pass


class BaseCamera(BaseDevice):
    name = Str('')
    initialized = Bool(False)
    recording = Bool(False)
    read_mode = Enum([mode for mode in ReadMode])
    shape = Tuple()
    img_buffer = Instance(deque, transient=True)
    buffer_size = Int(100)
    user_wants_stop = Bool(False)
    t = Any(transient=True)
    provides = Set({IOService.CAM_READ})
    view = View()

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def _read_mode_default(self):
        return ReadMode.LIVE

    def initialize(self):
        # print("init called")
        try:
            if self.mode == ReadMode.LIVE:
                self.img_buffer = deque(maxlen=1)
            else:
                self.img_buffer = deque(maxlen=self.buffer_size)
            success = self.init_cam()
            # print("init success: ", success)
            self.initialized = success
        except Exception as e:
            print("init exception: ", e)
            return False

    def init_cam(self):
        raise NotImplementedError

    def start(self, num=None):
        # self.recorder(num=num)
        self.user_wants_stop = False
        if not self.initialized:
            success = self.initialize()
            if not success:
                return False
        self.t = threading.Thread(target=self.recorder, args=(num,))
        self.t.setDaemon(True)
        self.t.start()
        #self.recording=True

    def read_data(self, samps=None):
        if samps is None:
            nsamp=1
        if self.recording:
            pass
        else:
            self.start(samps)
            sleep(0.05)
        try:
            for i in range(20):
                if len(self.img_buffer) < nsamp:
                    sleep(0.05)
                else:
                    break

            imgs = [self.read_next() for n in range(nsamp)]
            return np.squeeze(np.array(imgs[:nsamp]))
        except:
            return np.full(self.shape, np.nan)

    def read_next(self):
        if self.read_mode == ReadMode.FIFO:
            img = self.img_buffer.popleft()
        else:
            img = self.img_buffer.pop()
        return img

    def record(self,max=None,cont=False):
        raise NotImplemented

    def stop(self):
        pass

    def on_close(self):
        pass

    def close(self):
        self.user_wants_stop = True
        try:
            self.t.join(self.exposure + 5)
        except:
            pass

        self.on_close()
        self.initialized = False

    def add_to_queue(self, img):
        self.img_buffer.append(img)

    def recorder(self, num=None):
        #self.recording = True
        try:
            if num:
                nleft = num
                while nleft>0:
                    n = self.record(max=nleft)
                    nleft -= n
                    if self.user_wants_stop:
                        break
            else:
                while True:
                    self.record(cont=True)
                    sleep(0.01)
                    if self.user_wants_stop:
                        break
        except:
            print('Error reading from cam.')
        finally:
            self.stop()
            self.recording = False


class OpenCVCamera(BaseCamera):
    name = 'Generic Camera'

    cap = Any(transient=True)
    cam_num = Int(0)
    exposure = Int(5)
    gain = Int(1)
    # (480, 640, 0)
    shape = Tuple(cols=3, labels=['Rows', 'Columns','Color'])
    color_mode = Enum('GREYSCALE', ['RGB', 'GREYSCALE'])
    # image_buffer = List
    # buffer_size = Int(50)

    image = Array

    log = Instance(LogStream, transient=True)

    traits_view = View(
        HGroup(
            Item(name='read_mode', label='Mode', width=-100),
            Item(name='cam_num', label='Cam Number', width=-40),
            Item(name='shape', show_label=False, #editor=TupleEditor(cols=3, labels=['Rows', 'Columns','Color']),
                 enabled_when='False', width=-250),
            Item(name='exposure', label='Exposure', enabled_when='False', width=-40),
            Item(name='gain', label='Gain', enabled_when='False', width=-40),
        ),
    )

    # def _shape_default(self):
    # return (1280,1024)

    def _color_mode_changed(self, new):
        if new=='RGB':
            return (480, 640, 3)
        else:
            return (480, 640, 0)

    def init_cam(self):
        if self.initialized:
            return True
        try:
            import cv2
            # print('cv2 imported')
            # import ids
        except:
            # print('cv2 not imported')
            return False

        logger = logging.getLogger('__main__')
        self.cap = cv2.VideoCapture(self.cam_num)
        rows = self.cap.get(3)
        cols = self.cap.get(4)
        # self.shape = (int(rows), int(cols), 0)
        # self.cam.color_mode = ids.ids_core.COLOR_RGB8
        # self.cam.exposure = self.exposure
        if self.cap.isOpened():
            self.initialized = True
            logger.info('Cam opened.')
            return True
        else:
            self.cap.release()
            logger.info('Cam wont open')
            return False
            # raise RuntimeError, 'Cam wont open'
            # self.figure.tight_layout()

    def record(self,max=None,cont=False):

        if self.initialized:
            # print('initialized')
            ret, img = self.cap.read()
            # print(ret)
            if ret:
                # grey = img.sum(axis=2)
                if self.color_mode == 'GREYSCALE':
                    img = np.dot(img[..., :3], [0.299, 0.587, 0.114])
                if img.shape != self.shape:
                    self.shape = img.shape
                # print(img[0])
                self.add_to_queue(img)
                return True
        else:
            print('not initialized')
        return False

    def on_close(self):
        if self.initialized and self.cap.isOpened():
            self.cap.release()
        self.initialized = False
        logger = logging.getLogger('__main__')
        logger.info('Camera closed.')


class MockCamera(BaseCamera):
    name = 'Mock Camera'
    _shift = Int(0)
    frate = Float(100)
    shape = Tuple((50, 50), cols=2, labels=['rows', 'cols'])
    kind = Enum('spot',['spot','colors'])
    traits_view = View(
        HGroup(
            Item(name='read_mode', label='Mode', width=-120),
            Item(name='frate', label='FPS', width=-60),
            Item(name='shape', label='Dimensions', width=-200),
            Item(name='kind', label='Kind', width=-200),
            # Item(name='_shift', label='Shift', width=-60),

        ),
    )

    def init_cam(self):
        pass
    def color(self):
        x = np.linspace(0., 1., num=self.shape[0])
        y = np.arange(0., self.shape[1])
        img = np.meshgrid(x, y)[1]
        img = np.roll(img, self._shift, axis=0)
        self._shift += self.shape[1] // 50
        if self._shift > self.shape[1]:
            self._shift = 0
        return img

    def spot(self):
        x = np.arange(0., self.shape[0])
        y = np.arange(0., self.shape[1])
        X,Y = np.meshgrid(x, y)
        Z = 10000*np.random.random()*np.exp(-((X-self.shape[0]/2)**2/(self.shape[0]/20)**2 + (Y-self.shape[1]/2)**2/(self.shape[1]/20)**2)) + np.random.random()
        return Z

    def record(self,max=None,cont=False):
        img = getattr(self,self.kind)()

        self.shape = img.shape

        sleep(1 / self.frate)
        self.add_to_queue(img)
        return 1

class HamamatsuProperty(HasTraits):
    cam = Any(transient=True)
    name = Str()
    value = Any()
    writable = Bool(False)
    ptype = Str()

    def _value_changed(self, old, new):
        if new is None:
            return
        if old is None:
            return
        try:
            if self.writable and self.cam:
                self.cam.setPropertyValue(self.name, new)
        except:
            logger = logging.getLogger('__main__')
            logger.error('failed to set {} camera property'.format(self.name))

class PropertyColumn(ObjectColumn):
    def is_editable( self, object ):
        return object.writable

class CamPropertyTable(TableEditor):
    columns = [
        ObjectColumn(name='name', label='Name', width=0.2, style='readonly'),
        ObjectColumn(name='value', label='Value', width=0.1),
        ObjectColumn(name='ptype', label='Type', width=0.1, style='readonly'),
        # ReadonlyCheckboxColumn(name='in_use',label='In Use',editable=False)
    ]


class HamamatsuCameraGUI(BaseCamera):
    name = 'Hamamatsu Camera'
    cam = Any(transient=True)
    cam_num = Int(0)
    properties = List([])
    exposure = Int(0.001)
    gain = Int(1)
    shape = Tuple((2048, 2048), cols=2, labels=['Rows', 'Columns'])
    initialize_button = Button('Initialize')
    close_button = Button('Disconnect')
    # image_buffer = List

    log = Instance(LogStream, transient=True)

    traits_view = View(

        VGroup(
            HGroup(
                Item(name='initialized',enabled_when='False'),
                Item(name='initialize_button', visible_when='not initialized',
                     show_label=False, width=-100),
                Item(name='close_button', visible_when='initialized',
                     show_label=False, width=-100),
                Item(name='read_mode', label='Mode', width=-100),
            ),
            HGroup(
                Item(name='cam_num', label='Cam Number', width=-60),
                Item(name='shape', show_label=False, enabled_when='False', width=-250),
                Item(name='exposure', label='Exposure', enabled_when='False', width=-60),
                Item(name='gain', label='Gain', enabled_when='False', width=-60),

            ),

            VGroup(
                Item(name='properties', show_label=False, editor=CamPropertyTable(), width=0.5),
                scrollable=True, show_border=True, label='Properties'),
        scrollable=True),

    resizable=True)

    control_view = View(
        VGroup(
            HGroup(
                Item(name='initialized', enabled_when='False'),
                Item(name='initialize_button', visible_when='not initialized',
                     show_label=False, width=-100),
                Item(name='close_button', visible_when='initialized',
                     show_label=False, width=-100),
                Item(name='read_mode', label='Mode', width=-100),
            ),
            HGroup(
                Item(name='cam_num', label='Cam Number', width=-60),
                Item(name='shape', show_label=False, enabled_when='False', width=-250),
                Item(name='exposure', label='Exposure', enabled_when='False', width=-60),
                Item(name='gain', label='Gain', enabled_when='False', width=-60),

            ),
            scrollable=True),
    resizable=True)

    def _initialize_button_fired(self):
        self.initialize()

    def _close_button_fired(self):
        self.close()


    def init_cam(self):
        try:
            from hamamatsu_camera import HamamatsuCamera
        except:
            return False
        if self.initialized:
            return True

        self.cam = HamamatsuCamera(self.cam_num)
        self.cam.setPropertyValue("defect_correct_mode", 1)
        self.read_properties()
        # self.queue = Queue(self.buffer_size)
        self.camera_model = self.cam.getModelInfo(self.cam_num)
        #self.initialized = True
        return True

    def read_properties(self):
        props = self.cam.getProperties()
        for id_name in sorted(props.keys()):
            prop = HamamatsuProperty()
            prop.name = id_name
            prop.value, prop.ptype = self.cam.getPropertyValue(id_name)
            _, prop.writable = self.cam.getPropertyRW(id_name)
            prop.cam = self.cam
            self.properties.append(prop)


    def record(self,max=None, cont=False):
        if cont and self.recording:
            pass
        else:
            self.cam.startAcquisition()
            self.recording = True
        [frames, dims] = self.cam.getFrames()
        if tuple(dims) != self.shape:
            self.shape = tuple(dims)
        recorded = 0
        for aframe in frames:
            self.add_to_queue(aframe.np_array.reshape(self.shape))
            recorded += 1
            if max and (recorded >= max):
                break
        if not cont:
            self.cam.stopAcquisition()
            self.recording = False
        return recorded

    def stop(self):
        if self.cam:
            self.cam.stopAcquisition()
        self.recording = False

    def on_close(self):
        self.cam.shutdown()


class NIDAQ(BaseDevice):

    name = Str('NIDAQ')
    dev_name = Str('')
    dev_cat = Str('')

    model = Str('')

    #device = Str('')
    devices = List([])
    find_devices = Button('Scan')

    tasks = List(BaseDAQTask, [])
    task = Instance(BaseDAQTask)
    add_kind = Enum(task_dictionary.keys())
    add_task = Button('Add')
    remove_task = Button('Remove')

    di_line_names = List()
    di_port_names = List()
    do_line_names = List()
    do_port_names = List()

    #pfi_chan_names = List()
    ai_chan_names = List()
    ao_chan_names = List()
    ci_chan_names = List()
    co_chan_names = List()

    ndi = Property(fget=length_of('di_line_names'))
    #npfi = Property(fget=length_of('pfi_chan_names'))
    nai = Property(fget=length_of('ai_chan_names'))
    nao = Property(fget=length_of('ao_chan_names'))
    nctr = Property(fget=length_of('ci_chan_names'))

    traits_view = View(
        VGroup(
            HGroup(
                VGroup(
                    HGroup(
                    Item(name='dev_name', label='Device', editor=EnumEditor(name='devices')),
                    Item(name='find_devices', show_label=False),
                    ),
                    Item(name='dev_cat', label='Series', style='readonly'),
                    Item(name='model', label='Model', style='readonly'),
                    show_border=True, label='Properties'),

                VGroup(
                    Item(name='ndi', label='Digital I/Os'),
                    #Item(name='ndio', label='PFIs'),
                    Item(name='nai', label='Analog Inputs'),
                    Item(name='nao', label='Analog Outputs'),
                    Item(name='nctr', label='Counters'),
                    show_border=True, label='Device channel count',
                    columns=2, enabled_when='False'),
            ),
            HGroup(
                Item(name='add_kind', show_label=False),
                Item(name='add_task', show_label=False),
                Item(name='remove_task', show_label=False),
            ),
            HGroup(

                Item(name='tasks',editor=DAQTaskTable(selected='task'),show_label=False),
            show_border=True,label='Tasks'),
            Item(name='task', editor=InstanceEditor(),style='custom', show_label=False),

        ),

        resizable=True)

    task_view = View(
        HGroup(
            Item(name='task', editor=EnumEditor(name='tasks'), show_label=False),
            show_border=True, label='Task'),
    )


    def __init__(self,*args,**kwargs):
        super(NIDAQ, self).__init__(*args, **kwargs)
        self.discover()

            #self.read_properties()

    def _find_devices_fired(self):
        self.discover()

    def _tasks_default(self):
        if GLOBALS.MOCK_DAQ:
            return [MockDAQTask()]
        else:
            return [VITask()]

    def _add_task_fired(self):
        self.tasks.append(task_dictionary[self.add_kind]())

    def _remove_task_fired(self):
        self.tasks.remove(self.task)
        self.task = None

    def _dev_name_changed(self):
        self.read_properties()

    def discover(self):
        try:
            system = nidaqmx.system.system.System.local()
            self.devices = [device.name for device in system.devices]
        except:
            self.devices = ['MockDev{}'.format(n) for n in range(1, 3)]
            GLOBALS.MOCK_DAQ = True

        if len(self.devices):
            self.dev_name=self.devices[0]
            self.read_properties()

    def read_properties(self):
        if GLOBALS.MOCK_DAQ:
            self.dev_cat = 'Mock DAQ'
            self.model = '1.0.0'
            self.ai_chan_names = ['mock_ai{}'.format(n) for n in range(5)]
            self.ao_chan_names = ['mock_ao{}'.format(n) for n in range(5)]
            self.ci_chan_names = ['mock_ci{}'.format(n) for n in range(5)]
            self.co_chan_names = ['mock_co{}'.format(n) for n in range(5)]
            self.di_line_names = ['mock_di_line{}'.format(n) for n in range(5)]
            self.do_line_names = ['mock_do_line{}'.format(n) for n in range(5)]
            self.di_port_names = ['mock_di_port{}'.format(n) for n in range(5)]
            self.do_port_names = ['mock_do_port{}'.format(n) for n in range(5)]
            self.devices = ['Dev{}'.format(n) for n in range(1, 3)]
            self.name = '{} {}'.format(self.dev_cat,self.model )
            if len(self.devices):
                self.dev_name = self.devices[0]
            return
        else:
            system = nidaqmx.system.system.System.local()

            for device in system.devices:
                if device.name==self.dev_name:
                    break
            self.dev_cat = device.product_category.name
            self.model = device.product_type
            self.name = '{} {}'.format(self.dev_cat,self.model )
            self.ai_chan_names = device.ai_physical_chans.channel_names
            self.ao_chan_names = device.ao_physical_chans.channel_names
            self.ci_chan_names = device.ci_physical_chans.channel_names
            self.co_chan_names = device.co_physical_chans.channel_names
            self.di_line_names = device.di_lines.channel_names
            self.do_line_names = device.do_lines.channel_names
            self.di_port_names = device.di_ports.channel_names
            self.do_port_names = device.do_ports.channel_names


class TravelRange(HasTraits):
    pass

import os
import traits.api
from pyface.image_resource import ImageResource
search_path = [ os.path.join( os.path.dirname( traits.api.__file__ ),
                      '..', '..', 'examples', 'demo', 'Extras' ) ]
from saving import CanSaveMixin, SaveHandler

class MicronixStageHandler(SaveHandler):
    extension = ''

    def object_save_to_file_changed(self, info):
        self.saveAs(info)

    def object_load_from_file_changed(self,info):
        self.load(info)

class MicronixStage(BaseDevice):
    name = 'Micronix Stage'
    #travel_range = Tuple((-14.0, 14.0), labels=['Min limit', 'Max limit'])
    axis_num = Enum(GLOBALS.STAGE_DEFAULT_AXIS, GLOBALS.STAGE_AXES)  #Int(1)
    axis_name = Str('None')

    controller = Instance(MicronixStageController,(), transient=True)
    #provides = Delegate('controller')
    just_read = Bool(True)
    error_log = List([])

    status_byte = Int(0)
    status_bits = Property(List, depends_on='status_byte')
    status_names = List(['Error', 'Accelerating', 'Const. Velocity',
                         'Decelerating', 'Stopped', 'Program Running',
                         'Positive Switch', 'Negetive Switch'])

    velocity = Float()
    acceleration = Float()
    deceleration = Float()

    max_acceleration = Float()
    max_velocity = Float()

    read_settings = Button('Read Settings')
    soft_reset = Button('Soft Reset')
    save_to_memory = Button('Save Settings')
    read_errors = Button('Get Errors')
    defaults = Button('Restore Defaults')

    save_to_file = Button('Save to File')
    load_from_file = Button('Load File')
    #sync = Button('Sync')


    neg_lim = Float()
    pos_lim = Float()
    enable_limit = Int(0)

    encoder = Int()
    encoder_pol = Int()
    encoder_velocity = Float()
    encoder_res = Float()

    deadband = Tuple((1,0.0),labels=['Deadband','DB timeout'])
    feedback = Int()
    resolution = Int()

    version = Str

    motor_pol = Int()
    pid = Int()

    # IO Function setup
    io_function = Int(0)
    io_pin = Enum(1,range(1,5))

    set_io_function = Button('Set' )

    traits_view = View(
                VGroup(
                    Group(
                        Item(name='controller', show_label=False, style='custom'),
                        show_border=True, label='Communication settings'),
                    #Item(label=' '),
                    HGroup(
                        Item(name='save_to_file', show_label=False, ),
                        Item(name='load_from_file', show_label=False, ),
                    ),

                    #Item(label='  '),

                    Group(

                        HGroup(
                            Item(name='axis_num', label='Number', width=-60),
                            Item( label='    '),
                            #Item(name='axis_name', label='Axis Name', width=-60, style='readonly'),
                            Item(name='read_settings', show_label=False, label=''),
                            Item(name='defaults', show_label=False, label=''),
                            Item(name='save_to_memory', show_label=False, label=''),
                            Item(name='read_errors', show_label=False, label=''),
                            Item(name='soft_reset', show_label=False, label=''),

                        ),

                        HGroup(
                            VGroup(
                                Item(name='velocity', label='Velocity', width=-60),
                                Item(name='max_velocity', label='Max Velocity', width=-60, style='readonly'),
                                Item(name='acceleration', label='Acceleration', width=-60),
                                Item(name='max_acceleration', label='Max Acceleration', width=-60,style='readonly'),
                                Item(name='deceleration', label='Deceleration', width=-60),
                            ),
                            VGroup(
                                Item(name='enable_limit', label='Enable Limit', width=-60),
                                Item(name='neg_lim', label='Negetive Limit', width=-60),
                                Item(name='pos_lim', label='Positive Limit', width=-60),
                                Item(name='motor_pol', label='Motor Polarization', width=-60),
                                Item(name='version', label='Version', width=-60,style='readonly'),
                            ),

                            VGroup(
                                Item(name='encoder', label='Encoder (A/D)', width=-60),
                                Item(name='encoder_pol', label='Encoder Polarization', width=-60),
                                Item(name='encoder_velocity', label='Encoder Velocity', width=-60,style='readonly'),
                                Item(name='encoder_res', label='Encoder Resolution', width=-60),
                            ),

                            VGroup(
                                Group(Item(name='deadband',show_label=False, label='Deadband', width=-150),),

                                Item(name='feedback', label='Feadback', width=-60),
                                Item(name='resolution', label='Resolution', width=-60),
                                Item(name='pid', label='PID', width=-60),
                            ),
                        ),

                    show_border=True,label='Axis Settings'),
                    HGroup(
                        Group(
                            Item(name='status_bits', editor=CheckListEditor(name='status_names', cols=2),
                                 style='custom',show_label=False ),
                            label='Status', show_border=True, enabled_when='False'),


                    Group(
                        Item(name='io_pin', label='Pin', width=-60),
                        Item(name='io_function', label='Function', editor=EnumEditor(values={
                            0:'No function', 1:'[I] Logging Trigger',
                            2:'[O] In position Pulse', 3:'[O] In position level'
                        })),
                        Item(name='set_io_function', show_label=False,editor=ButtonEditor(image=ImageResource( 'info',
                                                 search_path = search_path))),
                        label=' IO Functions', show_border=True),
                    ),
                    Group(Item(name='error_log', show_label=False, width=40, height=30,
                               editor=ListStrEditor(), enabled_when='False'),
                          label='Error Log', show_border=True),
                    #spring,
                    #Group(
                     #   Item(name='error_log',editor=log_editor(), show_label=False,),
                    #show_border=True,label='Error Log'),
                show_border=True, label='Micronix Stage'),
    width=1200,
    height=800,
    resizable=True,
    handler=MicronixStageHandler,
    #toolbar = ToolBar(save_to_file, load_from_file),
    )

    @cached_property
    def _get_status_bits(self):
        return list(np.unpackbits(np.uint8(self.status_byte)))

    def _set_status_bits(self, val):
        pass

    def _read_settings_fired(self):
        self.read_all_settings()

    def _soft_reset_fired(self):
        self.controller.send_cmd(self.axis_num,'soft_reset', value='', response=False)

    def _save_to_memory_fired(self):
        self.controller.send_cmd(self.axis_num,'save_to_memory', value='', response=False)

    def _read_errors_fired(self):
        errors = self.controller.send_cmd(self.axis_num,'read_errors', value='?', response=True)
        if not isinstance(errors,list):
            errors = [errors]
        self.error_log = errors

    def _set_io_function(self):
        self.controller.write('%dIOF%d,%d'%(self.axis_num, self.io_pin, self.io_function))

    def read_status(self):
        if isinstance( self.axis_num,int):
            response = self.controller.send_cmd(self.axis_num, 'status_byte', value='?', response=True)
            if response is not None:
                self.status_byte = response

    def _defaults_fired(self):
        self.controller.send_cmd(self.axis_num,'defaults', value='', response=False)


    def _anytrait_changed(self,name, old, new):
        super(MicronixStage, self)._anytrait_changed(name, old, new)
        if old is Undefined or old is None:
            return
        if not self.controller.initialized:
            return
        self.read_status()

        if self.just_read:
            self.just_read = False
            return
        if name in ['status_byte','max_acceleration','max_velocity','encoder_velocity','version']:
            return
        if name in micronix_cmds.keys():
            if hasattr(new, '__iter__'):
                val = ','.join([str(x) for x in new])
            elif name=='pid':
                val = '%d,,'%new
            else:
                val = str(new)
            self.controller.send_cmd(self.axis_num,name, value=val, response=False)
            self.read_status()

    def save(self):
        try:
            import cPickle as pickle
        except:
            import pickle
        with open(self.filepath, 'wb') as f:
            pickle.dump(self,f)

    def load(self):
        try:
            import cPickle as pickle
        except:
            import pickle
        with open(self.filepath, 'rb') as f:
            obj = pickle.load(f)
            self.copy_traits(obj)

    def read_all_settings(self):
        if self.axis_num is None:
            return
        for cmd in self.editable_traits():
            if cmd in micronix_cmds.keys():
                response = self.controller.send_cmd(self.axis_num,cmd,value='?',response=True)
                if response is None:
                    continue
                value = {cmd:response}
                try:
                    self.trait_set(**value)
                except:
                    self.error_log.append('%s not read.'%cmd)
                    self.error_log.append(str(value[cmd]))
            #print cmd, isinstance(response,(int,float))
            #self.__dict__[cmd] = response
        self.just_read = True
        self.read_status()


    def __init__(self,**kwargs):
        super(MicronixStage, self).__init__(**kwargs)
        #self.read_all_settings()

class MockMicronixStage(MicronixStage):
    controller = Instance(MockMicronixStageController)
    name = 'Mock Stage'

    def _controller_default(self):
        return MockMicronixStageController()

    traits_view = View()

class PicomotorStage(BaseDevice):
    controller = Instance(PicomotorController, (), transient=True)
    provides = Delegate('controller')
    traits_view = View()
    name = 'Picomotor'
# class BaseDAQLightSource(BaseDevice):
#     class_name = 'BaseLightSource'
#     name = Str('BaseLightSource')
#     illum_on = Bool(False)
#     illum_amp_channel = Instance(BaseDAQChannel)
#     illum_mod_func = Str('5')
#     illum_on_channel = Instance(BaseDAQChannel)
#     max_mod_freq = Float()
#     daq = Instance(NIDAQ)
#
#     def _illum_on_changed(self,new):
#         if new:
#             self.turn_on()
#         else:
#             self.turn_off()
#
#     def turn_on(self):
#         pass
#
#     def turn_off(self):
#         pass

from controllers import OxxiusLaserController
class OxxiusLaser(BaseDevice):
    class_name = 'OxxiusLaser'
    name = 'OxxiusLaser'
    controller = Instance(OxxiusLaserController,())

    analog_control_mode = Enum(0,[0,1])  #0 Power, 1 Current
    analog_modulation_state = Enum(0,[0,1])  #0 Internal, 1 External
    base_plate_temp = Range(0.0,60.0) #C
    laser_diode_current = Range(0.0,3000.0) #mA
    cdrh_state = Enum(0,[0,1])
    modulation_state = Enum(1, [0, 1])  # 0 Modulated, 1 CW
    digital_modulation_state = Enum(0,[0,1]) #0 Disabled, 1 Enabled
    diode_temp_set_point = Range(20.0,35.0) #C
    measured_diode_temp = Range(10.0,50.0) #C
    measured_module_temp = Range(5.0,55.0) #C
    fault_number = Range(0,6)
    cum_time_of_operation = Range(0.0,20000.0)
    serial_num_and_wavelength = Str()
    interlock_state = Enum([0,1])   #0 Open, 1 Closed
    input_voltage = Range(5.0,9.5)
    laser_emission_activation = Enum([0,1])
    max_laser_current = Range(0.0,1000.0,1000.0) #mA
    max_laser_power = Range(0.0,500.0,500.0) #mW
    laser_output_power = Range(0.0,500.0) #mW
    processor_temp = Range(0.0,60.0)
    current_set_point = Range(0.0,1000.0)
    power_set_point = Range(0.0,500.0)
    operating_status = Range(1,6)
    software_version = Str('')
    alarm_reset = Button('Reset Alarm')
    emission_activation = Enum(0,[0,1]) #0:off , 1:on
    tec_enable = Enum([0,1])  #0 Disabled, 1 Enabled
    report = Str('')
    just_read = Bool(False)
    read_settings = Button('Read settings')

    view = View(

        VGroup(
            Item(name='controller', style='custom', show_label=False),
            Group(
            HGroup(
                Item(name='read_settings', show_label=False, width=-100, ),
                Item(name='emission_activation', label='Emission', style='custom',
                     editor=EnumEditor(values={0: 'Off', 1: 'On'}, cols=2)),
            ),


            HGroup(
                Group(
                    Item(name='analog_control_mode', show_label=False, style='custom',
                         editor=EnumEditor(values={0: 'Constant Power', 1: 'Constant Current'}, cols=1)),
                    label='Mode', show_border=True),

                Group(
                    Item(name='modulation_state', show_label=False, style='custom',
                         editor=EnumEditor(values={0: 'Modulated', 1: 'Constant Wave'})),
                    label='Modulation State', show_border=True, ),


                Group(
                    Item(name='analog_modulation_state',  show_label=False, style='custom',
                         editor=EnumEditor(values={0: 'Disbaled', 1: 'Enabled'})),
                    label='Analog Modulation', show_border=True,enabled_when='not modulation_state'),

                Group(
                    Item(name='digital_modulation_state',  show_label=False,style='custom',
                         editor=EnumEditor(values={0:'Disabled',1:'Enabled'})),
                    label='Digital Modulation', show_border=True,enabled_when='not modulation_state'),

        ),
            HGroup(
                VGroup(
                    Item(name='laser_output_power', label='Power [mW]', style='simple',# width=-350,
                         editor=RangeEditor(low=0.0, high_name='max_laser_power', mode='slider')),
                    Item(name='laser_diode_current', label='Current [mA]', #width=-350,
                         editor=RangeEditor(low=0.0, high_name='max_laser_current', mode='slider')),
                    #Item(name='laser_output_power', label='Measured Power [mW]', style='readonly'),
                    label='Setpoints', show_border=True),

            spring),
                HGroup(
                    VGroup(
                        Item(name='base_plate_temp', label='Base plate'),
                        Item(name='measured_diode_temp', label='Diode'),
                        Item(name='measured_module_temp', label='Module'),
                        Item(name='processor_temp', label='Processor'),
                        enabled_when='False'),
                    spring,

                    label='Temperatures', show_border=True),
                Item('report',style='readonly'),
            enabled_when='controller.initialized'),


            )

    )

    def _read_settings_fired(self):
        for name in self.editable_traits():
            val = self.controller.read_value(name)
            if val is not None:
                self.just_read = True
                self.trait_set(**{name:val})

    def _anytrait_changed(self,name,old,new):
        super(OxxiusLaser, self)._anytrait_changed(name,old,new)
        if old is Undefined:
            return
        if self.just_read:
            self.just_read = False
            return
        if name in self.controller.settable:
            ret = self.controller.write_value(name, new)
            if ret is None:
                self.report = 'Cannot set %s' % name
            if ret:
                self.report = '%s set to %s'%(name,str(new))
                #val = self.controller.read_value(name)
                #if val is not None:
                    #self.trait_set(trait_change_notify=False,**{name: val})
            else:
                self.report = 'Failed to set %s'%name



device_dict = {
    'MicronixStage': MicronixStage,
    'MockMicronixStage': MockMicronixStage,
    'PicomotorStage':PicomotorStage,
    'NIDAQ': NIDAQ,
    'OxxiusLaser':OxxiusLaser,
    'A Hamamatsu Camera': HamamatsuCameraGUI,
    'OpenCVCamera': OpenCVCamera,
    'MockCamera': MockCamera,
    #'ZIDemod':ZIDemod,
}

if __name__ == '__main__':
    cam = HamamatsuCameraGUI()
    cam.initialize()
    #img = cam.read_data(1)
    #cam.close()
    #cam.cam.shutdown()