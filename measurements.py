from traits.api import *
from traitsui.api import *
from traitsui.extras.checkbox_column import CheckboxColumn
import numpy as np
from data_viewers import BaseViewer, XYSliceBrowser,\
    TwoDViewer, OneDViewer, ImageViewer, ImageCollectionBrowser, OneDViewerFilled
from constants import IOService, UpdateDataMode, DataDimension
from global_state_manager import GlobalStateManager
from data_updating import data_updater
import logging
from pyface.api import FileDialog, CANCEL
from tempfile import mkdtemp
import os
import cfg
GLOBALS = cfg.Globals()


class ArraySavehandler(Handler):

    def object_save_changed(self, info):
        """ Saves the object to a new path, and sets this as the 'filepath' on
            the object. Returns whether the save_to_memory actually occurred.
        """
        fileDialog = FileDialog(action='save as', title='Save As',
                                wildcard='All files (*.*)|*.*',
                                parent=info.ui.control)
        fileDialog.open()
        if fileDialog.path == '' or fileDialog.return_code == CANCEL:
            return False
        else:
            data = { 'data': info.object.recorded_samples}
            if hasattr(info.object,'positions'):
                data['positions'] = info.object.positions
            # data['xbounds'] = np.array(info.object.xbounds)
            # if hasattr(info.object, 'yaxis') and info.object.yaxis:
            #     data['ybounds'] = np.array(info.object.ybounds)
            # if hasattr(info.object, 'zaxis') and info.object.zaxis:
            #     data['zbounds'] = np.array(info.object.calc_bounds(info.object.zaxis))
            np.savez(fileDialog.path, **data)


