from traits.api import *
from traitsui.api import *
from chaco.chaco_plot_editor import ChacoPlotItem
import logging
import numpy as np
from enum import Enum as PyEnum
from xyz_navigator import XYZNavigator
from constants import UpdateDataMode

from numpy import array,errstate

# Enthought library imports
from chaco.api import ArrayPlotData, ColorBar, ContourLinePlot, \
    ContourPolyPlot, DataRange1D, VPlotContainer, \
    DataRange2D, GridMapper, GridDataSource, \
    HPlotContainer, ImageData, LinearMapper, \
    OverlayPlotContainer, Plot, PlotAxis, GridPlotContainer
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



# Enthought library imports
from enable.api import Component, ComponentEditor
from traits.api import HasTraits, Instance
from traitsui.api import Item, Group, View

# Chaco imports
from chaco.api import ArrayPlotData, jet, Plot, YlOrRd
from chaco.default_colors import cbrewer
from chaco.tools.api import PanTool, ZoomTool, PointMarker,DrawPointsTool
from chaco.tools.cursor_tool import CursorTool, BaseCursorTool
from chaco.tools.image_inspector_tool import ImageInspectorTool, \
     ImageInspectorOverlay


def cmap_constant_range(cmap, drange):
    def new(range, **traits):
        return cmap(drange,**traits)
    return new

from pyface.api import FileDialog, CANCEL
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
            data = { 'data': info.object.data}
            # data['xbounds'] = np.array(info.object.xbounds)
            # if hasattr(info.object, 'yaxis') and info.object.yaxis:
            #     data['ybounds'] = np.array(info.object.ybounds)
            # if hasattr(info.object, 'zaxis') and info.object.zaxis:
            #     data['zbounds'] = np.array(info.object.calc_bounds(info.object.zaxis))
            np.savez(fileDialog.path, **data)


class BaseViewer(HasTraits):
    ndim = Int(0)
    handles_ndim = List([]) # what dimesions can viewer handles
    positions = Property(Array)
    data = Array
    shape = Property()
    max_size = Int(1000)
    save = Button('Save view')
    title = Str('Measurment')
    #default_mode = Enum(UpdateDataMode.REPLACE,[m for m in UpdateDataMode])

    def _get_shape(self):
        if self.data is not None:
            return self.data.shape
        else:
            return (0,)*self.ndim

    def set_data(self, new_data, idx=0):
        if idx:
            self.data[idx] = new_data
        else:
            self.data = new_data
        self.refresh()

    def refresh(self):
        pass

    def _get_positions(self):
        return np.array([0,1])

