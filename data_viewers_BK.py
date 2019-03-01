from traits.api import *
from traitsui.api import *
from chaco.chaco_plot_editor import ChacoPlotItem
import logging
#from measurements import BaseMeasurement
import numpy as np
from daq_control import BaseDAQChannel


class BaseViewer(HasTraits):
    class_name = 'BaseViewer'


class TimeSeriesViewer(BaseViewer):
    """ This class just contains the two data arrays that will be updated
    by the Controller.  The visualization/editor for this class is a
    Chaco plot.
    """

    class_name = 'TimeSeriesViewer'
    index = Array

    data = Array

    plot_type = Enum("line", "scatter")

    view = View(ChacoPlotItem("index", "data",
                              type_trait="plot_type",
                              resizable=True,
                              title='',
                              x_label="Time",
                              y_label="Signal",
                              color="blue",
                              bgcolor="white",
                              border_visible=True,
                              border_width=1,
                              #padding_bg_color="lightgray",
                              width=800,
                              height=380,
                              marker_size=2,
                              show_label=False),
                HGroup(spring, Item("plot_type", style='custom'), spring),
                resizable = True,
                buttons = ["OK"],
                width=800, height=500)


# Major library imports
from numpy import array,errstate

# Enthought library imports
from chaco.api import ArrayPlotData, ColorBar, ContourLinePlot, \
    ContourPolyPlot, DataRange1D, VPlotContainer, \
    DataRange2D, GridMapper, GridDataSource, \
    HPlotContainer, ImageData, LinearMapper, \
    OverlayPlotContainer, Plot, PlotAxis
from chaco import default_colormaps
from enable.component_editor import ComponentEditor
from chaco.tools.api import LineInspector, PanTool, ZoomTool
from traits.api import Array, Callable, CFloat, CInt, Enum, Event, Float, \
    Int, Instance, Str, Trait, on_trait_change, Button, Bool

from traitsui.api import Group, HGroup, Item, View, UItem, spring

# Remove the most boring colormaps from consideration:
colormaps = list(default_colormaps.color_map_name_dict.keys())
for boring in 'bone gray yarg gist_gray gist_yarg Greys'.split():
    colormaps.remove(boring)