class BaseMeasurement(HasTraits):
    name = Str('Base Measurement')

    state_manager = Instance(GlobalStateManager, (), transient=True)

    requires = Property(Set)
    sources = Property()
    source = Any()

    provides = Set()

    #display_mode = Enum('Live', ['Live', 'When Done'])
    #display_every = Int(1)
    update_mode = Enum([mode for mode in UpdateDataMode])
    preview_dim = Enum(DataDimension.D2, [dim for dim in DataDimension])
    display = Instance(BaseViewer, transient=True)
    display_options = Dict()
    flex_mode = Bool(False)

    resolution = DelegatesTo('display')
    start_pos = DelegatesTo('display')

    calc_diff = Bool(False)
    apply = Enum('median',['mean', 'median','std','None'])
    save = Button('Save all')

    recorded_samples = Array(transient=True)
    filename = File(transient=True)
    memmaped = Bool(False, transient=True)
    current_samp = Array(transient=True)
    dtype = Any(value=np.double)
    current_idx = Tuple()

    positions = Array()

    sample_shape = Property(depends_on='source')

    save_results = Bool(True)
    ndone = Property(Int)

    #delay = Float(0)

    #mode = Enum(['None'])

    every_N_callback = Function()
    done_callback = Function()

    initialized = Bool(False)

    traits_view = View()
    data_view = View(
        VGroup(
            VGroup(
                Item(name='display', show_label=False, style='custom', springy=True),
                show_border=False, ),
            HGroup(
                #Item(name='display_mode', label='Measurement Preview'),
                #Item(name='display_every', label='Refresh every',
                     #enabled_when='display_mode=="Live"', width=-60),
                #Item(name='save', show_label=False),
            ),

        scrollable=True),
    handler=ArraySavehandler,
    resizable=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __del__(self):
        if self.memmaped:
            self.recorded_samples.flush()
            del self.recorded_samples
            if os.path.isfile(self.filename):
                os.remove(self.filename)
        #super(BaseMeasurement,self).__del__()

    def _display_default(self):
        return XYSliceBrowser()

    def _results_default(self):
        return np.full((10,10,10),np.nan)


    def _display_options_default(self):
        # (position dimension, data dimension): viewer class

        displays = {
            DataDimension.D0: OneDViewer,
            DataDimension.D1: OneDViewer,
            DataDimension.D2: TwoDViewer,
            DataDimension.D3: XYSliceBrowser,
                    }

        return displays

    def _get_sample_shape(self):
        if self.apply == 'None':
            shp = self.source.shape
        else:
            shp = (1,)
        return shp

    def _get_requires(self):
        return set()

    def _get_sources(self):
        state = self.state_manager.global_state
        if state is None:
            return []
        srcs = [src for src in state.sources \
                 if IOService.services_all(self.requires, src.provides)]
        return srcs

    def _get_ndone(self):
        return np.product(np.array(self.current_idx)+1)

    def refresh_display(self):
        disp_data = self.current_samp
        if self.update_mode==UpdateDataMode.BYINDEX:
            idx = self.current_idx
            ndim = self.preview_dim.value
            idim = len(self.current_idx)
            dims = self.display.shape
            if idim==1 and ndim>1:
                idx = np.unravel_index(self.current_idx,dims=dims)
            elif idim>ndim:
                try:
                    self.preview_dim = DataDimension(idim)
                    self.initialize_display()
                except:
                    logger = logging.getLogger('__main__')
                    logger.info('No preview for {} dimensional data available'.format(idim))
                return
            if idx<dims:
                pass
            else:
                idx = tuple(d%dims[0] for d in idx)

            self.display.set_data(disp_data, idx=idx)

        elif self.update_mode==UpdateDataMode.REPLACE:
            self.display.set_data(disp_data)
        else:
            self.display.set_data(disp_data)

    def initialize(self):
        self.on_init()
        self.initialized = True

    def on_init(self):
        pass

    def allocate_memory(self, idx_shape, positions=None, data_shape=None):

        if positions is None:
            self.positions = np.array(np.meshgrid(*[np.arange(n) for n in idx_shape]))
        else:
            self.positions = positions
        pos_shape = self.positions[0].shape

        if data_shape is not None:
            data_shp = data_shape
        else:
            data_shp = self.sample_shape

        self.current_samp = np.full(self.sample_shape, np.nan,
                                    dtype=self.dtype).squeeze()
        self.current_idx = tuple(0 for n in pos_shape)

        size = np.product(pos_shape + data_shp)*self.current_samp.nbytes
        if size<(GLOBALS.MAX_SIZE*1e6):
            self.recorded_samples = np.full(pos_shape + data_shp,
                                        np.nan, dtype=self.dtype).squeeze()
        else:
            self.filename = os.path.join(mkdtemp(dir=GLOBALS.TEMPDIR), '{}.dat'.format(id(self)))

            self.recorded_samples = np.memmap(self.filename, dtype=self.dtype, mode='w+',
                                             shape=pos_shape + data_shp)
            self.memmaped = True
        return True


    def initialize_display(self):
        if self.preview_dim in self.display_options:
            self.display = \
                self.display_options[self.preview_dim]()
            store_shp = self.recorded_samples.shape
            disp_dim = self.preview_dim.value
            shp = tuple(dim for dim in store_shp[-disp_dim:])
            if len(shp)==disp_dim:
                self.display.data = np.full(shp ,np.nan, dtype=self.dtype)
            else:
                self.display.data = np.full(self.display.shape, np.nan, dtype=self.dtype)
            self.refresh_display()

    def perform(self, idx=None, record=True, preview=True):
        active = self.state_manager.active_sources
        if active and self.source in active:
            data = self.source.read_data()
            proc = self.process_data(data)
            if proc is None:
                return False
            else:
                self.current_idx = idx
                self.current_samp = np.asarray(proc).squeeze()
            if record:
                self.record_data()
            if preview:
                self.refresh_display()
            return True
        return False

    def record_data(self):
        if self.current_idx is None:
            return False
        else:
            #slc = idx + tuple(slice(None) for n in range(self.data_dim))
            self.recorded_samples[self.current_idx,...] = self.current_samp
            return True


    def process_data(self, data):
        proc = data
        if data is None:
            return None
        if self.calc_diff:
            proc = np.diff(data)

        if self.apply != 'None':
            proc = getattr(np, self.apply)(data)

        return proc


class BaseDAQMeasurement(BaseMeasurement):
    update_mode = UpdateDataMode.BYINDEX
    #preview_dim = DataDimension.D2



class CounterMeasurement(BaseDAQMeasurement):
    name = Str('Counter Measurement')


    @property_depends_on('mode')
    def _get_requires(self):
        return {IOService.DAQ_READ_COUNT}


class FrequencyMeasurement(BaseDAQMeasurement):
    name = Str('Frequency Measurement')


    def _get_requires(self):
        return {IOService.DAQ_READ_FREQUENCY}


class VoltageMeasurement(BaseDAQMeasurement):
    #class_name = 'VoltageMeasurement'
    name = Str('Voltage Measurement')
    #mode = Enum('ContSamps', ['ContSamps','FiniteSamps'])
    #daq = Instance(NIDAQ, ())

    channel_name = Str('')


    def _get_requires(self):
        return {IOService.DAQ_READ_VOLTAGE}


class CameraSingleFrame(BaseMeasurement):
    name = 'Camera SingleFrame'
    apply = 'None'
    update_mode = UpdateDataMode.REPLACE
    preview_dim = DataDimension.D2
    flex_mode = False
    dtype = np.uint16


    def _get_requires(self):
        return {IOService.CAM_READ}

    def _display_default(self):
        return ImageViewer()

    def _display_options_default(self):

        displays = {
            DataDimension.D2: ImageViewer,}

        return displays

class CameraMultiFrame(BaseMeasurement):
    nframes = Int(10)
    frames = List(CameraSingleFrame)
    name = 'Camera MultiFrame'
    apply = 'None'
    update_mode = UpdateDataMode.REPLACE
    preview_dim = DataDimension.D2
    flex_mode = False
    dtype = np.uint16
    recorded_samples = Property()
    #def initialize_display(self):
        #pass

    traits_view = View(
        VGroup(
            Item(name='nframes', label='Frames per position'),
        ),

    )

    def _frames_default(self):
        return [CameraSingleFrame(source=self.source) \
                       for n in range(self.nframes)]

    @property_depends_on('frames[]')
    def _get_recorded_samples(self):
        return np.array([frame.recorded_samples for frame in self.frames])

    def _source_changed(self):
        for frame in self.frames:
            frame.source = self.source

    def _nframes_changed(self):
        self.frames = [CameraSingleFrame(source=self.source) \
                       for n in range(self.nframes)]

    def allocate_memory(self, idx_shape, positions=None, data_shape=None):
        for frame in self.frames:
            frame.allocate_memory(idx_shape, positions, data_shape)
            frame.display = None
            self.current_samp = np.copy(frame.current_samp)
            self.current_idx = frame.current_idx
        return True

    def perform(self, idx=None, record=True, preview=True):
        for frame in self.frames:
            frame.perform(idx, record, preview=False)
            self.current_idx = frame.current_idx
        self.current_samp = np.mean([frame.current_samp for frame in self.frames], axis=0)
        if preview:
            self.refresh_display()
        return True


    def _get_requires(self):
        return {IOService.CAM_READ}

    def _display_default(self):
        return ImageViewer()

    def _display_options_default(self):

        displays = {
            DataDimension.D2: ImageViewer,}

        return displays


class UpdateColumn(ObjectColumn):
    def is_editable( self, object ):
        return not object.flex_mode

class MeasurementTableEditor(TableEditor):
    columns = [
        ObjectColumn(name='name', label='Name', width=-0.15),
        ObjectColumn(name='source',
                     editor=EnumEditor(name='sources'),label='Source', width=-0.150),
        CheckboxColumn(name='calc_diff', label='Diff.(1st)', width=-0.150),
        UpdateColumn(name='apply', label='Apply(2nd)', width=-0.150),
        UpdateColumn(name='update_mode', label='Update Mode', width=-0.15,),
        UpdateColumn(name='preview_dim', label='Preview Dim.', width=-0.15, ),
    ]


measurement_dict = {
    'Counter': CounterMeasurement,
    'Frequency': FrequencyMeasurement,
    'Voltage': VoltageMeasurement,
    'Camera SingleFrame': CameraSingleFrame,
    'Camera MultiFrame': CameraMultiFrame,

}