class OneDViewer(BaseViewer):
    """ This class just contains the two data arrays that will be updated
    by the Controller.  The visualization/editor for this class is a
    Chaco plot.
    """
    #mode = Enum(['Rolling','Replace'])
    #positions = Array()
    #max_num_points = Int(1000)
    ndim = Int(1)
    num_ticks = Int(0)
    resolution = Float(1.)
    start_pos = Float(0.)
    csr_pos = Array
    pd = Instance(ArrayPlotData,transient=True)
    plot = Any()
    #data = Array()
    #xbounds = Property(property_depends_on='index, start_pos, resolution')



    traits_view = View(

        Item('plot', editor=ComponentEditor(), show_label=False),
        #HGroup(spring, Item("plot_type", style='custom'), spring),
        resizable=True,

        )
    def __init__(self, *args,**kargs):
        super(OneDViewer, self).__init__( *args,**kargs)
        self.create_plot_element()

    def set_data(self, new_data, idx=None):
        if idx:
            self.data[idx] = new_data
            self.csr_pos = idx
        else:
            self.data = new_data
            self.csr_pos = np.array([0])
        self.refresh()

    def _data_default(self):
        return np.full((self.max_size,), np.nan)

    def _csr_pos_default(self):
        return np.array([0])

    def create_plot_element(self):
        self.pd = ArrayPlotData(x=np.arange(self.data.size),
                                y=self.data,

                                posx=self.csr_pos,
                                posy=np.array([self.data[self.csr_pos]]))

        plot = Plot(self.pd)
        plot.plot(("x", "y"),
                  #type_trait="plot_type",
                     #type='line_scatter_1d',
                              #resizable='',
                              title='',
                              #x_label="Time",
                              y_label="Signal",
                              color=tuple(cbrewer[np.random.randint(0,10)]),
                              bgcolor="grey",
                              border_visible=True,
                              border_width=1,
                              #padding_bg_color="lightgray",
                              width=800,
                              height=380,
                              marker_size=2,
                              show_label=False)

        plot.plot_1d("posx",
                             #type="scatter",
                     type="line_scatter_1d",
                             name="dot",
                            color="red",
                             #color_mapper=self._cmap(image_value_range),
                             marker="circle",
                             marker_size=4)
        self.pd.set_data('x', np.arange(self.data.size))
        self.pd.set_data('y', self.data)
        self.pd.set_data('posx', self.csr_pos)
        self.pd.set_data('posy', np.array([self.data[self.csr_pos]]))

        self.plot = plot

    def refresh(self):

        if self.data.size == self.pd.get_data('y').size:
            self.pd.set_data('x', np.arange(self.data.size))
            self.pd.set_data('y', self.data)
            self.pd.set_data('posx', self.csr_pos)
            self.pd.set_data('posy', np.array([self.data[self.csr_pos]]))
        else:
            self.create_plot_element()




                # def _data_changed(self,old, new):
    #     if old is None:
    #         self.create_plot_element()
    #         return
    #     if new is None:
    #         return
    #
    #     if new.shape==old.shape:
    #         self.pd.set_data('y', self.data)
    #     else:
    #         self.create_plot_element()

    #def _plot_default(self):
        #return self.create_plot_element()


    # @on_trait_change('data, resolution, start_pos')
    # def update_positions(self):
    #     if self.data is not None:
    #         return np.linspace(self.start_pos, self.start_pos+self.data.size * self.resolution, self.data.size)
    #     else:
    #         return (0.,1.)

    @property_depends_on('data[]')
    def _get_positions(self):
        if self.data is not None:
            return np.arange(self.data.size)
        else:
            return np.array([0,1])


class OneDViewerFilled(BaseViewer):
    xsource = Any
    ysource = Any
    plot = Instance(Component)

    traits_view = View(
        Group(
            Item('plot', editor=ComponentEditor(),
                 show_label=False),
            orientation="vertical"),
        resizable=True,
        #width=size[0], height=size[1]
    )

    def set_data(self, new_data, idx=None):
        if idx:
            self.data[idx] = new_data
            self.csr_pos = idx
        else:
            self.data = new_data
            self.csr_pos = np.array([0])
        self.refresh()

    def _data_default(self):
        return np.full((self.max_size,), np.nan)

    def _csr_pos_default(self):
        return np.array([0])

    def _plot_default(self):
        return self._create_plot_component()

    def refresh(self):
        if self.data.size == self.xsource.index_dimension:
            self.xsource.set_data(np.arange(self.data.size))
            self.ysource.set_data(self.data)
            #self.pd.set_data('posx', self.csr_pos)
            #self.pd.set_data('posy', np.array([self.data[self.csr_pos]]))
        else:
            self.plot = self._create_plot_component()

    def _create_plot_component(self):
        from numpy import abs, cumprod, random


        # Chaco imports
        from chaco.api import ArrayDataSource, BarPlot, DataRange1D, \
            LinearMapper, VPlotContainer, PlotAxis, \
            FilledLinePlot, add_default_grids, PlotLabel
        from chaco.tools.api import PanTool, ZoomTool

        from chaco.scales.api import CalendarScaleSystem, ScaleSystem
        from chaco.scales_tick_generator import ScalesTickGenerator

        # Create the data and datasource objects
        # In order for the date axis to work, the index data points need to
        # be in units of seconds since the epoch.  This is because we are using
        # the CalendarScaleSystem, whose formatters interpret the numerical values
        # as seconds since the epoch.
        numpoints = self.data.size
        index = np.arange(self.data.size)

        self.xsource = ArrayDataSource(index)
        #vol_ds = ArrayDataSource(volume, sort_order="none")
        self.ysource = ArrayDataSource(self.data, sort_order="none")

        xmapper = LinearMapper(range=DataRange1D(self.xsource))
        #vol_mapper = LinearMapper(range=DataRange1D(vol_ds))
        meas_mapper = LinearMapper(range=DataRange1D(self.ysource))

        price_plot = FilledLinePlot(index=self.xsource, value=self.ysource,
                                    index_mapper=xmapper,
                                    value_mapper=meas_mapper,
                                    edge_color=tuple(cbrewer[0]),
                                    face_color="paleturquoise",
                                    bgcolor="gray",
                                    border_visible=True)
        price_plot.overlays.append(PlotAxis(price_plot, orientation='left')),

        # Set the plot's bottom axis to use the Scales ticking system
        # bottom_axis = PlotAxis(price_plot, orientation="bottom",  # mapper=xmapper,
        #                        tick_generator=ScalesTickGenerator(scale=ScaleSystem()))
        # price_plot.overlays.append(bottom_axis)
        # hgrid, vgrid = add_default_grids(price_plot)
        # vgrid.tick_generator = bottom_axis.tick_generator
        #
        # price_plot.tools.append(PanTool(price_plot, constrain=True,
        #                                 constrain_direction="x"))
        # price_plot.overlays.append(ZoomTool(price_plot, drag_button="right",
        #                                     always_on=True,
        #                                     tool_mode="range",
        #                                     axis="index",
        #                                     max_zoom_out_factor=10.0,
        #                                     ))




        container = VPlotContainer(bgcolor="lightblue",
                                   spacing=40,
                                   padding=50,
                                   fill_padding=False)

        container.add(price_plot)
        container.overlays.append(PlotLabel(self.title,
                                            component=container,
                                            # font="Times New Roman 24"))
                                            ))

        return container