class TwoDScalarInspector(BaseViewer):
    class_name = 'TwoDScalarInspector'
    # Data
    xs = Array
    ys = Array
    zs = Array

    minz = Float(0)
    maxz = Float(1)
    # container for all plots
    container = Instance(HPlotContainer)

    # Plot components within this container:
    polyplot = Instance(ContourPolyPlot)
    lineplot = Instance(ContourLinePlot)
    cross_plot = Instance(Plot)
    cross_plot2 = Instance(Plot)
    colorbar = Instance(ColorBar)

    # plot data
    pd = Instance(ArrayPlotData)

    # view options
    num_levels = Int(15)
    colormap = Enum(colormaps)

    show_plot = Button('Show')
    # Traits view definitions:
    traits_view = View(
        Group(UItem('container', editor=ComponentEditor(size=(800, 600)))),
        Item('show_plot'),
        resizable=True)

    plot_edit_view = View(
        Group(Item('num_levels'),
              Item('colormap')),
        buttons=["OK", "Cancel"])

    # ---------------------------------------------------------------------------
    # Private Traits
    # ---------------------------------------------------------------------------

    _image_index = Instance(GridDataSource)
    _image_value = Instance(ImageData)

    _cmap = Trait(default_colormaps.jet, Callable)

    # ---------------------------------------------------------------------------
    # Public View interface
    # ---------------------------------------------------------------------------

    def _show_plot_fired(self):
        self.create_plot()

    def __init__(self, *args, **kwargs):
        super(TwoDScalarInspector, self).__init__(*args, **kwargs)
        # FIXME: 'with' wrapping is temporary fix for infinite range in initial
        # color map, which can cause a distracting warning print. This 'with'
        # wrapping should be unnecessary after fix in color_mapper.py.
        #with errstate(invalid='ignore'):
            #self.create_plot()



    def create_plot(self):

        # Create the mapper, etc
        self._image_index = GridDataSource(self.xs,
                                           self.ys,
                                           sort_order=("ascending", "ascending"))
        image_index_range = DataRange2D(self._image_index)
        self._image_index.on_trait_change(self._metadata_changed,
                                          "metadata_changed")

        self._image_value = ImageData(data=self.zs, value_depth=1)
        image_value_range = DataRange1D(self._image_value)

        # Create the contour plots
        self.polyplot = ContourPolyPlot(index=self._image_index,
                                        value=self._image_value,
                                        index_mapper=GridMapper(range=
                                                                image_index_range),
                                        color_mapper= \
                                            self._cmap(image_value_range),
                                        levels=self.num_levels)

        self.lineplot = ContourLinePlot(index=self._image_index,
                                        value=self._image_value,
                                        index_mapper=GridMapper(range=
                                                                self.polyplot.index_mapper.range),
                                        levels=self.num_levels)

        # Add a left axis to the plot
        left = PlotAxis(orientation='left',
                        title="y",
                        mapper=self.polyplot.index_mapper._ymapper,
                        component=self.polyplot)
        self.polyplot.overlays.append(left)

        # Add a bottom axis to the plot
        bottom = PlotAxis(orientation='bottom',
                          title="x",
                          mapper=self.polyplot.index_mapper._xmapper,
                          component=self.polyplot)
        self.polyplot.overlays.append(bottom)

        # Add some tools to the plot
        self.polyplot.tools.append(PanTool(self.polyplot,
                                           constrain_key="shift"))
        self.polyplot.overlays.append(ZoomTool(component=self.polyplot,
                                               tool_mode="box", always_on=False))
        self.polyplot.overlays.append(LineInspector(component=self.polyplot,
                                                    axis='index_x',
                                                    inspect_mode="indexed",
                                                    write_metadata=True,
                                                    is_listener=True,
                                                    color="white"))
        self.polyplot.overlays.append(LineInspector(component=self.polyplot,
                                                    axis='index_y',
                                                    inspect_mode="indexed",
                                                    write_metadata=True,
                                                    color="white",
                                                    is_listener=True))

        # Add these two plots to one container
        contour_container = OverlayPlotContainer(padding=20,
                                                 use_backbuffer=True,
                                                 unified_draw=True)
        contour_container.add(self.polyplot)
        contour_container.add(self.lineplot)

        # Create a colorbar
        cbar_index_mapper = LinearMapper(range=image_value_range)
        self.colorbar = ColorBar(index_mapper=cbar_index_mapper,
                                 plot=self.polyplot,
                                 padding_top=self.polyplot.padding_top,
                                 padding_bottom=self.polyplot.padding_bottom,
                                 padding_right=40,
                                 resizable='v',
                                 width=30)

        self.pd = ArrayPlotData(line_index=array([]),
                                line_value=array([]),
                                scatter_index=array([]),
                                scatter_value=array([]),
                                scatter_color=array([]))

        self.cross_plot = Plot(self.pd, resizable="h")
        self.cross_plot.height = 100
        self.cross_plot.padding = 20
        self.cross_plot.plot(("line_index", "line_value"),
                             line_style="dot")
        self.cross_plot.plot(("scatter_index", "scatter_value", "scatter_color"),
                             type="cmap_scatter",
                             name="dot",
                             color_mapper=self._cmap(image_value_range),
                             marker="circle",
                             marker_size=8)

        self.cross_plot.index_range = self.polyplot.index_range.x_range

        self.pd.set_data("line_index2", self.xs)
        self.pd.set_data("line_value2", self.ys)

        self.pd.set_data("scatter_index2", array([]))
        self.pd.set_data("scatter_value2", array([]))
        self.pd.set_data("scatter_color2", array([]))

        self.cross_plot2 = Plot(self.pd, width=140, orientation="v",
                                resizable="v", padding=20, padding_bottom=160)
        self.cross_plot2.plot(("line_index2", "line_value2"),
                              line_style="dot")
        self.cross_plot2.plot(("scatter_index2",
                               "scatter_value2",
                               "scatter_color2"),
                              type="cmap_scatter",
                              name="dot",
                              color_mapper=self._cmap(image_value_range),
                              marker="circle",
                              marker_size=8)



        self.cross_plot2.index_range = self.polyplot.index_range.y_range

        # Create a container and add components
        self.container = HPlotContainer(padding=40, fill_padding=True,
                                        bgcolor="white", use_backbuffer=False)
        inner_cont = VPlotContainer(padding=0, use_backbuffer=True)
        inner_cont.add(self.cross_plot)
        inner_cont.add(contour_container)
        self.container.add(self.colorbar)
        self.container.add(inner_cont)
        self.container.add(self.cross_plot2)

    def update(self):
        self.minz = self.zs.min()
        self.maxz = self.zs.max()
        self.colorbar.index_mapper.range.low = self.minz
        self.colorbar.index_mapper.range.high = self.maxz
        self._image_index.set_data(self.xs, self.ys)
        self._image_value.data = self.zs
        self.pd.update_data(line_index=self.xs, line_index2=self.ys)
        self.container.invalidate_draw()
        self.container.request_redraw()

    # ---------------------------------------------------------------------------
    # Event handlers
    # ---------------------------------------------------------------------------

    def _metadata_changed(self, old, new):
        """ This function takes out a cross section from the image data, based
        on the line inspector selections, and updates the line and scatter
        plots."""

        self.cross_plot.value_range.low = self.minz
        self.cross_plot.value_range.high = self.maxz
        self.cross_plot2.value_range.low = self.minz
        self.cross_plot2.value_range.high = self.maxz
        if "selections" in self._image_index.metadata:
            x_ndx, y_ndx = self._image_index.metadata["selections"]
            if y_ndx and x_ndx:
                xdata, ydata = self._image_index.get_data()
                xdata, ydata = xdata.get_data(), ydata.get_data()
                self.pd.update_data(
                    line_value=self._image_value.data[y_ndx, :],
                    line_value2=self._image_value.data[:, x_ndx],
                    scatter_index=array([xdata[x_ndx]]),
                    scatter_index2=array([ydata[y_ndx]]),
                    scatter_value=array([self._image_value.data[y_ndx, x_ndx]]),
                    scatter_value2=array([self._image_value.data[y_ndx, x_ndx]]),
                    scatter_color=array([self._image_value.data[y_ndx, x_ndx]]),
                    scatter_color2=array([self._image_value.data[y_ndx, x_ndx]])
                )
        else:
            self.pd.update_data({"scatter_value": array([]),
                                 "scatter_value2": array([]), "line_value": array([]),
                                 "line_value2": array([])})

    def _colormap_changed(self):

        self._cmap = default_colormaps.color_map_name_dict[self.colormap]
        if self.polyplot is not None:
            value_range = self.polyplot.color_mapper.range
            self.polyplot.color_mapper = self._cmap(value_range)
            value_range = self.cross_plot.color_mapper.range
            self.cross_plot.color_mapper = self._cmap(value_range)
            # FIXME: change when we decide how best to update plots using
            # the shared colormap in plot object
            self.cross_plot.plots["dot"
            ][0].color_mapper = self._cmap(value_range)
            self.cross_plot2.plots["dot"
            ][0].color_mapper = self._cmap(value_range)
            self.container.request_redraw()

    def _num_levels_changed(self):

        if self.num_levels > 3:
            self.polyplot.levels = self.num_levels
            self.lineplot.levels = self.num_levels


