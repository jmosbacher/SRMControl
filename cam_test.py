from traits.api import *
from traitsui.api import *
from cameras import BaseCamera, OpenCVCamera, MockCamera, camera_dict
from pyface.timer.api import Timer
import numpy as np
from time import sleep
import logging
import time
# Enthought library imports
from enable.api import Component, ComponentEditor
from traits.api import HasTraits, Instance
from traitsui.api import Item, Group, View

# Chaco imports
from chaco.api import ArrayPlotData, jet, Plot
from chaco.tools.api import PanTool, ZoomTool

from chaco.tools.image_inspector_tool import ImageInspectorTool, \
     ImageInspectorOverlay


class ImageViewer(HasTraits):
    class_name = 'ImageViewer'
    pd = Instance(ArrayPlotData,transient=True)
    title = Str('')
    plot = Instance(Component,transient=True)

    #cursor = Instance(BaseCursorTool,transient=True)
    #cursor_pos = DelegatesTo('cursor', prefix='current_position')
    #cursor_idx = DelegatesTo('cursor', prefix='current_index')
    zdata = Array()


    view = View(
        VGroup(
            Group(

                Item('plot', editor=ComponentEditor(),
                     show_label=False),
                orientation="vertical"),
        ),

        resizable=True,
    )

    def __init__(self,*args,**kwargs):
        super(ImageViewer, self).__init__(*args,**kwargs)
        self.create_plot_component()

    def _zdata_default(self):
        return np.random.random((300, 300))

    def update_data(self):
        self.pd.set_data("imagedata", self.zdata)

    @on_trait_change('data, xbounds, ybounds')
    def create_plot_component(self):# Create a scalar field to colormap
        # Create the plot
        self.pd = ArrayPlotData()
        self.pd.set_data("imagedata", self.zdata)
        plot = Plot(self.pd)
        img_plot = plot.img_plot("imagedata",
                                 colormap=jet,
                                 )[0]

        # Tweak some of the plot properties
        plot.title = self.title
        plot.padding = 50

        # Attach some tools to the plot
        plot.tools.append(PanTool(plot))
        zoom = ZoomTool(component=plot, tool_mode="box", always_on=False)
        plot.overlays.append(zoom)

        #csr = CursorTool(img_plot,
         #                 drag_button='left',
          #                color='white',
           #               line_width=2.0
            #              )
        #self.cursor = csr

        #csr.current_position = np.mean(self.xbounds), np.mean(self.ybounds)
        #img_plot.overlays.append(csr)

        imgtool = ImageInspectorTool(img_plot)
        img_plot.tools.append(imgtool)

        overlay = ImageInspectorOverlay(component=img_plot, image_inspector=imgtool,
                                        bgcolor="white", border_visible=True)

        img_plot.overlays.append(overlay)
        self.plot = plot


class ManualMeasurementHandler(Handler):

    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
        if info.object.timer:
            info.object.timer.Stop()
        return

class ManualCameraMeasurement(HasTraits):
    class_name = 'ManualCameraMeasurement'
    name = Str('CameraMeasurement')

    ### Camera ###
    camera_name = Enum(camera_dict.keys())
    cam = Instance(BaseCamera,transient=True)
    initialized = Bool(False)

    timer = Instance(Timer,transient=True)
    viewer = Instance(ImageViewer,transient=True)

    fps = Int(20)
    ncapt = Int(100)
    meas_time = Int(10)

    dt = Property(depends_on='fps')
    ndone = Int(0)

    captured = List()

    running = Bool(False)
    user_wants_stop = Bool(False)
    paused = Bool(False)

    mode = Enum('Live',['Live','Capture'])
    start = Button('Start')
    stop = Button('Stop')
    clear = Button('Clear')

    view = View(
        VGroup(
            HGroup(
                Item(name='mode', label='Mode'),
                Item(name='fps', label='Frame Rate'),
                Item(name='ncapt', label='Images to Capture'),
                Item(name='meas_time', label='Capture Time [ms]'),
                Item(name='start', style='custom', show_label=False,visible_when='not running'),
                Item(name='stop', style='custom', show_label=False, visible_when='running'),
                Item(name='clear', style='custom', show_label=False, visible_when='not running'),
                spring,

            ),
            Item(name='viewer', style='custom', show_label=False),
        ),


    resizable=True,
    handler=ManualMeasurementHandler,
    )

    @property_depends_on('fps')
    def _get_dt(self):
        return 1.0/self.fps

    def _cam_default(self):
        cam = OpenCVCamera()
        initialized = cam.initialize()
        if initialized:
            cam.close()
            return cam
        else:
            return MockCamera()

    def _camera_name_changed(self,new):
        self.cam = camera_dict[new]()

    def _viewer_default(self):
        return ImageViewer()

    def _start_fired(self):
        if self.cam is None:
            return
        if not self.initialized:
            self.initialize_cam()
        self.start_timer()
        self.start_time = time.time()

    def _stop_fired(self):
        self.user_wants_stop = True

    def _clear_fired(self):
        self.viewer.zdata = np.zeros(500,500)
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

            self.paused = False
            self.user_wants_stop = False
            self.running = False
            return


        self.viewer.zdata = self.cam.get_next_image()
        return

    def start_timer(self):
        self.running = True
        delay = max(self.dt*1000.0-2-self.meas_time, self.meas_time+2)    #in millisec
        self.timer = Timer(delay, self.timer_tick)

if __name__ == '__main__':
    app = ManualCameraMeasurement()
    app.configure_traits()