def format_pos( pos):
    return 'X: %.6f  Y: %.6f' %pos

class TwoDViewer(BaseViewer):
    name = Str('TwoDViewer')
    ndim = Int(2)
    pd = Instance(ArrayPlotData, transient=True)
    title = Str('')
    plot = Instance(Component, transient=True)
    max_size = 100
    cursor = Instance(BaseCursorTool,transient=True)
    cursor_pos = DelegatesTo('cursor', prefix='current_position')
    cursor_idx = DelegatesTo('cursor', prefix='current_index')
    xpos = Property()
    ypos = Property()

    data = Array()
    xaxis = Int(0)
    yaxis = Int(1)
    dims = Property()

    start_pos = List([0.,0.], editor=TupleEditor(cols=2, labels=['X','Y']))
    resolution = List([1.,1.], editor=TupleEditor(cols=2, labels=['X','Y']))
    xbounds = Property(depends_on='xaxis')
    ybounds = Property(depends_on='yaxis')
    transpose = Bool(False)
    rotate = Enum(0,[0,90,180,270])

    colormap = Enum('hot',colormaps)
    rev_cmap = Bool(False)

    view = View(
        VGroup(

            HGroup(
                Item('cursor_pos',label='Cursor',style='readonly',format_func=format_pos),
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
        handler=ArraySavehandler,
        #resizable=True,
    )

    def __init__(self,*args,**kwargs):
        super(TwoDViewer, self).__init__(*args,**kwargs)
        self.create_plot_component()


    def _data_default(self):
        return np.random.rand(self.max_size,self.max_size)

    def _get_xpos(self):
        return self.cursor_pos[self.xaxis]

    def _get_ypos(self):
        return self.cursor_pos[self.yaxis]


    def _get_xbounds(self):
        return self.start_pos[self.xaxis], self.data.shape[self.xaxis]*self.resolution[self.xaxis]

    def _get_ybounds(self):
        return self.start_pos[self.yaxis], self.data.shape[self.yaxis]*self.resolution[self.yaxis]

    def fxydata(self):
        data = self.data
        if self.transpose:
            data = data.T
        if self.rotate:
            data = np.rot90(data,int(self.rotate//90))
        return data

    def refresh(self):
        self.update_data()

    @on_trait_change('transpose, rotate')
    def update_data(self):
        self.pd.set_data("imagedata", self.fxydata())

    @on_trait_change('data, colormap, rev_cmap')
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


class XYSliceBrowser(BaseViewer):
    class_name = 'XYSliceBrowser'
    ndim = Int(3)
    pd = Instance(ArrayPlotData,transient=True)
    title = Str('')
    plot = Instance(Component,transient=True)
    max_size = 10
    save = Button('Save Data')

    cursor = Instance(BaseCursorTool,transient=True)
    cursor_pos = DelegatesTo('cursor', prefix='current_position')
    cursor_idx = DelegatesTo('cursor', prefix='current_index')
    xpos = Property()
    ypos = Property()

    data = Array()
    xaxis = Enum(2,[0,1,2])
    yaxis = Enum(1, [0,1,2])
    zaxis = Enum(0, [0,1,2])

    start_pos = List([0.,0.,0.], editor=TupleEditor(cols=3, labels=['X','Y','Z']))
    resolution = List([1.,1.,1.], editor=TupleEditor(cols=3, labels=['X','Y','Z']))

    xbounds = Property(depends_on='xaxis')
    ybounds = Property(depends_on='yaxis')

    zmin = Property(Float,depends_on='zaxis')
    zmax = Property(Float,depends_on='zaxis')

    zpos = Float()


    colormap = Enum('hot',colormaps)
    rev_cmap = Bool(False)

    view = View(
        VGroup(

            Group(
                Item('plot', editor=ComponentEditor(), width=-500, height=-400,
                     show_label=False),
            ),
            HGroup(
                Item('zpos', label='Z slice',  # width=200,
                     editor=RangeEditor(low_name='zmin', high_name='zmax')),
            ),
            HGroup(
                Item('cursor_pos',label='Cursor',style='readonly',format_func=format_pos),
                spring,
                Item(name='save', show_label=False),
            ),

            HGroup(
                HGroup(
                    Item('colormap', show_label=False, ),
                    Item('rev_cmap', label='Reverse', ),
                    spring,
                    label='Colormap', show_border=True, show_left=False, ),

                HGroup(
                    Item('xaxis', label='X', width=-50),
                    Item('yaxis', label='Y', width=-50),
                    Item('zaxis', label='Z', width=-50),
                    label='Axes', show_border=True),
                ),

        ),
        handler=ArraySavehandler,
        #resizable=True,
    )

    def __init__(self,*args,**kwargs):
        super(XYSliceBrowser, self).__init__(*args,**kwargs)
        self.create_plot_component()


    def _data_default(self):
        return np.random.rand(self.max_size,self.max_size, self.max_size)

    def _get_xpos(self):
        return self.cursor_pos[self.xaxis]

    def _get_ypos(self):
        return self.cursor_pos[self.yaxis]

    def _get_zmin(self):
        return  self.start_pos[self.zaxis]

    def _get_zmax(self):
        return self.zmin + (self.data.shape[self.zaxis]-1)*self.resolution[self.zaxis]


    def _get_xbounds(self):
        return self.start_pos[self.xaxis], self.data.shape[self.xaxis]*self.resolution[self.xaxis]

    def _get_ybounds(self):
        return self.start_pos[self.yaxis], self.data.shape[self.yaxis]*self.resolution[self.yaxis]


    def fxydata(self):
        if self.data is None:
            return np.zeros((100, 100))
        if self.data.ndim==3:
            sl = [slice(None)]*3
            sl[self.zaxis] = int(self.zpos*self.resolution[self.zaxis])
            return self.data[sl]

    def refresh(self):
        self.update_data()

    @on_trait_change('zpos')
    def update_data(self):
        self.pd.set_data("imagedata", self.fxydata())

    @on_trait_change('data, xaxis, yaxis, zaxis, colormap, rev_cmap')
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
    container = Instance(GridPlotContainer,transient=True)
    shape = Tuple()

    cursor = Instance(BaseCursorTool, transient=True)
    cursor_pos = DelegatesTo('cursor', prefix='current_position')
    cursor_value = Float()
    #cursor_idx = DelegatesTo('cursor', prefix='current_idx')
    xpos = Property()
    ypos = Property()
    autoscale = Bool(True)

    save = Button('Save')

    data = Array()
    xaxis = Enum(0, [0, 1])
    yaxis = Enum(1, [0, 1])
    zaxis = None

    start_pos = Tuple((0.,0.),cols=2, labels=['X','Y'])
    resolution = Tuple((1.,1.),cols=2, labels=['X','Y'])
    xbounds = Property(depends_on='xaxis,data, start_pos,resolution')
    ybounds = Property(depends_on='yaxis,data, start_pos,resolution')
    colormap = Enum('hot', colormaps)
    rev_cmap = Bool(False)

    view = View(
        VGroup(spring,
               HGroup(Item(name='autoscale', label='Autoscale'), spring,
                      Item(name='cursor_value', show_label=False, style='text', enabled_when='False'),
                      show_left=False),
            HGroup(
                spring,
                Item('container', editor=ComponentEditor(), #width=450,height=400,
                     show_label=False),
                spring,
                ),
        spring),
        handler=ArraySavehandler,
        resizable=True,
    )

    def __init__(self,*args,**kwargs):
        super(ImageViewer, self).__init__(*args, **kwargs)
        self.create_plot_component()

    def _data_default(self):
        return np.random.random((1280, 1024))

    def _get_xpos(self):
        return self.cursor_pos[self.xaxis]

    def _get_ypos(self):
        return self.cursor_pos[self.yaxis]

    def _get_xbounds(self):
        if len(self.data.shape)>self.xaxis:
            return self.start_pos[self.xaxis], self.data.shape[self.xaxis]*self.resolution[self.xaxis]
        else:
            return (0.,1.)

    def _get_ybounds(self):
        if len(self.data.shape)>self.yaxis:
            return self.start_pos[self.yaxis], self.data.shape[self.yaxis]*self.resolution[self.yaxis]
        else:
            return (0.,1.)

    @on_trait_change('data,cursor_idx')
    def update_data(self):
        #pos = self.cursor
        if self.shape == self.data.shape:
            csr_idx = tuple(self.cursor.current_index)
            self.pd.set_data("imagedata", self.data)
            self.pd.set_data("left_line", self.data[:, csr_idx[0]])
            self.pd.set_data("top_line", self.data[csr_idx[1], :])
            self.cursor_value = self.data[csr_idx[1], csr_idx[0]]
            return
        else:
            self.create_plot_component()

    """
    @on_trait_change('data, xaxis, yaxis, rev_colormap, colormap')
    def create_plot_component(self):# Create a scalar field to colormap
        # Create the plot
        if not self.data.size:
            return

        if self.shape==self.data.shape:
            self.pd.set_data("imagedata", self.data)
            return
        self.pd = ArrayPlotData()
        self.shape = self.data.shape
        self.pd.set_data("imagedata", self.data)
        plot = Plot(self.pd)
        cmap = default_colormaps.color_map_name_dict[self.colormap]
        if self.rev_cmap:
            cmap = default_colormaps.reverse(cmap)
        img_plot = plot.img_plot("imagedata",
                                 colormap=cmap,
                                 #xbounds=self.xbounds,
                                 #ybounds=self.ybounds,
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

        csr.current_index = self.shape[0]//2, self.shape[1]//2
        img_plot.overlays.append(csr)

        imgtool = ImageInspectorTool(img_plot)
        img_plot.tools.append(imgtool)

        overlay = ImageInspectorOverlay(component=img_plot, image_inspector=imgtool,
                                        bgcolor="white", border_visible=True)

        img_plot.overlays.append(overlay)
        self.plot = plot
    """
    @on_trait_change('autoscale')
    def change_cmap(self):
        if not self.img_plot:
            return
        if self.autoscale:
            cmap = self.cmap
        else:
            cmap = self.ccmap
        self.img_plot.value_mapper = cmap

    @on_trait_change('xaxis,yaxis,rev_colormap,colormap')
    def create_plot_component(self):
        if not self.data.size:
            return

        self.pd = ArrayPlotData()
        self.shape = self.data.shape
        self.pd.set_data("imagedata", self.data)
        self.pd.set_data("left_line", self.data[:, self.shape[0]//2])
        self.pd.set_data("top_line", self.data[self.shape[1]//2,:])

        plot = Plot(self.pd)
        cmap = default_colormaps.color_map_name_dict[self.colormap]

        if self.rev_cmap:
            cmap = default_colormaps.reverse(cmap)

        drange = DataRange1D(ImageData(data=self.data, value_depth=1))



        self.ccmap = cmap_constant_range(cmap, drange)(drange)

            #from copy import copy
        self.img_plot = plot.img_plot("imagedata",
                                 colormap=cmap,
                                 #xbounds=self.xbounds,
                                 #ybounds=self.ybounds,
                                 )[0]
        self.cmap = self.img_plot.value_mapper
        if not self.autoscale:
            self.img_plot.value_mapper = self.ccmap
        # Tweak some of the plot properties
        plot.title = self.title
        plot.padding = 10

        # Attach some tools to the plot
        plot.tools.append(PanTool(plot))
        zoom = ZoomTool(component=plot, tool_mode="box", always_on=False)
        plot.overlays.append(zoom)

        csr = CursorTool(self.img_plot,
                          drag_button='right',
                          color='white',
                          line_width=2.0
                          )
        self.cursor = csr

        csr.current_index = self.shape[0]//2, self.shape[1]//2
        self.img_plot.overlays.append(csr)

        imgtool = ImageInspectorTool(self.img_plot)
        self.img_plot.tools.append(imgtool)

        overlay = ImageInspectorOverlay(component=self.img_plot, image_inspector=imgtool,
                                        bgcolor="white", border_visible=True)

        self.img_plot.overlays.append(overlay)
        self.plot = plot

        self.cross_plot = Plot(self.pd,resizable='h')
        self.cross_plot.height = 40
        self.cross_plot.padding = 15
        self.cross_plot.plot("top_line",
                             line_style="dot")


        self.cross_plot.index_range = self.img_plot.index_range.x_range


        self.cross_plot2 = Plot(self.pd, width=40, orientation="v",
                                padding=15, padding_bottom=10, resizable='v')
        self.cross_plot2.plot("left_line",
                              line_style="dot")


        self.cross_plot2.index_range = self.img_plot.index_range.y_range

        # Create a container and add components
        #self.container = HPlotContainer(padding=10, fill_padding=False,
        #                                bgcolor="none", use_backbuffer=False)
        #inner_cont = VPlotContainer(padding=0, use_backbuffer=True, bgcolor="none")
        #inner_cont.add(self.plot)
        #inner_cont.add(self.cross_plot)
        self.container = GridPlotContainer(padding=20, fill_padding=False,
                                      bgcolor="none", use_backbuffer=True,
                                      shape=(2, 2), spacing=(12, 20))

        #self.container.add(self.colorbar)
        self.container.add(self.plot)
        self.container.add(self.cross_plot2)
        self.container.add(self.cross_plot)
        #self.container.add(inner_cont)


class ImageCollectionBrowser(BaseViewer):
    naxes = Int(3)
    axes = List()
    position = List()
    slicer = List()
    data = Array
    navigate = Button('Navigate')
    navigator = Instance(XYZNavigator)
    img_viewer = Instance(ImageViewer)
    traits_view = View(
        VGroup(spring,
               HGroup(
                   Item(name='navigate',show_label=False),
                   spring,
                   Item(name='save',show_label=False),
               ),

               HGroup(
                   spring,

                   Item('img_viewer', style='custom',
                        show_label=False),
                   spring,
               ),
               spring),
        handler=ArraySavehandler,
        resizable=True,
    )
    def _navigator_default(self):
        return XYZNavigator(controller=self)

    def _img_viewer_default(self):
        return ImageViewer()

    def _data_changed(self, new):
        ndim = len(np.asarray(new).shape)
        self.naxes = ndim-2
        not_nans = np.where(~np.isnan(self.data))
        if np.any(not_nans):
            self.slicer = [not_nans[d][0] for d in range(ndim)]
        else:
            self.slicer = [0]*ndim
        self.slicer[-2:] = slice(None), slice(None)
        self.position = self.data[self.slicer[:-2]]

    def _navigate_fired(self):
        self.navigator.edit_traits(view='button_view')

    @on_trait_change('position[]')
    def update_data(self):
        if self.position:
            self.slicer[:-2] = self.position
            self.img_viewer.data = self.data[self.slicer]

    def move_rel(self, ax, stp):
        if ax<=self.naxes:
            next_pos = self.position[ax-1] + int(stp/abs(stp))
            if next_pos<self.data.shape(ax-1):
                self.position[ax-1] = next_pos
            else:
                self.position[ax-1] = 0


# Enthought imports.
from traits.api import HasTraits, Instance, Property, Enum
from traitsui.api import View, Item, HSplit, VSplit, InstanceEditor
#from tvtk.pyface.scene_editor import SceneEditor
# from mayavi.core.ui.engine_view import EngineView
# #from mayavi.tools.mlab_scene_model import MlabSceneModel
# from mayavi.core.ui.api import MayaviScene, MlabSceneModel, \
#     SceneEditor
# 
# ######################################################################
# class ThreeDPointViewer(BaseViewer):
#     class_name = 'ThreeDPointViewer'
#     # The scene model.
#     scene = Instance(MlabSceneModel, ())
#     #plot = Instance()
#     # The mayavi engine view.
#     engine_view = Instance(EngineView)
#     working = Bool(False)
#     data = Array
#     positions = Array
#     opacity = Float(0.05)
#     mode = Enum('cube',['cube','2dsquare','2dcircle','sphere'])
#     show = Button('Show')
# 
#     ######################
#     view = View(VGroup(
#         HGroup(
# 
#             Item(name='opacity', label='Opacity', ),
#             Item(name='mode', label='Mode', ),
#             Item(name='show',show_label=False),
#         ),
# 
#         Item(name='scene',
#              editor=SceneEditor(scene_class=MayaviScene),
#              show_label=False,
#              resizable=True,
#              height=500,
#              width=500),
#     ),
# 
#                 resizable=True,
#                 scrollable=True
#                 )
# 
#     def __init__(self, **traits):
#         HasTraits.__init__(self, **traits)
#         #self.engine_view = EngineView(engine=self.scene.engine)
#         self.plot = None
# 
#     @on_trait_change('scene.activated,show')
#     def plot_measurement(self):
#         #self.working = True
#         if self.measurement is None:
#             return
#         if self.positions is None:
#             return
#         self.scene.mlab.clf()
#         x = self.positions[:,:,:,0]
#         y = self.positions[:,:,:,1]
#         z = self.positions[:,:,:,2]
#         s = self.data
#         self.plot = self.scene.mlab.points3d(x, y, z, s,scale_mode='none',
#                                              mode=self.mode, #colormap='YlOrRd',
#                                              transparent=True,
#                                              figure=self.scene.mayavi_scene,
#                                              opacity=self.opacity,scale_factor=0.01)
#         self.plot.glyph.glyph.clamping = False
#         #self.scene.disable_render = True
#         #self.working = False
# 
#     #@on_trait_change('measurement, positions')
#     def update_data(self):
#         if self.working:
#             return
#         self.working = True
#         if self.plot is None:
#             return
#         x = self.positions[:,:,:,0]
#         y = self.positions[:, :, :, 1]
#         z = self.positions[:, :, :, 2]
#         s = self.measurement.results
#         self.plot.mlab_source.set(x=x, y=y, z=z, scalars=s)
#         self.scene.reset_zoom()
#         self.working = False
# 
#     def __repr__(self):
#         return self.class_name
# 
#     def __str__(self):
#         return self.class_name

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
if __name__=='__main__':
    app = OneDViewer()
    app.configure_traits()