# Enthought library imports
from enable.api import Component, ComponentEditor
from traits.api import HasTraits, Instance
from traitsui.api import Item, Group, View

# Chaco imports
from chaco.api import ArrayPlotData, jet, Plot, YlOrRd
from chaco.tools.api import PanTool, ZoomTool, PointMarker,DrawPointsTool
from chaco.tools.cursor_tool import CursorTool, BaseCursorTool
from chaco.tools.image_inspector_tool import ImageInspectorTool, \
     ImageInspectorOverlay
from scan_axes import BaseScanAxis
#from measurements import BaseMeasurement


def format_pos( pos):
    return 'X: %.6f  Y: %.6f' %pos

from pyface.api import FileDialog, CANCEL
class XYSliceBrowserHandler(Handler):

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
            data = {'data': info.object.data}
            data['xbounds'] = np.array(info.object.xbounds)
            data['ybounds'] = np.array(info.object.ybounds)
            if info.object.zaxis:
                data['zbounds'] = np.array(info.object.calc_bounds(info.object.zaxis))
            np.savez(fileDialog.path, **data)


class XYSliceBrowser(BaseViewer):
    class_name = 'XYSliceBrowser'
    pd = Instance(ArrayPlotData,transient=True)
    title = Str('')
    plot = Instance(Component,transient=True)
    #container = Instance(HPlotContainer,transient=True)

    save = Button('Save')

    cursor = Instance(BaseCursorTool,transient=True)
    cursor_pos = DelegatesTo('cursor', prefix='current_position')
    move_to_cursor = Button('Move to cursor')
    cursor_idx = DelegatesTo('cursor', prefix='current_index')

    xbounds = Property(depends_on='xaxis')
    ybounds = Property(depends_on='yaxis')#Tuple((0.0,1.0))

    zmin = Property(Float,depends_on='zaxis')
    zmax = Property(Float,depends_on='zaxis')

    #fxyzdata = Property(Array)
    zpos = Int()
    #fxydata = Property(Array)
    colormap = Enum('hot',colormaps)
    rev_cmap = Bool(False)

    view = View(
        VGroup(
            HGroup(
                Item(name='measurement', label='Measurement',
                     editor=EnumEditor(name='measurements'), ),
                Item(name='channel', label='Channel',
                     editor=EnumEditor(name='channels'), ),
                Item('zpos', label='Z slice', width=-200,
                     editor=RangeEditor(low_name='zmin', high_name='zmax')),
            ),

            HGroup(
                Item('cursor_pos',label='Cursor',style='readonly',format_func=format_pos),
                Item('move_to_cursor', show_label=False,),
                spring,
                Item(name='save', show_label=False),
            ),
            HGroup(
                Item('colormap', show_label=False, ),
                Item('rev_cmap', label='Reverse', ),
                spring,
            show_left=False,),

            Group(
                Item('plot', editor=ComponentEditor(), width=-500,height=-500,
                     show_label=False),
                ),
        ),
        handler=XYSliceBrowserHandler,
        #resizable=True,
    )

    def __init__(self,*args,**kwargs):
        super(XYSliceBrowser, self).__init__(*args,**kwargs)
        self.create_plot_component()

    def _move_to_cursor_fired(self):
        logger = logging.getLogger('__main__')
        self.xaxis.move_abs(pos=self.cursor_pos[0])
        self.yaxis.move_abs(pos=self.cursor_pos[1])
        logger.info('x: {} y: {}'.format(self.xaxis.current_pos(),self.yaxis.current_pos()))

    def format_pos(self,pos):
        return 'X: %.6f  Y: %.6f'%pos

    def _get_channels(self):
        if self.measurement:
            return self.measurement.channels
        else:
            return []

    def _get_zmin(self):
        return 0
        #return self.calc_bounds(self.zaxis)[0]

    def _get_zmax(self):
        if self.zaxis is None:
            return 1
        return self.zaxis.nsteps
        #return self.calc_bounds(self.zaxis)[1]

    def _get_xbounds(self):
        return self.calc_bounds(self.xaxis)

    def _get_ybounds(self):
        return self.calc_bounds(self.yaxis)

    def fxyzdata(self):
        if self.measurement is None:
            return np.zeros((300, 300))
        if self.channel and self.channel.name in self.measurement.results.keys():
            return self.measurement.results[self.channel.name]

    def fxydata(self):
        data = self.fxyzdata()
        if len(self.axes)>2:
            if abs(self.zmax-self.zmin):
                zindex = self.zpos
            else:
                zindex=0
            idx = []

            for axis in self.axes:
                if axis in [self.xaxis, self.yaxis]:
                    idx.append(slice(None))
                elif axis is self.zaxis:
                    idx.append(zindex)
                else:
                    idx.append(0)

            return data[idx]
        elif len(data.shape)<3:
            return data
        else:
            return np.zeros((300, 300))

    def _zaxis_default(self):
        if len(self.axes)<2:
            return None
        for axis in self.axes:
            if axis.axis_name=='Z':
                return axis
        else:
            return None

    def _xaxis_default(self):
        if len(self.axes)<2:
            return None
        for axis in self.axes:
            if axis.axis_name=='X':
                return axis
        else:
            return self.axes[0]

    def _yaxis_default(self):
        if len(self.axes)<2:
            return None
        for axis in self.axes:
            if axis.axis_name=='Y':
                return axis
        else:
            return self.axes[1]

    def calc_bounds(self,axis):
        if axis is None:
            return 0.0, 1.0
        start, stop = axis.start_pos, axis.stop_pos
        half_step = abs(stop - start)/(float(axis.nsteps) * 2.0)
        return (min(start, stop)-half_step, max(start,stop)+half_step)

    @on_trait_change('zpos')
    def update_data(self):
        self.pd.set_data("imagedata", self.fxydata())


    @on_trait_change('colormap,rev_cmap')
    #measurement,channel, xaxis, yaxis, zaxis,
    def create_plot_component(self):# Create a scalar field to colormap
        # Create the plot
        self.pd = ArrayPlotData()
        self.pd.set_data("imagedata", self.fxydata())
        plot = Plot(self.pd)
        cmap = default_colormaps.color_map_name_dict[self.colormap]
        if self.rev_cmap:
            cmap = default_colormaps.reverse(cmap)
        img_plot = plot.img_plot("imagedata",
                                 xbounds = self.xbounds,
                                 ybounds = self.ybounds,
                                 colormap=cmap,

                                 )[0]

        # Tweak some of the plot properties
        plot.title = self.title
        plot.padding = 50

        # Attach some tools to the plot
        #plot.tools.append(PanTool(plot))
        #zoom = ZoomTool(component=plot, tool_mode="box", always_on=False)
        #plot.overlays.append(zoom)

        csr = CursorTool(img_plot,
                          drag_button='left',
                          color='white',
                          line_width=2.0
                          )
        self.cursor = csr

        csr.current_position = np.mean(self.xbounds), np.mean(self.ybounds)
        img_plot.overlays.append(csr)

        imgtool = ImageInspectorTool(img_plot)
        img_plot.tools.append(imgtool)

        overlay = ImageInspectorOverlay(component=img_plot, image_inspector=imgtool,
                                        bgcolor="white", border_visible=True,)

        #img_plot.overlays.append(overlay)
        colorbar = ColorBar(index_mapper=LinearMapper(range=plot.color_mapper.range),
                            color_mapper=plot.color_mapper,
                            orientation='v',
                            resizable='v',
                            width=30,
                            padding=20)
        colorbar.plot = plot
        colorbar.padding_top = plot.padding_top + 10
        colorbar.padding_bottom = plot.padding_bottom

        # Add pan and zoom tools to the colorbar
        colorbar.tools.append(PanTool(colorbar, constrain_direction="y", constrain=True))
        zoom_overlay = ZoomTool(colorbar, axis="index", tool_mode="range",
                                always_on=True, drag_button="right")
        colorbar.overlays.append(zoom_overlay)

        # Create a container to position the plot and the colorbar side-by-side
        container = HPlotContainer(plot, colorbar, use_backbuffer=True, bgcolor="transparent",)
        container.overlays.append(overlay)
        #self.plot = plot
        self.plot = container

    def __repr__(self):
        return self.class_name


    def __str__(self):
        return self.class_name


class ImageViewer(BaseViewer):
    class_name = 'ImageViewer'
    pd = Instance(ArrayPlotData,transient=True)
    title = Str('')
    plot = Instance(Component,transient=True)
    shape = Tuple()
    #cursor = Instance(BaseCursorTool,transient=True)
    #cursor_pos = DelegatesTo('cursor', prefix='current_position')
    #cursor_idx = DelegatesTo('cursor', prefix='current_index')
    zdata = Array()


    view = View(
        VGroup(spring,
            HGroup(
                spring,
                Item('plot', editor=ComponentEditor(),width=640,height=512,
                     show_label=False),
                spring,
                ),
        spring),

        resizable=True,
    )

    def __init__(self,*args,**kwargs):
        super(ImageViewer, self).__init__(*args,**kwargs)
        self.create_plot_component()

    def _zdata_default(self):
        return np.random.random((1280, 1024))

    def update_data(self):
        #pos = self.cursor
        self.pd.set_data("imagedata", self.zdata)

    @on_trait_change('data, xbounds, ybounds')
    def create_plot_component(self):# Create a scalar field to colormap
        # Create the plot
        if self.shape==self.zdata.shape:
            self.pd.set_data("imagedata", self.zdata)
            return
        self.pd = ArrayPlotData()
        self.shape = self.zdata.shape
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

        csr = CursorTool(img_plot,
                          drag_button='right',
                          color='white',
                          line_width=2.0
                          )
        self.cursor = csr

        csr.current_position = self.shape[0]/2, self.shape[1]/2 #np.mean(self.xbounds), np.mean(self.ybounds)
        img_plot.overlays.append(csr)

        imgtool = ImageInspectorTool(img_plot)
        img_plot.tools.append(imgtool)

        overlay = ImageInspectorOverlay(component=img_plot, image_inspector=imgtool,
                                        bgcolor="white", border_visible=True)

        img_plot.overlays.append(overlay)
        self.plot = plot



# Enthought imports.
from traits.api import HasTraits, Instance, Property, Enum
from traitsui.api import View, Item, HSplit, VSplit, InstanceEditor
#from tvtk.pyface.scene_editor import SceneEditor
from mayavi.core.ui.engine_view import EngineView
#from mayavi.tools.mlab_scene_model import MlabSceneModel
from mayavi.core.ui.api import MayaviScene, MlabSceneModel, \
    SceneEditor

######################################################################
class ThreeDPointViewer(BaseViewer):
    class_name = 'ThreeDPointViewer'
    # The scene model.
    scene = Instance(MlabSceneModel, ())
    #plot = Instance()
    # The mayavi engine view.
    engine_view = Instance(EngineView)
    working = Bool(False)
    measurements = List(BaseMeasurement)
    measurement = Instance(BaseMeasurement)
    positions = Array
    opacity = Float(0.05)
    mode = Enum('cube',['cube','2dsquare','2dcircle','sphere'])
    show = Button('Show')

    ######################
    view = View(VGroup(
        HGroup(
            Item(name='measurement', label='Measurement',editor=EnumEditor(name='measurements')),
            Item(name='opacity', label='Opacity', ),
            Item(name='mode', label='Mode', ),
            Item(name='show',show_label=False),
        ),

        Item(name='scene',
             editor=SceneEditor(scene_class=MayaviScene),
             show_label=False,
             resizable=True,
             height=500,
             width=500),
    ),

                resizable=True,
                scrollable=True
                )

    def __init__(self, **traits):
        HasTraits.__init__(self, **traits)
        #self.engine_view = EngineView(engine=self.scene.engine)
        self.plot = None

    @on_trait_change('scene.activated,show')
    def plot_measurement(self):
        #self.working = True
        if self.measurement is None:
            return
        if self.positions is None:
            return
        self.scene.mlab.clf()
        x = self.positions[:,:,:,0]
        y = self.positions[:,:,:,1]
        z = self.positions[:,:,:,2]
        s = self.measurement.results
        self.plot = self.scene.mlab.points3d(x, y, z, s,scale_mode='none',
                                             mode=self.mode, #colormap='YlOrRd',
                                             transparent=True,
                                             figure=self.scene.mayavi_scene,
                                             opacity=self.opacity,scale_factor=0.01)
        self.plot.glyph.glyph.clamping = False
        #self.scene.disable_render = True
        #self.working = False

    #@on_trait_change('measurement, positions')
    def update_data(self):
        if self.working:
            return
        self.working = True
        if self.plot is None:
            return
        x = self.positions[:,:,:,0]
        y = self.positions[:, :, :, 1]
        z = self.positions[:, :, :, 2]
        s = self.measurement.results
        self.plot.mlab_source.set(x=x, y=y, z=z, scalars=s)
        self.scene.reset_zoom()
        self.working = False

    def __repr__(self):
        return self.class_name

    def __str__(self):
        return self.class_name


if __name__=='__main__':
    im_view = ThreeDPointViewer()
    im_view.configure_traits()



    """
     import numpy as np

    min_x = -10
    max_x = 10
    min_y = 3
    max_y = 10
    npts_x = 50
    npts_y = 50
    xs = np.linspace(min_x, max_x, npts_x + 1)
    ys = np.linspace(min_y, max_y, npts_y + 1)

    # The grid of points at which we will evaluate the 2D function
    # is located at cell centers, so use halfsteps from the
    # min/max values (which are edges)
    xstep = (max_x - min_x) / npts_x
    ystep = (max_y - min_y) / npts_y
    gridx = np.linspace(min_x + xstep / 2, max_x - xstep / 2, npts_x)
    gridy = np.linspace(min_y + xstep / 2, max_y - xstep / 2, npts_y)
    x, y = np.meshgrid(gridx, gridy)
    zs = np.cos(x+y)
    viewer = TwoDScalarInspector(xs=xs, ys=ys, zs=zs)
    viewer.minz = zs.min()
    viewer.maxz = zs.max()
    viewer.configure_traits()


    """
